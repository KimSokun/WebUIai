import time
from pathlib import Path
from typing import Any, Dict
from backend.config import SANDBOX_DIR
from backend.tools.base import BaseTool, ToolResult

class SandboxPreviewTool(BaseTool):
    """Provides live HTTP preview URLs for web applications, HTML files, and dashboards inside sandbox."""
    def __init__(self):
        super().__init__(
            name="sandbox.preview",
            description="Generate a live browser preview URL (http://127.0.0.1:8000/sandbox/...) for any web app or HTML page in sandbox.",
            risk_level="LOW",
            requires_confirmation=False
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "target_path": {
                    "type": "string",
                    "description": "Folder or HTML file name inside sandbox (e.g. 'my_app', 'calculator/index.html')"
                }
            },
            "required": ["target_path"]
        }

    async def execute(self, **kwargs) -> ToolResult:
        rel = str(kwargs.get("target_path") or kwargs.get("path") or "").strip().replace("\\", "/")
        if not rel:
            return ToolResult(success=False, data=None, error="target_path or path parameter is required.")

        start_t = time.perf_counter()

        # Security: Canonical sandbox check
        dest = (SANDBOX_DIR / rel).resolve()
        root = SANDBOX_DIR.resolve()
        if not str(dest).startswith(str(root)):
            return ToolResult(success=False, data=None, error="Sandbox violation: Path escapes sandbox boundary.")

        # Determine target file and entry point
        file_type = "unknown"
        entry_point = None
        if dest.is_dir():
            for cand_name in ["index.html", "index.htm", "index.js", "app.html", "app.js"]:
                candidate = dest / cand_name
                if candidate.exists():
                    entry_point = cand_name
                    dest = candidate
                    rel = f"{rel.rstrip('/')}/{cand_name}"
                    break
            if not entry_point:
                rel = rel.rstrip('/') + "/"

        rel_clean = rel.lstrip("/")
        if dest.is_file():
            file_type = dest.suffix.lower().lstrip(".")
        elif rel_clean.endswith(".html") or rel_clean.endswith(".htm"):
            file_type = "html"
        elif rel_clean.endswith(".js"):
            file_type = "js"

        preview_url = f"http://127.0.0.1:8000/sandbox/{rel_clean}"
        exists = dest.exists()

        elapsed = (time.perf_counter() - start_t) * 1000
        return ToolResult(
            success=True,
            data={
                "preview_url": preview_url,
                "file_path": str(dest.relative_to(root)) if exists else rel_clean,
                "exists": exists,
                "file_type": file_type,
                "entry_point": entry_point,
                "is_html": file_type == "html",
                "markdown_link": f"[🚀 Open Live App Preview]({preview_url})"
            },
            execution_time_ms=elapsed
        )

