import sys
import asyncio
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.tools import tool_registry
from backend.platform.executor import tool_execution_manager

class TestCoreToolsSuite(unittest.IsolatedAsyncioTestCase):
    async def test_fs_tools(self):
        # 1. fs.create
        res_create = await tool_execution_manager.execute_tool("fs.create", {
            "filename": "alpha_test.txt",
            "content": "Hello K-Jocker Production Engine Alpha"
        }, is_owner=True)
        self.assertTrue(res_create.success)

        # 2. fs.read
        res_read = await tool_execution_manager.execute_tool("fs.read", {
            "file_path": "workspace/sandbox/alpha_test.txt"
        }, is_owner=True)
        self.assertTrue(res_read.success)
        self.assertIn("Hello K-Jocker", res_read.data["content"])

        # 3. fs.patch
        res_patch = await tool_execution_manager.execute_tool("fs.patch", {
            "filename": "alpha_test.txt",
            "target_text": "Hello K-Jocker",
            "replacement_text": "Verified K-Jocker"
        }, is_owner=True)
        self.assertTrue(res_patch.success)

        # 4. fs.metadata
        res_meta = await tool_execution_manager.execute_tool("fs.metadata", {
            "file_path": "workspace/sandbox/alpha_test.txt"
        }, is_owner=True)
        self.assertTrue(res_meta.success)
        self.assertGreater(res_meta.data["size_bytes"], 0)
        print("PASS: fs.* suite (create, read, patch, metadata)")

    async def test_terminal_suite(self):
        # 1. terminal.detect (Safe read)
        res_detect = await tool_execution_manager.execute_tool("terminal.detect", {}, is_owner=False)
        self.assertTrue(res_detect.success)
        self.assertIn("powershell", res_detect.data)

        # 2. terminal.powershell blocked for non-owner (OWNER_ONLY)
        res_pwsh_unauth = await tool_execution_manager.execute_tool("terminal.powershell", {
            "command": "Write-Output 'test'"
        }, is_owner=False)
        self.assertFalse(res_pwsh_unauth.success)
        self.assertIn("PERMISSION_DENIED", res_pwsh_unauth.error)

        # 3. terminal.powershell allowed for authenticated owner
        res_pwsh_auth = await tool_execution_manager.execute_tool("terminal.powershell", {
            "command": "Write-Output 'KJocker_Alpha_Ready'"
        }, is_owner=True)
        self.assertTrue(res_pwsh_auth.success)
        self.assertIn("KJocker_Alpha_Ready", res_pwsh_auth.data["stdout"])

        # 4. terminal.cmd allowed for authenticated owner
        res_cmd = await tool_execution_manager.execute_tool("terminal.cmd", {
            "command": "echo KJocker_CMD_Ready"
        }, is_owner=True)
        self.assertTrue(res_cmd.success)
        self.assertIn("KJocker_CMD_Ready", res_cmd.data["stdout"])

        # 5. terminal.environment (sanitized secret inspection)
        res_env = await tool_execution_manager.execute_tool("terminal.environment", {}, is_owner=True)
        self.assertTrue(res_env.success)
        self.assertGreater(res_env.data["count"], 0)
        print("PASS: terminal.* suite (detect, owner authorization enforcement, powershell, cmd, environment)")

    async def test_git_difflib_suite(self):
        # git.status detects environment accurately
        res_status = await tool_execution_manager.execute_tool("git.status", {}, is_owner=True)
        self.assertTrue(res_status.success)

        # git.diff computes pure Python difflib unified diff
        res_diff = await tool_execution_manager.execute_tool("git.diff", {
            "original_text": "def calculate(a, b):\n    return a + b\n",
            "new_text": "def calculate(a, b):\n    return a * b\n",
            "filename": "calc.py"
        }, is_owner=True)
        self.assertTrue(res_diff.success)
        self.assertTrue(res_diff.data["has_changes"])
        self.assertIn("-    return a + b", res_diff.data["diff"])
        self.assertIn("+    return a * b", res_diff.data["diff"])
        print("PASS: git.* suite (environment detection + pure Python difflib engine)")

    async def test_web_docs_github_suites(self):
        # web.extract
        res_web = await tool_execution_manager.execute_tool("web.extract", {
            "raw_html_or_text": "<h1>Title</h1><p>Test</p>```python\nprint(1)\n```"
        }, is_owner=True)
        self.assertTrue(res_web.success)
        self.assertIn("Title Test", res_web.data["clean_text"])
        self.assertEqual(len(res_web.data["code_blocks"]), 1)

        # url.validate
        res_url = await tool_execution_manager.execute_tool("url.validate", {
            "url": "http://127.0.0.1:8000/api"
        }, is_owner=True)
        self.assertTrue(res_url.success)
        self.assertTrue(res_url.data["is_private_ip"])

        # docs.specification
        res_docs = await tool_execution_manager.execute_tool("docs.specification", {
            "standard": "python"
        }, is_owner=True)
        self.assertTrue(res_docs.success)

        # github.license
        res_gh = await tool_execution_manager.execute_tool("github.license", {
            "repo": "owner/project"
        }, is_owner=True)
        self.assertTrue(res_gh.success)
        print("PASS: web.*, docs.*, github.* suites")

if __name__ == "__main__":
    unittest.main()
