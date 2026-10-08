import sys
import asyncio
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.platform.workflows import tool_workflows

class TestToolWorkflows(unittest.IsolatedAsyncioTestCase):
    async def test_debug_python_workflow(self):
        broken_code = "raise ZeroDivisionError('Workflow error test')"
        res = await tool_workflows.debug_python("test.py", code_snippet=broken_code, is_owner=True)
        self.assertEqual(res["workflow"], "DebugPython")
        self.assertEqual(res["completed_steps"], 2)
        step1 = res["steps"][0]
        step2 = res["steps"][1]
        self.assertEqual(step1["step"], "execute_test")
        self.assertFalse(step1["result"]["success"])
        self.assertEqual(step2["step"], "traceback_diagnosis")
        self.assertEqual(step2["result"]["data"]["error_type"], "ZeroDivisionError")

    async def test_research_gguf_workflow(self):
        res = await tool_workflows.research_gguf("Qwen2.5-Coder", is_owner=True)
        self.assertEqual(res["workflow"], "ResearchGGUF")
        self.assertEqual(res["completed_steps"], 2)
        hw_step = res["steps"][0]
        self.assertTrue(hw_step["result"]["success"])
        self.assertIn("cpu_physical_cores", hw_step["result"]["data"])

if __name__ == "__main__":
    unittest.main()
