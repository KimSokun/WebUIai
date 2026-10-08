import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from fastapi.testclient import TestClient
from backend.main import app
from backend.engine.self_healing import SelfHealingEngine
from backend.tools.self_heal_tools import CodeSelfHealTool

class TestSelfHealingEngine(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = SelfHealingEngine()
        self.client = TestClient(app)

    async def test_syntax_error_colon_healing(self):
        broken_code = "def calculate_total(a, b)\n    return a + b"
        test_script = "assert calculate_total(10, 20) == 30"

        res = await self.engine.auto_heal_code(
            code=broken_code,
            test_script=test_script,
            filename="test_syntax_fix.py",
            max_retries=3
        )
        self.assertEqual(res["status"], "RESOLVED")
        self.assertGreaterEqual(res["iterations"], 1)
        self.assertIn("calculate_total", res["healed_code"])
        self.assertTrue(len(res["diff"]) > 0)

    async def test_missing_standard_import_healing(self):
        broken_code = "def calc_hypot(a, b):\n    return math.sqrt(a**2 + b**2)"
        test_script = "assert calc_hypot(3, 4) == 5.0"

        res = await self.engine.auto_heal_code(
            code=broken_code,
            test_script=test_script,
            filename="test_import_fix.py",
            max_retries=3
        )
        self.assertEqual(res["status"], "RESOLVED")
        self.assertIn("import math", res["healed_code"])

    async def test_code_self_heal_tool_execution(self):
        tool = CodeSelfHealTool()
        res = await tool.execute(
            code="def multiply(x, y)\n    return x * y",
            test_script="assert multiply(6, 7) == 42",
            filename="test_multiply_tool.py"
        )
        self.assertTrue(res.success)
        self.assertEqual(res.data["status"], "RESOLVED")

    def test_api_self_heal_endpoint(self):
        payload = {
            "code": "def greet(name)\n    return f'Hello {name}'",
            "test_script": "assert greet('World') == 'Hello World'",
            "filename": "test_greet_api.py"
        }
        response = self.client.post("/api/engine/self-heal", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("data", {}).get("status"), "RESOLVED")

if __name__ == "__main__":
    unittest.main()
