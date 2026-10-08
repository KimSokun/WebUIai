import time
from typing import Any, Dict, List, Optional
from backend.tools.base import BaseTool, ToolResult
from backend.knowledge.rag_engine import local_rag

class RAGSearchTool(BaseTool):
    """Semantic vector & BM25 document search over workspace/documents/ (<5ms)."""
    def __init__(self):
        super().__init__(
            name="rag.search",
            description="Query local document knowledge base (PDFs, docs, books, code) and extract relevant passages without token bloat.",
            risk_level="LOW",
            requires_confirmation=False
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query or question about indexed documents"},
                "top_k": {"type": "integer", "description": "Number of top passages to return (default 3)"}
            },
            "required": ["query"]
        }

    async def execute(self, **kwargs) -> ToolResult:
        query = str(kwargs.get("query", "")).strip()
        top_k = int(kwargs.get("top_k", 3))

        if not query:
            return ToolResult(success=False, data=None, error="Query parameter is required.")

        start_t = time.perf_counter()
        passages = local_rag.search(query=query, top_k=top_k)
        elapsed = (time.perf_counter() - start_t) * 1000

        return ToolResult(
            success=True,
            data={
                "query": query,
                "passages": passages,
                "context": "\n\n".join(p.get("content", "") for p in passages),
                "total_found": len(passages)
            },
            execution_time_ms=elapsed
        )

class RAGIndexTool(BaseTool):
    """Re-index all documents in workspace/documents/."""
    def __init__(self):
        super().__init__(
            name="rag.index",
            description="Re-index all documents, books, and code in workspace/documents/ for instant semantic retrieval.",
            risk_level="LOW",
            requires_confirmation=False
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}

    async def execute(self, **kwargs) -> ToolResult:
        start_t = time.perf_counter()
        res = local_rag.index_documents()
        elapsed = (time.perf_counter() - start_t) * 1000
        return ToolResult(success=True, data=res, execution_time_ms=elapsed)

class RAGListDocsTool(BaseTool):
    """List all indexed documents in the local knowledge base."""
    def __init__(self):
        super().__init__(
            name="rag.list_docs",
            description="List all documents and text files currently indexed in the local knowledge base.",
            risk_level="LOW",
            requires_confirmation=False
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}

    async def execute(self, **kwargs) -> ToolResult:
        start_t = time.perf_counter()
        docs = local_rag.list_documents()
        elapsed = (time.perf_counter() - start_t) * 1000
        return ToolResult(success=True, data={"documents": docs, "total": len(docs)}, execution_time_ms=elapsed)
