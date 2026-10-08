import hashlib
import time
from pathlib import Path
from typing import Any, Dict, List
from backend.platform.manifest import PlatformTool, ToolManifest, ToolCategory, RiskLevel
from backend.tools.base import ToolResult
from backend.config import BASE_DIR, SANDBOX_DIR

class SearchFilesTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="search_files",
            name="Search Files",
            category=ToolCategory.FILESYSTEM,
            description="Find files in project workspace matching glob pattern (e.g. '*.py', '**/*.json').",
            tags=["files", "glob", "search", "find"],
            risk_level=RiskLevel.READ,
            timeout_seconds=5.0
        ))

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Glob pattern (e.g. '*.py')"},
                "subfolder": {"type": "string", "description": "Subdirectory to restrict search"}
            },
            "required": ["pattern"]
        }

    async def execute(self, pattern: str = "*", subfolder: str = "", **kwargs) -> ToolResult:
        base = BASE_DIR / subfolder if subfolder else BASE_DIR
        matches = [str(f.relative_to(BASE_DIR)).replace("\\", "/") for f in base.glob(pattern) if not any(x in f.parts for x in [".git", "__pycache__"])]
        return ToolResult(success=True, data=matches[:50])

class ReadFileRangeTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="read_file_range",
            name="Read File Range",
            category=ToolCategory.FILESYSTEM,
            description="Reads a slice of lines from a workspace file with line numbers.",
            tags=["read", "range", "lines", "slice"],
            risk_level=RiskLevel.READ,
            timeout_seconds=5.0
        ))

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to file"},
                "start_line": {"type": "integer", "default": 1},
                "end_line": {"type": "integer", "default": 50}
            },
            "required": ["file_path"]
        }

    async def execute(self, file_path: str = "", start_line: int = 1, end_line: int = 50, **kwargs) -> ToolResult:
        target = (BASE_DIR / file_path.strip().lstrip("/\\")).resolve()
        try:
            target.relative_to(BASE_DIR.resolve())
        except ValueError:
            return ToolResult(success=False, data=None, error="Access denied: Cannot read outside project root.")
        if not target.exists() or not target.is_file():
            return ToolResult(success=False, data=None, error=f"File '{file_path}' not found.")
        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        s = max(1, start_line)
        e = min(len(lines), max(s, end_line))
        content = "\n".join(f"{idx}: {line}" for idx, line in enumerate(lines[s-1:e], start=s))
        return ToolResult(success=True, data={"lines": content, "start": s, "end": e, "total": len(lines)})

class FileHashTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="file_hash",
            name="Calculate File Hash",
            category=ToolCategory.FILESYSTEM,
            description="Calculates cryptographic SHA256 or MD5 checksum of a local file.",
            tags=["hash", "sha256", "checksum", "integrity"],
            risk_level=RiskLevel.ANALYZE,
            timeout_seconds=5.0
        ))

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Relative file path"},
                "algorithm": {"type": "string", "enum": ["sha256", "md5"], "default": "sha256"}
            },
            "required": ["file_path"]
        }

    async def execute(self, file_path: str = "", algorithm: str = "sha256", **kwargs) -> ToolResult:
        target = (BASE_DIR / file_path.strip().lstrip("/\\")).resolve()
        if not target.exists() or not target.is_file():
            return ToolResult(success=False, data=None, error="File not found.")
        h = hashlib.sha256() if algorithm == "sha256" else hashlib.md5()
        h.update(target.read_bytes())
        return ToolResult(success=True, data={"file": file_path, "algorithm": algorithm, "hash": h.hexdigest()})
