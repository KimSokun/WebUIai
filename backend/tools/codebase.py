import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from backend.tools.base import BaseTool, ToolResult
from backend.config import BASE_DIR

class CodebaseSearchTool(BaseTool):
    """
    Searches the local K-Jocker project codebase for symbols, function definitions,
    callers, class definitions, and usages to support codebase self-research.
    """
    def __init__(self):
        super().__init__(
            name="codebase_search",
            description="Search local project codebase (backend, tests, config) for functions, classes, callers, or variables.",
            risk_level="LOW",
            requires_confirmation=False
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The symbol, function name, class name, or text to search for"},
                "subfolder": {"type": "string", "description": "Optional subfolder to restrict search (e.g. backend, tests)"}
            },
            "required": ["query"]
        }

    async def execute(self, query: str = "", subfolder: str = "", **kwargs) -> ToolResult:
        start_time = time.time()
        if not query:
            return ToolResult(success=False, data=[], error="Search query cannot be empty.")

        target_dir = BASE_DIR / subfolder if subfolder else BASE_DIR
        if not target_dir.exists():
            return ToolResult(success=False, data=[], error=f"Directory '{subfolder}' not found.")

        matches: List[Dict[str, Any]] = []
        try:
            pattern = re.compile(re.escape(query), re.IGNORECASE)
            # Scan only python, json, md, and bat files in project
            for ext in ("*.py", "*.json", "*.md", "*.bat"):
                for file_path in target_dir.rglob(ext):
                    if any(part in file_path.parts for part in ("__pycache__", ".git", "sandbox")):
                        continue
                    try:
                        text = file_path.read_text(encoding="utf-8", errors="replace")
                        for idx, line in enumerate(text.splitlines(), start=1):
                            if pattern.search(line):
                                rel_path = file_path.relative_to(BASE_DIR)
                                matches.append({
                                    "file": str(rel_path).replace("\\", "/"),
                                    "line": idx,
                                    "snippet": line.strip()[:160]
                                })
                                if len(matches) >= 30:
                                    break
                    except Exception:
                        continue
                if len(matches) >= 30:
                    break

            elapsed = (time.time() - start_time) * 1000
            return ToolResult(
                success=True,
                data=matches,
                execution_time_ms=elapsed
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=[],
                error=f"Codebase search error: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000
            )

class CodebaseReadTool(BaseTool):
    """
    Reads code files from the local K-Jocker project codebase with line-number slices.
    Strictly read-only.
    """
    def __init__(self):
        super().__init__(
            name="codebase_read",
            description="Read lines from a local project file to inspect definitions, callers, or implementations.",
            risk_level="LOW",
            requires_confirmation=False
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Relative path to file inside project (e.g. backend/main.py)"},
                "start_line": {"type": "integer", "description": "Starting line number (1-indexed)", "default": 1},
                "end_line": {"type": "integer", "description": "Ending line number (inclusive)", "default": 100}
            },
            "required": ["file_path"]
        }

    async def execute(self, file_path: str = "", start_line: int = 1, end_line: int = 100, **kwargs) -> ToolResult:
        start_time = time.time()
        clean_rel = file_path.strip().lstrip("/\\")
        target = (BASE_DIR / clean_rel).resolve()

        # Security check: must reside inside BASE_DIR
        try:
            target.relative_to(BASE_DIR.resolve())
        except ValueError:
            return ToolResult(success=False, data=None, error="Access denied: Cannot read files outside project root.")

        if not target.exists() or not target.is_file():
            return ToolResult(success=False, data=None, error=f"File '{file_path}' does not exist.")

        try:
            lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
            total_lines = len(lines)
            s_idx = max(1, start_line)
            e_idx = min(total_lines, max(s_idx, end_line))

            selected = lines[s_idx - 1:e_idx]
            numbered = [f"{idx}: {l}" for idx, l in enumerate(selected, start=s_idx)]

            return ToolResult(
                success=True,
                data={
                    "file": clean_rel.replace("\\", "/"),
                    "start_line": s_idx,
                    "end_line": e_idx,
                    "total_lines": total_lines,
                    "content": "\n".join(numbered)
                },
                execution_time_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"Error reading file '{file_path}': {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000
            )

class CodebaseStructureTool(BaseTool):
    """
    Summarizes the project architectural structure and files.
    """
    def __init__(self):
        super().__init__(
            name="codebase_structure",
            description="Inspect the architectural layout of the K-Jocker project directories and modules.",
            risk_level="LOW",
            requires_confirmation=False
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "max_depth": {"type": "integer", "description": "Maximum directory depth to scan", "default": 2}
            }
        }

    async def execute(self, max_depth: int = 2, **kwargs) -> ToolResult:
        start_time = time.time()
        structure: Dict[str, List[str]] = {}

        try:
            for item in sorted(BASE_DIR.glob("*")):
                if item.name.startswith(".") or item.name in ("__pycache__", "sandbox"):
                    continue
                if item.is_dir():
                    files = [f.name for f in sorted(item.glob("*")) if not f.name.startswith(".") and f.is_file()]
                    structure[item.name] = files[:15]
                else:
                    if "root" not in structure:
                        structure["root"] = []
                    structure["root"].append(item.name)

            return ToolResult(
                success=True,
                data=structure,
                execution_time_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data={},
                error=f"Structure scan error: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000
            )
