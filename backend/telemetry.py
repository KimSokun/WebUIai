import psutil
import socket
import time
from pydantic import BaseModel
from backend.config import system_config

class TelemetrySnapshot(BaseModel):
    cpu_percent: float
    ram_used_gb: float
    ram_total_gb: float
    ram_percent: float
    tokens_per_sec: float
    context_used: int
    context_max: int
    model_name: str
    runtime: str
    mode: str
    owner_authenticated: bool
    sandbox_enabled: bool
    online_tools_enabled: bool
    internet_connected: bool
    timestamp: float

class TelemetryTracker:
    _last_token_count = 0
    _last_token_time = time.time()
    _current_tps = 6.2  # Initial baseline
    _current_context = 18432

    @classmethod
    def update_generation_metrics(cls, tokens_generated: int, elapsed_seconds: float, current_context: int):
        if elapsed_seconds > 0:
            cls._current_tps = round(tokens_generated / elapsed_seconds, 1)
        cls._current_context = current_context

    _internet_cache_status: bool = False
    _internet_cache_time: float = 0.0
    _INTERNET_TTL: float = 30.0

    @classmethod
    def check_internet(cls) -> bool:
        now = time.time()
        if (now - cls._internet_cache_time) < cls._INTERNET_TTL:
            return cls._internet_cache_status

        try:
            # Quick check to DNS 1.1.1.1 or 8.8.8.8 with short timeout
            with socket.create_connection(("1.1.1.1", 53), timeout=0.4):
                cls._internet_cache_status = True
        except OSError:
            cls._internet_cache_status = False

        cls._internet_cache_time = now
        return cls._internet_cache_status

    @classmethod
    def get_snapshot(cls, owner_auth: bool = True) -> TelemetrySnapshot:
        mem = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=None)
        
        return TelemetrySnapshot(
            cpu_percent=round(cpu, 1),
            ram_used_gb=round((mem.total - mem.available) / (1024 ** 3), 1),
            ram_total_gb=round(mem.total / (1024 ** 3), 1),
            ram_percent=round(mem.percent, 1),
            tokens_per_sec=cls._current_tps,
            context_used=cls._current_context,
            context_max=system_config.model.context_length,
            model_name=system_config.model.model_name,
            runtime=system_config.model.runtime,
            mode="LOCAL",
            owner_authenticated=owner_auth,
            sandbox_enabled=system_config.tools.local_files_enabled,
            online_tools_enabled=system_config.tools.web_search_enabled,
            internet_connected=cls.check_internet(),
            timestamp=time.time()
        )
