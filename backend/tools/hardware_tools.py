import os
import sys
import psutil
from typing import Any, Dict
from backend.platform.manifest import PlatformTool, ToolManifest, ToolCategory, RiskLevel
from backend.tools.base import ToolResult

class CPUInfoTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="cpu_info",
            name="CPU Specifications",
            category=ToolCategory.HARDWARE,
            description="Inspects physical/logical CPU cores, usage percent, and architecture.",
            tags=["cpu", "cores", "processor", "hardware"],
            risk_level=RiskLevel.READ,
            timeout_seconds=3.0
        ))

    def get_input_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}

    async def execute(self, **kwargs) -> ToolResult:
        p_cores = psutil.cpu_count(logical=False) or 4
        l_cores = psutil.cpu_count(logical=True) or 8
        usage = psutil.cpu_percent(interval=0.1)
        return ToolResult(success=True, data={"physical_cores": p_cores, "logical_cores": l_cores, "usage_percent": usage})

class RAMInfoTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="ram_info",
            name="RAM Memory Info",
            category=ToolCategory.HARDWARE,
            description="Inspects total, available, and used system RAM.",
            tags=["ram", "memory", "vram", "hardware"],
            risk_level=RiskLevel.READ,
            timeout_seconds=3.0
        ))

    def get_input_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}

    async def execute(self, **kwargs) -> ToolResult:
        vm = psutil.virtual_memory()
        return ToolResult(success=True, data={
            "total_gb": round(vm.total / (1024**3), 2),
            "available_gb": round(vm.available / (1024**3), 2),
            "used_gb": round(vm.used / (1024**3), 2),
            "percent_used": vm.percent
        })
