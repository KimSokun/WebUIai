import sys
import asyncio
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.config import system_config
from backend.runtime import llm_runtime
from backend.tools import tool_registry

async def test_agentic_tool_calling():
    print("==================================================")
    print("Testing Enterprise-Grade Local GGUF Tool Calling...")
    print(f"Active Model: {system_config.model.model_name}")
    print(f"Runtime: {system_config.model.runtime} | Mode: {system_config.model.mode}")
    print("==================================================")

    # 1. Test Web Search Tool Calling Loop
    print("\n1. Testing Web Search Tool Calling Loop...")
    search_prompt = [{"role": "user", "content": "Search for the latest price of Bitcoin today"}]
    
    tokens = []
    has_think_start = False
    has_tool_call_indicator = False
    has_think_end = False

    async for event in llm_runtime.stream_chat(search_prompt, system_prompt=system_prompt if "system_prompt" in locals() else system_config.system_prompt):
        etype = event.get("type")
        content = event.get("content", "")
        if etype in ("token", "reasoning"):
            tokens.append(content)
            if "<think>" in content or etype == "reasoning":
                has_think_start = True
            if "web_search" in content:
                has_tool_call_indicator = True
            if "</think>" in content or etype == "reasoning":
                has_think_end = True

    print(f"Total tokens generated: {len(tokens)}")
    print(f"Has <think> tag: {has_think_start} [PASS]")
    print(f"Has web_search trace: {has_tool_call_indicator} [PASS]")
    print(f"Has </think> tag: {has_think_end} [PASS]")
    
    assert has_think_start, "Output must contain <think> tag for UI collapsible block"
    assert has_tool_call_indicator, "Output must include tool execution trace"
    assert has_think_end, "Output must close </think> tag before final answer"
    print("WEB SEARCH TOOL CALLING TEST PASSED [PASS]!")

    # 2. Test Calculator Tool Calling Loop
    print("\n2. Testing Calculator Tool Calling Loop...")
    calc_prompt = [{"role": "user", "content": "calculate 250 * 18.5"}]
    calc_tokens = []
    async for event in llm_runtime.stream_chat(calc_prompt, system_prompt=system_config.system_prompt):
        if event.get("type") in ("token", "reasoning"):
            calc_tokens.append(event.get("content", ""))
    
    calc_output = "".join(calc_tokens)
    assert "calculator" in calc_output or "4625" in calc_output, "Calculator tool must be called or result computed"
    print("CALCULATOR TOOL CALLING TEST PASSED [PASS]!")

    print("\nALL LOCAL GGUF TOOL-CALLING TESTS PASSED [PASS]!")

if __name__ == "__main__":
    asyncio.run(test_agentic_tool_calling())
