import sys
import unittest
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from fastapi.testclient import TestClient
from backend.main import app
from backend.conversations import conversation_manager

class TestConversationEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.orig_storage = conversation_manager.storage_dir
        conversation_manager.storage_dir = Path(self.temp_dir.name)

    def tearDown(self):
        conversation_manager.storage_dir = self.orig_storage
        self.temp_dir.cleanup()

    def test_create_and_get_conversation(self):
        # 1. Post new conversation
        payload = {
            "id": "api_test_001",
            "name": "API Chat Test",
            "model": "gemma-3-4b-it",
            "messages": [
                {"id": "msg1", "role": "user", "content": "What is Python?"},
                {"id": "msg2", "role": "assistant", "content": "Python is a programming language."}
            ]
        }
        res_post = self.client.post("/api/conversations", json=payload)
        self.assertEqual(res_post.status_code, 200)
        data = res_post.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data["conversation"]["id"], "api_test_001")
        self.assertEqual(data["conversation"]["name"], "API Chat Test")

        # 2. Get the conversation
        res_get = self.client.get("/api/conversations/api_test_001")
        self.assertEqual(res_get.status_code, 200)
        retrieved = res_get.json()
        self.assertEqual(retrieved["id"], "api_test_001")
        self.assertEqual(len(retrieved["messages"]), 2)

    def test_post_auto_generate_id_if_omitted(self):
        res = self.client.post("/api/conversations", json={"name": "Auto ID Chat"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        self.assertTrue(data["conversation"]["id"].startswith("conv_"))

    def test_get_nonexistent_returns_404(self):
        res = self.client.get("/api/conversations/does_not_exist_999")
        self.assertEqual(res.status_code, 404)
        self.assertIn("not found", res.json()["detail"].lower())

    def test_list_conversations(self):
        self.client.post("/api/conversations", json={"id": "c1", "name": "First"})
        self.client.post("/api/conversations", json={"id": "c2", "name": "Second"})

        res = self.client.get("/api/conversations")
        self.assertEqual(res.status_code, 200)
        convs = res.json().get("conversations", [])
        self.assertEqual(len(convs), 2)
        ids = {c["id"] for c in convs}
        self.assertEqual(ids, {"c1", "c2"})

    def test_delete_single_conversation(self):
        self.client.post("/api/conversations", json={"id": "target_del", "name": "Delete Me"})
        # Confirm it exists
        self.assertEqual(self.client.get("/api/conversations/target_del").status_code, 200)

        # Delete it
        res_del = self.client.delete("/api/conversations/target_del")
        self.assertEqual(res_del.status_code, 200)
        self.assertTrue(res_del.json()["success"])
        self.assertTrue(res_del.json()["deleted"])

        # Confirm 404 now
        self.assertEqual(self.client.get("/api/conversations/target_del").status_code, 404)

    def test_bulk_delete_conversations(self):
        for i in range(5):
            self.client.post("/api/conversations", json={"id": f"bulk_api_{i}", "name": f"Chat {i}"})

        res_bulk = self.client.post("/api/conversations/bulk-delete", json={"ids": ["bulk_api_0", "bulk_api_2", "bulk_api_4"]})
        self.assertEqual(res_bulk.status_code, 200)
        self.assertEqual(res_bulk.json()["deleted_count"], 3)

        # Verify only 2 remain
        res_list = self.client.get("/api/conversations")
        remaining = res_list.json().get("conversations", [])
        self.assertEqual(len(remaining), 2)

    def test_delete_all_conversations(self):
        for i in range(3):
            self.client.post("/api/conversations", json={"id": f"all_api_{i}", "name": f"Chat {i}"})

        res_del = self.client.delete("/api/conversations")
        self.assertEqual(res_del.status_code, 200)
        self.assertEqual(res_del.json()["deleted_count"], 3)

        # List should be empty
        res_list = self.client.get("/api/conversations")
        self.assertEqual(len(res_list.json().get("conversations", [])), 0)

if __name__ == "__main__":
    unittest.main()
