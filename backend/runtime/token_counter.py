import re
import httpx
from typing import List, Dict, Any, Optional
from backend.config import system_config

# Fast BPE-like segmentation pattern:
# Captures Latin/digits, Khmer orthographic syllable clusters, and punctuation/symbols.
TOKEN_PATTERN = re.compile(
    r"[A-Za-z0-9_]+|[\u1780-\u17B3][\u17B4-\u17DD]*|[^\s\w]+"
)

class FastTokenCounter:
    """
    High-speed, dual-mode token counter for K-Jocker runtime:
    1. If llama-server is online: requests exact GGUF token count via POST /tokenize (<2ms).
    2. Fallback / offline: high-fidelity regex BPE estimator (<0.05ms) for English, Khmer, code, and symbols.
    """
    def __init__(self, llama_url: Optional[str] = None):
        self.llama_url = llama_url or system_config.model.llama_server_url

    def estimate_tokens(self, text: str) -> int:
        if not text or not text.strip():
            return 0
        matches = TOKEN_PATTERN.findall(text)
        return max(1, len(matches))

    async def count_tokens_async(self, text: str) -> int:
        if not text:
            return 0
        try:
            async with httpx.AsyncClient(timeout=0.4) as client:
                res = await client.post(
                    f"{self.llama_url}/tokenize",
                    json={"content": text}
                )
                if res.status_code == 200:
                    data = res.json()
                    tokens = data.get("tokens", [])
                    if tokens:
                        return len(tokens)
        except Exception:
            pass
        return self.estimate_tokens(text)

    def count_tokens_sync(self, text: str) -> int:
        if not text:
            return 0
        try:
            with httpx.Client(timeout=0.3) as client:
                res = client.post(
                    f"{self.llama_url}/tokenize",
                    json={"content": text}
                )
                if res.status_code == 200:
                    data = res.json()
                    tokens = data.get("tokens", [])
                    if tokens:
                        return len(tokens)
        except Exception:
            pass
        return self.estimate_tokens(text)

    def count_messages_tokens(self, messages: List[Dict[str, Any]], system_prompt: str = "") -> int:
        total = 0
        if system_prompt:
            total += self.estimate_tokens(system_prompt) + 4  # system header / role overhead

        for m in messages:
            content = m.get("content", "")
            if isinstance(content, list):
                text_parts = [p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"]
                content_text = " ".join(text_parts)
            else:
                content_text = str(content)
            
            # Each message has role tags overhead (<|im_start|>role\n...<|im_end|>) ~4 tokens
            total += self.estimate_tokens(content_text) + 4

        return max(1, total)

token_counter = FastTokenCounter()

def count_tokens(text: str) -> int:
    return token_counter.estimate_tokens(text)

def count_messages_tokens(messages: List[Dict[str, Any]], system_prompt: str = "") -> int:
    return token_counter.count_messages_tokens(messages, system_prompt)
