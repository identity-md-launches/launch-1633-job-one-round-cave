"""Offline checks against the saved real ZTO/IMD pool observation."""
import contextlib
import copy
import io
import json
import unittest

import zto_capacity as capacity


class CapacityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.observation = capacity.path.read_json(str(capacity.DEFAULT_SNAPSHOT))

    def test_zto_adjacent_bound_on_real_pool(self):
        report = capacity.find_bound(self.observation, 'ZTO', '1000000000', 100)
        self.assertEqual(report['status'], 'bounded')
        self.assertEqual(report['maximum_complete_input_raw'], '532032773748606186868770127')
        self.assertEqual(int(report['next_input_raw']),
                         int(report['maximum_complete_input_raw']) + 1)
        self.assertEqual(report['next_input_status'], 'outside_coverage')
        self.assertEqual(int(report['minimum_output_raw']),
                         int(report['estimated_output_raw']) * 9900 // 10000)
        self.assertEqual(report['block'], self.observation['base']['block'])

    def test_imd_direction_has_independent_bound(self):
        report = capacity.find_bound(self.observation, 'IMD', '10000', 50)
        self.assertEqual(report['status'], 'bounded')
        self.assertEqual(report['maximum_complete_input_raw'], '8533813925163446123806')
        self.assertEqual(report['output_token'], 'ZTO')

    def test_ceiling_reached_does_not_claim_pool_capacity(self):
        report = capacity.find_bound(self.observation, 'ZTO', '100000000', 100)
        self.assertEqual(report['status'], 'ceiling_reached')
        self.assertIsNone(report['next_input_raw'])
        self.assertEqual(report['maximum_complete_input'], '100000000')

    def test_invalid_inputs_and_corrupt_pool_refused(self):
        for ceiling, bps in [('0', 100), ('1e9', 100), ('1', -1), ('1', 10000)]:
            with self.subTest(ceiling=ceiling, bps=bps), self.assertRaises(ValueError):
                capacity.find_bound(self.observation, 'ZTO', ceiling, bps)
        altered = copy.deepcopy(self.observation)
        altered['base']['initialize']['topics'][1] = '0x' + '11' * 32
        with self.assertRaises(ValueError):
            capacity.find_bound(altered, 'ZTO', '1', 100)

    def test_cli_is_offline_and_machine_readable(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = capacity.main(['--ceiling', '100000000', '--slippage-bps', '100'])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())['status'], 'ceiling_reached')


if __name__ == '__main__':
    unittest.main()
