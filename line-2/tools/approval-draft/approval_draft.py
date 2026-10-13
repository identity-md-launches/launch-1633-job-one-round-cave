#!/usr/bin/env python3
"""Prepare owner-reviewable unsigned ERC-20 revoke drafts from checked evidence."""

import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'permission-gate'))
import permission_gate as gate

DEFAULT_OBSERVATION = HERE.parent / 'permission-gate' / 'live-observation.json'
DEFAULT_POLICY = HERE.parent / 'permission-gate' / 'demo-policy.json'
VIOLATIONS = {'exceeds_limit', 'unlisted_active_permission'}
APPROVE_SELECTOR = '0x095ea7b3'
ZERO_UINT256 = '0' * 64


def build(observation, policy):
    """Create optional approve(spender, 0) drafts only after a sufficient deny."""
    assessment = gate.evaluate(observation, policy)
    drafts = []
    if assessment['decision'] == 'deny':
        for row in assessment['pairs']:
            if row['status'] not in VIOLATIONS:
                continue
            # The validated gate report carries canonical decimal uint256 strings.
            allowance = int(row['allowance_raw'])
            if allowance == 0:
                continue
            spender = gate.lens.address(row['spender'])
            owner = gate.lens.address(row['owner'])
            calldata = APPROVE_SELECTOR + gate.lens.address_arg(spender) + ZERO_UINT256
            drafts.append({
                'owner': owner,
                'spender': spender,
                'allowance_raw': row['allowance_raw'],
                'balance_raw': row['balance_raw'],
                'policy_limit_raw': row['maximum_allowance_raw'],
                'target_allowance_raw': '0',
                'review_note': 'Optional revoke candidate; the owner must choose and verify it.',
                'transaction': {
                    'chainId': '0x1',
                    'from': owner,
                    'to': assessment['token_address'],
                    'value': '0x0',
                    'data': calldata,
                },
            })

    if assessment['decision'] == 'insufficient_evidence':
        state = 'insufficient_evidence'
    elif drafts:
        state = 'owner_review_required'
    else:
        state = 'no_revoke_drafts'
    return {
        'schema': 'allowance-revoke-drafts-v1',
        'state': state,
        'permission_gate_decision': assessment['decision'],
        'chain_id': assessment['chain_id'],
        'token': assessment['token'],
        'token_address': assessment['token_address'],
        'block_number': assessment['block_number'],
        'block_hash': assessment['block_hash'],
        'block_time_utc': assessment['block_time_utc'],
        'complete_wallet_audit': False,
        'draft_count': len(drafts),
        'drafts': drafts,
        'limitations': [
            'A policy violation is not an instruction from the owner to revoke.',
            'Drafts contain no nonce or fee fields and are never signed, sent, simulated, or saved.',
            'Re-read the pair at a suitably fresh canonical block before any owner action.',
            'The input inventory is only the supplied measured coverage, not a complete wallet audit.',
            'Permit2 sub-permissions, unused signatures, custom authorizations and unknown spenders are omitted.',
            'A draft proposes approve(spender, 0); the owner may instead retain or set another allowance.',
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observation', help='raw Allowance Lens observation or Changes inventory')
    parser.add_argument('--policy', help='explicit Permission Gate policy JSON')
    args = parser.parse_args(argv)
    try:
        gate.lens.require((args.observation is None) == (args.policy is None),
                          'provide both --observation and --policy, or neither for the demonstration')
        demo = args.observation is None
        observation = gate.load(args.observation or DEFAULT_OBSERVATION)
        policy = gate.load(args.policy or DEFAULT_POLICY)
        result = build(observation, policy)
        result['demonstration'] = demo
        print(json.dumps(result, indent=2))
        return 4 if result['state'] == 'insufficient_evidence' else 0
    except (ValueError, KeyError, TypeError, OSError, OverflowError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
