import os
import json
import time
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from backend.config import CONVERSATIONS_DIR

class ConversationManager:
    """
    Persistent Backend Conversation Engine for K-Jocker.
    Stores and manages conversation lifecycle in workspace/conversations/{conv_id}.json.
    Guarantees physical disk deletion when conversations are deleted from WebUI.
    """
    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or CONVERSATIONS_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_id(self, conv_id: str) -> str:
        """Sanitize conversation id to prevent directory traversal or invalid characters."""
        clean = str(conv_id).strip().replace("..", "__")
        clean = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', clean)
        return clean or f"conv_{int(time.time()*1000)}"

    def _get_path(self, conv_id: str) -> Path:
        safe_id = self._sanitize_id(conv_id)
        return self.storage_dir / f"{safe_id}.json"

    def save_conversation(self, conv_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Saves or updates conversation data and its messages.
        """
        safe_id = self._sanitize_id(conv_id)
        path = self._get_path(safe_id)

        existing = self.get_conversation(safe_id) or {}
        merged = {**existing, **data}
        merged["id"] = safe_id
        if "lastModified" not in merged:
            merged["lastModified"] = int(time.time() * 1000)
        if "name" not in merged or not merged["name"]:
            merged["name"] = data.get("name") or "New Chat"

        temp_path = path.with_suffix(".tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(merged, f, ensure_ascii=False, indent=2)
            temp_path.replace(path)
        except Exception:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
            raise

        return merged

    def get_conversation(self, conv_id: str) -> Optional[Dict[str, Any]]:
        """
        Reads conversation details and messages.
        """
        path = self._get_path(conv_id)
        if not path.exists() or not path.is_file():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def list_conversations(self) -> List[Dict[str, Any]]:
        """
        Returns all conversations metadata sorted by lastModified descending.
        """
        results = []
        if not self.storage_dir.exists():
            return results

        for p in self.storage_dir.glob("*.json"):
            if p.name.endswith(".tmp"):
                continue
            try:
                with open(p, "r", encoding="utf-8") as f:
                    c = json.load(f)
                    summary = {
                        "id": c.get("id", p.stem),
                        "name": c.get("name", "Chat"),
                        "lastModified": c.get("lastModified", int(p.stat().st_mtime * 1000)),
                        "currNode": c.get("currNode", ""),
                        "messageCount": len(c.get("messages", [])),
                        "pinned": bool(c.get("pinned", False)),
                        "model": c.get("model", "")
                    }
                    results.append(summary)
            except Exception:
                continue

        results.sort(key=lambda x: x.get("lastModified", 0), reverse=True)
        return results

    def delete_conversation(self, conv_id: str) -> bool:
        """
        Permanently deletes the conversation file from disk.
        """
        path = self._get_path(conv_id)
        if path.exists() and path.is_file():
            try:
                path.unlink()
                return True
            except Exception:
                return False
        return False

    def bulk_delete_conversations(self, conv_ids: List[str]) -> int:
        """
        Deletes multiple conversations from disk.
        """
        deleted_count = 0
        for cid in conv_ids:
            if self.delete_conversation(cid):
                deleted_count += 1
        return deleted_count

    def delete_all_conversations(self) -> int:
        """
        Wipes all conversations from disk.
        """
        count = 0
        if not self.storage_dir.exists():
            return count

        for p in self.storage_dir.glob("*.json"):
            try:
                p.unlink()
                count += 1
            except Exception:
                pass
        return count

conversation_manager = ConversationManager()
