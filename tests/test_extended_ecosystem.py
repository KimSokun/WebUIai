import sys
import asyncio
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.tools.hardware_tools import CPUInfoTool, RAMInfoTool
from backend.tools.code_intelligence import FindDefinitionTool, FindCallersTool, DetectSecurityIssueTool, DetectUnusedCodeTool
from backend.tools.filesystem_tools import SearchFilesTool, ReadFileRangeTool, FileHashTool
from backend.tools.debugging_tools import TracebackAnalyzerTool
from backend.tools.khmer_tools import KhmerLanguageDetectTool, KhmerTerminologyLookupTool
from backend.tools.benchmark_tools import BenchmarkLatencyTool

class TestExtendedEcosystem(unittest.IsolatedAsyncioTestCase):
    async def test_hardware_tools(self):
        cpu = CPUInfoTool()
        ram = RAMInfoTool()
        r_cpu = await cpu.execute()
        r_ram = await ram.execute()
        self.assertTrue(r_cpu.success)
        self.assertGreater(r_cpu.data["physical_cores"], 0)
        self.assertTrue(r_ram.success)
        self.assertGreater(r_ram.data["total_gb"], 0)

    async def test_code_intelligence_definition(self):
        find_def = FindDefinitionTool()
        res = await find_def.execute(symbol_name="LLMRuntime")
        self.assertTrue(res.success)
        self.assertGreater(len(res.data), 0)
        self.assertEqual(res.data[0]["file"], "backend/runtime/llm_runtime.py")

    async def test_code_intelligence_callers(self):
        callers = FindCallersTool()
        res = await callers.execute(function_name="load_config")
        self.assertTrue(res.success)
        self.assertGreater(len(res.data), 0)

    async def test_security_issue_detection(self):
        sec = DetectSecurityIssueTool()
        code_with_eval = "user_input = '1+1'; result = eval(user_input)"
        res = await sec.execute(code_or_file=code_with_eval)
        self.assertTrue(res.success)
        self.assertEqual(res.data["issues_found"], 1)
        self.assertIn("CRITICAL", res.data["findings"][0]["issue"])

    async def test_unused_code_detection(self):
        unused = DetectUnusedCodeTool()
        code = "import os\nimport sys\nprint(os.name)"
        res = await unused.execute(code=code)
        self.assertTrue(res.success)
        self.assertIn("sys", res.data["unused_imports"])

    async def test_filesystem_tools(self):
        search = SearchFilesTool()
        res = await search.execute(pattern="*.py", subfolder="backend/tools")
        self.assertTrue(res.success)
        self.assertGreater(len(res.data), 5)

        fhash = FileHashTool()
        h_res = await fhash.execute(file_path="backend/config.py")
        self.assertTrue(h_res.success)
        self.assertEqual(len(h_res.data["hash"]), 64)

    async def test_khmer_tools(self):
        detect = KhmerLanguageDetectTool()
        res = await detect.execute(text="សូមជួយ fix កូដនេះ")
        self.assertTrue(res.success)
        self.assertTrue(res.data["has_khmer"])
        self.assertEqual(res.data["primary_intent"], "code_fix")

        lookup = KhmerTerminologyLookupTool()
        res_l = await lookup.execute(english_term="backend")
        self.assertTrue(res_l.success)
        self.assertEqual(res_l.data["dual_term"], "ផ្នែកខាងក្រោយ (Backend)")

if __name__ == "__main__":
    unittest.main()
