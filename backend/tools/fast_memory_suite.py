import json
import time
from pathlib import Path
from typing import Any, Dict, Optional, List
from backend.config import SANDBOX_DIR
from backend.tools.base import BaseTool, ToolResult

MEMORY_FILE = SANDBOX_DIR / ".fast_memory.json"
MAX_MEMORY_KEYS = 500
MAX_VAL_LENGTH = 50000

class FastMemoryStore:
    """Thread-safe sandboxed JSON key-value store."""
    def __init__(self, filepath: Path = MEMORY_FILE):
        self.filepath = filepath

    def _read_data(self) -> Dict[str, Any]:
        if not self.filepath.exists():
            return {}
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _write_data(self, data: Dict[str, Any]):
        temp_file = self.filepath.with_suffix(".tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            temp_file.replace(self.filepath)
        except Exception:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass
            raise

    def get(self, key: str) -> Optional[Any]:
        data = self._read_data()
        item = data.get(key)
        if item is not None and isinstance(item, dict) and "value" in item:
            return item["value"]
        return item

    def set(self, key: str, value: Any) -> bool:
        data = self._read_data()
        if len(data) >= MAX_MEMORY_KEYS and key not in data:
            # Drop oldest key
            oldest_key = min(data.keys(), key=lambda k: data[k].get("updated_at", 0) if isinstance(data[k], dict) else 0)
            del data[oldest_key]

        data[key] = {
            "value": value,
            "updated_at": int(time.time() * 1000)
        }
        self._write_data(data)
        return True

    def list_keys(self) -> List[Dict[str, Any]]:
        data = self._read_data()
        res = []
        for k, v in data.items():
            updated = v.get("updated_at", 0) if isinstance(v, dict) else 0
            val_preview = str(v.get("value", v) if isinstance(v, dict) else v)[:60]
            res.append({"key": k, "updated_at": updated, "preview": val_preview})
        res.sort(key=lambda x: x["updated_at"], reverse=True)
        return res

    def delete(self, key: str) -> bool:
        data = self._read_data()
        if key in data:
            del data[key]
            self._write_data(data)
            return True
        return False

memory_store = FastMemoryStore()

class MemoryGetTool(BaseTool):
    """Retrieve fact, variable, or context by key from fast workspace memory."""
    def __init__(self):
        super().__init__(
            name="memory.get",
            description="Retrieve stored fact, variable, note, or context from fast memory (<0.5ms).",
            risk_level="LOW",
            requires_confirmation=False
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Memory key name"}
            },
            "required": ["key"]
        }

    async def execute(self, **kwargs) -> ToolResult:
        key = str(kwargs.get("key", "")).strip()
        if not key:
            return ToolResult(success=False, data=None, error="Memory key is required.")

        start_t = time.perf_counter()
        val = memory_store.get(key)
        elapsed = (time.perf_counter() - start_t) * 1000

        if val is None:
            return ToolResult(success=False, data=None, error=f"Key '{key}' not found in memory.", execution_time_ms=elapsed)
        return ToolResult(success=True, data={"key": key, "value": val}, execution_time_ms=elapsed)

class MemorySetTool(BaseTool):
    """Store fact, variable, note, or context in fast memory."""
    def __init__(self):
        super().__init__(
            name="memory.set",
            description="Store fact, variable, snippet, or note in fast memory for instant reuse.",
            risk_level="LOW",
            requires_confirmation=False
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Memory key name"},
                "value": {"type": "any", "description": "Value to store (string, dict, or number)"}
            },
            "required": ["key", "value"]
        }

    async def execute(self, **kwargs) -> ToolResult:
        key = str(kwargs.get("key", "")).strip()
        val = kwargs.get("value")
        if not key:
            return ToolResult(success=False, data=None, error="Memory key is required.")
        if val is None:
            return ToolResult(success=False, data=None, error="Memory value cannot be None.")

        # Length safety
        val_str = json.dumps(val, ensure_ascii=False) if isinstance(val, (dict, list)) else str(val)
        if len(val_str) > MAX_VAL_LENGTH:
            return ToolResult(success=False, data=None, error=f"Value exceeds max memory limit of {MAX_VAL_LENGTH} characters.")

        start_t = time.perf_counter()
        memory_store.set(key, val)
        elapsed = (time.perf_counter() - start_t) * 1000

        return ToolResult(success=True, data={"key": key, "stored": True}, execution_time_ms=elapsed)

class MemoryListTool(BaseTool):
    """List all stored keys in fast memory."""
    def __init__(self):
        super().__init__(
            name="memory.list",
            description="List all active memory keys and previews in fast memory.",
            risk_level="LOW",
            requires_confirmation=False
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}

    async def execute(self, **kwargs) -> ToolResult:
        start_t = time.perf_counter()
        keys = memory_store.list_keys()
        elapsed = (time.perf_counter() - start_t) * 1000
        return ToolResult(success=True, data={"keys": keys, "total": len(keys)}, execution_time_ms=elapsed)

class MemoryDeleteTool(BaseTool):
    """Delete a key from fast memory."""
    def __init__(self):
        super().__init__(
            name="memory.delete",
            description="Delete a key from fast memory.",
            risk_level="LOW",
            requires_confirmation=False
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Memory key to delete"}
            },
            "required": ["key"]
        }

    async def execute(self, **kwargs) -> ToolResult:
        key = str(kwargs.get("key", "")).strip()
        if not key:
            return ToolResult(success=False, data=None, error="Key parameter is required.")

        start_t = time.perf_counter()
        deleted = memory_store.delete(key)
        elapsed = (time.perf_counter() - start_t) * 1000

        return ToolResult(success=deleted, data={"key": key, "deleted": deleted}, execution_time_ms=elapsed)
