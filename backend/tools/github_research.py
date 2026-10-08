import time
import httpx
from typing import Any, Dict, List
from backend.tools.base import BaseTool, ToolResult

class GitHubSearchTool(BaseTool):
    """
    Searches public GitHub repositories, code, and issues for libraries, runtimes,
    and open-source implementations.
    """
    def __init__(self):
        super().__init__(
            name="github_search",
            description="Search public GitHub repositories, issues, or releases for implementation references and fixes.",
            risk_level="LOW",
            requires_confirmation=False
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search term (e.g. 'llama.cpp gguf metadata', 'FastAPI lifespan error')"},
                "search_type": {"type": "string", "enum": ["repositories", "issues"], "default": "repositories"}
            },
            "required": ["query"]
        }

    async def execute(self, query: str = "", search_type: str = "repositories", **kwargs) -> ToolResult:
        start_time = time.time()
        headers = {
            "User-Agent": "K-Jocker-Research-Engine/1.0",
            "Accept": "application/vnd.github.v3+json"
        }
        url = f"https://api.github.com/search/{search_type}"
        params = {"q": query, "per_page": 5}

        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.get(url, params=params, headers=headers)
                if resp.status_code == 200:
                    data = resp.json().get("items", [])
                    results = []
                    for item in data[:5]:
                        if search_type == "repositories":
                            results.append({
                                "full_name": item.get("full_name"),
                                "description": item.get("description"),
                                "url": item.get("html_url"),
                                "stars": item.get("stargazers_count"),
                                "language": item.get("language")
                            })
                        else:
                            results.append({
                                "title": item.get("title"),
                                "url": item.get("html_url"),
                                "state": item.get("state"),
                                "snippet": (item.get("body") or "")[:200]
                            })
                    return ToolResult(
                        success=True,
                        data=results,
                        execution_time_ms=(time.time() - start_time) * 1000
                    )

            # Fallback to web search for GitHub if API hit rate-limit
            from backend.tools.search import WebSearchTool
            web_tool = WebSearchTool()
            fb_res = await web_tool.execute(query=f"site:github.com {query}")
            return ToolResult(
                success=fb_res.success,
                data=fb_res.data,
                execution_time_ms=(time.time() - start_time) * 1000
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data=[],
                error=f"GitHub search failed: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000
            )

class GitHubSourceReadTool(BaseTool):
    """
    Reads source files directly from public GitHub repositories using raw content URLs.
    Allows K-Jocker to inspect actual implementation code when documentation is insufficient.
    """
    def __init__(self):
        super().__init__(
            name="github_source_read",
            description="Inspect raw source code of public GitHub repository files to verify actual implementation.",
            risk_level="LOW",
            requires_confirmation=False
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "GitHub username or organization (e.g. ggerganov)"},
                "repo": {"type": "string", "description": "GitHub repository name (e.g. llama.cpp)"},
                "file_path": {"type": "string", "description": "Path to file inside repo (e.g. examples/server/server.cpp)"},
                "branch": {"type": "string", "description": "Branch name (default: master)", "default": "master"}
            },
            "required": ["owner", "repo", "file_path"]
        }

    async def execute(self, owner: str, repo: str, file_path: str, branch: str = "master", **kwargs) -> ToolResult:
        start_time = time.time()
        clean_file = file_path.strip().lstrip("/")
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{clean_file}"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(raw_url)
                if resp.status_code == 200:
                    text = resp.text
                    lines = text.splitlines()[:1500]  # Up to 1500 lines enabled by 100k context
                    return ToolResult(
                        success=True,
                        data={
                            "url": raw_url,
                            "lines_retrieved": len(lines),
                            "content": "\n".join(lines)
                        },
                        execution_time_ms=(time.time() - start_time) * 1000
                    )
                elif resp.status_code == 404 and branch == "master":
                    # Try 'main' branch
                    resp_main = await client.get(f"https://raw.githubusercontent.com/{owner}/{repo}/main/{clean_file}")
                    if resp_main.status_code == 200:
                        lines = resp_main.text.splitlines()[:150]
                        return ToolResult(
                            success=True,
                            data={
                                "url": f"https://raw.githubusercontent.com/{owner}/{repo}/main/{clean_file}",
                                "lines_retrieved": len(lines),
                                "content": "\n".join(lines)
                            },
                            execution_time_ms=(time.time() - start_time) * 1000
                        )

                return ToolResult(
                    success=False,
                    data=None,
                    error=f"GitHub file not found (HTTP {resp.status_code}) at '{raw_url}'",
                    execution_time_ms=(time.time() - start_time) * 1000
                )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"GitHub source fetch error: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000
            )
