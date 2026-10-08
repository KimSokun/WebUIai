import sys
import asyncio
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.tools.codebase import CodebaseSearchTool, CodebaseReadTool, CodebaseStructureTool
from backend.config import BASE_DIR

class TestCodebaseTools(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.search_tool = CodebaseSearchTool()
        self.read_tool = CodebaseReadTool()
        self.struct_tool = CodebaseStructureTool()

    async def test_codebase_search_found(self):
        result = await self.search_tool.execute(query="BASE_DIR", subfolder="backend")
        self.assertTrue(result.success, f"Search failed: {result.error}")
        self.assertIsInstance(result.data, list)
        self.assertGreater(len(result.data), 0, "Expected at least one match for BASE_DIR in backend")
        first_match = result.data[0]
        self.assertIn("file", first_match)
        self.assertIn("line", first_match)
        self.assertIn("snippet", first_match)

    async def test_codebase_search_empty(self):
        result = await self.search_tool.execute(query="")
        self.assertFalse(result.success)
        self.assertIn("empty", result.error.lower())

    async def test_codebase_read_success(self):
        result = await self.read_tool.execute(file_path="backend/config.py", start_line=1, end_line=15)
        self.assertTrue(result.success, f"Read failed: {result.error}")
        self.assertIsInstance(result.data, dict)
        self.assertEqual(result.data["start_line"], 1)
        self.assertGreaterEqual(result.data["total_lines"], 10)
        self.assertIn("BASE_DIR", result.data["content"])

    async def test_codebase_read_traversal_blocked(self):
        result = await self.read_tool.execute(file_path="../../Windows/System32/drivers/etc/hosts")
        self.assertFalse(result.success)
        self.assertIn("access denied", result.error.lower())

    async def test_codebase_structure(self):
        result = await self.struct_tool.execute(max_depth=2)
        self.assertTrue(result.success, f"Structure failed: {result.error}")
        self.assertIsInstance(result.data, dict)
        self.assertIn("backend", result.data)
        self.assertIn("tests", result.data)

if __name__ == "__main__":
    unittest.main()
