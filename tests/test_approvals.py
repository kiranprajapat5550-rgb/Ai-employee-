import tempfile
import unittest
from pathlib import Path
from ai_employee_system.approvals import ApprovalQueue
from ai_employee_system.roles import ROLES, create_agent_brief, create_task_proposal

class ApprovalQueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.queue = ApprovalQueue(Path(self.tmp.name) / "test.sqlite3")
    def tearDown(self):
        self.tmp.cleanup()
    def test_submit_starts_pending(self):
        item = self.queue.submit("Draft post", "Prepare a draft", "content", {"channel": "instagram"})
        self.assertEqual(item["status"], "pending_approval")
        self.assertEqual(item["payload"]["channel"], "instagram")
    def test_review_records_approval_without_execution_field(self):
        item = self.queue.submit("Draft post", "Prepare a draft")
        reviewed = self.queue.review(item["id"], "approved", "founder", "Looks good")
        self.assertEqual(reviewed["status"], "approved")
        self.assertEqual(reviewed["reviewer"], "founder")
        self.assertNotIn("executed", reviewed)
    def test_cannot_review_twice(self):
        item = self.queue.submit("Draft", "Description")
        self.queue.review(item["id"], "rejected", "founder")
        with self.assertRaises(ValueError):
            self.queue.review(item["id"], "approved", "founder")
    def test_unknown_proposal(self):
        with self.assertRaises(KeyError):
            self.queue.get(999)
    def test_empty_fields_rejected(self):
        with self.assertRaises(ValueError):
            self.queue.submit("", "Description")
    def test_role_catalog_and_brief(self):
        self.assertEqual(len(ROLES), 10)
        brief = create_agent_brief("content_creator", "Draft a weekly plan")
        self.assertEqual(brief["role"], "content_creator")
        self.assertTrue(brief["constraints"])
    def test_unknown_role_and_empty_objective(self):
        with self.assertRaises(ValueError):
            create_agent_brief("unknown", "task")
        with self.assertRaises(ValueError):
            create_agent_brief("content_creator", " ")
    def test_task_proposal_is_pending(self):
        self.assertEqual(create_task_proposal("Title", "Description")["status"], "pending_approval")

if __name__ == "__main__":
    unittest.main()
