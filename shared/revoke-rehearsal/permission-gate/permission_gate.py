#!/usr/bin/env python3
"""Check measured ERC-20 permissions against an explicit, bounded allowance policy."""
import argparse
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'allowance-changes'))
import allowance_changes as changes
lens = changes.lens
SCHEMA = 'permission-gate-policy-v1'
LIMIT = 98_304


def unique_object(items):
    result = {}
    for key, value in items:
        lens.require(key not in result, 'duplicate JSON key: ' + key)
        result[key] = value
    return result


def load(path):
    with lens.workspace_path(path).open('rb') as stream:
        data = stream.read(LIMIT + 1)
    lens.require(len(data) <= LIMIT, 'input exceeds 96 KiB')
    return json.loads(data, object_pairs_hook=unique_object)


def exact_keys(value, keys, label):
    lens.require(isinstance(value, dict) and set(value) == set(keys),
                 label + ' must have exactly these keys: ' + ', '.join(keys))


def raw_uint(value):
    lens.require(isinstance(value, str) and re.fullmatch(r'0|[1-9][0-9]{0,77}', value),
                 'allowance ceiling must be a canonical decimal integer string')
    result = int(value)
    lens.require(result <= lens.MAX_UINT, 'allowance ceiling exceeds uint256')
    return result


def policy(value):
    exact_keys(value, ('schema', 'chain_id', 'token_address', 'minimum_block',
                       'maximum_block', 'pairs'), 'policy')
    lens.require(value['schema'] == SCHEMA, 'unsupported policy schema')
    lens.require(type(value['chain_id']) is int and value['chain_id'] == 1,
                 'policy must select Ethereum chain 1')
    token = lens.address(value['token_address'])
    lens.require(token in lens.TOKENS.values(), 'policy must select real ZTO or IMD')
    low, high = value['minimum_block'], value['maximum_block']
    lens.require(type(low) is int and type(high) is int and 0 <= low <= high,
                 'policy requires an inclusive nonnegative block interval')
    pairs = value['pairs']
    lens.require(isinstance(pairs, list) and len(pairs) <= lens.MAX_PAIRS,
                 'policy permits at most 64 explicit pairs')
    limits = {}
    for entry in pairs:
        exact_keys(entry, ('owner', 'spender', 'maximum_allowance_raw'), 'pair')
        pair = (lens.address(entry['owner']), lens.address(entry['spender']))
        lens.require(pair not in limits, 'duplicate policy pair')
        limits[pair] = raw_uint(entry['maximum_allowance_raw'])
    return token, low, high, limits


def evaluate(observation, specification):
    token, low, high, limits = policy(specification)
    measured = changes.flatten(observation)
    lens.require(measured['chain_id'] == specification['chain_id']
                 and measured['token_address'] == token, 'policy and observation identity differ')
    fresh = low <= measured['block_number'] <= high
    rows = []
    for pair in sorted(set(measured['pairs']) | set(limits)):
        entry = measured['pairs'].get(pair)
        ceiling = limits.get(pair, 0)
        if entry is None:
            status = 'missing_evidence'
        elif int(entry['allowance_raw']) > ceiling:
            status = 'exceeds_limit' if pair in limits else 'unlisted_active_permission'
        else:
            status = 'within_limit'
        rows.append({'owner': pair[0], 'spender': pair[1], 'explicit_policy_pair': pair in limits,
                     'maximum_allowance_raw': str(ceiling),
                     'allowance_raw': None if entry is None else entry['allowance_raw'],
                     'balance_raw': None if entry is None else entry['balance_raw'],
                     'status': status})
    missing = sum(row['status'] == 'missing_evidence' for row in rows)
    violations = sum(row['status'] in ('exceeds_limit', 'unlisted_active_permission') for row in rows)
    # An empty scan cannot pass even an empty deny-all policy.
    sufficient = bool(measured['pairs']) and fresh and missing == 0
    decision = 'insufficient_evidence' if not sufficient else ('deny' if violations else 'pass_measured_pairs')
    return {'schema': 'permission-gate-report-v1', 'decision': decision,
            'chain_id': measured['chain_id'], 'token': measured['token'], 'token_address': token,
            'block_number': measured['block_number'], 'block_hash': measured['block_hash'],
            'block_time_utc': measured['block_time_utc'],
            'policy_block_interval': {'minimum': low, 'maximum': high, 'observed_in_interval': fresh},
            'complete_wallet_audit': False, 'measured_pair_count': len(measured['pairs']),
            'required_pair_count': len(limits), 'missing_pair_count': missing,
            'violating_pair_count': violations, 'pairs': rows,
            'limitations': [
                'Pass applies only to measured pairs at the reported historical block, not an entire wallet.',
                'Unlisted measured pairs have a zero ceiling; every explicit policy pair must be measured.',
                'Allowance itself is checked, including on empty balances; later receipts may become spendable.',
                'The block interval is chosen by the worker; no wall-clock freshness or future-state guarantee.',
                'Missing pairs, empty observations and blocks outside the policy interval cannot pass.',
                'Permit2 sub-permissions, unused signatures, custom authorizations and other tokens are omitted.',
                'RPC evidence is trusted, not a proof. No transaction, signing or wallet interaction is performed.',
            ]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observation', help='raw Allowance Lens observation or Changes inventory')
    parser.add_argument('--policy', help='explicit policy JSON; both arguments required together')
    args = parser.parse_args(argv)
    try:
        lens.require((args.observation is None) == (args.policy is None),
                     'provide both --observation and --policy, or neither for the demonstration')
        demo = args.observation is None
        result = evaluate(load(args.observation or HERE / 'live-observation.json'),
                          load(args.policy or HERE / 'demo-policy.json'))
        result['demonstration'] = demo
        print(json.dumps(result, indent=2))
        # Demo succeeds as a demonstration even though the policy correctly denies.
        return 0 if demo or result['decision'] == 'pass_measured_pairs' else (
            4 if result['decision'] == 'insufficient_evidence' else 3)
    except (ValueError, KeyError, TypeError, OSError, OverflowError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
