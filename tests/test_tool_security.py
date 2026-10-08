import sys
import asyncio
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.platform.executor import tool_execution_manager
from backend.platform.manifest import PlatformTool, ToolManifest, ToolCategory, RiskLevel
from backend.platform.registry import tool_platform
from backend.tools.base import ToolResult

class OwnerRestrictedTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="owner_restricted_test_tool",
            name="Owner Only Test Tool",
            category=ToolCategory.SECURITY,
            description="Testing owner authorization lock.",
            risk_level=RiskLevel.OWNER_ONLY,
            requires_owner_auth=True
        ))
    def get_input_schema(self):
        return {"type": "object", "properties": {}}
    async def execute(self, **kwargs):
        return ToolResult(success=True, data="Sensitive owner action executed")

tool_platform.register(OwnerRestrictedTool(), category="security", risk="OWNER_ONLY")

class TestToolSecurity(unittest.IsolatedAsyncioTestCase):
    async def test_owner_only_rejection_unauthenticated(self):
        res = await tool_execution_manager.execute_tool("owner_restricted_test_tool", {}, is_owner=False)
        self.assertFalse(res.success)
        self.assertIn("PERMISSION_DENIED", res.error)

    async def test_owner_only_success_authenticated(self):
        res = await tool_execution_manager.execute_tool("owner_restricted_test_tool", {}, is_owner=True)
        self.assertTrue(res.success)
        self.assertEqual(res.data, "Sensitive owner action executed")

    async def test_invalid_argument_validation(self):
        # file_hash requires 'file_path'
        res = await tool_execution_manager.execute_tool("file_hash", {})
        self.assertFalse(res.success)
        self.assertIn("Invalid arguments", res.error)

if __name__ == "__main__":
    unittest.main()
