import unittest
import asyncio
from backend.tools.doc_analyzer import DocAnalyzeTool
from backend.tools import tool_registry
from backend.pipeline.permission_gate import permission_gate
from backend.pipeline.router import intent_router
from backend.runtime.llm_runtime import format_display_result

class TestDocAnalyzerAndRouterTurbo(unittest.TestCase):
    def setUp(self):
        self.tool = DocAnalyzeTool()
        self.master_prompt = (
            "Master Prompt — Runtime Integration Upgrade.md\n"
            "13.61 KB\n"
            "# MASTER PROMPT — LOCAL GGUF AGENT RUNTIME INTEGRATION UPGRADE\n\n"
            "You are a senior AI systems architect and Python runtime engineer.\n\n"
            "Upgrade the existing runtime to support local GGUF models.\n"
            "RULES:\n"
            "- Rule 1: No external unverified dependencies\n"
            "- Rule 2: Strict high-performance CPU execution\n"
            "Action items:\n"
            "1. upgrade the engine backend\n"
            "2. optimize batching with flash attention\n\n"
            "Referenced files: backend/models_manager.py, backend/pipeline/router.py\n\n"
            "help me analay this\n"
        )

    def test_doc_analyzer_execution_speed_and_structure(self):
        async def run_test():
            result = await self.tool.execute(text=self.master_prompt)
            self.assertTrue(result.success)
            self.assertIsNotNone(result.data)
            self.assertIn("MASTER PROMPT", result.data["title"])
            self.assertIn("senior AI systems architect", result.data["role_mission"])
            self.assertGreater(result.data["approx_tokens"], 10)
            self.assertGreater(len(result.data["action_tasks"]), 0)
            self.assertGreater(len(result.data["key_rules"]), 0)
            self.assertLess(result.execution_time_ms, 50.0)

        asyncio.run(run_test())

    def test_doc_analyzer_empty_input(self):
        async def run_test():
            result = await self.tool.execute(text="")
            self.assertFalse(result.success)
            self.assertIn("empty", result.error.lower())

        asyncio.run(run_test())

    def test_permission_gate_doc_analyze(self):
        ok, err = permission_gate.verify("doc.analyze", {"text": self.master_prompt})
        self.assertTrue(ok)
        self.assertIsNone(err)

        ok_alt, err_alt = permission_gate.verify("doc_analyze", {"text": self.master_prompt})
        self.assertTrue(ok_alt)
        self.assertIsNone(err_alt)

    def test_tool_registry_doc_analyze(self):
        t1 = tool_registry.get_tool("doc.analyze")
        self.assertIsNotNone(t1)
        t2 = tool_registry.get_tool("doc_analyze")
        self.assertIsNotNone(t2)

    def test_router_never_calls_web_search_on_master_prompt(self):
        intent, allowed = intent_router.classify_intent(self.master_prompt)
        tool_name, params = intent_router.route(self.master_prompt)
        self.assertNotEqual(tool_name, "web_search", "Router must NOT trigger web_search on Master Prompt / spec")
        self.assertEqual(tool_name, "doc.analyze")
        self.assertEqual(params.get("text"), self.master_prompt.strip())

    def test_router_long_document_false_positive_shield(self):
        long_doc = (
            "# System Architecture Specification 2026\n\n"
            "Today we document where is the primary database located and latest news updates.\n"
            "Guidelines and requirements:\n"
            "- Must enforce sandbox boundaries\n"
            "- Search indexes must be rebuilt daily\n\n"
            "Tasks:\n"
            "1. Implement cache reuse\n"
            "2. Optimize prompt ingestion\n\n"
            "Please review and summarize this document.\n"
        )
        long_doc = long_doc + ("\nAdditional system details..." * 15)
        intent, allowed = intent_router.classify_intent(long_doc)
        tool_name, params = intent_router.route(long_doc)
        self.assertNotEqual(tool_name, "web_search", "Router must not trigger web_search on long document review")
        self.assertEqual(tool_name, "doc.analyze")

    def test_router_explicit_search_still_works(self):
        search_query = "search for latest python 3.12 features"
        tool_name, params = intent_router.route(search_query)
        self.assertEqual(tool_name, "web_search")
        self.assertEqual(params.get("query"), "latest python 3.12 features")

    def test_runtime_observation_formatting(self):
        mock_data = {
            "title": "Test Doc",
            "role_mission": "Test Architect",
            "approx_tokens": 1500,
            "analysis_time_ms": 1.2,
            "key_headers": ["# Header 1", "## Header 2"],
            "action_tasks": ["Task 1", "Task 2"],
            "key_rules": ["Rule 1"]
        }
        obs = format_display_result("doc.analyze", mock_data)
        self.assertIn("Fast Document Analysis", obs)
        self.assertIn("Test Doc", obs)
        self.assertIn("Task 1", obs)

if __name__ == "__main__":
    unittest.main()
