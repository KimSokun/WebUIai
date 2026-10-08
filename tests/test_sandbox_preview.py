import sys
import unittest
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from fastapi.testclient import TestClient
from backend.config import SANDBOX_DIR
from backend.main import app
from backend.tools.preview_tools import SandboxPreviewTool

class TestSandboxPreview(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
        self.test_dir = SANDBOX_DIR / "preview_test_suite"
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.client = TestClient(app)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    async def test_preview_html_file(self):
        html_file = self.test_dir / "index.html"
        html_file.write_text("<!DOCTYPE html><html><body><h1>Sandbox App Preview</h1></body></html>", encoding="utf-8")

        tool = SandboxPreviewTool()
        res = await tool.execute(path="preview_test_suite/index.html")
        self.assertTrue(res.success)
        self.assertEqual(res.data["file_type"], "html")
        self.assertIn("/sandbox/preview_test_suite/index.html", res.data["preview_url"])
        self.assertTrue(res.data["exists"])

    async def test_preview_directory_auto_detects_index_html(self):
        app_dir = self.test_dir / "dashboard"
        app_dir.mkdir(parents=True, exist_ok=True)
        (app_dir / "index.html").write_text("<h1>Dashboard</h1>", encoding="utf-8")

        tool = SandboxPreviewTool()
        res = await tool.execute(path="preview_test_suite/dashboard")
        self.assertTrue(res.success)
        self.assertEqual(res.data["entry_point"], "index.html")
        self.assertIn("/sandbox/preview_test_suite/dashboard/index.html", res.data["preview_url"])

    async def test_preview_directory_auto_detects_index_js(self):
        js_dir = self.test_dir / "jsapp"
        js_dir.mkdir(parents=True, exist_ok=True)
        (js_dir / "index.js").write_text("console.log('App');", encoding="utf-8")

        tool = SandboxPreviewTool()
        res = await tool.execute(path="preview_test_suite/jsapp")
        self.assertTrue(res.success)
        self.assertEqual(res.data["entry_point"], "index.js")
        self.assertEqual(res.data["file_type"], "js")

    async def test_preview_path_traversal_blocked(self):
        tool = SandboxPreviewTool()
        res = await tool.execute(path="../../../windows/system32")
        self.assertFalse(res.success)
        self.assertIn("Sandbox violation", res.error)

    def test_api_sandbox_apps_endpoint(self):
        demo_app = self.test_dir / "my_web_app"
        demo_app.mkdir(parents=True, exist_ok=True)
        (demo_app / "index.html").write_text("<h1>Hello App</h1>", encoding="utf-8")

        response = self.client.get("/api/sandbox/apps")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        apps = data.get("apps", [])
        self.assertIsInstance(apps, list)
        found = any(app_item.get("name") == "my_web_app" for app_item in apps)
        self.assertTrue(found)

    def test_sandbox_static_mount_serves_html(self):
        mount_file = self.test_dir / "served.html"
        mount_file.write_text("<p>Static Content Served</p>", encoding="utf-8")

        response = self.client.get("/sandbox/preview_test_suite/served.html")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Static Content Served", response.text)

if __name__ == "__main__":
    unittest.main()
