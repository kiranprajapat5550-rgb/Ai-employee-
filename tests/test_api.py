import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from ai_employee_system.api import create_app
from ai_employee_system.approvals import ApprovalQueue


class ApprovalApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.queue = ApprovalQueue(Path(self.tmp.name) / "api-test.sqlite3")
        self.client = TestClient(create_app(self.queue))
        self.env = patch.dict(os.environ, {
            "API_BEARER_TOKEN": "test-api-token",
            "FOUNDER_BEARER_TOKEN": "test-founder-token",
        })
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.client.close()
        self.tmp.cleanup()

    def test_health_is_public_and_execution_disabled(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["execution"], "disabled")

    def test_create_requires_api_token(self):
        response = self.client.post("/proposals", json={
            "title": "Draft only", "description": "Create a draft"
        })
        self.assertEqual(response.status_code, 401)

    def test_create_and_list_pending_proposal(self):
        response = self.client.post(
            "/proposals",
            headers={"Authorization": "Bearer test-api-token"},
            json={"title": "Draft post", "description": "Draft only", "payload": {"channel": "test"}},
        )
        self.assertEqual(response.status_code, 201)
        item = response.json()
        self.assertEqual(item["status"], "pending_approval")
        self.assertEqual(item["payload"]["channel"], "test")
        listed = self.client.get(
            "/proposals",
            headers={"Authorization": "Bearer test-api-token"},
        )
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()), 1)

    def test_rejects_unknown_fields(self):
        response = self.client.post(
            "/proposals",
            headers={"Authorization": "Bearer test-api-token"},
            json={"title": "Draft", "description": "Draft only", "execute_now": True},
        )
        self.assertEqual(response.status_code, 422)

    def test_review_requires_separate_founder_token(self):
        item = self.queue.submit("Draft", "Draft only")
        response = self.client.post(
            f"/proposals/{item['id']}/review",
            headers={"Authorization": "Bearer test-api-token"},
            json={"decision": "approved"},
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.queue.get(item["id"])["status"], "pending_approval")

    def test_founder_review_records_decision_without_execution(self):
        item = self.queue.submit("Draft", "Draft only")
        response = self.client.post(
            f"/proposals/{item['id']}/review",
            headers={"Authorization": "Bearer test-founder-token"},
            json={"decision": "approved", "note": "Reviewed test proposal"},
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["status"], "approved")
        self.assertEqual(result["reviewer"], "founder_api")
        self.assertNotIn("executed", result)
        self.assertNotIn("action_executed", result)

    def test_invalid_status_filter_is_rejected(self):
        response = self.client.get(
            "/proposals?status=anything",
            headers={"Authorization": "Bearer test-api-token"},
        )
        self.assertEqual(response.status_code, 422)

    def test_missing_server_token_configuration_fails_closed(self):
        with patch.dict(os.environ, {"API_BEARER_TOKEN": ""}):
            response = self.client.get(
                "/proposals",
                headers={"Authorization": "Bearer test-api-token"},
            )
        self.assertEqual(response.status_code, 503)


    def test_invalid_api_token_is_rejected(self):
        response = self.client.get(
            "/proposals",
            headers={"Authorization": "Bearer wrong-token"},
        )
        self.assertEqual(response.status_code, 401)

    def test_missing_founder_token_configuration_fails_closed(self):
        with patch.dict(os.environ, {"FOUNDER_BEARER_TOKEN": ""}):
            item = self.queue.submit("Draft", "Draft only")
            response = self.client.post(
                f"/proposals/{item['id']}/review",
                headers={"Authorization": "Bearer test-founder-token"},
                json={"decision": "approved"},
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.queue.get(item["id"])["status"], "pending_approval")

    def test_get_proposal_by_id(self):
        item = self.queue.submit("Draft", "Draft only")
        response = self.client.get(
            f"/proposals/{item['id']}",
            headers={"Authorization": "Bearer test-api-token"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], item["id"])

    def test_rejected_decision_is_recorded_without_execution(self):
        item = self.queue.submit("Draft", "Draft only")
        response = self.client.post(
            f"/proposals/{item['id']}/review",
            headers={"Authorization": "Bearer test-founder-token"},
            json={"decision": "rejected", "note": "Not approved"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "rejected")
        self.assertNotIn("executed", response.json())
        self.assertNotIn("action_executed", response.json())

    def test_reviewing_an_already_reviewed_proposal_conflicts(self):
        item = self.queue.submit("Draft", "Draft only")
        headers = {"Authorization": "Bearer test-founder-token"}
        first = self.client.post(
            f"/proposals/{item['id']}/review",
            headers=headers,
            json={"decision": "approved"},
        )
        second = self.client.post(
            f"/proposals/{item['id']}/review",
            headers=headers,
            json={"decision": "rejected"},
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(self.queue.get(item["id"])["status"], "approved")

    def test_oversized_payload_is_rejected(self):
        response = self.client.post(
            "/proposals",
            headers={"Authorization": "Bearer test-api-token"},
            json={
                "title": "Draft",
                "description": "Draft only",
                "payload": {"blob": "x" * 10001},
            },
        )
        self.assertEqual(response.status_code, 413)


if __name__ == "__main__":
    unittest.main()
