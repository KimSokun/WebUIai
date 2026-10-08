import json
import asyncio
from typing import Any, Dict, Optional, Tuple, Set
from backend.tools import tool_registry
from backend.pipeline.validator import schema_validator
from backend.pipeline.permission_gate import permission_gate
from backend.pipeline.router import intent_router
from backend.tools.base import ToolResult
from backend.runtime.events import runtime_logger

class ToolPipeline:
    """
    K-JOCKER Tool Architecture Pipeline:

                        WebUI / Request
                             │
                             ▼
                      Intent / Router
                             │
                      Tool Permission Gate
                             │
                      Schema Validator
                             │
                    Tool Registry Lookup
                             │
                     Real Tool Execution (Timeout & Isolation)
                             │
                   Runtime Evidence Logger
                             │
                        Tool Result
                             │
                        Model Stream
    """
    def __init__(self):
        self.router = intent_router
        self.registry = tool_registry
        self.validator = schema_validator
        self.permission_gate = permission_gate
        self.logger = runtime_logger

    async def execute_pipeline(
        self,
        tool_name: str,
        params: Dict[str, Any],
        allowed_tools: Optional[Set[str]] = None,
        request_id: str = "default_req",
        intent: str = "general",
        timeout: float = 15.0
    ) -> ToolResult:
        """
        Executes stages 3 through 8 of the pipeline:
        Permission Gate -> Registry Lookup -> Schema Validation -> Execution -> Event Log -> Tool Result
        """
        # Stage 3: Tool Permission Gate (enforcing intent and policy)
        allowed, perm_err = self.permission_gate.verify(tool_name, params, allowed_tools=allowed_tools)
        if not allowed:
            self.logger.log_event(
                request_id=request_id,
                event_type="tool_rejected",
                intent=intent,
                tool_name=tool_name,
                arguments=params,
                authorized=False,
                executed=False,
                success=False,
                error=perm_err
            )
            return ToolResult(success=False, data=None, error=perm_err)

        # Stage 4: Tool Registry Lookup
        tool = self.registry.get_tool(tool_name)
        if not tool:
            err_msg = f"UNKNOWN_TOOL: Tool '{tool_name}' not found in Tool Registry."
            self.logger.log_event(
                request_id=request_id,
                event_type="tool_rejected",
                intent=intent,
                tool_name=tool_name,
                arguments=params,
                authorized=False,
                executed=False,
                success=False,
                error=err_msg
            )
            return ToolResult(success=False, data=None, error=err_msg)

        # Stage 5: Schema Validator
        schema = tool.get_input_schema()
        valid, val_err = self.validator.validate(schema, params)
        if not valid:
            self.logger.log_event(
                request_id=request_id,
                event_type="validation_error",
                intent=intent,
                tool_name=tool_name,
                arguments=params,
                authorized=True,
                executed=False,
                success=False,
                error=val_err
            )
            return ToolResult(success=False, data=None, error=val_err)

        # Stage 6: Tool Execution with Timeout & Fault Isolation
        try:
            result = await asyncio.wait_for(tool.execute(**params), timeout=timeout)
            self.logger.log_event(
                request_id=request_id,
                event_type="tool_execution",
                intent=intent,
                tool_name=tool_name,
                arguments=params,
                authorized=True,
                executed=True,
                success=result.success,
                result=result.data,
                error=result.error
            )
            return result
        except asyncio.TimeoutError:
            timeout_err = f"TOOL_TIMEOUT: Tool '{tool_name}' timed out after {timeout}s."
            self.logger.log_event(
                request_id=request_id,
                event_type="tool_timeout",
                intent=intent,
                tool_name=tool_name,
                arguments=params,
                authorized=True,
                executed=True,
                success=False,
                error=timeout_err
            )
            return ToolResult(success=False, data=None, error=timeout_err)
        except Exception as e:
            exec_err = f"Tool Execution Exception: {str(e)}"
            self.logger.log_event(
                request_id=request_id,
                event_type="tool_execution",
                intent=intent,
                tool_name=tool_name,
                arguments=params,
                authorized=True,
                executed=True,
                success=False,
                error=exec_err
            )
            return ToolResult(success=False, data=None, error=exec_err)

    async def process_user_query(
        self,
        user_msg: str,
        request_id: str = "default_req"
    ) -> Tuple[Optional[str], Optional[ToolResult], Optional[str]]:
        """
        Processes stages 1 through 8 for user input:
        1. User Input Analysis
        2. Intent Router (Classifies intent and allowed tools)
        3-6. Pipeline Execution
        7. Observation text formatted for Model context
        Returns: (tool_name, ToolResult, observation_context)
        """
        # Stage 2: Intent / Router
        intent, allowed_tools = self.router.classify_intent(user_msg)
        tool_name, params = self.router.route(user_msg)
        if not tool_name:
            return None, None, None

        # Stages 3-6: Pipeline Execution
        result = await self.execute_pipeline(
            tool_name=tool_name,
            params=params,
            allowed_tools=allowed_tools,
            request_id=request_id,
            intent=intent
        )

        # Stage 7: Format Tool Result into Model Observation Context
        context_observation = self._format_observation(tool_name, params, result)
        return tool_name, result, context_observation

    def _format_observation(self, tool_name: str, params: Dict[str, Any], result: ToolResult) -> str:
        if not result.success:
            return f"Notice on {tool_name}: {result.error}. Inform Owner Kimsokun directly and provide the best available technical explanation."

        if tool_name == "web_search":
            data = result.data or []
            obs = "Real-time Live Web Search Results:\n"
            for item in data[:4]:
                obs += f"- Title: {item.get('title')}\n  Snippet: {item.get('snippet')} [URL: {item.get('link')}]\n\n"
            obs += "Answer Owner Kimsokun's query accurately using these live sources."
            return obs

        elif tool_name == "web_fetch":
            url = params.get("url", "")
            return f"Webpage Content ({url}):\n{result.data[:2500]}\n\nAnalyze and summarize this webpage content for Owner Kimsokun."

        elif tool_name == "calculator":
            expr = params.get("expression", "")
            return f"Calculator evaluated '{expr}' with exact result: {result.data}. Present this verified result clearly to Owner Kimsokun."

        elif tool_name == "local_files":
            action = params.get("action", "list")
            formatted = json.dumps(result.data, indent=2, ensure_ascii=False) if isinstance(result.data, (dict, list)) else str(result.data)
            return f"Sandbox Files Result ({action}):\n{formatted}\n\nPresent this file information to Owner Kimsokun."

        elif tool_name == "codebase_search":
            data = result.data or []
            obs = f"Codebase Search Results for '{params.get('query')}':\n"
            for item in data[:8]:
                obs += f"- {item.get('file')}:{item.get('line')} -> {item.get('snippet')}\n"
            obs += "\nUse these local codebase occurrences to answer accurately."
            return obs

        elif tool_name == "codebase_read":
            info = result.data or {}
            return f"Codebase File Content ({info.get('file')} lines {info.get('start_line')}-{info.get('end_line')} of {info.get('total_lines')}):\n```\n{info.get('content')}\n```"

        elif tool_name == "codebase_structure":
            return f"Project Architecture Directory Structure:\n{json.dumps(result.data, indent=2, ensure_ascii=False)}"

        elif tool_name == "github_search":
            data = result.data or []
            obs = f"GitHub Search Results for '{params.get('query')}':\n"
            for item in data[:4]:
                obs += f"- {item.get('full_name') or item.get('title')}: {item.get('description') or item.get('snippet')} [URL: {item.get('url')}]\n"
            return obs

        elif tool_name == "github_source_read":
            info = result.data or {}
            return f"GitHub Source Code ({info.get('url')}):\n```\n{info.get('content')}\n```"

        elif tool_name == "hardware_capability_detect":
            hw = result.data or {}
            return (
                f"Local Machine Hardware Specs:\n"
                f"- Physical Cores: {hw.get('cpu_physical_cores')}, Logical: {hw.get('cpu_logical_cores')}\n"
                f"- Total RAM: {hw.get('total_ram_gb')} GB, Available RAM: {hw.get('available_ram_gb')} GB (Used: {hw.get('ram_usage_percent')}%)\n"
                f"- Recommended GGUF Model Tier: {hw.get('recommended_model_tier')}\n"
                f"- Safe Context Length Limit: {hw.get('safe_context_limit')} tokens"
            )

        elif tool_name == "gguf_metadata_inspect":
            m = result.data or {}
            return (
                f"GGUF Model Metadata ({m.get('filename')}):\n"
                f"- Valid GGUF: {m.get('is_valid_gguf')} (Version {m.get('gguf_version')})\n"
                f"- Tensors: {m.get('tensor_count')}, Metadata Keys: {m.get('metadata_kv_count')}\n"
                f"- File Size: {m.get('size_mb')} MB ({m.get('size_gb')} GB)"
            )

        elif tool_name == "huggingface_search":
            data = result.data or []
            obs = f"Hugging Face Model Repositories for '{params.get('query')}':\n"
            for item in data[:4]:
                obs += f"- Model: {item.get('model_id')} (Downloads: {item.get('downloads')}, Likes: {item.get('likes')}) [URL: {item.get('url')}]\n"
            return obs

        elif tool_name == "python_execute":
            data = result.data or {}
            stdout = data.get("stdout", "")
            stderr = data.get("stderr", "")
            exit_code = data.get("exit_code", 0)
            return (
                f"Python Execution Result (Exit Code {exit_code}, Time: {data.get('execution_time_ms')}ms):\n"
                f"Stdout:\n```\n{stdout}\n```\n"
                + (f"Stderr:\n```\n{stderr}\n```\n" if stderr else "")
                + "\nAnalyze this execution output and present the result to Owner Kimsokun."
            )

        elif tool_name == "package_registry":
            data = result.data or {}
            recent_v = ", ".join(data.get("recent_versions", []))
            return (
                f"Package Registry Data ({data.get('ecosystem')} - {data.get('name')} v{data.get('latest_version')}):\n"
                f"- Summary: {data.get('summary') or data.get('description')}\n"
                f"- License: {data.get('license')}\n"
                f"- Docs/Home: {data.get('docs_url') or data.get('home_page') or data.get('homepage')}\n"
                + (f"- Recent Versions: {recent_v}\n" if recent_v else "")
            )

        return str(result.data)

tool_pipeline = ToolPipeline()
