import json
import time
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any
from backend.config import BASE_DIR

KNOWLEDGE_DIR = BASE_DIR / "knowledge"

@dataclass
class KnowledgeEntry:
    topic: str
    category: str
    content: str
    source: str
    source_type: str  # SPEC, DOCS, REPO, RELEASE_NOTES, TESTS, REGISTRY, PAPER
    license: str = "Open"
    version: str = "1.0"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    confidence: str = "HIGH"  # HIGH, MEDIUM, LOW
    verification_status: str = "VERIFIED"  # VERIFIED, SUPPORTED, UNVERIFIED, CONFLICTING, OUTDATED

class KnowledgeStore:
    """
    Manages structured, verifiable knowledge entries across categories.
    Tracks freshness and lifecycle status.
    """
    def __init__(self, root_dir: Path = KNOWLEDGE_DIR):
        self.root_dir = root_dir
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def add_entry(self, entry: KnowledgeEntry) -> Path:
        cat_dir = self.root_dir / entry.category
        cat_dir.mkdir(parents=True, exist_ok=True)
        safe_topic = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in entry.topic.lower())
        file_path = cat_dir / f"{safe_topic}.json"
        
        entry.updated_at = time.time()
        file_path.write_text(json.dumps(asdict(entry), indent=2, ensure_ascii=False), encoding="utf-8")
        return file_path

    def get_entry(self, category: str, topic: str) -> Optional[KnowledgeEntry]:
        safe_topic = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in topic.lower())
        file_path = self.root_dir / category / f"{safe_topic}.json"
        if not file_path.exists():
            return None
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            return KnowledgeEntry(**data)
        except Exception:
            return None

    def search(self, query: str, category: Optional[str] = None) -> List[KnowledgeEntry]:
        results = []
        q = query.lower()
        search_dirs = [self.root_dir / category] if category and (self.root_dir / category).exists() else self.root_dir.glob("*")
        
        for d in search_dirs:
            if not d.is_dir():
                continue
            for f in d.glob("*.json"):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    if q in data.get("topic", "").lower() or q in data.get("content", "").lower():
                        results.append(KnowledgeEntry(**data))
                except Exception:
                    continue
        return results

    def check_freshness(self, entry: KnowledgeEntry, max_age_days: float = 90.0) -> str:
        """
        Calculates age and marks entry OUTDATED if older than threshold.
        """
        age_days = (time.time() - entry.updated_at) / (24 * 3600)
        if age_days > max_age_days and entry.verification_status == "VERIFIED":
            entry.verification_status = "OUTDATED"
            self.add_entry(entry)
        return entry.verification_status

knowledge_store = KnowledgeStore()
