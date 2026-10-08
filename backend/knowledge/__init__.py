"""
K-Jocker Verified Knowledge Store Package
Persistent, verifiable technical knowledge with freshness tracking and status lifecycle.
"""
from backend.knowledge.store import knowledge_store, KnowledgeStore, KnowledgeEntry

__all__ = ["knowledge_store", "KnowledgeStore", "KnowledgeEntry"]
