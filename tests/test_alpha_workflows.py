import sys
import asyncio
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.engine.workflows import alpha_workflows

class TestAlphaWorkflows(unittest.IsolatedAsyncioTestCase):
    async def test_definition_of_done_coding_workflow(self):
        """
        Tests the complete 15-step Definition of Done Coding Workflow:
        Understand -> Identify file -> Detect language -> Patch code
        -> Run sandbox tests -> Inspect diff -> Verify -> Report
        """
        orig_code = "def add(x, y):\n    return x - y  # BUG\n"
        patched_code = "def add(x, y):\n    return x + y  # FIXED\n"
        test_script = """from run_sandbox import add
assert add(10, 20) == 30
print("CODING_TEST_SUCCESS")
"""
        res = await alpha_workflows.run_coding_workflow(
            problem_description="Fix arithmetic bug in add function",
            relative_file="run_sandbox.py",
            original_code=orig_code,
            patched_code=patched_code,
            test_script=test_script,
            is_owner=True
        )

        self.assertEqual(res["status"], "PASS")
        self.assertTrue(res["test_passed"])
        self.assertIn("CODING_TEST_SUCCESS", res["stdout"])
        self.assertIn("-    return x - y", res["diff"])
        self.assertIn("+    return x + y", res["diff"])
        print("PASS: Definition of Done Coding Workflow (Patch -> Diff -> Sandbox Test -> Report)")

    async def test_definition_of_done_research_workflow(self):
        """
        Tests Definition of Done Research Workflow:
        Detect version -> Search official docs -> Cross-check -> Conclusion with evidence
        """
        res = await alpha_workflows.run_research_workflow(
            library_or_topic="Pydantic",
            version="2.0.0",
            question="Does Pydantic v2 use model_dump instead of dict?"
        )
        self.assertEqual(res["status"], "PASS")
        self.assertEqual(res["evidence_status"], "VERIFIED")
        self.assertGreater(res["confidence"], 0.8)
        print("PASS: Definition of Done Research Workflow (Cross-checked evidence)")

    async def test_definition_of_done_model_workflow(self):
        """
        Tests Definition of Done Model Workflow:
        Detect hardware -> Model candidates -> Quantization sizing -> Owner authorization
        """
        res = await alpha_workflows.run_model_workflow(task_type="coding", is_owner=True)
        self.assertEqual(res["status"], "PASS")
        self.assertEqual(res["owner_authorization"], "AUTHORIZED")
        self.assertIn("ram_total_gb", res["hardware"])
        self.assertEqual(res["recommended_quantization"], "Q4_K_M")
        print("PASS: Definition of Done Model Workflow (Hardware detection -> Sizing -> Owner check)")

if __name__ == "__main__":
    unittest.main()
