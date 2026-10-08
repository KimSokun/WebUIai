import sys
import asyncio
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.research.package_research import package_registry_tool
from backend.research.conflict_resolver import conflict_resolver, EvidenceItem

class TestPackageResearch(unittest.IsolatedAsyncioTestCase):
    async def test_pypi_query(self):
        res = await package_registry_tool.execute(package_name="fastapi", ecosystem="pypi")
        self.assertTrue(res.success, f"PyPI query failed: {res.error}")
        self.assertEqual(res.data.get("ecosystem"), "PyPI")
        self.assertIsNotNone(res.data.get("latest_version"))

    async def test_npm_query(self):
        res = await package_registry_tool.execute(package_name="svelte", ecosystem="npm")
        self.assertTrue(res.success, f"NPM query failed: {res.error}")
        self.assertEqual(res.data.get("ecosystem"), "npm")
        self.assertIsNotNone(res.data.get("latest_version"))

    def test_conflict_resolver_priority(self):
        ev1 = EvidenceItem(
            claim="Official lifespan event context manager recommended",
            source_url="https://fastapi.tiangolo.com",
            source_type="DOCS",
            priority_tier=2
        )
        ev2 = EvidenceItem(
            claim="Use on_event startup",
            source_url="https://stackoverflow.com/questions/123",
            source_type="STACKOVERFLOW",
            priority_tier=9
        )
        res = conflict_resolver.resolve([ev1, ev2])
        self.assertEqual(res["status"], "FACT")
        self.assertEqual(res["confidence"], "HIGH")
        self.assertEqual(res["conclusion"], ev1.claim)

    def test_conflict_resolver_discrepancy(self):
        ev1 = EvidenceItem(
            claim="Feature is deprecated in v2",
            source_url="https://github.com/repo/releases",
            source_type="RELEASE_NOTES",
            priority_tier=4
        )
        ev2 = EvidenceItem(
            claim="Feature is active and supported in v1",
            source_url="https://docs.official.com",
            source_type="DOCS",
            priority_tier=2
        )
        res = conflict_resolver.resolve([ev1, ev2])
        self.assertEqual(res["status"], "CONFLICTING")
        self.assertIn("Discrepancy detected", res.get("conflict_note", ""))

if __name__ == "__main__":
    unittest.main()
