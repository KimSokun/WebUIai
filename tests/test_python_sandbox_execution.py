import sys
import asyncio
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.tools.python_executor import python_executor_tool

class TestPythonSandboxExecution(unittest.IsolatedAsyncioTestCase):
    async def test_successful_execution(self):
        code = "print(100 * 45)"
        res = await python_executor_tool.execute(code=code)
        self.assertTrue(res.success, f"Execution failed: {res.error}")
        self.assertEqual(res.data["stdout"], "4500")
        self.assertEqual(res.data["exit_code"], 0)

    async def test_stderr_capture(self):
        code = "raise ValueError('Custom test error')"
        res = await python_executor_tool.execute(code=code)
        self.assertFalse(res.success)
        self.assertIn("ValueError", res.data["stderr"])
        self.assertNotEqual(res.data["exit_code"], 0)

    async def test_infinite_loop_timeout_protection(self):
        code = "while True: pass"
        res = await python_executor_tool.execute(code=code, timeout_seconds=1.0)
        self.assertFalse(res.success)
        self.assertIn("timed out", res.error.lower())

if __name__ == "__main__":
    unittest.main()
