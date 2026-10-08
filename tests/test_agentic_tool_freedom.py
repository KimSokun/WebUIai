import sys
import unittest
import asyncio
import json
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.platform.discovery import tool_discovery
from backend.runtime.llm_runtime import get_tools_system_prompt, llm_runtime
from backend.openai_router import execute_tool, ToolExecuteRequest, get_tools

class TestAgenticToolFreedom(unittest.IsolatedAsyncioTestCase):
    def test_dynamic_discovery_khmer_queries(self):
        # Khmer math query
        discovered_math = tool_discovery.discover_tools("សូមជួយគណនា 25 * 40 ឱ្យខ្ញុំ")
        math_names = [t.name for t in discovered_math]
        self.assertIn("calculator", math_names)

        # Khmer filesystem query
        discovered_fs = tool_discovery.discover_tools("ជួយស្វែងរកឯកសារ file នៅក្នុង folder នេះ")
        fs_names = [t.name for t in discovered_fs]
        self.assertTrue(any(n in ("fs.search", "fs.list", "local_files", "search_files", "read_file_range", "file_hash") for n in fs_names))

        # Khmer code / programming query
        discovered_code = tool_discovery.discover_tools("ជួយពិនិត្យកូដ python function នេះបន្តិច")
        code_names = [t.name for t in discovered_code]
        self.assertTrue(any(n in ("python_execute", "codebase_search", "codebase_read") for n in code_names))

    def test_get_tools_system_prompt_empowerment(self):
        # Ensure system prompt never gags the model even with general intent
        prompt = get_tools_system_prompt(allowed_tools=set(), task_description="Hello, can you help me?")
        self.assertNotIn("Available Tools: None required", prompt)
        self.assertNotIn("Do not generate any tool calls", prompt)
        self.assertIn("<tool_call>", prompt)
        self.assertIn("Available K-Jocker Engineering & Research Tools", prompt)

    async def test_openai_tools_list_all_platform_tools(self):
        # Verify /tools endpoint exposes full platform ecosystem
        tools_list = await get_tools()
        self.assertGreaterEqual(len(tools_list), 40)
        tool_names = [t["tool"] for t in tools_list]
        self.assertIn("calculator", tool_names)
        self.assertIn("fs.list", tool_names)
        self.assertIn("git.status", tool_names)
        self.assertIn("web_search", tool_names)

    async def test_openai_execute_tool_platform(self):
        # Test calculator execution via /tools endpoint
        req_calc = ToolExecuteRequest(tool="calculator", params={"expression": "15 * 6"})
        res_calc = await execute_tool(req_calc)
        self.assertFalse(res_calc.get("isError"))
        self.assertEqual(res_calc.get("content"), "90")

        # Test fs.list execution via /tools endpoint
        req_fs = ToolExecuteRequest(tool="fs.list", params={"directory": "."})
        res_fs = await execute_tool(req_fs)
        self.assertFalse(res_fs.get("isError"))
        self.assertIn("items", res_fs.get("content", ""))

    async def test_multi_turn_stream_chat_tool_call_interception(self):
        # Mock adapter to return a tool call in Turn 1, and synthesis in Turn 2
        async def mock_stream_turn(messages, system_prompt="", **kwargs):
            has_tool_obs = any("[Tool Observation" in m.get("content", "") for m in messages)
            if not has_tool_obs:
                yield {"type": "token", "content": '<tool_call>{"name": "calculator", "arguments": {"expression": "12 * 12"}}</tool_call>'}
            else:
                yield {"type": "token", "content": "លទ្ធផលនៃការគណនាគឺ 144"}

        with patch.object(llm_runtime.adapter, "stream_chat", side_effect=mock_stream_turn), \
             patch.object(llm_runtime, "check_connection", return_value=True):

            events = []
            async for event in llm_runtime.stream_chat(
                messages=[{"role": "user", "content": "Calculate 12 * 12"}],
                request_id="test_freedom_req"
            ):
                events.append(event)

            # Check that tool was called, executed, and synthesized
            event_types = [e.get("type") for e in events]
            self.assertIn("tool_call", event_types)
            self.assertIn("done", event_types)

            # Check visible markdown token stream
            tokens_text = "".join(e.get("content", "") for e in events if e.get("type") == "token")
            self.assertIn("Executing Tool", tokens_text)
            self.assertIn("Tool Verified Result", tokens_text)
            self.assertIn("144", tokens_text)

if __name__ == "__main__":
    unittest.main()
