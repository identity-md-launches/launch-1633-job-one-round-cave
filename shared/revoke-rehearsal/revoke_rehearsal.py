#!/usr/bin/env python3
"""Join measured revoke candidates to exact, block-bound call expectations offline."""
import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'approval-draft'))
import approval_draft as draft
import call_expectation as expectation

core = expectation.core
SCHEMA = 'revoke-rehearsal-v1'
LIMITS = ('Historical provider-reported return evidence only. A true return does not prove '
          'allowance changed, token effects, gas, authenticity, freshness or future execution. '
          'A policy denial is not an owner instruction. No transaction signed or sent.')


def prepare(observation, policy):
    report = draft.build(observation, policy)
    measured = draft.gate.changes.flatten(observation)
    observations = observation['observations'] if observation.get('schema') == draft.gate.changes.BUNDLE_SCHEMA else [observation]
    block = core.header(observations[0]['block'])
    items = []
    for candidate in report['drafts']:
        transaction = candidate['transaction']
        call = core.transaction({k: transaction[k] for k in ('from', 'to', 'value', 'data')})
        wanted = {'schema': expectation.SCHEMA, 'chain_id': 1, 'call': call,
                  'block': block, 'evidence': 'single', 'expect': {'kind': 'bool_true'}}
        expectation.policy(wanted)
        items.append({'owner': candidate['owner'], 'spender': candidate['spender'],
                      'allowance_raw': candidate['allowance_raw'], 'unsigned_draft': transaction,
                      'expectation': wanted})
    return {'schema': SCHEMA, 'state': report['state'],
            'permission_gate_decision': report['permission_gate_decision'],
            'block': block, 'token': measured['token'], 'candidate_count': len(items),
            'candidates': items, 'limits': LIMITS}


def assess(observation, policy, evidence):
    plan = prepare(observation, policy)
    core.require(isinstance(evidence, list) and len(evidence) <= draft.gate.lens.MAX_PAIRS,
                 'evidence must be a list of at most 64 single rehearsals')
    indexed = {}
    for obs in evidence:
        expectation.changes.validate(obs)
        call = core.transaction(obs['call'])
        key = json.dumps(call, sort_keys=True)
        core.require(key not in indexed, 'duplicate rehearsal for one candidate call')
        indexed[key] = obs
    results = []
    expected_keys = set()
    for item in plan['candidates']:
        key = json.dumps(item['expectation']['call'], sort_keys=True)
        expected_keys.add(key)
        obs = indexed.get(key)
        result = (expectation.evaluate(obs, item['expectation']) if obs is not None else
                  {'verdict': 'inconclusive', 'reason': 'missing exact caller/calldata rehearsal'})
        results.append({'owner': item['owner'], 'spender': item['spender'],
                        'verdict': result['verdict'], 'reason': result['reason']})
    extra = len(set(indexed) - expected_keys)
    verdict = ('inconclusive' if extra or not results or any(r['verdict'] == 'inconclusive' for r in results)
               else 'mismatch' if any(r['verdict'] == 'mismatch' for r in results) else 'match')
    return {'schema': SCHEMA, 'verdict': verdict, 'permission_gate_decision': plan['permission_gate_decision'],
            'block': plan['block'], 'token': plan['token'], 'candidate_count': len(results),
            'unmatched_evidence_count': extra, 'candidates': results, 'limits': LIMITS}


def load(path):
    return expectation.read_json(path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest='mode', required=True)
    modes.add_parser('demo', help='offline real ZTO owner/caller rehearsal checks')
    for name in ('prepare', 'check'):
        command = modes.add_parser(name)
        command.add_argument('--observation', required=True)
        command.add_argument('--policy', required=True)
        if name == 'check':
            command.add_argument('--evidence', required=True, help='JSON list of single rehearsals')
    args = parser.parse_args(argv)
    try:
        demo = args.mode == 'demo'
        observation = load(HERE / 'zto-inventory.json' if demo else args.observation)
        policy = load(HERE / 'deny-policy.json' if demo else args.policy)
        if args.mode == 'prepare':
            result = prepare(observation, policy)
            code = 2 if result['state'] == 'insufficient_evidence' else 0
        else:
            evidence = load(HERE / 'zto-rehearsals.json' if demo else args.evidence)
            result = assess(observation, policy, evidence)
            code = {'match': 0, 'mismatch': 1, 'inconclusive': 2}[result['verdict']]
        result['demonstration'] = demo
        print(json.dumps(result, indent=2, allow_nan=False))
        return code
    except (ValueError, KeyError, TypeError, OSError, OverflowError, RecursionError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
