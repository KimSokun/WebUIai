import time
from typing import Any, Dict, Optional
from backend.tools.base import BaseTool, ToolResult

class CodeSelfHealTool(BaseTool):
    """Autonomous iterative code repair engine: diagnoses tracebacks and auto-patches buggy code."""
    def __init__(self):
        super().__init__(
            name="code.self_heal",
            description="Autonomous multi-turn code healing: runs code in sandbox, catches exceptions, applies fixes, and re-tests until PASS.",
            risk_level="MEDIUM",
            requires_confirmation=False
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Buggy or incomplete code snippet"},
                "test_script": {"type": "string", "description": "Validation test script (e.g. assert / unittest statements)"},
                "filename": {"type": "string", "description": "Target script filename in sandbox (default 'script.py')"}
            },
            "required": ["code"]
        }

    async def execute(self, **kwargs) -> ToolResult:
        code = str(kwargs.get("code", "")).strip()
        test_script = kwargs.get("test_script")
        filename = str(kwargs.get("filename", "script.py")).strip()

        if not code:
            return ToolResult(success=False, data=None, error="Code parameter is required.")

        start_t = time.perf_counter()
        from backend.engine.self_healing import self_healing_engine
        result = await self_healing_engine.auto_heal_code(
            code=code,
            test_script=test_script,
            filename=filename,
            max_retries=3
        )
        elapsed = (time.perf_counter() - start_t) * 1000

        is_success = result.get("status") == "RESOLVED"
        return ToolResult(
            success=is_success,
            data=result,
            error=None if is_success else "Could not fully resolve all bugs within max iterations.",
            execution_time_ms=elapsed
        )
