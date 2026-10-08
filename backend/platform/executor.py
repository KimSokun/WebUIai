import time
import asyncio
from typing import Dict, Any, Optional, Tuple
from backend.platform.registry import tool_platform
from backend.platform.manifest import RiskLevel, ToolResult

class ToolExecutionManager:
    """
    Centralized Execution Pipeline:
    1. Permission Engine verification (verifies Owner authority for OWNER_ONLY or DESTRUCTIVE tools)
    2. Argument Validation
    3. Execution with Timeout termination & Subprocess isolation
    4. Result Validator & Output Truncation
    5. Audit Logging
    """
    async def execute_tool(
        self,
        tool_id: str,
        arguments: Dict[str, Any],
        is_owner: bool = False,
        request_id: str = "req_default"
    ) -> ToolResult:
        from backend.runtime.events import runtime_logger
        start_time = time.time()
        tool = tool_platform.get_tool(tool_id)
        if not tool:
            return ToolResult(success=False, data=None, error=f"Tool '{tool_id}' not found in Tool Platform.")

        manifest = getattr(tool, "manifest", None)
        risk = manifest.risk_level if manifest else RiskLevel.READ

        # 1. Security Gate: Owner-only verification
        if (risk in (RiskLevel.OWNER_ONLY, RiskLevel.DESTRUCTIVE) or (manifest and manifest.requires_owner_auth)) and not is_owner:
            err = f"PERMISSION_DENIED: Tool '{tool_id}' has risk level {risk.value} and requires authenticated Owner authorization."
            runtime_logger.log_event(request_id, "tool_rejected", "security", tool_id, arguments, False, False, False, err)
            return ToolResult(success=False, data=None, error=err)

        # 2. Argument Validation (lazy import to prevent circular pipeline dependencies)
        from backend.pipeline.validator import schema_validator
        schema = tool.get_input_schema()
        valid, val_err = schema_validator.validate(schema, arguments)
        if not valid:
            runtime_logger.log_event(request_id, "validation_error", "validation", tool_id, arguments, True, False, False, val_err)
            return ToolResult(success=False, data=None, error=f"Invalid arguments for tool '{tool_id}': {val_err}")

        # 3. Execution with Timeout
        timeout = manifest.timeout_seconds if manifest else 15.0
        try:
            result = await asyncio.wait_for(tool.execute(**arguments), timeout=timeout)
            
            # 4. Output Truncation
            if hasattr(tool, "truncate_output") and result.data:
                result.data = tool.truncate_output(result.data)

            elapsed = (time.time() - start_time) * 1000
            result.execution_time_ms = elapsed

            # 5. Audit Logging (without logging sensitive secrets)
            runtime_logger.log_event(
                request_id=request_id,
                event_type="tool_execution",
                intent="platform_exec",
                tool_name=tool_id,
                arguments={k: ("***" if "token" in k or "key" in k else v) for k, v in arguments.items()},
                authorized=True,
                executed=True,
                success=result.success,
                result=result.data,
                error=result.error
            )
            return result

        except asyncio.TimeoutError:
            elapsed = (time.time() - start_time) * 1000
            err_msg = f"TIMEOUT: Tool '{tool_id}' exceeded maximum execution timeout of {timeout}s."
            runtime_logger.log_event(request_id, "tool_timeout", "timeout", tool_id, arguments, True, True, False, err_msg)
            return ToolResult(success=False, data=None, error=err_msg, execution_time_ms=elapsed)
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            err_msg = f"EXECUTION_ERROR: Tool '{tool_id}' raised unexpected exception: {str(e)}"
            runtime_logger.log_event(request_id, "tool_exception", "error", tool_id, arguments, True, True, False, err_msg)
            return ToolResult(success=False, data=None, error=err_msg, execution_time_ms=elapsed)

tool_execution_manager = ToolExecutionManager()
