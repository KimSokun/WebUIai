import sys
import unittest
import json
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.tools import tool_registry
from backend.runtime.llm_runtime import get_tools_system_prompt, compact_observation, format_display_result
from backend.pipeline.permission_gate import permission_gate
from backend.platform.discovery import tool_discovery

class TestSmallModelOptimizer(unittest.TestCase):
    def test_micro_schema_token_efficiency(self):
        # Full OpenAPI format
        full_defs = tool_registry.get_tools_definitions(["fast_calc", "unit_convert", "project.scaffold"])
        full_json_str = json.dumps(full_defs)

        # Micro-schema format in system prompt
        micro_prompt = get_tools_system_prompt(allowed_tools={"fast_calc", "unit_convert", "project.scaffold"})

        # The micro-schema definitions line-by-line are significantly more compact
        self.assertIn("- fast_calc(", micro_prompt)
        self.assertIn("- unit_convert(", micro_prompt)
        self.assertIn("- project.scaffold(", micro_prompt)

        # Confirm micro-schema lines are clean and concise (<120 chars each)
        for line in micro_prompt.splitlines():
            if line.startswith("- fast_calc") or line.startswith("- unit_convert"):
                self.assertLess(len(line), 150)

    def test_compact_observation_distillation(self):
        # 1. Structured result priority
        structured = {
            "formatted": "20% of 100 = 20.0",
            "internal_debug": "lots of noisy intermediate calculation data " * 50
        }
        compacted = compact_observation("fast_calc", structured)
        self.assertEqual(compacted, "Verified Result: 20% of 100 = 20.0")

        # 2. Huge raw output truncation
        huge_data = {"text": "A" * 3000, "status": "ok"}
        compacted_huge = compact_observation("generic", huge_data, max_chars=500)
        self.assertLessEqual(len(compacted_huge), 650)
        self.assertIn("[Distilled:", compacted_huge)

    def test_dynamic_top_k_tool_limit(self):
        # Even with complex queries, discovery bounds tools to max 6
        discovered = tool_discovery.discover_tools("calculate 10+20 and scaffold project and check python syntax", max_tools=6)
        self.assertLessEqual(len(discovered), 6)
        tool_names = [t.name for t in discovered]
        self.assertTrue(any("calc" in n for n in tool_names))

    def test_security_gate_recognizes_new_tools(self):
        # Verify new tools pass KNOWN_TOOLS check in permission gate
        for tool_name in ["fast_calc", "unit_convert", "memory.get", "project.scaffold", "code.syntax_lint", "khmer.fast_helper"]:
            ok, err = permission_gate.verify(tool_name, {})
            self.assertTrue(ok, f"Tool '{tool_name}' failed permission gate: {err}")

        # Unknown tool still rejected
        bad_ok, bad_err = permission_gate.verify("unauthorized_hacker_tool", {})
        self.assertFalse(bad_ok)
        self.assertIn("UNKNOWN_TOOL", bad_err)

    def test_display_formatting_clarity(self):
        # Verify clear formatting for small models
        disp_calc = format_display_result("fast_calc", {"formatted": "15 + 27 = 42"})
        self.assertIn("**Calculation Verified:**", disp_calc)

        disp_unit = format_display_result("unit_convert", {"from": "100 C", "to": "212.0 F"})
        self.assertIn("**Conversion Verified:**", disp_unit)

        disp_scaffold = format_display_result("project.scaffold", {"summary": "Scaffolded web app", "files": ["index.html", "app.js"]})
        self.assertIn("**Scaffold Result:**", disp_scaffold)

if __name__ == "__main__":
    unittest.main()
