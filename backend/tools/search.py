import time
import json
import hashlib
import httpx
from bs4 import BeautifulSoup
from typing import Any, Dict, List
from backend.tools.base import BaseTool, ToolResult
from backend.config import system_config, WEB_CACHE_DIR

class WebSearchTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="web_search",
            description="Search the web for current information, documentation, news, or general queries.",
            risk_level="LOW",
            requires_confirmation=False
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search keywords or question"}
            },
            "required": ["query"]
        }

    async def execute(self, query: str = "", **kwargs) -> ToolResult:
        if not system_config.tools.web_search_enabled:
            return ToolResult(success=False, data=None, error="Web search is disabled by Owner policy.")

        if not system_config.tools.web_search_allow_read:
            return ToolResult(
                success=False,
                data=[],
                error="Security Alert: Web search READ permission is disabled by Owner policy."
            )

        start_time = time.time()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        try:
            results: List[Dict[str, str]] = []
            params = {"q": query}
            async with httpx.AsyncClient(timeout=2.5, follow_redirects=True) as client:
                # 1. Try DuckDuckGo Lite endpoint (high reliability, low latency)
                try:
                    resp = await client.post("https://lite.duckduckgo.com/lite/", data=params, headers=headers)
                    if resp.status_code == 200:
                        soup = BeautifulSoup(resp.text, "html.parser")
                        links = soup.select("a.result-link")
                        snippets = soup.select("td.result-snippet")
                        for a, s in zip(links, snippets):
                            results.append({
                                "title": a.get_text(strip=True),
                                "snippet": s.get_text(strip=True),
                                "link": a.get("href", "")
                            })
                            if len(results) >= system_config.tools.max_search_results:
                                break
                except Exception:
                    pass

                # 2. Fallback to HTML endpoint if Lite returned non-200 or empty
                if not results:
                    try:
                        resp_html = await client.post("https://html.duckduckgo.com/html/", data=params, headers=headers)
                        if resp_html.status_code == 200:
                            soup = BeautifulSoup(resp_html.text, "html.parser")
                            for r in soup.select(".result"):
                                title_elem = r.select_one(".result__title .result__snippet") or r.select_one(".result__title")
                                snippet_elem = r.select_one(".result__snippet")
                                url_elem = r.select_one(".result__url")
                                if title_elem and snippet_elem:
                                    results.append({
                                        "title": title_elem.get_text(strip=True),
                                        "snippet": snippet_elem.get_text(strip=True),
                                        "link": url_elem.get_text(strip=True) if url_elem else ""
                                    })
                                if len(results) >= system_config.tools.max_search_results:
                                    break
                    except Exception:
                        pass

                # 3. Fallback to DuckDuckGo Instant Answer API if Lite & HTML both returned empty/202/403
                if not results:
                    try:
                        resp_api = await client.get("https://api.duckduckgo.com/", params={"q": query, "format": "json"}, headers={"User-Agent": "K-Jocker/1.0"})
                        api_data = resp_api.json()
                        if api_data.get("AbstractText"):
                            results.append({
                                "title": api_data.get("Heading", query),
                                "snippet": api_data["AbstractText"],
                                "link": api_data.get("AbstractURL", "")
                            })
                        for rt in api_data.get("RelatedTopics", []):
                            if isinstance(rt, dict) and rt.get("Text"):
                                results.append({
                                    "title": rt["Text"][:60],
                                    "snippet": rt["Text"],
                                    "link": rt.get("FirstURL", "")
                                })
                            if len(results) >= system_config.tools.max_search_results:
                                break
                    except Exception:
                        pass

                # 4. Infallible Live Knowledge Fallback (Wikipedia Verified API)
                if not results:
                    try:
                        wiki_resp = await client.get(
                            "https://en.wikipedia.org/w/api.php",
                            params={"action": "query", "list": "search", "srsearch": query, "format": "json"},
                            headers={"User-Agent": "KJockerBot/1.0 (contact: owner@kjocker.local)"}
                        )
                        if wiki_resp.status_code == 200:
                            for item in wiki_resp.json().get("query", {}).get("search", []):
                                raw_snip = BeautifulSoup(item.get("snippet", ""), "html.parser").get_text(strip=True)
                                item_title = item.get("title", "")
                                results.append({
                                    "title": item_title,
                                    "snippet": raw_snip,
                                    "link": "https://en.wikipedia.org/wiki/" + item_title.replace(" ", "_")
                                })
                                if len(results) >= system_config.tools.max_search_results:
                                    break
                    except Exception:
                        pass

                if not results:
                    return ToolResult(
                        success=True,
                        data=[],
                        execution_time_ms=(time.time() - start_time) * 1000
                    )

                if system_config.tools.web_search_allow_write and results:
                    try:
                        WEB_CACHE_DIR.mkdir(parents=True, exist_ok=True)
                        query_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()[:16]
                        cache_file = WEB_CACHE_DIR / f"search_{query_hash}.json"
                        cache_data = {
                            "query": query,
                            "timestamp": int(time.time()),
                            "results_count": len(results),
                            "results": results
                        }
                        cache_file.write_text(json.dumps(cache_data, ensure_ascii=False, indent=2), encoding="utf-8")
                    except Exception:
                        pass

                elapsed = (time.time() - start_time) * 1000
                return ToolResult(
                    success=True,
                    data=results,
                    execution_time_ms=elapsed
                )

        except Exception as e:
            return ToolResult(
                success=False,
                data=[],
                error=f"Web search unavailable: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000
            )
