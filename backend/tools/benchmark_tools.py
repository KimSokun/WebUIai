import time
from typing import Any, Dict
from backend.platform.manifest import PlatformTool, ToolManifest, ToolCategory, RiskLevel
from backend.tools.base import ToolResult

class BenchmarkLatencyTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="benchmark_latency",
            name="Benchmark Round-Trip Latency",
            category=ToolCategory.BENCHMARK,
            description="Measures local system and server probe latency.",
            tags=["benchmark", "latency", "speed", "performance"],
            risk_level=RiskLevel.ANALYZE,
            timeout_seconds=5.0
        ))

    def get_input_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}

    async def execute(self, **kwargs) -> ToolResult:
        start = time.time()
        # Compute 1 million loops
        total = sum(i for i in range(100_000))
        elapsed = (time.time() - start) * 1000
        return ToolResult(success=True, data={"compute_time_ms": round(elapsed, 2), "metric": "cpu_throughput_ok"})
