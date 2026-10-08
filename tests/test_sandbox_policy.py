import sys
import asyncio
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.tools.search import WebSearchTool
from backend.tools.fetch import WebFetchTool
from backend.tools.sandbox import LocalFilesSandboxTool
from backend.config import system_config, SANDBOX_DIR, WEB_CACHE_DIR, save_config
from fastapi.testclient import TestClient
from backend.main import app

async def run_sandbox_policy_tests():
    print("==================================================")
    print("[SECURE] RUNNING ONLINE SANDBOX & PERMISSION POLICY TESTS")
    print("==================================================")

    search_tool = WebSearchTool()
    fetch_tool = WebFetchTool()
    sandbox_tool = LocalFilesSandboxTool()

    # ----------------------------------------------------
    # 1. Web Search READ Permission Test
    # ----------------------------------------------------
    print("\n1. Testing Web Search READ Permission...")
    system_config.tools.web_search_enabled = True
    system_config.tools.web_search_allow_read = False

    res_blocked_read = await search_tool.execute(query="test query")
    assert res_blocked_read.success is False, "Web search should fail when READ is disabled"
    assert "Web search READ permission is disabled" in res_blocked_read.error
    print("   [PASS] Web search READ disabled blocks external query correctly.")

    system_config.tools.web_search_allow_read = True
    res_allow_read = await search_tool.execute(query="Cambodia")
    assert res_allow_read.success is True, f"Web search failed: {res_allow_read.error}"
    assert len(res_allow_read.data) > 0
    print(f"   [PASS] Web search READ enabled successfully retrieved {len(res_allow_read.data)} live items.")

    # ----------------------------------------------------
    # 2. Web Search WRITE (Sandbox Cache) Permission Test
    # ----------------------------------------------------
    print("\n2. Testing Web Search WRITE (Sandbox Caching) Permission...")
    # Clear test cache
    for f in WEB_CACHE_DIR.glob("search_*.json"):
        try:
            f.unlink()
        except Exception:
            pass

    # With WRITE = True
    system_config.tools.web_search_allow_write = True
    unique_query_1 = "Phnom Penh"
    res_cache_write = await search_tool.execute(query=unique_query_1)
    assert res_cache_write.success is True, f"Search failed: {res_cache_write.error}"
    cache_files = list(WEB_CACHE_DIR.glob("search_*.json"))
    assert len(cache_files) > 0, "Cache file should be created in sandbox web_cache when WRITE is enabled"
    print(f"   [PASS] Search cache created in sandbox: {cache_files[0].name}")

    # With WRITE = False
    system_config.tools.web_search_allow_write = False
    initial_count = len(list(WEB_CACHE_DIR.glob("search_*.json")))
    await asyncio.sleep(0.5)
    unique_query_2 = "Angkor Wat"
    res_no_cache = await search_tool.execute(query=unique_query_2)
    assert res_no_cache.success is True, f"Search failed: {res_no_cache.error}"
    current_count = len(list(WEB_CACHE_DIR.glob("search_*.json")))
    assert current_count == initial_count, "No new cache file should be created on disk when WRITE is disabled"
    print("   [PASS] Search operated strictly in-memory without disk writes when WRITE disabled.")

    # ----------------------------------------------------
    # 3. Web Fetch READ & Sandbox Cache Permission Test
    # ----------------------------------------------------
    print("\n3. Testing Web Fetch READ Permission...")
    system_config.tools.web_search_allow_read = False
    res_fetch_blocked = await fetch_tool.execute(url="https://example.com")
    assert res_fetch_blocked.success is False
    assert "Web fetch READ permission is disabled" in res_fetch_blocked.error
    print("   [PASS] Web fetch blocked when READ is disabled.")
    system_config.tools.web_search_allow_read = True

    # ----------------------------------------------------
    # 4. Sandbox Local Files READ Permission Test
    # ----------------------------------------------------
    print("\n4. Testing Sandbox Local Files READ Permission...")
    system_config.tools.sandbox_read_enabled = False

    res_list_blocked = await sandbox_tool.execute(action="list")
    assert res_list_blocked.success is False
    assert "Sandbox READ permission is disabled" in res_list_blocked.error
    print("   [PASS] Sandbox list blocked when READ is disabled.")

    res_read_blocked = await sandbox_tool.execute(action="read", filename="welcome.txt")
    assert res_read_blocked.success is False
    assert "Sandbox READ permission is disabled" in res_read_blocked.error
    print("   [PASS] Sandbox read blocked when READ is disabled.")

    system_config.tools.sandbox_read_enabled = True
    res_read_allowed = await sandbox_tool.execute(action="read", filename="welcome.txt")
    assert res_read_allowed.success is True
    print("   [PASS] Sandbox read permitted when READ is enabled.")

    # ----------------------------------------------------
    # 5. Sandbox Local Files WRITE Permission Test
    # ----------------------------------------------------
    print("\n5. Testing Sandbox Local Files WRITE Permission...")
    system_config.tools.sandbox_write_enabled = False
    res_write_blocked = await sandbox_tool.execute(action="write", filename="blocked.txt", content="Danger")
    assert res_write_blocked.success is False
    assert "Sandbox WRITE permission is disabled" in res_write_blocked.error
    print("   [PASS] Sandbox write blocked when WRITE is disabled.")

    system_config.tools.sandbox_write_enabled = True
    res_write_allowed = await sandbox_tool.execute(action="write", filename="allowed.txt", content="Owner Authorized")
    assert res_write_allowed.success is True
    assert (SANDBOX_DIR / "allowed.txt").exists()
    print("   [PASS] Sandbox write permitted and strictly isolated inside sandbox folder.")

    # ----------------------------------------------------
    # 6. Path Traversal & Host Jail Security Test
    # ----------------------------------------------------
    print("\n6. Testing Sandbox Path Traversal Jail Enforcement...")
    traversal_paths = [
        "../../test.txt",
        "..\\..\\windows\\system32\\calc.exe",
        "/etc/passwd",
        "C:\\Windows\\System32\\cmd.exe"
    ]
    for p in traversal_paths:
        res_trav = await sandbox_tool.execute(action="read", filename=p)
        assert res_trav.success is False
        assert "Path traversal blocked" in res_trav.error or "Access outside sandbox" in res_trav.error
    print("   [PASS] All directory traversal and external filesystem escapes blocked.")

    # ----------------------------------------------------
    # 7. API /api/tools/toggle Endpoint Test
    # ----------------------------------------------------
    print("\n7. Testing API Policy Toggle Endpoint...")
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {system_config.owner.auth_token}"}

    # Test toggling web_search_write off
    resp = client.post("/api/tools/toggle?tool_id=web_search_write&enabled=false", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["policy"]["web_search_allow_write"] is False
    assert system_config.tools.web_search_allow_write is False
    print("   [PASS] API successfully toggled web_search_write to False.")

    # Test toggling web_search_write back on
    resp2 = client.post("/api/tools/toggle?tool_id=web_search_write&enabled=true", headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["policy"]["web_search_allow_write"] is True
    print("   [PASS] API successfully toggled web_search_write back to True.")

    # Restore default enabled settings
    system_config.tools.web_search_enabled = True
    system_config.tools.web_search_allow_read = True
    system_config.tools.web_search_allow_write = True
    system_config.tools.sandbox_read_enabled = True
    system_config.tools.sandbox_write_enabled = True
    system_config.tools.online_sandbox_strict_mode = True
    save_config(system_config)

    print("\n==================================================")
    print("[PASS] ALL ONLINE SANDBOX & PERMISSION TESTS PASSED!")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(run_sandbox_policy_tests())
