import unittest
from ai_employee_system.roles import ROLES, create_agent_brief, create_task_proposal

class AgentRoleTests(unittest.TestCase):
    def test_ten_roles_have_unique_keys(self):
        self.assertEqual(len(ROLES), 10)
        self.assertEqual(len({role.key for role in ROLES}), 10)

    def test_brief_contains_safety_constraints(self):
        brief = create_agent_brief("content_creator", "Draft three social posts", "Hindi + English")
        self.assertEqual(brief["role"], "content_creator")
        self.assertEqual(brief["objective"], "Draft three social posts")
        self.assertTrue(any("do not execute" in item.lower() for item in brief["constraints"]))

    def test_unknown_role_and_blank_objective_rejected(self):
        with self.assertRaises(ValueError):
            create_agent_brief("unknown_role", "Do work")
        with self.assertRaises(ValueError):
            create_agent_brief("content_creator", "  ")

    def test_proposal_is_only_a_pending_proposal(self):
        proposal = create_task_proposal("Draft campaign", "Prepare a draft only", "marketing")
        self.assertEqual(proposal["status"], "pending_approval")
        self.assertNotIn("execute", proposal)

if __name__ == "__main__":
    unittest.main()
