"""Offline checks; modified outcomes are synthetic, never live-chain claims."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import call_expectation as tool


class Expectations(unittest.TestCase):
    def setUp(self):
        self.bundle = tool.read_json(tool.HERE.parent / 'call-witness' / 'zto-witness.json')
        self.expected = tool.read_json(tool.HERE / 'zto-expectation.json')

    def evaluate(self):
        return tool.evaluate(self.bundle, self.expected)

    def replace_outcomes(self, outcome, returns):
        for obs in self.bundle['observations']:
            obs['outcome'] = copy.deepcopy(outcome)
            obs['returns'] = returns

    def test_saved_real_zto_matches(self):
        report = self.evaluate()
        self.assertEqual(report['verdict'], 'match')
        self.assertEqual(report['agreement'], 'agree')
        self.assertEqual(report['observations'][0]['result']['uint256'],
                         '1000000000000000000000000000')

    def test_agreed_false_is_mismatch_not_match(self):
        self.replace_outcomes({'result': '0x' + '00' * 32}, 'bool')
        self.expected['expect'] = {'kind': 'bool_true'}
        report = self.evaluate()
        self.assertEqual(report['agreement'], 'agree')
        self.assertEqual(report['verdict'], 'mismatch')

    def test_agreed_true_matches(self):
        self.replace_outcomes({'result': '0x' + format(1, '064x')}, 'bool')
        self.expected['expect'] = {'kind': 'bool_true'}
        self.assertEqual(self.evaluate()['verdict'], 'match')

    def test_agreed_revert_is_mismatch(self):
        self.replace_outcomes({'error': {'code': 3, 'message': 'execution reverted',
                                        'data': '0x'}}, 'uint256')
        report = self.evaluate()
        self.assertEqual(report['agreement'], 'agree')
        self.assertEqual(report['verdict'], 'mismatch')

    def test_missing_revert_bytes_remain_inconclusive_for_witness(self):
        self.replace_outcomes({'error': {'code': 3, 'message': 'execution reverted'}}, 'uint256')
        self.assertEqual(self.evaluate()['verdict'], 'inconclusive')

    def test_real_single_revert_cannot_match_return(self):
        obs = tool.read_json(tool.HERE.parent / 'call-rehearsal' / 'zto-revert-observation.json')
        self.expected.update(call=obs['call'], block=obs['block'], evidence='single',
                             expect={'kind': 'return_bytes', 'data': '0x'})
        self.assertEqual(tool.evaluate(obs, self.expected)['verdict'], 'mismatch')

    def test_uint256_range_boundaries_and_full_precision(self):
        self.expected['expect'] = {'kind': 'uint256_range', 'min': '1', 'max': str(2**256-2)}
        for n, verdict in [(0, 'mismatch'), (1, 'match'), (2**256-2, 'match'),
                           (2**256-1, 'mismatch')]:
            self.replace_outcomes({'result': '0x' + format(n, '064x')}, 'uint256')
            with self.subTest(value=n):
                self.assertEqual(self.evaluate()['verdict'], verdict)

    def test_exact_bytes_including_explicit_empty_and_case(self):
        self.expected['expect'] = {'kind': 'return_bytes', 'data': '0xAABB'}
        self.replace_outcomes({'result': '0xaabb'}, 'raw')
        self.assertEqual(self.evaluate()['verdict'], 'match')
        self.expected['expect']['data'] = '0xaa'
        self.assertEqual(self.evaluate()['verdict'], 'mismatch')
        self.expected['expect']['data'] = '0x'
        self.replace_outcomes({'result': '0x'}, 'raw')
        self.assertEqual(self.evaluate()['verdict'], 'match')

    def test_bad_bool_encoding_and_empty_abi_returns_are_inconclusive(self):
        self.expected['expect'] = {'kind': 'bool_true'}
        for raw in ['0x', '0x01', '0x' + format(2, '064x'), '0x' + '00' * 64]:
            self.replace_outcomes({'result': raw}, 'bool')
            with self.subTest(raw=raw):
                self.assertEqual(self.evaluate()['verdict'], 'inconclusive')

    def test_rpc_failure_is_inconclusive(self):
        self.replace_outcomes({'error': {'code': -32000, 'message': 'state unavailable'}}, 'uint256')
        self.assertEqual(self.evaluate()['verdict'], 'inconclusive')

    def test_witness_disagreement_is_not_success_even_within_range(self):
        self.expected['expect'] = {'kind': 'uint256_range', 'min': '0', 'max': str(2**256-1)}
        self.bundle['observations'][1]['outcome'] = {'result': '0x' + format(1, '064x')}
        self.assertEqual(self.evaluate()['verdict'], 'inconclusive')

    def test_all_call_fields_bind_expectation(self):
        mutations = {'to': tool.core.TOKENS['IMD'], 'from': tool.core.TOKENS['IMD'],
                     'value': '0x1', 'data': '0x12345678'}
        for obs in self.bundle['observations']:
            obs['call']['from'] = tool.core.TOKENS['ZTO']
        self.expected['call']['from'] = tool.core.TOKENS['ZTO']
        original = copy.deepcopy(self.expected)
        for field, value in mutations.items():
            self.expected = copy.deepcopy(original)
            self.expected['call'][field] = value
            with self.subTest(field=field):
                self.assertEqual(self.evaluate()['verdict'], 'inconclusive')
        self.expected = original
        del self.expected['call']['from']
        self.assertEqual(self.evaluate()['verdict'], 'inconclusive')

    def test_each_block_field_is_bound(self):
        for field, value in [('number', '0x1'), ('hash', '0x' + 'ef'*32), ('timestamp', '0x1')]:
            expected = copy.deepcopy(self.expected)
            expected['block'][field] = value
            with self.subTest(field=field):
                self.assertEqual(tool.evaluate(self.bundle, expected)['verdict'], 'inconclusive')

    def test_return_interpretation_cannot_be_silently_changed(self):
        self.expected['expect'] = {'kind': 'return_bytes',
                                   'data': self.bundle['observations'][0]['outcome']['result']}
        self.assertEqual(self.evaluate()['verdict'], 'inconclusive')

    def test_no_silent_witness_downgrade_or_upgrade(self):
        obs = self.bundle['observations'][0]
        self.assertEqual(tool.evaluate(obs, self.expected)['verdict'], 'inconclusive')
        self.expected['evidence'] = 'single'
        self.assertEqual(tool.evaluate(obs, self.expected)['verdict'], 'match')
        self.assertEqual(self.evaluate()['verdict'], 'inconclusive')

    def test_invalid_expectations_rejected(self):
        for value in [None, {'kind': 'anything'}, {'kind': 'bool_true', 'value': False},
                      {'kind': 'uint256_range', 'min': '2', 'max': '1'},
                      {'kind': 'uint256_range', 'min': '0', 'max': str(2**256)},
                      {'kind': 'uint256_range', 'min': 0, 'max': '1'},
                      {'kind': 'uint256_range', 'min': '-1', 'max': '1'},
                      {'kind': 'uint256_range', 'min': '00', 'max': '1'},
                      {'kind': 'return_bytes', 'data': '0x1'}]:
            self.expected['expect'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.evaluate()

    def test_wrong_chain_unknown_fields_or_missing_block_rejected(self):
        for field, value in [('chain_id', True), ('chain_id', 8453), ('extra', 1),
                             ('block', {'number': '0x1'}), ('evidence', 'any')]:
            expected = dict(self.expected, **{field: value})
            with self.subTest(field=field), self.assertRaises(ValueError):
                tool.evaluate(self.bundle, expected)

    def test_precomputed_verdict_cannot_be_trusted(self):
        self.bundle['verdict'] = 'agree'
        with self.assertRaises(ValueError):
            self.evaluate()

    def test_input_objects_not_mutated(self):
        before = copy.deepcopy((self.bundle, self.expected))
        self.evaluate()
        self.assertEqual((self.bundle, self.expected), before)


class FilesAndCLI(unittest.TestCase):
    def setUp(self):
        scratch = Path('test/scratch')
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_strict_json_size_and_workspace(self):
        path = self.root / 'input.json'
        for raw in ['{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}', ' ' * (tool.LIMIT+1)]:
            path.write_text(raw)
            with self.subTest(raw=raw[:25]), self.assertRaises(ValueError):
                tool.read_json(path)
        with self.assertRaisesRegex(ValueError, 'workspace'):
            tool.read_json('../outside.json')

    def test_cli_all_exit_codes(self):
        obs = tool.read_json(tool.HERE.parent / 'call-witness' / 'zto-witness.json')['observations'][0]
        expected = tool.read_json(tool.HERE / 'zto-expectation.json')
        expected['evidence'] = 'single'
        evidence_path, expected_path = self.root / 'obs.json', self.root / 'expected.json'
        expected_path.write_text(json.dumps(expected))
        for outcome, code in [(obs['outcome'], 0), ({'result': '0x'+'00'*32}, 1),
                              ({'result': '0x'}, 2)]:
            obs['outcome'] = outcome
            evidence_path.write_text(json.dumps(obs))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                actual = tool.main(['check', str(evidence_path), str(expected_path)])
            self.assertEqual(actual, code)
            self.assertEqual(tool.exit_code(json.loads(output.getvalue())), code)

    def test_invalid_input_has_json_error_and_exit_two(self):
        path = self.root / 'bad.json'
        path.write_text('{"schema":')
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            self.assertEqual(tool.main(['check', str(path), str(path)]), 2)
        self.assertEqual(json.loads(output.getvalue())['verdict'], 'inconclusive')

    def test_demo_is_offline(self):
        with patch.object(tool.core, 'RPC', side_effect=AssertionError('no network')), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(tool.main(['demo']), 0)


if __name__ == '__main__':
    unittest.main()
