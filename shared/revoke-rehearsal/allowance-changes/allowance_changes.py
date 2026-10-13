#!/usr/bin/env python3
"""Compare ERC-20 permissions, or recheck a saved inventory without losing old pairs."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

# Reuse the reviewed ancestor's strict observation decoder and read-only client.
LENS_DIR = Path(__file__).resolve().parents[1] / 'allowance-lens'
sys.path.insert(0, str(LENS_DIR))
import allowance_lens as lens

BUNDLE_SCHEMA = 'allowance-changes-inventory-v1'
HERE = Path(__file__).resolve().parent
LIMIT = 98_304


def load(path):
    with lens.workspace_path(path).open('rb') as stream:
        data = stream.read(LIMIT + 1)
    lens.require(len(data) <= LIMIT, 'input exceeds 96 KiB')
    return json.loads(data)


def save(path, value):
    data = json.dumps(value, indent=2) + '\n'
    lens.require(len(data.encode()) <= LIMIT, 'output exceeds 96 KiB')
    with lens.workspace_path(path).open('x', encoding='utf-8') as stream:
        stream.write(data)


def flatten(value):
    """Validate raw evidence, then normalize a single observation or same-block bundle."""
    lens.require(isinstance(value, dict), 'expected observation or inventory object')
    if value.get('schema') == BUNDLE_SCHEMA:
        observations = value['observations']
        lens.require(isinstance(observations, list) and 1 <= len(observations) <= lens.MAX_PAIRS,
                     'inventory must contain 1..64 observations')
    else:
        observations = [value]
    reports = [lens.report(observation) for observation in observations]
    first = reports[0]
    identity = ('chain_id', 'token', 'token_address', 'decimals',
                'block_number', 'block_hash', 'block_time_utc')
    pairs, balances = {}, {}
    for report in reports:
        lens.require(all(report[key] == first[key] for key in identity),
                     'inventory observations must share chain, token, decimals and block')
        for row in report['pairs']:
            pair = (row['owner'], row['spender'])
            lens.require(pair not in pairs, 'duplicate inventory pair')
            pairs[pair] = row
            owner, balance = row['owner'], row['balance_raw']
            lens.require(owner not in balances or balances[owner] == balance,
                         'conflicting same-block owner balances')
            balances[owner] = balance
    lens.require(len(pairs) <= lens.MAX_PAIRS, 'inventory exceeds 64 pairs')
    return {**{key: first[key] for key in identity}, 'pairs': pairs,
            'sources': sorted({report['source'] for report in reports})}


def compare(before, after):
    old, new = flatten(before), flatten(after)
    lens.require(all(old[key] == new[key] for key in ('chain_id', 'token', 'token_address', 'decimals')),
                 'observations must have matching chain, token and decimals')
    lens.require(new['block_number'] >= old['block_number'], 'after block is older than before block')
    lens.require(new['block_time_utc'] >= old['block_time_utc'], 'after block timestamp predates before block')
    if new['block_number'] == old['block_number']:
        lens.require(new['block_hash'] == old['block_hash']
                     and new['block_time_utc'] == old['block_time_utc'],
                     'same-height block conflict')
    rows = []
    compared = set(old['pairs']) & set(new['pairs'])
    all_pairs = set(old['pairs']) | set(new['pairs'])
    for owner, spender in sorted(all_pairs):
        pair = (owner, spender)
        previous, current = old['pairs'].get(pair), new['pairs'].get(pair)
        row = {'owner': owner, 'spender': spender,
               'before': state(previous), 'after': state(current)}
        if previous is None:
            row['change'] = 'newly_observed'
        elif current is None:
            row['change'] = 'not_rechecked'
        else:
            a, b = int(previous['allowance_raw']), int(current['allowance_raw'])
            if old['block_number'] == new['block_number']:
                lens.require(row['before'] == row['after'], 'conflicting state at the same block')
            if a == b:
                change = 'unchanged'
            elif b == 0:
                change = 'became_zero'
            elif a == 0:
                change = 'became_active'
            else:
                change = 'increased' if b > a else 'decreased'
            row.update(change=change, allowance_delta_raw=str(b - a),
                       balance_delta_raw=str(int(current['balance_raw']) - int(previous['balance_raw'])),
                       spendable_delta_raw=str(int(current['spendable_upper_bound_raw'])
                                               - int(previous['spendable_upper_bound_raw'])))
        rows.append(row)
    owners = []
    # Only compare owner totals over the intersection, so coverage loss is not
    # accidentally presented as a reduction in permission or exposure.
    for owner in sorted({pair[0] for pair in compared}):
        keys = sorted(pair for pair in compared if pair[0] == owner)
        caps = []
        for observation in (old, new):
            balance = int(observation['pairs'][keys[0]]['balance_raw'])
            cap = min(balance, sum(int(observation['pairs'][key]['allowance_raw']) for key in keys))
            caps.append(cap)
        owners.append({'owner': owner, 'compared_pair_count': len(keys),
                       'before_combined_spendable_upper_bound_raw': str(caps[0]),
                       'after_combined_spendable_upper_bound_raw': str(caps[1]),
                       'delta_raw': str(caps[1] - caps[0])})
    return {
        'schema': 'allowance-changes-report-v1', 'chain_id': old['chain_id'],
        'token': old['token'], 'token_address': old['token_address'], 'decimals': old['decimals'],
        'before_block': block_summary(old), 'after_block': block_summary(new),
        'complete_wallet_audit': False,
        'coverage': {'before_pairs': len(old['pairs']), 'after_pairs': len(new['pairs']),
                     'compared_pairs': len(compared),
                     'all_previous_pairs_rechecked': set(old['pairs']) <= set(new['pairs'])},
        'counts': dict(sorted(Counter(row['change'] for row in rows).items())),
        'balance_changed_pairs': sum(row.get('balance_delta_raw', '0') != '0' for row in rows),
        'spendable_changed_pairs': sum(row.get('spendable_delta_raw', '0') != '0' for row in rows),
        'pairs': rows, 'owners_over_compared_pairs': owners,
        'limitations': [
            'Missing pairs are unknown, never treated as zero or revoked.',
            'A zero allowance may reflect spending or revocation; these reads do not establish cause.',
            'Newly observed means previously unmeasured, not newly approved.',
            'Refresh preserves the listed inventory but does not discover additional spenders.',
            'Empty balance leaves permission active; future receipts may become spendable.',
            'Owner totals use only pairs measured at both blocks and cap overlapping allowances at balance.',
            'Standard ERC-20 assumptions only; Permit2, unused signatures, other tokens and chains are omitted.',
            'RPC evidence is trusted, not a proof; saved reports are historical and do not predict execution.',
        ],
    }


def state(row):
    if row is None:
        return None
    return {key: row[key] for key in ('allowance_raw', 'balance_raw',
                                     'spendable_upper_bound_raw', 'status', 'max_uint256')}


def block_summary(observation):
    return {key: observation[key] for key in ('block_number', 'block_hash', 'block_time_utc', 'sources')}


def refresh(rpc, before, block_tag='finalized'):
    old = flatten(before)
    lens.require(old['pairs'], 'cannot refresh an empty inventory; discover or supply actual pairs first')
    lens.require(block_tag in ('finalized', 'safe', 'latest') or
                 (isinstance(block_tag, str) and block_tag.startswith('0x')
                  and lens.quantity(block_tag) >= 0), 'invalid block selector')
    lens.require(rpc.call('eth_chainId', []) == '0x1', 'expected Ethereum chain 1')
    previous_header = lens.header(rpc.call('eth_getBlockByNumber', [hex(old['block_number']), False]))
    lens.require(lens.quantity(previous_header['number']) == old['block_number']
                 and previous_header['hash'] == old['block_hash'], 'before block is no longer canonical')
    block = lens.header(rpc.call('eth_getBlockByNumber', [block_tag, False]))
    if block_tag.startswith('0x'):
        lens.require(block['number'] == block_tag, 'RPC returned a different block than requested')
    lens.require(lens.quantity(block['number']) >= old['block_number'], 'refresh block predates inventory')
    observations = []
    for owner in sorted({pair[0] for pair in old['pairs']}):
        spenders = sorted(pair[1] for pair in old['pairs'] if pair[0] == owner)
        observed = lens.capture(rpc, old['token'], block['number'], 1, owner, spenders)
        lens.require(observed['block'] == block, 'refresh block changed between owners')
        observations.append(observed)
    final = lens.header(rpc.call('eth_getBlockByNumber', [block['number'], False]))
    lens.require(final == block, 'refresh block changed during capture')
    result = {'schema': BUNDLE_SCHEMA, 'observations': observations}
    checked = compare(before, result)
    lens.require(checked['coverage']['all_previous_pairs_rechecked'], 'incomplete inventory refresh')
    return result


def refresh_endpoint(endpoint, before, block_tag):
    return refresh(lens.RPC(endpoint), before, block_tag)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', help='Allowance Lens observation or this tool\'s saved inventory')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--after', help='offline comparison observation or inventory')
    mode.add_argument('--refresh', action='store_true', help='read each previously listed pair again')
    parser.add_argument('--rpc', choices=sorted(lens.ENDPOINTS), default=lens.PUBLIC_RPC)
    parser.add_argument('--block', default='finalized', help='finalized, safe, latest, or decimal block')
    parser.add_argument('--timeout', type=float, default=90, help='total live-read deadline, 0 < seconds <= 600')
    parser.add_argument('--save', help='new workspace file for refreshed raw evidence (never overwritten)')
    args = parser.parse_args(argv)
    try:
        if args.refresh:
            lens.require(args.before is not None, '--refresh requires --before with an actual inventory')
            before = load(args.before)
            tag = hex(int(args.block)) if args.block.isdecimal() else args.block
            after = lens.run_bounded(refresh_endpoint, (args.rpc, before, tag), timeout=args.timeout)
        else:
            lens.require(not args.save and args.rpc == lens.PUBLIC_RPC
                         and args.block == 'finalized' and args.timeout == 90,
                         'RPC, block, timeout and save options require --refresh')
            lens.require((args.before is None) == (args.after is None),
                         'provide both --before and --after, or neither for the offline demo')
            before = load(args.before or LENS_DIR / 'observation.json')
            after = load(args.after or HERE / 'recheck.json')
        result = compare(before, after)
        if args.save:
            save(args.save, after)
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, KeyError, TypeError, OSError, OverflowError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
