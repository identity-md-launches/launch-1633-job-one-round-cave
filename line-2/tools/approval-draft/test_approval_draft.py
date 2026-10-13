import copy
import unittest

import approval_draft as draft
import permission_gate as gate


class ApprovalDraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.observation = gate.load(draft.DEFAULT_OBSERVATION)
        cls.policy = gate.load(draft.DEFAULT_POLICY)

    def test_real_zto_deny_produces_only_measured_active_pairs(self):
        result = draft.build(self.observation, self.policy)
        self.assertEqual(result['permission_gate_decision'], 'deny')
        self.assertEqual(result['draft_count'], 3)
        for item in result['drafts']:
            tx = item['transaction']
            self.assertEqual(tx['chainId'], '0x1')
            self.assertEqual(tx['from'], item['owner'])
            self.assertEqual(tx['to'], gate.lens.TOKENS['ZTO'])
            self.assertEqual(tx['value'], '0x0')
            self.assertEqual(tx['data'], '0x095ea7b3' + gate.lens.address_arg(item['spender'])
                             + '0' * 64)
            self.assertGreater(int(item['allowance_raw']), int(item['policy_limit_raw']))

    def test_sufficient_passing_policy_has_no_drafts(self):
        policy = copy.deepcopy(self.policy)
        rows = gate.changes.flatten(self.observation)['pairs'].values()
        policy['pairs'] = [
            {'owner': row['owner'], 'spender': row['spender'],
             'maximum_allowance_raw': row['allowance_raw']}
            for row in rows
        ]
        result = draft.build(self.observation, policy)
        self.assertEqual(result['permission_gate_decision'], 'pass_measured_pairs')
        self.assertEqual(result['draft_count'], 0)
        self.assertEqual(result['state'], 'no_revoke_drafts')

    def test_out_of_interval_evidence_never_creates_drafts(self):
        policy = copy.deepcopy(self.policy)
        next_block = policy['maximum_block'] + 1
        policy['minimum_block'] = next_block
        policy['maximum_block'] = next_block
        result = draft.build(self.observation, policy)
        self.assertEqual(result['permission_gate_decision'], 'insufficient_evidence')
        self.assertEqual(result['draft_count'], 0)
        self.assertEqual(result['state'], 'insufficient_evidence')


if __name__ == '__main__':
    unittest.main()
