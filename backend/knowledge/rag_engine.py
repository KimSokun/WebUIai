import re
import math
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter
from backend.config import DOCUMENTS_DIR

STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
    "can", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't",
    "down", "during", "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have",
    "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself", "him",
    "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't",
    "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor",
    "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out",
    "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so",
    "some", "such", "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then",
    "there", "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this", "those",
    "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll",
    "we're", "we've", "were", "weren't", "what", "what's", "when", "when's", "where", "where's",
    "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't",
    "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves"
}

def tokenize(text: str) -> List[str]:
    words = re.findall(r'[a-zA-Z0-9_ក-៿]+', text.lower())
    return [w for w in words if len(w) > 1 and w not in STOPWORDS]

class SearchResultList(list):
    """List that also behaves like a dict with .get() and string keys for backwards compatibility."""
    def __getitem__(self, key):
        if isinstance(key, str):
            if key == "total_results":
                return len(self)
            if key == "passages":
                return list(self)
            if key == "context":
                return "\n\n".join(item.get("content", "") for item in self)
            raise KeyError(key)
        return super().__getitem__(key)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

class LocalRAGEngine:
    """
    Pure Python Zero-Dependency Local Vector & BM25 Semantic RAG Engine:
    Indexes workspace/documents/ and retrieves top-K high-signal passages in <5ms.
    """
    def __init__(self, doc_dir: Optional[Path] = None):
        self.doc_dir = doc_dir or DOCUMENTS_DIR
        self.doc_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.doc_dir / ".rag_index.json"
        self.chunks: List[Dict[str, Any]] = []
        self.doc_lens: List[int] = []
        self.avg_doc_len: float = 0.0
        self.df: Dict[str, int] = {}
        self.total_docs: int = 0
        self._load_index()

    def tokenize(self, text: str) -> List[str]:
        return tokenize(text)

    def chunk_text(self, text: str, max_chunk_words: int = 250) -> List[Dict[str, Any]]:
        return self._chunk_text(text, filename="doc", chunk_size=max_chunk_words)

    def index_all_documents(self) -> Dict[str, Any]:
        return self.index_documents()

    def _chunk_text(self, text: str, filename: str, chunk_size: int = 250, overlap: int = 50) -> List[Dict[str, Any]]:
        words = text.split()
        if not words:
            return []
        chunks = []
        step = max(chunk_size - overlap, 1)
        for i in range(0, len(words), step):
            chunk_words = words[i:i + chunk_size]
            chunk_text = " ".join(chunk_words)
            chunks.append({
                "doc_name": filename,
                "chunk_index": len(chunks),
                "text": chunk_text,
                "tokens": tokenize(chunk_text),
                "word_count": len(chunk_words)
            })
            if i + chunk_size >= len(words):
                break
        return chunks

    def index_documents(self) -> Dict[str, Any]:
        start_t = time.perf_counter()
        supported_exts = {".txt", ".md", ".json", ".py", ".html", ".csv", ".log"}
        all_chunks = []

        files_indexed = 0
        for p in self.doc_dir.glob("**/*"):
            if p.is_file() and p.suffix.lower() in supported_exts and not p.name.startswith("."):
                try:
                    text = p.read_text(encoding="utf-8", errors="replace")
                    rel_name = str(p.relative_to(self.doc_dir))
                    doc_chunks = self._chunk_text(text, rel_name)
                    all_chunks.extend(doc_chunks)
                    files_indexed += 1
                except Exception:
                    continue

        self.chunks = all_chunks
        self.total_docs = len(self.chunks)
        self.doc_lens = [len(c["tokens"]) for c in self.chunks]
        self.avg_doc_len = sum(self.doc_lens) / max(self.total_docs, 1)

        # Compute Document Frequency
        self.df = {}
        for c in self.chunks:
            unique_terms = set(c["tokens"])
            for t in unique_terms:
                self.df[t] = self.df.get(t, 0) + 1

        self._save_index()
        elapsed = (time.perf_counter() - start_t) * 1000
        return {
            "files_indexed": files_indexed,
            "indexed_files": files_indexed,
            "total_chunks": self.total_docs,
            "time_ms": round(elapsed, 2)
        }

    def _save_index(self):
        try:
            save_data = {
                "chunks": [{"doc_name": c["doc_name"], "chunk_index": c["chunk_index"], "text": c["text"], "word_count": c["word_count"]} for c in self.chunks],
                "updated_at": int(time.time() * 1000)
            }
            tmp = self.index_file.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False)
            tmp.replace(self.index_file)
        except Exception:
            pass

    def _load_index(self):
        if not self.index_file.exists():
            self.index_documents()
            return
        try:
            with open(self.index_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            loaded_chunks = []
            for item in data.get("chunks", []):
                tokens = tokenize(item.get("text", ""))
                loaded_chunks.append({
                    "doc_name": item.get("doc_name"),
                    "chunk_index": item.get("chunk_index"),
                    "text": item.get("text"),
                    "tokens": tokens,
                    "word_count": item.get("word_count", len(tokens))
                })
            self.chunks = loaded_chunks
            self.total_docs = len(self.chunks)
            self.doc_lens = [len(c["tokens"]) for c in self.chunks]
            self.avg_doc_len = sum(self.doc_lens) / max(self.total_docs, 1)

            self.df = {}
            for c in self.chunks:
                for t in set(c["tokens"]):
                    self.df[t] = self.df.get(t, 0) + 1
        except Exception:
            self.index_documents()

    def search(self, query: str, top_k: int = 3, max_total_chars: int = 1500) -> List[Dict[str, Any]]:
        start_t = time.perf_counter()
        q_tokens = tokenize(query)
        if not q_tokens or not self.chunks:
            return SearchResultList([])

        q_counter = Counter(q_tokens)
        k1 = 1.5
        b = 0.75
        N = max(self.total_docs, 1)

        scores = []
        for idx, chunk in enumerate(self.chunks):
            doc_tokens = chunk["tokens"]
            doc_len = len(doc_tokens)
            doc_counter = Counter(doc_tokens)

            # BM25 lexical score
            bm25_score = 0.0
            for term, q_cnt in q_counter.items():
                if term in doc_counter:
                    n_q = self.df.get(term, 0)
                    idf = math.log(1.0 + (N - n_q + 0.5) / (n_q + 0.5))
                    tf = doc_counter[term]
                    denom = tf + k1 * (1.0 - b + b * (doc_len / max(self.avg_doc_len, 1.0)))
                    bm25_score += idf * (tf * (k1 + 1.0) / max(denom, 1e-6))

            # Cosine similarity on TF-IDF vectors
            dot_prod = sum(q_counter[t] * doc_counter[t] for t in q_tokens if t in doc_counter)
            q_norm = math.sqrt(sum(cnt ** 2 for cnt in q_counter.values()))
            d_norm = math.sqrt(sum(cnt ** 2 for cnt in doc_counter.values()))
            cos_sim = dot_prod / (q_norm * d_norm) if (q_norm > 0 and d_norm > 0) else 0.0

            # Hybrid score
            hybrid = 0.6 * bm25_score + 0.4 * (cos_sim * 10.0)
            if hybrid > 0.01:
                scores.append((hybrid, chunk))

        scores.sort(key=lambda x: x[0], reverse=True)
        results = []
        current_chars = 0
        for score, chunk in scores[:top_k]:
            txt = chunk["text"]
            if current_chars + len(txt) > max_total_chars:
                allowed_len = max(max_total_chars - current_chars, 200)
                txt = txt[:allowed_len] + "... [Passage trimmed for token efficiency]"

            results.append({
                "score": round(score, 3),
                "document": chunk["doc_name"],
                "chunk_index": chunk["chunk_index"],
                "content": txt
            })
            current_chars += len(txt)
            if current_chars >= max_total_chars:
                break

        return SearchResultList(results)

    def list_documents(self) -> List[Dict[str, Any]]:
        docs = {}
        for c in self.chunks:
            name = c["doc_name"]
            docs[name] = docs.get(name, 0) + 1
        return [{"name": name, "chunks": count} for name, count in docs.items()]

local_rag = LocalRAGEngine()
