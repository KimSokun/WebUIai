import shutil
import difflib
import subprocess
from pathlib import Path
from typing import Dict, Any
from backend.platform.manifest import PlatformTool, ToolManifest, ToolCategory, RiskLevel, ToolResult
from backend.config import BASE_DIR

class GitStatusTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="git.status",
            name="Git Status Inspection",
            category=ToolCategory.GIT,
            description="Inspect Git repository status or detect if git binary is present.",
            tags=["git", "status", "vcs", "repository"],
            risk_level=RiskLevel.READ
        ))
    def get_input_schema(self):
        return {"type": "object", "properties": {}}
    async def execute(self, **kwargs) -> ToolResult:
        git_bin = shutil.which("git")
        if not git_bin:
            return ToolResult(success=True, data={
                "git_installed": False,
                "message": "git executable is not in PATH. Fallback Python difflib engine is active for diff and change tracking."
            })
        try:
            res = subprocess.run(["git", "status", "--short"], cwd=str(BASE_DIR), capture_output=True, text=True, timeout=5.0)
            return ToolResult(success=res.returncode == 0, data={
                "git_installed": True,
                "output": res.stdout.strip()
            })
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))

class GitDiffTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="git.diff",
            name="Git / Difflib Unified Diff",
            category=ToolCategory.GIT,
            description="Compute unified diff between two file contents or repository diff.",
            tags=["git", "diff", "patch", "difflib"],
            risk_level=RiskLevel.READ
        ))
    def get_input_schema(self):
        return {
            "type": "object",
            "properties": {
                "original_text": {"type": "string", "description": "Original text"},
                "new_text": {"type": "string", "description": "New modified text"},
                "filename": {"type": "string", "description": "Filename reference (optional)", "default": "code.py"}
            },
            "required": ["original_text", "new_text"]
        }
    async def execute(self, original_text: str = "", new_text: str = "", filename: str = "code.py", **kwargs) -> ToolResult:
        diff = list(difflib.unified_diff(
            original_text.splitlines(keepends=True),
            new_text.splitlines(keepends=True),
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}"
        ))
        diff_text = "".join(diff)
        return ToolResult(success=True, data={"filename": filename, "diff": diff_text, "has_changes": len(diff_text) > 0})
