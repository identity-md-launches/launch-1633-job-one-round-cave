"""Real evidence replay plus explicit synthetic refusal cases; no RPC calls."""
import copy
import unittest
from unittest.mock import patch
import revoke_rehearsal as tool


class RevokeRehearsalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = tool.load(tool.HERE / 'zto-inventory.json')
        cls.policy = tool.load(tool.HERE / 'deny-policy.json')
        cls.evidence = tool.load(tool.HERE / 'zto-rehearsals.json')

    def assess(self, evidence=None, policy=None):
        return tool.assess(self.inventory, self.policy if policy is None else policy,
                           self.evidence if evidence is None else evidence)

    def test_real_zto_replay(self):
        with patch.object(tool.core.RPC, 'call', side_effect=AssertionError('offline means no RPC')):
            report = self.assess()
        self.assertEqual(report['verdict'], 'match')
        self.assertEqual(report['candidate_count'], 3)
        self.assertEqual(report['permission_gate_decision'], 'deny')

    def test_exact_unsigned_drafts_and_intended_true(self):
        plan = tool.prepare(self.inventory, self.policy)
        for candidate in plan['candidates']:
            tx = candidate['unsigned_draft']
            self.assertEqual(tx['from'], candidate['owner'])
            self.assertEqual(tx['to'], tool.core.TOKENS['ZTO'])
            self.assertEqual(tx['data'], '0x095ea7b3' + candidate['spender'][2:].rjust(64, '0') + '0' * 64)
            self.assertEqual(candidate['expectation']['expect'], {'kind': 'bool_true'})
            self.assertEqual(set(tx), {'chainId', 'from', 'to', 'data', 'value'})

    def test_missing_rehearsal(self):
        self.assertEqual(self.assess(self.evidence[:-1])['verdict'], 'inconclusive')

    def test_wrong_caller_not_matched(self):
        evidence = copy.deepcopy(self.evidence)
        evidence[0]['call']['from'] = evidence[2]['call']['from']
        report = self.assess(evidence)
        self.assertEqual(report['verdict'], 'inconclusive')
        self.assertEqual(report['unmatched_evidence_count'], 1)

    def test_wrong_calldata_not_matched(self):
        evidence = copy.deepcopy(self.evidence)
        evidence[0]['call']['data'] = evidence[0]['call']['data'][:-1] + '1'
        self.assertEqual(self.assess(evidence)['verdict'], 'inconclusive')

    def test_each_block_field_is_bound(self):
        for field in ('number', 'hash', 'timestamp'):
            with self.subTest(field=field):
                evidence = copy.deepcopy(self.evidence)
                value = evidence[0]['block'][field]
                evidence[0]['block'][field] = '0x' + ('f' * 64 if field == 'hash' else format(int(value, 16) + 1, 'x'))
                self.assertEqual(self.assess(evidence)['verdict'], 'inconclusive')

    def test_false_return_is_mismatch(self):
        evidence = copy.deepcopy(self.evidence)
        evidence[0]['outcome'] = {'result': '0x' + '0' * 64}
        self.assertEqual(self.assess(evidence)['verdict'], 'mismatch')

    def test_revert_is_mismatch(self):
        evidence = copy.deepcopy(self.evidence)
        evidence[0]['outcome'] = {'error': {'code': 3, 'message': 'execution reverted', 'data': '0x'}}
        self.assertEqual(self.assess(evidence)['verdict'], 'mismatch')

    def test_duplicate_rehearsal_refused(self):
        with self.assertRaisesRegex(ValueError, 'duplicate rehearsal'):
            self.assess(self.evidence + [self.evidence[0]])

    def test_stale_policy_never_uses_matching_returns(self):
        policy = copy.deepcopy(self.policy)
        policy['minimum_block'] += 1
        policy['maximum_block'] += 1
        report = self.assess(policy=policy)
        self.assertEqual(report['permission_gate_decision'], 'insufficient_evidence')
        self.assertEqual(report['candidate_count'], 0)
        self.assertEqual(report['verdict'], 'inconclusive')

    def test_unnecessary_evidence_cannot_pass_empty_plan(self):
        policy = copy.deepcopy(self.policy)
        policy['pairs'] = [{'owner': row['owner'], 'spender': row['spender'],
                            'maximum_allowance_raw': row['allowance_raw']}
                           for row in tool.draft.gate.evaluate(self.inventory, self.policy)['pairs']]
        report = self.assess(policy=policy)
        self.assertEqual(report['permission_gate_decision'], 'pass_measured_pairs')
        self.assertEqual(report['verdict'], 'inconclusive')

    def test_wrong_return_interpretation_is_inconclusive(self):
        evidence = copy.deepcopy(self.evidence)
        evidence[0]['returns'] = 'uint256'
        self.assertEqual(self.assess(evidence)['verdict'], 'inconclusive')


if __name__ == '__main__':
    unittest.main()
