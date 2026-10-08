import sys
import asyncio
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.tools.search import WebSearchTool
from backend.tools.fetch import WebFetchTool
from backend.tools.sandbox import LocalFilesSandboxTool
from backend.config import system_config

async def run_tool_tests():
    print("Testing Sandbox Local Files Tool...")
    sandbox = LocalFilesSandboxTool()
    
    # 1. List files
    res_list = await sandbox.execute(action="list")
    assert res_list.success is True, f"List failed: {res_list.error}"
    assert any(f["name"] == "welcome.txt" for f in res_list.data["files"])
    print(" - List files [PASS]")

    # 2. Read file
    res_read = await sandbox.execute(action="read", filename="welcome.txt")
    assert res_read.success is True
    assert "K-Jocker Owner AI" in res_read.data["content"]
    print(" - Read file [PASS]")

    # 3. Write file
    res_write = await sandbox.execute(action="write", filename="test_output.txt", content="Testing 123")
    assert res_write.success is True
    print(" - Write file [PASS]")

    # 4. Policy toggle
    system_config.tools.local_files_enabled = False
    res_blocked = await sandbox.execute(action="list")
    assert res_blocked.success is False
    assert "disabled by Owner policy" in res_blocked.error
    system_config.tools.local_files_enabled = True
    print(" - Tool policy disable [PASS]")

    print("\nTesting Web Search Tool...")
    search = WebSearchTool()
    res_search = await search.execute(query="Cambodia technology")
    assert res_search.success is True
    assert len(res_search.data) > 0
    print(f" - Web search returned {len(res_search.data)} results [PASS]")

    print("\nALL TOOL TESTS PASSED [PASS]!")

if __name__ == "__main__":
    asyncio.run(run_tool_tests())
