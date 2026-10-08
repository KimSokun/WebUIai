import sys
import unittest
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from fastapi.testclient import TestClient
from backend.main import app
from backend.config import DOCUMENTS_DIR
from backend.knowledge.rag_engine import LocalRAGEngine
from backend.tools.rag_tools import RAGSearchTool, RAGIndexTool, RAGListDocsTool

class TestLocalRAGEngine(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
        self.doc_file = DOCUMENTS_DIR / "test_ai_architecture.md"
        self.doc_file.write_text(
            "# K-Jocker Architecture Overview\n\n"
            "K-Jocker is an autonomous AI agent operating environment built on FastAPI and GGUF runtime.\n\n"
            "The system includes a local semantic RAG engine supporting BM25 lexical ranking and vector cosine similarity.\n\n"
            "Hardware requirements include minimum 8GB RAM, AVX2 instruction support, and optional NVIDIA GPU acceleration.",
            encoding="utf-8"
        )
        self.rag = LocalRAGEngine()
        self.client = TestClient(app)

    def tearDown(self):
        if self.doc_file.exists():
            self.doc_file.unlink(missing_ok=True)
        index_file = DOCUMENTS_DIR / ".rag_index.json"
        if index_file.exists():
            index_file.unlink(missing_ok=True)

    def test_tokenization_and_chunking(self):
        tokens = self.rag.tokenize("The FastAPI backend runs with GGUF runtime!")
        self.assertIn("fastapi", tokens)
        self.assertIn("gguf", tokens)
        self.assertIn("runtime", tokens)

        chunks = self.rag.chunk_text("Paragraph one.\n\nParagraph two with more details.", max_chunk_words=100)
        self.assertGreaterEqual(len(chunks), 1)

    def test_index_and_search_hybrid(self):
        idx_res = self.rag.index_all_documents()
        self.assertTrue(idx_res["indexed_files"] >= 1)
        self.assertTrue(idx_res["total_chunks"] >= 1)

        search_res = self.rag.search("vector cosine similarity and BM25", top_k=3)
        self.assertGreaterEqual(search_res["total_results"], 1)
        self.assertIn("BM25", search_res["context"])

        doc_list = self.rag.list_documents()
        self.assertGreaterEqual(len(doc_list), 1)
        self.assertTrue(any(d["name"] == "test_ai_architecture.md" for d in doc_list))

    async def test_rag_tools(self):
        # Index tool
        idx_tool = RAGIndexTool()
        res_idx = await idx_tool.execute()
        self.assertTrue(res_idx.success)

        # Search tool
        search_tool = RAGSearchTool()
        res_search = await search_tool.execute(query="hardware requirements RAM AVX2")
        self.assertTrue(res_search.success)
        self.assertIn("RAM", res_search.data["context"])

        # List docs tool
        list_tool = RAGListDocsTool()
        res_list = await list_tool.execute()
        self.assertTrue(res_list.success)
        self.assertGreaterEqual(len(res_list.data["documents"]), 1)

    def test_api_rag_endpoints(self):
        # Trigger index via API
        resp_idx = self.client.post("/api/rag/index")
        self.assertEqual(resp_idx.status_code, 200)
        self.assertTrue(resp_idx.json()["success"])

        # List docs via API
        resp_docs = self.client.get("/api/rag/documents")
        self.assertEqual(resp_docs.status_code, 200)
        self.assertTrue(resp_docs.json()["success"])

        # Search via API
        resp_search = self.client.post("/api/rag/search", json={"query": "GGUF runtime FastAPI", "top_k": 2})
        self.assertEqual(resp_search.status_code, 200)
        data = resp_search.json()
        self.assertTrue(data["success"])
        self.assertIn("context", data["data"])

if __name__ == "__main__":
    unittest.main()
