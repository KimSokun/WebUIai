import ast
import json
import time
from typing import Any, Dict
from backend.tools.base import BaseTool, ToolResult

class CodeSyntaxLintTool(BaseTool):
    """In-memory fast AST syntax and format validation (<0.5ms)."""
    def __init__(self):
        super().__init__(
            name="code.syntax_lint",
            description="Fast syntax check for Python, JSON, and HTML/XML code snippets without subprocess overhead.",
            risk_level="LOW",
            requires_confirmation=False
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Code string to check"},
                "language": {"type": "string", "description": "Language: 'python', 'json', 'html', 'auto'"}
            },
            "required": ["code"]
        }

    async def execute(self, **kwargs) -> ToolResult:
        code = str(kwargs.get("code", "")).strip()
        lang = str(kwargs.get("language", "auto")).lower().strip()

        if not code:
            return ToolResult(success=False, data=None, error="Code parameter cannot be empty.")

        start_t = time.perf_counter()

        # Auto detection
        if lang == "auto":
            if (code.startswith("{") and code.endswith("}")) or (code.startswith("[") and code.endswith("]")):
                lang = "json"
            elif "<html" in code.lower() or ("<div" in code.lower() and "</" in code):
                lang = "html"
            else:
                lang = "python"

        if lang == "python":
            try:
                ast.parse(code)
                elapsed = (time.perf_counter() - start_t) * 1000
                return ToolResult(success=True, data={"valid": True, "language": "python", "message": "Python syntax is 100% valid."}, execution_time_ms=elapsed)
            except SyntaxError as se:
                elapsed = (time.perf_counter() - start_t) * 1000
                return ToolResult(success=True, data={
                    "valid": False,
                    "language": "python",
                    "error": se.msg,
                    "line": se.lineno,
                    "offset": se.offset,
                    "text": se.text
                }, execution_time_ms=elapsed)

        elif lang == "json":
            try:
                json.loads(code)
                elapsed = (time.perf_counter() - start_t) * 1000
                return ToolResult(success=True, data={"valid": True, "language": "json", "message": "JSON structure is 100% valid."}, execution_time_ms=elapsed)
            except json.JSONDecodeError as je:
                elapsed = (time.perf_counter() - start_t) * 1000
                return ToolResult(success=True, data={
                    "valid": False,
                    "language": "json",
                    "error": je.msg,
                    "line": je.lineno,
                    "col": je.colno
                }, execution_time_ms=elapsed)

        elif lang == "html":
            # Tag balance check
            import re
            tags = re.findall(r'<([a-zA-Z0-9]+)[^>]*>|<\/([a-zA-Z0-9]+)>', code)
            stack = []
            void_tags = {"meta", "link", "img", "br", "hr", "input", "source"}
            errors = []
            for open_t, close_t in tags:
                if open_t:
                    t_lower = open_t.lower()
                    if t_lower not in void_tags:
                        stack.append(t_lower)
                elif close_t:
                    t_lower = close_t.lower()
                    if not stack or stack[-1] != t_lower:
                        errors.append(f"Mismatched closing tag </{close_t}>")
                    else:
                        stack.pop()

            elapsed = (time.perf_counter() - start_t) * 1000
            is_valid = len(errors) == 0 and len(stack) == 0
            return ToolResult(success=True, data={
                "valid": is_valid,
                "language": "html",
                "unclosed_tags": stack,
                "tag_errors": errors
            }, execution_time_ms=elapsed)

        return ToolResult(success=False, data=None, error=f"Unsupported linting language: {lang}")
