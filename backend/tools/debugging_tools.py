import re
from typing import Any, Dict
from backend.platform.manifest import PlatformTool, ToolManifest, ToolCategory, RiskLevel
from backend.tools.base import ToolResult
from backend.research.error_diagnostic import error_diagnostic

class TracebackAnalyzerTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="traceback_analyzer",
            name="Traceback Analyzer",
            category=ToolCategory.DEBUGGING,
            description="Systematically parses Python stack traces into exception type, file, line number, and root cause.",
            tags=["traceback", "stack trace", "error", "debugging", "crash"],
            risk_level=RiskLevel.ANALYZE,
            timeout_seconds=3.0
        ))

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "traceback_text": {"type": "string", "description": "The raw traceback or error string"}
            },
            "required": ["traceback_text"]
        }

    async def execute(self, traceback_text: str = "", **kwargs) -> ToolResult:
        diag = error_diagnostic.analyze_error(traceback_text)
        return ToolResult(success=True, data={
            "is_error": diag.is_error,
            "error_type": diag.error_type,
            "error_message": diag.error_message,
            "file": diag.faulting_file,
            "line": diag.line_number,
            "missing_symbol": diag.faulting_symbol,
            "suggested_queries": diag.suggested_queries
        })
