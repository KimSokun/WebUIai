import sys
import unittest
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.config import SANDBOX_DIR
from backend.tools.fast_utility_suite import FastCalcTool, UnitConvertTool, TextCompactTool, RegexExtractTool
from backend.tools.fast_memory_suite import MemoryGetTool, MemorySetTool, MemoryListTool, MemoryDeleteTool, memory_store
from backend.tools.project_scaffold import ProjectScaffoldTool
from backend.tools.code_lint_suite import CodeSyntaxLintTool
from backend.tools.khmer_fast_helper import KhmerFastHelperTool

class TestFastToolsSuite(unittest.IsolatedAsyncioTestCase):
    async def test_fast_calc_arithmetic_and_percentages(self):
        tool = FastCalcTool()
        # Basic arithmetic
        res1 = await tool.execute(expression="15 + 27")
        self.assertTrue(res1.success)
        self.assertEqual(res1.data["result"], 42)

        res2 = await tool.execute(expression="8 * 7")
        self.assertTrue(res2.success)
        self.assertEqual(res2.data["result"], 56)

        # Percentage
        res_pct = await tool.execute(expression="20% of 100")
        self.assertTrue(res_pct.success)
        self.assertEqual(res_pct.data["result"], 20.0)

        # Discount
        res_disc = await tool.execute(expression="100 with 15% off")
        self.assertTrue(res_disc.success)
        self.assertEqual(res_disc.data["result"], 85.0)

        # Date math
        res_date = await tool.execute(expression="today + 3 days")
        self.assertTrue(res_date.success)
        self.assertIn("day_of_week", res_date.data)

        # Execution time < 5ms
        self.assertLess(res1.execution_time_ms, 5.0)

    async def test_unit_convert(self):
        tool = UnitConvertTool()
        # Data storage
        res_mb_gb = await tool.execute(value=2048, from_unit="MB", to_unit="GB")
        self.assertTrue(res_mb_gb.success)
        self.assertEqual(res_mb_gb.data["result"], 2.0)

        # Temperature
        res_c_f = await tool.execute(value=100, from_unit="C", to_unit="F")
        self.assertTrue(res_c_f.success)
        self.assertEqual(res_c_f.data["result"], 212.0)

        # Length
        res_km_mile = await tool.execute(value=10, from_unit="km", to_unit="mile")
        self.assertTrue(res_km_mile.success)
        self.assertAlmostEqual(res_km_mile.data["result"], 6.2137, places=2)

    async def test_text_compact(self):
        tool = TextCompactTool()
        multiline = "Line 1\n\n\n   Line 2   \n\n\nLine 3\n"
        res = await tool.execute(text=multiline, max_chars=50)
        self.assertTrue(res.success)
        self.assertIn("Line 1\nLine 2\nLine 3", res.data["compacted_text"])

    async def test_regex_extract(self):
        tool = RegexExtractTool()
        text = "Contact support@kjocker.ai or admin@kimsokun.com for 192.168.1.1 server info."
        res_email = await tool.execute(text=text, pattern="email")
        self.assertTrue(res_email.success)
        self.assertIn("support@kjocker.ai", res_email.data["matches"])
        self.assertIn("admin@kimsokun.com", res_email.data["matches"])

        res_ip = await tool.execute(text=text, pattern="ip")
        self.assertTrue(res_ip.success)
        self.assertEqual(res_ip.data["matches"], ["192.168.1.1"])

    async def test_fast_memory_lifecycle(self):
        set_tool = MemorySetTool()
        get_tool = MemoryGetTool()
        list_tool = MemoryListTool()
        del_tool = MemoryDeleteTool()

        # Set
        res_set = await set_tool.execute(key="owner_title", value="Owner Kimsokun")
        self.assertTrue(res_set.success)

        # Get
        res_get = await get_tool.execute(key="owner_title")
        self.assertTrue(res_get.success)
        self.assertEqual(res_get.data["value"], "Owner Kimsokun")

        # List
        res_list = await list_tool.execute()
        self.assertTrue(res_list.success)
        keys = [k["key"] for k in res_list.data["keys"]]
        self.assertIn("owner_title", keys)

        # Delete
        res_del = await del_tool.execute(key="owner_title")
        self.assertTrue(res_del.success)

        # Confirm gone
        res_get_after = await get_tool.execute(key="owner_title")
        self.assertFalse(res_get_after.success)

    async def test_project_scaffold_and_security(self):
        tool = ProjectScaffoldTool()
        test_folder = "test_scaffold_app"
        folder_path = SANDBOX_DIR / test_folder
        if folder_path.exists():
            shutil.rmtree(folder_path, ignore_errors=True)

        res = await tool.execute(template="web_app", target_folder=test_folder)
        self.assertTrue(res.success)
        self.assertTrue((folder_path / "index.html").exists())
        self.assertTrue((folder_path / "app.js").exists())
        self.assertTrue((folder_path / "style.css").exists())

        # Security check: Escaping sandbox
        res_escape = await tool.execute(template="web_app", target_folder="../../escaped_app")
        self.assertFalse(res_escape.success)
        self.assertIn("Security violation", res_escape.error)

        # Cleanup
        shutil.rmtree(folder_path, ignore_errors=True)

    async def test_code_syntax_lint(self):
        tool = CodeSyntaxLintTool()
        # Valid Python
        valid_py = "def hello():\n    return 'world'"
        res_py_ok = await tool.execute(code=valid_py, language="python")
        self.assertTrue(res_py_ok.data["valid"])

        # Invalid Python
        invalid_py = "def hello(:\n    return 'world'"
        res_py_err = await tool.execute(code=invalid_py, language="python")
        self.assertFalse(res_py_err.data["valid"])
        self.assertIn("error", res_py_err.data)

        # Valid JSON
        valid_json = '{"name": "K-Jocker", "status": "active"}'
        res_j_ok = await tool.execute(code=valid_json, language="json")
        self.assertTrue(res_j_ok.data["valid"])

        # Invalid JSON
        invalid_json = '{"name": "K-Jocker", missing_quote: 12}'
        res_j_err = await tool.execute(code=invalid_json, language="json")
        self.assertFalse(res_j_err.data["valid"])

    async def test_khmer_fast_helper(self):
        tool = KhmerFastHelperTool()
        # Numeral translation
        res_to_km = await tool.execute(text="2026", action="to_khmer_num")
        self.assertTrue(res_to_km.success)
        self.assertEqual(res_to_km.data["result"], "២០២៦")

        res_to_ar = await tool.execute(text="២០២៦", action="to_arabic_num")
        self.assertTrue(res_to_ar.success)
        self.assertEqual(res_to_ar.data["result"], "2026")

        # Glossary
        res_term = await tool.execute(text="variable", action="glossary")
        self.assertTrue(res_term.success)
        self.assertIn("អថេរ", res_term.data["khmer"])

        # Calendar
        res_day = await tool.execute(text="monday", action="auto")
        self.assertTrue(res_day.success)
        self.assertEqual(res_day.data["khmer"], "ថ្ងៃច័ន្ទ")

if __name__ == "__main__":
    unittest.main()
