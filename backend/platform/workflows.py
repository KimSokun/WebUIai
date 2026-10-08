from typing import Dict, Any, List
from backend.platform.executor import tool_execution_manager

class ToolWorkflowManager:
    """
    Composite Multi-Tool Workflows (Section 31):
    Controlled composition of smaller tools to achieve complex engineering goals.
    """
    @staticmethod
    async def debug_python(file_path: str, code_snippet: str = "", is_owner: bool = False) -> Dict[str, Any]:
        """Workflow: Inspect code -> Test execution -> Analyze error -> Search fix"""
        steps = []
        
        # Step 1: Code execution in sandbox
        exec_res = await tool_execution_manager.execute_tool("python_execute", {"code": code_snippet}, is_owner=is_owner)
        steps.append({"step": "execute_test", "result": exec_res.model_dump()})

        # Step 2: If error, run traceback diagnosis
        if not exec_res.success and exec_res.error:
            tb_res = await tool_execution_manager.execute_tool("traceback_analyzer", {"traceback_text": exec_res.error}, is_owner=is_owner)
            steps.append({"step": "traceback_diagnosis", "result": tb_res.model_dump()})

        return {"workflow": "DebugPython", "completed_steps": len(steps), "steps": steps}

    @staticmethod
    async def research_gguf(model_query: str = "Qwen2.5-Coder", is_owner: bool = False) -> Dict[str, Any]:
        """Workflow: Detect Hardware -> Search Hugging Face -> GGUF Model Analysis"""
        steps = []
        
        # Step 1: Detect hardware
        hw_res = await tool_execution_manager.execute_tool("hardware_capability_detect", {}, is_owner=is_owner)
        steps.append({"step": "hardware_spec", "result": hw_res.model_dump()})

        # Step 2: Search Hugging Face
        hf_res = await tool_execution_manager.execute_tool("huggingface_search", {"query": model_query}, is_owner=is_owner)
        steps.append({"step": "model_discovery", "result": hf_res.model_dump()})

        return {"workflow": "ResearchGGUF", "completed_steps": len(steps), "steps": steps}

tool_workflows = ToolWorkflowManager()
