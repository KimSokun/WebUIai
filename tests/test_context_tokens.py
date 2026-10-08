"""
Unit test suite for Context Token Counter, llama.cpp timings telemetry,
OpenAI router proxy endpoints (/tokenize, /detokenize, /slots, /props),
and SSE streaming timings payload compatibility.
"""
import sys
import unittest
import json
from unittest.mock import patch, AsyncMock
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from fastapi.testclient import TestClient
from backend.main import app
from backend.runtime.token_counter import FastTokenCounter, count_tokens, count_messages_tokens
from backend.config import system_config

class TestContextTokens(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.counter = FastTokenCounter()

    # -------------------------------------------------------------
    # 1. Fast Token Counter Unit Tests
    # -------------------------------------------------------------
    def test_token_counter_english(self):
        text = "Hello world! This is a test of the fast token estimator."
        tokens = self.counter.estimate_tokens(text)
        self.assertGreaterEqual(tokens, 10)
        self.assertLessEqual(tokens, 20)

    def test_token_counter_khmer(self):
        khmer_text = "សួស្តីពិភពលោក! ខ្ញុំជាជំនួយការ AI របស់អ្នក។"
        tokens = self.counter.estimate_tokens(khmer_text)
        self.assertGreater(tokens, 5)

    def test_token_counter_code(self):
        code_text = "def calculate_speed(tokens: int, ms: float) -> float:\n    return (tokens / ms) * 1000.0"
        tokens = self.counter.estimate_tokens(code_text)
        self.assertGreater(tokens, 15)

    def test_token_counter_empty_and_whitespace(self):
        self.assertEqual(self.counter.estimate_tokens(""), 0)
        self.assertEqual(self.counter.estimate_tokens("   \n\t  "), 0)

    def test_count_messages_tokens(self):
        messages = [
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": "Python is an interpreted programming language."}
        ]
        total = count_messages_tokens(messages, system_prompt="You are a helpful assistant.")
        self.assertGreater(total, 15)

    # -------------------------------------------------------------
    # 2. Tokenize & Detokenize Endpoints
    # -------------------------------------------------------------
    def test_tokenize_endpoint(self):
        payload = {"content": "Test tokenization string"}
        resp = self.client.post("/tokenize", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("tokens", data)
        self.assertIsInstance(data["tokens"], list)
        self.assertGreater(len(data["tokens"]), 0)

    def test_detokenize_endpoint(self):
        payload = {"tokens": [100, 200, 300]}
        resp = self.client.post("/detokenize", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("content", data)
        self.assertIsInstance(data["content"], str)

    # -------------------------------------------------------------
    # 3. Slots & Props n_ctx Telemetry
    # -------------------------------------------------------------
    def test_slots_reports_n_ctx(self):
        resp = self.client.get("/slots")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        slot = data[0]
        self.assertIn("n_ctx", slot)
        self.assertGreater(slot["n_ctx"], 0)
        self.assertIn("id_task", slot)

    def test_props_reports_default_generation_settings(self):
        resp = self.client.get("/props")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("default_generation_settings", data)
        settings = data["default_generation_settings"]
        self.assertIn("n_ctx", settings)
        self.assertGreater(settings["n_ctx"], 0)

    # -------------------------------------------------------------
    # 4. OpenAI Chat Completions - Streaming Telemetry
    # -------------------------------------------------------------
    @patch("backend.openai_router.llm_runtime.stream_chat")
    def test_chat_completions_streaming_timings(self, mock_loop):
        async def mock_generator(*args, **kwargs):
            yield {"type": "content", "content": "Hello"}
            yield {"type": "content", "content": " world from K-Jocker!"}

        mock_loop.return_value = mock_generator()

        payload = {
            "model": "qwen2.5-coder-7b",
            "messages": [
                {"role": "user", "content": "Hello AI"}
            ],
            "stream": True
        }

        resp = self.client.post("/v1/chat/completions", json=payload)
        self.assertEqual(resp.status_code, 200)
        lines = [line if isinstance(line, str) else line.decode("utf-8") for line in resp.iter_lines() if line]

        has_timings = False
        final_stop_found = False
        final_timings = None

        for line in lines:
            if line.startswith("data: ") and line != "data: [DONE]":
                chunk = json.loads(line[6:])
                if "timings" in chunk:
                    has_timings = True
                    t = chunk["timings"]
                    self.assertIn("prompt_n", t)
                    self.assertIn("predicted_n", t)
                    self.assertIn("predicted_per_second", t)
                
                # Check finish_reason == stop chunk
                choices = chunk.get("choices", [])
                if choices and choices[0].get("finish_reason") == "stop":
                    final_stop_found = True
                    final_timings = chunk.get("timings")

        self.assertTrue(has_timings, "Expected at least one SSE chunk with timings")
        self.assertTrue(final_stop_found, "Expected final stop chunk")
        self.assertIsNotNone(final_timings, "Expected final stop chunk to contain timings")
        self.assertGreater(final_timings["predicted_n"], 0)
        self.assertGreater(final_timings["prompt_n"], 0)

    # -------------------------------------------------------------
    # 5. OpenAI Chat Completions - Non-Streaming Telemetry
    # -------------------------------------------------------------
    @patch("backend.openai_router.llm_runtime.stream_chat")
    def test_chat_completions_non_streaming_timings(self, mock_loop):
        async def mock_generator(*args, **kwargs):
            yield {"type": "content", "content": "Non-streaming answer."}

        mock_loop.return_value = mock_generator()

        payload = {
            "model": "qwen2.5-coder-7b",
            "messages": [
                {"role": "user", "content": "Give me a quick answer"}
            ],
            "stream": False
        }

        resp = self.client.post("/v1/chat/completions", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertIn("timings", data)
        self.assertIn("usage", data)
        t = data["timings"]
        self.assertGreater(t["prompt_n"], 0)
        self.assertGreater(t["predicted_n"], 0)
        self.assertIn("predicted_per_second", t)

        u = data["usage"]
        self.assertEqual(u["prompt_tokens"], t["prompt_n"])
        self.assertEqual(u["completion_tokens"], t["predicted_n"])
        self.assertEqual(u["total_tokens"], t["prompt_n"] + t["predicted_n"])

if __name__ == "__main__":
    unittest.main()
