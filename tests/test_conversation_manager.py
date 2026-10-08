import sys
import unittest
import tempfile
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.conversations import ConversationManager

class TestConversationManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_path = Path(self.temp_dir.name)
        self.mgr = ConversationManager(storage_dir=self.storage_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_sanitize_id(self):
        self.assertEqual(self.mgr._sanitize_id("chat_123-abc.v1"), "chat_123-abc.v1")
        # Traversal attempt should be sanitized
        self.assertEqual(self.mgr._sanitize_id("../../evil_chat"), "______evil_chat")
        # Empty string generates timestamp-based id
        generated = self.mgr._sanitize_id("")
        self.assertTrue(generated.startswith("conv_"))

    def test_save_and_get_conversation(self):
        data = {
            "name": "K-Jocker Test Session",
            "model": "gemma-3-4b-it",
            "messages": [
                {"id": "m1", "role": "user", "content": "Hello K-Jocker"},
                {"id": "m2", "role": "assistant", "content": "Welcome Owner Kimsokun"}
            ]
        }
        saved = self.mgr.save_conversation("session_001", data)
        self.assertEqual(saved["id"], "session_001")
        self.assertEqual(saved["name"], "K-Jocker Test Session")
        self.assertIn("lastModified", saved)

        # Retrieve
        retrieved = self.mgr.get_conversation("session_001")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["id"], "session_001")
        self.assertEqual(len(retrieved["messages"]), 2)
        self.assertEqual(retrieved["messages"][1]["content"], "Welcome Owner Kimsokun")

        # Physical file exists
        file_path = self.storage_path / "session_001.json"
        self.assertTrue(file_path.exists())

    def test_get_nonexistent_conversation(self):
        self.assertIsNone(self.mgr.get_conversation("nonexistent_id"))

    def test_list_conversations_sorted(self):
        # Save chat 1
        self.mgr.save_conversation("chat1", {
            "name": "Old Chat",
            "lastModified": 1000,
            "messages": [{"id": "1"}]
        })
        # Save chat 2
        self.mgr.save_conversation("chat2", {
            "name": "New Chat",
            "lastModified": 5000,
            "messages": [{"id": "1"}, {"id": "2"}]
        })
        # Save chat 3
        self.mgr.save_conversation("chat3", {
            "name": "Mid Chat",
            "lastModified": 3000,
            "messages": []
        })

        summaries = self.mgr.list_conversations()
        self.assertEqual(len(summaries), 3)
        # Should be ordered descending: chat2 (5000), chat3 (3000), chat1 (1000)
        self.assertEqual(summaries[0]["id"], "chat2")
        self.assertEqual(summaries[0]["messageCount"], 2)
        self.assertEqual(summaries[1]["id"], "chat3")
        self.assertEqual(summaries[1]["messageCount"], 0)
        self.assertEqual(summaries[2]["id"], "chat1")
        self.assertEqual(summaries[2]["messageCount"], 1)

    def test_delete_conversation_physical(self):
        self.mgr.save_conversation("del_target", {"name": "To Delete"})
        file_path = self.storage_path / "del_target.json"
        self.assertTrue(file_path.exists())

        # Physical deletion
        deleted = self.mgr.delete_conversation("del_target")
        self.assertTrue(deleted)
        self.assertFalse(file_path.exists())
        self.assertIsNone(self.mgr.get_conversation("del_target"))

        # Deleting again returns False
        self.assertFalse(self.mgr.delete_conversation("del_target"))

    def test_bulk_delete_conversations(self):
        for i in range(5):
            self.mgr.save_conversation(f"bulk_{i}", {"name": f"Chat {i}"})
        self.assertEqual(len(self.mgr.list_conversations()), 5)

        deleted_count = self.mgr.bulk_delete_conversations(["bulk_0", "bulk_2", "bulk_4", "non_existent"])
        self.assertEqual(deleted_count, 3)
        remaining = self.mgr.list_conversations()
        self.assertEqual(len(remaining), 2)
        remaining_ids = {c["id"] for c in remaining}
        self.assertEqual(remaining_ids, {"bulk_1", "bulk_3"})

    def test_delete_all_conversations(self):
        for i in range(4):
            self.mgr.save_conversation(f"all_{i}", {"name": f"Chat {i}"})
        self.assertEqual(len(self.mgr.list_conversations()), 4)

        deleted_count = self.mgr.delete_all_conversations()
        self.assertEqual(deleted_count, 4)
        self.assertEqual(len(self.mgr.list_conversations()), 0)
        self.assertEqual(len(list(self.storage_path.glob("*.json"))), 0)

if __name__ == "__main__":
    unittest.main()
