import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.knowledge import knowledge_store, KnowledgeEntry

class TestVerifiedKnowledgeStore(unittest.TestCase):
    def test_seed_knowledge_exists(self):
        entry = knowledge_store.get_entry("gguf", "gguf_binary_format_specification")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.source_type, "SPEC")
        self.assertEqual(entry.verification_status, "VERIFIED")

    def test_crud_and_search(self):
        new_entry = KnowledgeEntry(
            topic="AsyncIO TaskGroup in Python 3.11",
            category="python",
            content="TaskGroup provides a safe way to manage concurrent tasks with exception groups.",
            source="https://docs.python.org/3/library/asyncio-task.html",
            source_type="DOCS",
            version="3.11+"
        )
        file_path = knowledge_store.add_entry(new_entry)
        self.assertTrue(file_path.exists())

        search_results = knowledge_store.search("TaskGroup", category="python")
        self.assertGreater(len(search_results), 0)
        self.assertEqual(search_results[0].topic, "AsyncIO TaskGroup in Python 3.11")

    def test_freshness_status_transition(self):
        old_entry = KnowledgeEntry(
            topic="Old Python 2 syntax",
            category="python",
            content="print statement without parentheses",
            source="historical archive",
            source_type="COMMUNITY",
            version="2.7",
            verification_status="VERIFIED"
        )
        old_entry.updated_at = 0.0  # 1970
        status = knowledge_store.check_freshness(old_entry, max_age_days=30.0)
        self.assertEqual(status, "OUTDATED")

if __name__ == "__main__":
    unittest.main()
