import time
import json
import hashlib
import httpx
from bs4 import BeautifulSoup
from typing import Any, Dict
from backend.tools.base import BaseTool, ToolResult
from backend.config import system_config, WEB_CACHE_DIR

class WebFetchTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="web_fetch",
            description="Fetch the text contents of an approved web page URL.",
            risk_level="MEDIUM",
            requires_confirmation=False
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The full HTTP/HTTPS URL to fetch"}
            },
            "required": ["url"]
        }

    async def execute(self, url: str = "", **kwargs) -> ToolResult:
        if not system_config.tools.web_fetch_enabled:
            return ToolResult(success=False, data=None, error="Web fetching is disabled by Owner policy.")

        if not system_config.tools.web_search_allow_read:
            return ToolResult(
                success=False,
                data=None,
                error="Security Alert: Web fetch READ permission is disabled by Owner policy."
            )

        start_time = time.time()
        if not url.startswith("http://") and not url.startswith("https://"):
            return ToolResult(success=False, data=None, error="Invalid URL protocol. Only HTTP and HTTPS are permitted.")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        try:
            async with httpx.AsyncClient(timeout=system_config.tools.tool_timeout_seconds, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code != 200:
                    return ToolResult(
                        success=False,
                        data=None,
                        error=f"Web server returned HTTP {resp.status_code}",
                        execution_time_ms=(time.time() - start_time) * 1000
                    )

                soup = BeautifulSoup(resp.text, "html.parser")
                for s in soup(["script", "style", "nav", "footer", "header"]):
                    s.decompose()

                text = soup.get_text(separator=" ", strip=True)
                if len(text) > 32000:
                    text = text[:32000] + "\n...[Content truncated for context safety]..."

                if system_config.tools.web_search_allow_write and text:
                    try:
                        WEB_CACHE_DIR.mkdir(parents=True, exist_ok=True)
                        url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
                        cache_file = WEB_CACHE_DIR / f"fetch_{url_hash}.json"
                        cache_data = {
                            "url": url,
                            "timestamp": int(time.time()),
                            "content_length": len(text),
                            "content": text
                        }
                        cache_file.write_text(json.dumps(cache_data, ensure_ascii=False, indent=2), encoding="utf-8")
                    except Exception:
                        pass

                return ToolResult(
                    success=True,
                    data={"url": url, "content": text},
                    execution_time_ms=(time.time() - start_time) * 1000
                )

        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"Web fetch error: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000
            )
