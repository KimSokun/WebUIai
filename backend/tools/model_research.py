import os
import struct
import time
import psutil
import httpx
from pathlib import Path
from typing import Any, Dict, List, Optional
from backend.tools.base import BaseTool, ToolResult
from backend.config import MODELS_DIR

class HardwareCapabilityDetectTool(BaseTool):
    """
    Detects local machine hardware specifications (CPU cores, RAM, GPU, OS)
    and calculates model quantization fit and RAM suitability.
    """
    def __init__(self):
        super().__init__(
            name="hardware_capability_detect",
            description="Inspect local physical hardware specs (cores, RAM, available memory) to determine model fit.",
            risk_level="LOW",
            requires_confirmation=False
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }

    async def execute(self, **kwargs) -> ToolResult:
        start_time = time.time()
        try:
            mem = psutil.virtual_memory()
            p_cores = psutil.cpu_count(logical=False) or 4
            l_cores = psutil.cpu_count(logical=True) or 8

            total_ram_gb = round(mem.total / (1024 ** 3), 2)
            avail_ram_gb = round(mem.available / (1024 ** 3), 2)

            # Recommend safe max model parameter size based on available RAM
            if avail_ram_gb > 16.0:
                recommended_param_tier = "7B to 14B (Q4_K_M / Q5_K_M)"
            elif avail_ram_gb > 6.0:
                recommended_param_tier = "3B to 7B (Q4_K_M)"
            elif avail_ram_gb > 3.0:
                recommended_param_tier = "1.5B to 3B (Q4_K_M)"
            else:
                recommended_param_tier = "0.5B to 1.5B (Q4_0 / Q4_K_M)"

            data = {
                "cpu_physical_cores": p_cores,
                "cpu_logical_cores": l_cores,
                "total_ram_gb": total_ram_gb,
                "available_ram_gb": avail_ram_gb,
                "ram_usage_percent": mem.percent,
                "recommended_model_tier": recommended_param_tier,
                "safe_context_limit": 102400 if avail_ram_gb > 8.0 else 32768
            }

            return ToolResult(
                success=True,
                data=data,
                execution_time_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data={},
                error=f"Hardware detection error: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000
            )

class GGUFMetadataInspectTool(BaseTool):
    """
    Parses and inspects local GGUF file headers to extract actual architecture,
    tensor count, and quantization metadata without running inference.
    """
    def __init__(self):
        super().__init__(
            name="gguf_metadata_inspect",
            description="Inspect local GGUF file binary header (magic, version, tensor count, file size).",
            risk_level="LOW",
            requires_confirmation=False
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "GGUF filename in models directory (e.g. qwen3-1.7b-flashhead-q4_k_m.gguf)"}
            },
            "required": ["filename"]
        }

    async def execute(self, filename: str = "", **kwargs) -> ToolResult:
        start_time = time.time()
        clean_name = filename.strip()
        target = MODELS_DIR / clean_name
        if not target.exists():
            # Try finding any match
            matches = list(MODELS_DIR.glob(f"*{clean_name}*"))
            if matches:
                target = matches[0]
            else:
                return ToolResult(success=False, data=None, error=f"GGUF file '{clean_name}' not found in {MODELS_DIR}")

        try:
            size_bytes = target.stat().st_size
            size_mb = round(size_bytes / (1024 ** 2), 1)
            size_gb = round(size_bytes / (1024 ** 3), 2)

            with open(target, "rb") as f:
                header = f.read(16)
                if len(header) < 16:
                    return ToolResult(success=False, data=None, error="File is too small to be a valid GGUF model.")

                magic, version, tensor_count, kv_count = struct.unpack("<4sIII", header)
                is_gguf = (magic == b"GGUF")

            return ToolResult(
                success=True,
                data={
                    "filename": target.name,
                    "is_valid_gguf": is_gguf,
                    "gguf_version": version if is_gguf else None,
                    "tensor_count": tensor_count if is_gguf else None,
                    "metadata_kv_count": kv_count if is_gguf else None,
                    "size_mb": size_mb,
                    "size_gb": size_gb,
                    "path": str(target.resolve())
                },
                execution_time_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"Error inspecting GGUF metadata: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000
            )

class HuggingFaceSearchTool(BaseTool):
    """
    Searches Hugging Face Hub API for compatible GGUF models, quantized variants,
    and download statistics.
    """
    def __init__(self):
        super().__init__(
            name="huggingface_search",
            description="Search Hugging Face Hub for GGUF models, quantizations, and model cards.",
            risk_level="LOW",
            requires_confirmation=False
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Model family or name (e.g. Qwen2.5-Coder GGUF, Llama-3.2 GGUF)"}
            },
            "required": ["query"]
        }

    async def execute(self, query: str = "", **kwargs) -> ToolResult:
        start_time = time.time()
        url = "https://huggingface.co/api/models"
        search_query = f"{query} GGUF" if "gguf" not in query.lower() else query
        params = {"search": search_query, "limit": 5, "full": "false"}

        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    models = resp.json()
                    results = []
                    for m in models[:5]:
                        results.append({
                            "model_id": m.get("id"),
                            "downloads": m.get("downloads", 0),
                            "likes": m.get("likes", 0),
                            "tags": [t for t in m.get("tags", []) if "gguf" in t.lower() or "qwen" in t.lower() or "llama" in t.lower()][:4],
                            "url": f"https://huggingface.co/{m.get('id')}"
                        })
                    return ToolResult(
                        success=True,
                        data=results,
                        execution_time_ms=(time.time() - start_time) * 1000
                    )

            # Web search fallback
            from backend.tools.search import WebSearchTool
            web_tool = WebSearchTool()
            fb_res = await web_tool.execute(query=f"site:huggingface.co {search_query}")
            return ToolResult(
                success=fb_res.success,
                data=fb_res.data,
                execution_time_ms=(time.time() - start_time) * 1000
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data=[],
                error=f"Hugging Face search failed: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000
            )
