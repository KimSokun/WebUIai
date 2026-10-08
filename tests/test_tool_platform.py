import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.platform.registry import tool_platform
from backend.platform.discovery import tool_discovery
from backend.tools import tool_registry

class TestToolPlatform(unittest.TestCase):
    def test_registry_size_and_categories(self):
        all_tools = tool_platform.list_all_tools()
        self.assertGreaterEqual(len(all_tools), 25, "Expected at least 25 tools indexed in platform")
        cats = tool_platform.list_categories()
        self.assertIn("documentation", cats)
        self.assertIn("code_intelligence", cats)
        self.assertIn("filesystem", cats)
        self.assertIn("hardware", cats)
        self.assertIn("khmer", cats)

    def test_discovery_fastapi_error(self):
        tools = tool_discovery.discover_tools("Help me fix this FastAPI error", max_tools=5)
        self.assertGreater(len(tools), 0)
        tool_ids = [t.name for t in tools]
        # Should discover debugging, python_execute, or research tools
        has_relevant = any(t in tool_ids for t in ["traceback_analyzer", "python_execute", "web_search", "package_registry"])
        self.assertTrue(has_relevant, f"Expected relevant tool in {tool_ids}")

    def test_discovery_callers(self):
        tools = tool_discovery.discover_tools("find callers of function get_settings", max_tools=5)
        tool_ids = [t.name for t in tools]
        self.assertIn("find_callers", tool_ids)

    def test_discovery_hardware(self):
        tools = tool_discovery.discover_tools("check my cpu and ram specs", max_tools=5)
        tool_ids = [t.name for t in tools]
        has_hw = any(t in tool_ids for t in ["cpu_info", "ram_info", "hardware_capability_detect"])
        self.assertTrue(has_hw, f"Expected hardware tool in {tool_ids}")

    def test_selective_schema_export(self):
        # Guarantee no prompt bloat: export only 2 tools
        subset = {"calculator", "cpu_info"}
        defs = tool_platform.get_tools_definitions(tool_ids=subset)
        self.assertEqual(len(defs), 2)
        names = [d["function"]["name"] for d in defs]
        self.assertIn("calculator", names)
        self.assertIn("cpu_info", names)

if __name__ == "__main__":
    unittest.main()
