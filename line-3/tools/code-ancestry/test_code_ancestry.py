"""Real saved-header replay plus explicitly synthetic adversarial chains."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import code_ancestry as tool

HERE = Path(__file__).resolve().parent
BUNDLES = HERE.parent / 'code-proof'


def bundle(token='zto'):
    return tool.read_json(BUNDLES / (token + '-proof.json'))


def saved():
    return tool.read_json(HERE / 'zto-ancestry.json')


def encode(fields):
    return '0x' + tool.proof.rlp_encode(fields).hex()


def synthetic(count=3, base=None):
    """Valid hashes and links, invented descendants: never a chain observation."""
    base = bundle() if base is None else base
    current, fields = tool.header_identity(base['header_rlp'])
    links = []
    for _ in range(count):
        fields[0] = bytes.fromhex(current['hash'][2:])
        fields[8] = tool.proof.integer_bytes(tool.lens.quantity(current['number']) + 1)
        fields[11] = tool.proof.integer_bytes(tool.proof.scalar(fields[11]) + 12)
        raw = encode(fields)
        links.append(raw)
        current, _ = tool.header_identity(raw)
    return {'schema': tool.SCHEMA, 'chain_id': 1, 'start': base['observation']['block'],
            'checkpoint': current, 'headers': links,
            'provenance': {'source': tool.lens.PUBLIC_RPC,
                           'transport_source': tool.lens.PUBLIC_RPC,
                           'source_kind': 'selected-public-endpoint'}}


def as_rpc_header(encoded):
    block, fields = tool.header_identity(encoded)
    header = {'hash': block['hash']}
    for value, (name, width) in zip(fields, tool.proof.HEADER_FIELDS):
        header[name] = hex(int.from_bytes(value, 'big')) if width is None else '0x' + value.hex()
    return header


class FakeRPC:
    endpoint = tool.lens.PUBLIC_RPC

    def __init__(self, base, ancestry):
        values = [base['header_rlp']] + ancestry['headers']
        self.headers = {as_rpc_header(raw)['number']: as_rpc_header(raw) for raw in values}
        self.calls = []
        self.chain = '0x1'
        self.change_after = None
        self.missing = None
        self.checkpoint = ancestry['checkpoint']['number']
        self.checkpoint_reads = 0

    def call(self, method, params):
        self.calls.append((method, copy.deepcopy(params)))
        if method == 'eth_chainId':
            return self.chain
        assert method == 'eth_getBlockByNumber'
        assert params[1] is False
        if params[0] == self.missing:
            return None
        if params[0] == self.checkpoint:
            self.checkpoint_reads += 1
        header = copy.deepcopy(self.headers[params[0]])
        if self.change_after and params[0] == self.checkpoint and self.checkpoint_reads >= self.change_after:
            header['extraData'] = '0x01'
            fields = [tool.proof.integer_bytes(tool.lens.quantity(header[name])) if width is None
                      else bytes.fromhex(header[name][2:])
                      for name, width in tool.proof.HEADER_FIELDS if name in header]
            header['hash'] = tool.lens.digest(tool.proof.rlp_encode(fields))
        return header


class AncestryTests(unittest.TestCase):
    def test_saved_real_zto_and_imd(self):
        for token in ('zto', 'imd'):
            result = tool.verify(bundle(token), saved())
            self.assertEqual(result['parent_links_verified'], 8)
            self.assertEqual(result['anchor'], 'unanchored-rpc-checkpoint')
            self.assertFalse(result['checkpoint_hash_matched'])
            self.assertFalse(result['consensus_verified'])
            self.assertTrue(result['state_inclusion_verified'])
            self.assertEqual(result['target'], {'zto': tool.lens.ZTO, 'imd': tool.lens.IMD}[token])
            self.assertEqual(result['unproven_beacon_call_results'], [])

    def test_separate_checkpoint_comparison_and_wrong_hash(self):
        chain = saved()
        result = tool.verify(bundle(), chain, chain['checkpoint']['hash'])
        self.assertEqual(result['anchor'], 'caller-supplied-checkpoint-hash')
        self.assertTrue(result['checkpoint_hash_matched'])
        self.assertFalse(result['consensus_verified'])
        with self.assertRaisesRegex(ValueError, 'caller checkpoint'):
            tool.verify(bundle(), chain, tool.lens.digest(b'wrong checkpoint'))

    def test_embedded_trust_claim_cannot_promote_anchor(self):
        for field in ('expected_checkpoint', 'trusted', 'anchor'):
            chain = saved()
            chain[field] = True
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'extra ancestry'):
                tool.verify(bundle(), chain)

    def test_linked_forgery_is_explicitly_unanchored(self):
        chain = synthetic()
        self.assertEqual(tool.verify(bundle(), chain)['anchor'], 'unanchored-rpc-checkpoint')
        with self.assertRaisesRegex(ValueError, 'caller checkpoint'):
            tool.verify(bundle(), chain, saved()['checkpoint']['hash'])

    def test_start_height_and_hash_must_match(self):
        for key, value in [('number', '0x1'), ('hash', tool.lens.digest(b'fork'))]:
            chain = saved()
            chain['start'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                tool.verify(bundle(), chain)

    def test_missing_extra_reordered_duplicate_headers(self):
        original = saved()
        headers = original['headers']
        for bad in (headers[:-1], headers[1:], headers + headers[-1:],
                    list(reversed(headers)), [headers[0]] * len(headers)):
            chain = copy.deepcopy(original)
            chain['headers'] = bad
            with self.subTest(count=len(bad)), self.assertRaises(ValueError):
                tool.verify(bundle(), chain)

    def test_parent_tampering_cannot_be_hidden_by_rehashing(self):
        chain = synthetic(1)
        _, fields = tool.header_identity(chain['headers'][0])
        fields[0] = tool.proof.keccak256(b'another parent')
        chain['headers'][0] = encode(fields)
        chain['checkpoint'], _ = tool.header_identity(chain['headers'][0])
        with self.assertRaisesRegex(ValueError, 'parent hash'):
            tool.verify(bundle(), chain, chain['checkpoint']['hash'])

    def test_nonconsecutive_heights_and_timestamp_rejected(self):
        for index in (8, 11):
            chain = synthetic(1)
            _, fields = tool.header_identity(chain['headers'][0])
            _, previous = tool.header_identity(bundle()['header_rlp'])
            fields[index] = previous[index]
            chain['headers'][0] = encode(fields)
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, 'consecutive|timestamps'):
                tool.verify(bundle(), chain)

    def test_checkpoint_hash_and_number_not_just_labels(self):
        for key, value in [('number', '0x1'), ('hash', tool.lens.digest(b'other checkpoint'))]:
            chain = saved()
            chain['checkpoint'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                tool.verify(bundle(), chain)

    def test_state_proof_is_reverified(self):
        base = bundle()
        base['proofs'][0]['accountProof'].pop()
        with self.assertRaises(ValueError):
            tool.verify(base, saved())

    def test_forged_runtime_with_self_consistent_hash_still_fails(self):
        base = bundle()
        node = base['observation']['nodes'][0]
        node.update(code='0x6000', code_bytes=2, code_hash=tool.lens.digest(b'\x60\x00'))
        base['observation']['effective_code_hash'] = node['code_hash']
        base['proofs'][0]['codeHash'] = node['code_hash']
        with self.assertRaisesRegex(ValueError, 'proven code hash'):
            tool.verify(base, saved())

    def test_beacon_call_limitation_survives_anchoring(self):
        sys.path.insert(0, str(BUNDLES))
        from test_code_proof import synthetic_beacon_bundle
        base = synthetic_beacon_bundle()
        chain = synthetic(1, base)
        result = tool.verify(base, chain, chain['checkpoint']['hash'])
        self.assertEqual(result['unproven_beacon_call_results'], [tool.lens.IMD])

    def test_bounds_and_malformed_headers(self):
        for headers in ([], saved()['headers'] * 5, 'not a list', ['0x'], ['0xc0']):
            chain = saved()
            chain['headers'] = headers
            with self.subTest(headers=str(headers)[:20]), self.assertRaises(ValueError):
                tool.verify(bundle(), chain)
        for raw in ('0x' + '00' * 2049, '0x81', '0xzz'):
            with self.assertRaises(ValueError):
                tool.header_identity(raw)

    def test_maximum_interval(self):
        self.assertEqual(tool.verify(bundle(), synthetic(32))['parent_links_verified'], 32)

    def test_unsupported_header_shape_and_noncanonical_scalar(self):
        _, original = tool.header_identity(bundle()['header_rlp'])
        for fields in (original[:18], [b'x'] + original[1:], original[:8] + [b'\x00'] + original[9:]):
            with self.assertRaises(ValueError):
                tool.header_identity(encode(fields))

    def test_wrong_chain_bool_chain_and_provenance_mismatch(self):
        for value in (True, 8453, '1'):
            chain = saved()
            chain['chain_id'] = value
            with self.assertRaisesRegex(ValueError, 'chain'):
                tool.verify(bundle(), chain)
        chain = saved()
        chain['provenance']['source_kind'] = 'selected-public-endpoint'
        with self.assertRaisesRegex(ValueError, 'upstream'):
            tool.verify(bundle(), chain)

    def test_collection_reads_only_existing_explicit_heights(self):
        base, chain = bundle(), synthetic()
        rpc = FakeRPC(base, chain)
        result = tool.collect(rpc, base, int(chain['checkpoint']['number'], 16))
        self.assertEqual(result['headers'], chain['headers'])
        for method, params in rpc.calls:
            self.assertIn(method, ('eth_chainId', 'eth_getBlockByNumber'))
            if method == 'eth_getBlockByNumber':
                self.assertTrue(params[0].startswith('0x'))
                self.assertFalse(params[1])

    def test_collection_refuses_bad_range_before_network(self):
        base, chain = bundle(), synthetic()
        height = int(chain['start']['number'], 16)
        for finish in (height - 1, height, height + 33, True):
            rpc = FakeRPC(base, chain)
            with self.assertRaisesRegex(ValueError, '1 to 32'):
                tool.collect(rpc, base, finish)
            self.assertEqual(rpc.calls, [])

    def test_collection_wrong_chain_missing_header_and_wrong_height(self):
        base, chain = bundle(), synthetic()
        end = int(chain['checkpoint']['number'], 16)
        rpc = FakeRPC(base, chain)
        rpc.chain = '0x2105'
        with self.assertRaisesRegex(ValueError, 'mainnet'):
            tool.collect(rpc, base, end)
        rpc = FakeRPC(base, chain)
        rpc.missing = chain['checkpoint']['number']
        with self.assertRaisesRegex(ValueError, 'unavailable'):
            tool.collect(rpc, base, end)
        rpc = FakeRPC(base, chain)
        rpc.headers[chain['checkpoint']['number']] = rpc.headers[chain['start']['number']]
        with self.assertRaisesRegex(ValueError, 'wrong header height'):
            tool.collect(rpc, base, end)

    def test_collection_detects_checkpoint_reorg(self):
        base, chain = bundle(), synthetic()
        rpc = FakeRPC(base, chain)
        rpc.change_after = 3
        with self.assertRaisesRegex(ValueError, 'changed during collection'):
            tool.collect(rpc, base, int(chain['checkpoint']['number'], 16))

    def test_collection_checks_expected_hash_before_interval(self):
        base, chain = bundle(), synthetic()
        rpc = FakeRPC(base, chain)
        with self.assertRaisesRegex(ValueError, 'caller checkpoint'):
            tool.collect(rpc, base, int(chain['checkpoint']['number'], 16), tool.lens.digest(b'wrong'))
        self.assertEqual(len(rpc.calls), 2)

    def test_cli_failure_has_no_partial_json(self):
        args = [sys.executable, '-B', str(HERE / 'code_ancestry.py'), '--bundle',
                str(BUNDLES / 'zto-proof.json'), '--ancestry', str(HERE / 'zto-ancestry.json'),
                '--expect-checkpoint-hash', tool.lens.digest(b'wrong')]
        result = subprocess.run(args, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, '')
        self.assertIn('caller checkpoint', result.stderr)

    def test_json_duplicate_keys_file_bounds_and_workspace_boundaries(self):
        scratch = Path.cwd() / 'test' / 'scratch'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            path = Path(directory) / 'bad.json'
            path.write_text('{"schema": "one", "schema": "two"}')
            with self.assertRaisesRegex(ValueError, 'duplicate JSON'):
                tool.read_json(path)
            path.write_bytes(b' ' * 100001)
            with self.assertRaisesRegex(ValueError, '100000'):
                tool.read_json(path)
            path.unlink()
            path.symlink_to(Path.cwd().parent / 'not-read')
            with self.assertRaisesRegex(ValueError, 'inside workspace'):
                tool.read_json(path)


if __name__ == '__main__':
    unittest.main()
