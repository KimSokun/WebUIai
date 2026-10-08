import time
import httpx
from typing import Any, Dict, List, Optional
from backend.tools.base import BaseTool, ToolResult

class PackageRegistryTool(BaseTool):
    """
    Queries authoritative package registries (PyPI, npm, crates.io) for verified
    package versions, licenses, dependencies, and release histories.
    """
    def __init__(self):
        super().__init__(
            name="package_registry",
            description="Inspect package ecosystems (PyPI, npm, crates.io) for versions, dependencies, and docs.",
            risk_level="LOW",
            requires_confirmation=False
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "package_name": {"type": "string", "description": "The exact name of the package (e.g. 'fastapi', 'svelte', 'tokio')"},
                "ecosystem": {"type": "string", "enum": ["pypi", "npm", "crates"], "default": "pypi", "description": "Package ecosystem"}
            },
            "required": ["package_name"]
        }

    async def execute(self, package_name: str = "", ecosystem: str = "pypi", **kwargs) -> ToolResult:
        start_time = time.time()
        clean_name = package_name.strip()
        if not clean_name:
            return ToolResult(success=False, data=None, error="Package name cannot be empty.")

        eco = ecosystem.lower().strip()
        try:
            async with httpx.AsyncClient(timeout=4.0, headers={"User-Agent": "K-Jocker-Research-Engine/1.0"}) as client:
                if eco == "pypi":
                    resp = await client.get(f"https://pypi.org/pypi/{clean_name}/json")
                    if resp.status_code == 200:
                        data = resp.json()
                        info = data.get("info", {})
                        releases = list(data.get("releases", {}).keys())
                        return ToolResult(
                            success=True,
                            data={
                                "ecosystem": "PyPI",
                                "name": info.get("name"),
                                "latest_version": info.get("version"),
                                "summary": info.get("summary"),
                                "license": info.get("license"),
                                "home_page": info.get("home_page") or info.get("project_urls", {}).get("Homepage"),
                                "docs_url": info.get("docs_url") or info.get("project_urls", {}).get("Documentation"),
                                "recent_versions": releases[-5:] if releases else []
                            },
                            execution_time_ms=(time.time() - start_time) * 1000
                        )

                elif eco == "npm":
                    resp = await client.get(f"https://registry.npmjs.org/{clean_name}")
                    if resp.status_code == 200:
                        data = resp.json()
                        dist_tags = data.get("dist-tags", {})
                        latest_ver = dist_tags.get("latest")
                        latest_meta = data.get("versions", {}).get(latest_ver, {}) if latest_ver else {}
                        return ToolResult(
                            success=True,
                            data={
                                "ecosystem": "npm",
                                "name": data.get("name"),
                                "latest_version": latest_ver,
                                "description": data.get("description"),
                                "license": data.get("license"),
                                "homepage": latest_meta.get("homepage"),
                                "repository": latest_meta.get("repository", {}).get("url") if isinstance(latest_meta.get("repository"), dict) else None
                            },
                            execution_time_ms=(time.time() - start_time) * 1000
                        )

                elif eco == "crates":
                    resp = await client.get(f"https://crates.io/api/v1/crates/{clean_name}")
                    if resp.status_code == 200:
                        data = resp.json().get("crate", {})
                        return ToolResult(
                            success=True,
                            data={
                                "ecosystem": "crates.io",
                                "name": data.get("name"),
                                "latest_version": data.get("max_version"),
                                "description": data.get("description"),
                                "homepage": data.get("homepage"),
                                "documentation": data.get("documentation"),
                                "repository": data.get("repository"),
                                "downloads": data.get("downloads")
                            },
                            execution_time_ms=(time.time() - start_time) * 1000
                        )

            # Fallback to search if not found in specific registry
            from backend.tools.search import WebSearchTool
            web = WebSearchTool()
            fb = await web.execute(query=f"{clean_name} {eco} package documentation official")
            return ToolResult(
                success=fb.success,
                data={"fallback_search": fb.data},
                execution_time_ms=(time.time() - start_time) * 1000
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"Package registry fetch error: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000
            )

package_registry_tool = PackageRegistryTool()
