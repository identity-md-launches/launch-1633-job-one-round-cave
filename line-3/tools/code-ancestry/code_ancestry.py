#!/usr/bin/env python3
"""Link an Ethereum code proof to a later, caller-chosen execution checkpoint."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'code-proof'))
import code_proof as proof

lens = proof.lens
require = lens.require
SCHEMA = 'code-ancestry-v1'
MAX_LINKS = 32


def keys(value, expected, label):
    require(isinstance(value, dict) and set(value) == set(expected),
            'missing or extra ' + label + ' fields')


def block_identity(value):
    keys(value, ('number', 'hash'), 'block')
    number = lens.quantity(value['number'])
    require(number < 2**64, 'block number exceeds uint64')
    return {'number': hex(number), 'hash': lens.fixed_hex(value['hash'], 32)}


def header_identity(encoded):
    raw = proof.hex_bytes(encoded)
    fields = proof.rlp_decode(raw)
    require(isinstance(fields, list) and len(fields) in proof.HEADER_COUNTS,
            'unsupported header fork field count')
    block = block_identity({'number': hex(proof.scalar(fields[8])), 'hash': lens.digest(raw)})
    proof.verify_header(encoded, block)
    return block, fields


def verify(bundle, ancestry, expected_checkpoint=None):
    """No embedded field can grant trust: only the separate argument pins a hash."""
    keys(ancestry, ('schema', 'chain_id', 'start', 'checkpoint', 'headers', 'provenance'), 'ancestry')
    require(ancestry['schema'] == SCHEMA and type(ancestry['chain_id']) is int
            and ancestry['chain_id'] == 1, 'wrong ancestry schema or chain')
    provenance = ancestry['provenance']
    keys(provenance, ('source', 'transport_source', 'source_kind'), 'provenance')
    lens.provenance({'schema': lens.CURRENT_SCHEMA, **provenance})
    start = block_identity(ancestry['start'])
    checkpoint = block_identity(ancestry['checkpoint'])
    headers = ancestry['headers']
    require(isinstance(headers, list) and 1 <= len(headers) <= MAX_LINKS,
            'ancestry must contain 1 to 32 descendant headers')
    require(lens.quantity(checkpoint['number']) - lens.quantity(start['number']) == len(headers),
            'checkpoint distance does not match header count')
    require(start == block_identity(bundle['observation']['block']), 'proof and ancestry start differ')
    current, fields = header_identity(bundle['header_rlp'])
    require(current == start, 'start header does not match proof block')
    timestamp = proof.scalar(fields[11])
    for encoded in headers:
        child, fields = header_identity(encoded)
        require(lens.quantity(child['number']) == lens.quantity(current['number']) + 1,
                'header heights are not consecutive')
        require('0x' + fields[0].hex() == current['hash'], 'broken parent hash link')
        next_timestamp = proof.scalar(fields[11])
        require(next_timestamp > timestamp, 'header timestamps are not increasing')
        current, timestamp = child, next_timestamp
    require(current == checkpoint, 'last header does not match checkpoint')
    if expected_checkpoint is not None:
        require(checkpoint['hash'] == lens.fixed_hex(expected_checkpoint, 32),
                'caller checkpoint hash does not match')
    checked = proof.verify(bundle)
    return {
        'schema': 'code-ancestry-result-v1', 'chain_id': 1,
        'target': checked['target'], 'code_block': start, 'checkpoint': checkpoint,
        'parent_links_verified': len(headers), 'state_inclusion_verified': True,
        'state_root': checked['state_root'], 'accounts': checked['accounts'],
        'anchor': 'caller-supplied-checkpoint-hash' if expected_checkpoint is not None
                  else 'unanchored-rpc-checkpoint',
        'checkpoint_hash_matched': expected_checkpoint is not None,
        'consensus_verified': False,
        'unproven_beacon_call_results': checked['unproven_beacon_call_results'],
        'proof_provenance': checked['provenance'], 'ancestry_provenance': provenance,
        'scope': 'Runtime and measured slots are proven at code_block, linked to checkpoint. '
                 'The caller must independently trust the checkpoint. This does not verify '
                 'consensus, finality, anchor authenticity, beacon call results, routing semantics, '
                 'contract safety, or code at the later checkpoint or today.',
    }


def collect(rpc, bundle, through_block, expected_checkpoint=None):
    """Read a bounded existing interval, fail on forks; never wait for a new block."""
    proof.verify(bundle)
    start = block_identity(bundle['observation']['block'])
    height = lens.quantity(start['number'])
    require(type(through_block) is int and 1 <= through_block - height <= MAX_LINKS,
            'checkpoint must be 1 to 32 blocks after proof')
    require(lens.quantity(rpc.call('eth_chainId', [])) == 1, 'endpoint is not Ethereum mainnet')

    def read_header(number):
        header = rpc.call('eth_getBlockByNumber', [hex(number), False])
        require(isinstance(header, dict), 'requested header is unavailable; no waiting or fallback')
        encoded = proof.encode_header(header)
        block, _ = header_identity(encoded)
        require(lens.quantity(block['number']) == number, 'RPC returned the wrong header height')
        return block, encoded

    # Observe the endpoint before collecting; all intermediate links are checked offline.
    checkpoint, _ = read_header(through_block)
    if expected_checkpoint is not None:
        require(checkpoint['hash'] == lens.fixed_hex(expected_checkpoint, 32),
                'caller checkpoint hash does not match')
    observed_start, _ = read_header(height)
    require(observed_start == start, 'RPC start conflicts with saved proof')
    headers = [read_header(number)[1] for number in range(height + 1, through_block + 1)]
    after, _ = read_header(through_block)
    require(after == checkpoint, 'checkpoint changed during collection')
    ancestry = {'schema': SCHEMA, 'chain_id': 1, 'start': start, 'checkpoint': checkpoint,
                'headers': headers, 'provenance': lens.collection_provenance(rpc)}
    verify(bundle, ancestry, expected_checkpoint)
    require(len(json.dumps(ancestry, indent=2).encode()) < lens.MAX_RESPONSE,
            'ancestry exceeds 100000 bytes')
    return ancestry


def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON key: ' + key)
        result[key] = value
    return result


def read_json(filename):
    path = Path(filename).resolve()
    require(path.is_relative_to(Path.cwd().resolve()), 'input must be inside workspace')
    with path.open('rb') as stream:
        raw = stream.read(lens.MAX_RESPONSE + 1)
    require(len(raw) <= lens.MAX_RESPONSE, 'input exceeds 100000 bytes')
    return json.loads(raw, object_pairs_hook=no_duplicates)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True, help='workspace Code Proof bundle')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--ancestry', help='workspace ancestry file; fully offline')
    mode.add_argument('--through-block', type=int, help='collect through this existing decimal block height')
    parser.add_argument('--rpc', default=lens.PUBLIC_RPC)
    parser.add_argument('--expect-checkpoint-hash', help='independently obtained execution block hash')
    parser.add_argument('--save-ancestry', help='new workspace file; collection only; no overwrite')
    args = parser.parse_args()
    try:
        require(not args.save_ancestry or args.through_block is not None,
                'saving is available only during collection')
        destination = None
        if args.save_ancestry:
            destination = Path(args.save_ancestry).resolve()
            require(destination.is_relative_to(Path.cwd().resolve()), 'output must be inside workspace')
            require(not destination.exists(), 'output already exists')
        bundle = read_json(args.bundle)
        ancestry = read_json(args.ancestry) if args.ancestry else collect(
            lens.RPC(args.rpc), bundle, args.through_block, args.expect_checkpoint_hash)
        result = verify(bundle, ancestry, args.expect_checkpoint_hash)
        if destination:
            with destination.open('x', encoding='utf-8') as stream:
                stream.write(json.dumps(ancestry, indent=2) + '\n')
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, KeyError, TypeError, OSError, OverflowError, AttributeError,
            IndexError, RecursionError) as error:
        print('Code Ancestry: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
