#!/usr/bin/env python3
"""Check saved Ethereum call evidence against an explicit, block-bound expectation."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'call-witness'))
import call_witness as witness

changes, core = witness.changes, witness.core
HERE = Path(__file__).resolve().parent
SCHEMA = 'call-expectation-v1'
LIMIT = 95_000
POLICY_KEYS = {'schema', 'chain_id', 'call', 'block', 'evidence', 'expect'}
LIMITS = ('Checks saved provider claims against a declared expectation at one historical block. '
          'A match is not transaction success, token movement, gas estimation, authentication, '
          'provider independence or a guarantee of future execution. Nothing sent.')


def read_json(path):
    with core.workspace_path(path).open('rb') as handle:
        raw = handle.read(LIMIT + 1)
    core.require(len(raw) <= LIMIT, 'input exceeds 95 KB')
    return json.loads(raw, object_pairs_hook=changes.no_duplicates,
                      parse_constant=changes.reject_constant)


def policy(value):
    """Require a complete expectation; normalize hex without mutating caller data."""
    core.require(isinstance(value, dict) and set(value) == POLICY_KEYS,
                 'expectation must have exactly the documented fields')
    core.require(value['schema'] == SCHEMA, 'unsupported expectation schema')
    core.require(type(value['chain_id']) is int and value['chain_id'] == 1,
                 'expected Ethereum mainnet chain_id 1')
    core.require(value['evidence'] in ('single', 'witness'), 'evidence must be single or witness')
    block = value['block']
    core.require(isinstance(block, dict) and set(block) == {'number', 'hash', 'timestamp'},
                 'expectation requires an exact block number, hash and timestamp')
    expected = value['expect']
    core.require(isinstance(expected, dict), 'expect must be an object')
    kind = expected.get('kind')
    if kind == 'bool_true':
        core.require(set(expected) == {'kind'}, 'bool_true accepts only kind')
        expected = {'kind': kind}
    elif kind == 'uint256_range':
        core.require(set(expected) == {'kind', 'min', 'max'}, 'range requires min and max')
        lower, upper = core.amount(expected['min']), core.amount(expected['max'])
        core.require(lower <= upper, 'minimum exceeds maximum')
        expected = {'kind': kind, 'min': str(lower), 'max': str(upper)}
    elif kind == 'return_bytes':
        core.require(set(expected) == {'kind', 'data'}, 'return_bytes requires data')
        expected = {'kind': kind, 'data': core.data(expected['data'])}
    else:
        raise ValueError('unsupported expectation kind')
    return {'schema': SCHEMA, 'chain_id': 1, 'call': core.transaction(value['call']),
            'block': core.header(block), 'evidence': value['evidence'], 'expect': expected}


def evaluate(evidence, expectation):
    wanted = policy(expectation)
    if isinstance(evidence, dict) and evidence.get('schema') == witness.SCHEMA:
        core.require(set(evidence) == {'schema', 'observations'}, 'invalid witness bundle fields')
        pair = witness.witness(evidence['observations'])
        observations = evidence['observations']
        agreement = pair['verdict']
        evidence_kind = 'witness'
    else:
        changes.validate(evidence)
        observations, agreement, evidence_kind = [evidence], 'not_requested', 'single'
    return_type = {'bool_true': 'bool', 'uint256_range': 'uint256',
                   'return_bytes': 'raw'}[wanted['expect']['kind']]
    results = [changes.validate(obs)['result'] for obs in observations]
    report = {'schema': SCHEMA, 'verdict': 'inconclusive', 'reason': '',
              'chain_id': 1, 'expected': wanted, 'evidence': evidence_kind,
              'agreement': agreement,
              'observations': [{'source': obs['source'], 'block': core.header(obs['block']),
                                'call': core.transaction(obs['call']), 'returns': obs['returns'],
                                'result': result} for obs, result in zip(observations, results)],
              'limits': LIMITS}

    def finish(verdict, reason):
        report.update(verdict=verdict, reason=reason)
        return report

    if wanted['evidence'] != evidence_kind:
        return finish('inconclusive', 'evidence kind does not match the requested single/witness mode')
    for obs in observations:
        if core.transaction(obs['call']) != wanted['call']:
            return finish('inconclusive', 'evidence is for a different call')
        if core.header(obs['block']) != wanted['block']:
            return finish('inconclusive', 'evidence is for a different block')
        if obs['returns'] != return_type:
            return finish('inconclusive', 'saved return interpretation differs from expectation kind')
    if agreement in ('disagree', 'inconclusive'):
        return finish('inconclusive', 'witnesses disagree or lack comparable execution evidence')
    result = results[0]
    if result['status'] == 'reverted':
        return finish('mismatch', 'provider reported a revert; expected a return')
    if result['status'] not in changes.SUCCESS:
        return finish('inconclusive', 'RPC failure or malformed ABI return prevents checking expectation')
    expected = wanted['expect']
    if expected['kind'] == 'bool_true':
        matches = result['boolean'] is True
    elif expected['kind'] == 'uint256_range':
        matches = int(expected['min']) <= int(result['uint256']) <= int(expected['max'])
    else:
        matches = result['raw'] == expected['data']
    return finish('match' if matches else 'mismatch',
                  'returned value satisfies expectation' if matches else
                  'returned value does not satisfy expectation')


def exit_code(result):
    return {'match': 0, 'mismatch': 1, 'inconclusive': 2}[result['verdict']]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='mode', required=True)
    commands.add_parser('demo', help='offline check of saved real ZTO supply witness')
    check = commands.add_parser('check', help='check raw evidence against your expectation JSON')
    check.add_argument('evidence')
    check.add_argument('expectation')
    args = parser.parse_args(argv)
    try:
        if args.mode == 'demo':
            evidence = read_json(HERE.parent / 'call-witness' / 'zto-witness.json')
            expected = read_json(HERE / 'zto-expectation.json')
        else:
            expected = read_json(args.expectation)
            policy(expected)
            evidence = read_json(args.evidence)
        report = evaluate(evidence, expected)
        print(json.dumps(report, indent=2, allow_nan=False))
        return exit_code(report)
    except (ValueError, KeyError, TypeError, OSError, RecursionError, core.RPCError) as exc:
        print(json.dumps({'schema': SCHEMA, 'verdict': 'inconclusive', 'error': str(exc)}),
              file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
