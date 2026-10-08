import json
import asyncio
from typing import AsyncGenerator, Dict, Any, List
from backend.config import system_config
from backend.tools import tool_registry
from backend.runtime import llm_runtime

class AgentController:
    """
    Coordinates tool-calling, security validation, and model synthesis.
    Model output is treated purely as a REQUEST; Backend makes all execution decisions.
    """

    async def handle_chat_stream(
        self,
        messages: List[Dict[str, str]]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        async for event in llm_runtime.stream_chat(messages, system_prompt=system_config.system_prompt):
            yield event

agent_controller = AgentController()
