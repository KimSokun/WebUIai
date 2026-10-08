import time
import re
import threading
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class RuntimeEvent(BaseModel):
    request_id: str
    timestamp: float = Field(default_factory=time.time)
    event: str  # e.g., 'tool_execution', 'tool_rejected', 'validation_error', 'tool_timeout', 'tool_loop_limit'
    intent: str
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    authorized: bool
    executed: bool
    success: bool
    result: Any = None
    error: Optional[str] = None

class RuntimeEventLogger:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self._events: List[RuntimeEvent] = []
        self._mutex = threading.Lock()

    @classmethod
    def get_instance(cls) -> 'RuntimeEventLogger':
        with cls._lock:
            if cls._instance is None:
                cls._instance = RuntimeEventLogger()
            return cls._instance

    @staticmethod
    def sanitize(data: Any) -> Any:
        if isinstance(data, dict):
            sanitized = {}
            for k, v in data.items():
                if any(sensitive in k.lower() for sensitive in ['token', 'password', 'secret', 'key', 'auth']):
                    sanitized[k] = '[REDACTED]'
                else:
                    sanitized[k] = RuntimeEventLogger.sanitize(v)
            return sanitized
        elif isinstance(data, list):
            return [RuntimeEventLogger.sanitize(x) for x in data]
        elif isinstance(data, str):
            # Redact bearer tokens or api keys if found
            cleaned = re.sub(r'(bearer\s+|sk-|token_)[a-zA-Z0-9_\-]{8,}', r'\1[REDACTED]', data, flags=re.IGNORECASE)
            return cleaned
        return data

    def record(self, event: RuntimeEvent):
        with self._mutex:
            self._events.append(event)
            # Memory leak protection: keep latest 5,000 events
            if len(self._events) > 5000:
                self._events = self._events[-2500:]

    def log_event(
        self,
        request_id: str,
        event_type: str,
        intent: str,
        tool_name: str,
        arguments: Dict[str, Any],
        authorized: bool,
        executed: bool,
        success: bool,
        result: Any = None,
        error: Optional[str] = None
    ) -> RuntimeEvent:
        event = RuntimeEvent(
            request_id=request_id,
            timestamp=time.time(),
            event=event_type,
            intent=intent,
            tool_name=tool_name,
            arguments=self.sanitize(arguments or {}),
            authorized=authorized,
            executed=executed,
            success=success,
            result=self.sanitize(result),
            error=error
        )
        self.record(event)
        return event

    def get_events(self, request_id: Optional[str] = None) -> List[RuntimeEvent]:
        with self._mutex:
            if request_id is None:
                return list(self._events)
            return [e for e in self._events if e.request_id == request_id]

    def get_evidence(self, request_id: str, tool_name: Optional[str] = None) -> List[Dict[str, Any]]:
        evs = self.get_events(request_id)
        if tool_name:
            evs = [e for e in evs if e.tool_name == tool_name]
        return [
            {
                'request_id': e.request_id,
                'tool_name': e.tool_name,
                'authorized': e.authorized,
                'executed': e.executed,
                'success': e.success,
                'result': e.result,
                'error': e.error
            }
            for e in evs
        ]

    def clear(self):
        with self._mutex:
            self._events.clear()

runtime_logger = RuntimeEventLogger.get_instance()
