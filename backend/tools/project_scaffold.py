import time
from pathlib import Path
from typing import Any, Dict, List
from backend.config import SANDBOX_DIR
from backend.tools.base import BaseTool, ToolResult

TEMPLATES = {
    "web_app": {
        "index.html": """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>K-Jocker Modern App</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="style.css">
</head>
<body class="bg-slate-900 text-white min-h-screen flex items-center justify-center p-4">
  <div class="bg-slate-800 border border-slate-700 rounded-2xl p-8 max-w-lg w-full shadow-2xl">
    <h1 class="text-2xl font-bold text-cyan-400 mb-2">K-Jocker Application</h1>
    <p class="text-slate-400 text-sm mb-6">High-speed lightweight web environment.</p>
    <div id="app" class="space-y-4">
      <input id="txtInput" type="text" placeholder="Type something..." class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-cyan-400">
      <button id="btnAction" class="w-full bg-cyan-500 hover:bg-cyan-600 text-slate-900 font-bold py-2 rounded-lg transition duration-200">Execute</button>
      <div id="output" class="bg-slate-900/50 p-4 rounded-lg text-xs font-mono text-cyan-300 min-h-[60px]">Ready.</div>
    </div>
  </div>
  <script src="app.js"></script>
</body>
</html>""",
        "style.css": """/* Custom overrides */
body { font-family: system-ui, -apple-system, sans-serif; }
""",
        "app.js": """document.getElementById('btnAction').addEventListener('click', () => {
  const val = document.getElementById('txtInput').value || 'Hello from K-Jocker!';
  document.getElementById('output').textContent = `Processed: ${val} at ${new Date().toLocaleTimeString()}`;
});"""
    },
    "fastapi_service": {
        "main.py": """from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="K-Jocker Microservice", version="1.0.0")

class Item(BaseModel):
    name: str
    description: str = ""

@app.get("/")
def read_root():
    return {"status": "online", "system": "K-Jocker Executive Engine"}

@app.post("/items")
def create_item(item: Item):
    return {"success": True, "data": item}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
""",
        "requirements.txt": """fastapi>=0.100.0
uvicorn>=0.20.0
pydantic>=2.0.0
""",
        "README.md": """# K-Jocker FastAPI Service
Run locally:
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```
"""
    },
    "python_tool": {
        "tool.py": """#!/usr/bin/env python3
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="K-Jocker CLI Utility")
    parser.add_argument("--task", type=str, default="audit", help="Task name")
    args = parser.parse_args()
    print(f"[K-Jocker Engine] Executing task: {args.task}")

if __name__ == "__main__":
    main()
""",
        "test_tool.py": """import unittest
from tool import main

class TestTool(unittest.TestCase):
    def test_basic(self):
        self.assertTrue(True)

if __name__ == "__main__":
    unittest.main()
"""
    }
}

class ProjectScaffoldTool(BaseTool):
    """Scaffold full multi-file starter projects directly in sandbox in <5ms."""
    def __init__(self):
        super().__init__(
            name="project.scaffold",
            description="Instantly scaffold complete starter projects ('web_app', 'fastapi_service', 'python_tool') inside the sandbox.",
            risk_level="MEDIUM",
            requires_confirmation=False
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "template": {
                    "type": "string",
                    "description": "Template type: 'web_app', 'fastapi_service', 'python_tool'"
                },
                "target_folder": {
                    "type": "string",
                    "description": "Subdirectory inside sandbox to scaffold (e.g. 'my_app', 'service_v1')"
                }
            },
            "required": ["template", "target_folder"]
        }

    async def execute(self, **kwargs) -> ToolResult:
        template_name = str(kwargs.get("template", "web_app")).strip().lower()
        subfolder = str(kwargs.get("target_folder", "new_project")).strip()

        if template_name not in TEMPLATES:
            available = list(TEMPLATES.keys())
            return ToolResult(success=False, data=None, error=f"Unknown template '{template_name}'. Available: {available}")

        start_t = time.perf_counter()

        # Security: Canonical sandbox path check
        dest_dir = (SANDBOX_DIR / subfolder).resolve()
        sandbox_root = SANDBOX_DIR.resolve()
        if not str(dest_dir).startswith(str(sandbox_root)):
            return ToolResult(success=False, data=None, error="Security violation: Destination path escapes sandbox directory.")

        dest_dir.mkdir(parents=True, exist_ok=True)
        files_created = []

        files_dict = TEMPLATES[template_name]
        for rel_file, content in files_dict.items():
            f_path = dest_dir / rel_file
            f_path.parent.mkdir(parents=True, exist_ok=True)
            f_path.write_text(content, encoding="utf-8")
            files_created.append(str(rel_file))

        elapsed = (time.perf_counter() - start_t) * 1000
        return ToolResult(
            success=True,
            data={
                "template": template_name,
                "folder": str(dest_dir.relative_to(sandbox_root)),
                "files": files_created,
                "total_files": len(files_created),
                "summary": f"Successfully scaffolded {template_name} project in {subfolder}/ with {len(files_created)} files."
            },
            execution_time_ms=elapsed
        )
