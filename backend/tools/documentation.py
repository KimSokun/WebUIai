import time
import httpx
from typing import Any, Dict, List
from backend.platform.manifest import PlatformTool, ToolManifest, ToolCategory, RiskLevel
from backend.tools.base import ToolResult

class DocumentationSearchTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="documentation_search",
            name="Documentation Search",
            category=ToolCategory.DOCUMENTATION,
            description="Search official developer documentation across Python, MDN, Microsoft, Google, Qt, Rust, Go, C++, Linux.",
            tags=["docs", "reference", "api", "official", "manual"],
            risk_level=RiskLevel.RESEARCH,
            timeout_seconds=5.0
        ))

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The technical topic or API to search for"},
                "technology": {"type": "string", "description": "Target technology (e.g. python, mdn, rust, go, qt, microsoft)"}
            },
            "required": ["query"]
        }

    async def execute(self, query: str = "", technology: str = "", **kwargs) -> ToolResult:
        from backend.tools.search import WebSearchTool
        web = WebSearchTool()
        target_q = f"site:docs.python.org {query}" if technology.lower() == "python" else (
            f"site:developer.mozilla.org {query}" if technology.lower() == "mdn" else (
                f"site:doc.rust-lang.org {query}" if technology.lower() == "rust" else (
                    f"site:go.dev {query}" if technology.lower() == "go" else (
                        f"{technology} official documentation {query}"
                    )
                )
            )
        )
        res = await web.execute(query=target_q)
        return ToolResult(success=res.success, data=res.data, error=res.error)

class RFCSearchTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="rfc_search",
            name="RFC Standards Search",
            category=ToolCategory.DOCUMENTATION,
            description="Search official IETF RFC specifications and internet protocol standards.",
            tags=["rfc", "standard", "ietf", "protocol", "spec"],
            risk_level=RiskLevel.RESEARCH,
            timeout_seconds=5.0
        ))

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "rfc_number_or_topic": {"type": "string", "description": "RFC number (e.g. '7540') or protocol topic (e.g. 'HTTP/2')"}
            },
            "required": ["rfc_number_or_topic"]
        }

    async def execute(self, rfc_number_or_topic: str = "", **kwargs) -> ToolResult:
        from backend.tools.search import WebSearchTool
        web = WebSearchTool()
        q = f"site:rfc-editor.org/rfc/ {rfc_number_or_topic} OR rfc {rfc_number_or_topic}"
        res = await web.execute(query=q)
        return ToolResult(success=res.success, data=res.data, error=res.error)

class ReleaseNotesSearchTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="release_notes_search",
            name="Release Notes Search",
            category=ToolCategory.DOCUMENTATION,
            description="Search official software release notes, migration guides, and changelogs.",
            tags=["release", "changelog", "migration", "version", "breaking change"],
            risk_level=RiskLevel.RESEARCH,
            timeout_seconds=5.0
        ))

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "software_name": {"type": "string", "description": "Name of the software or library"},
                "version": {"type": "string", "description": "Target version or upgrade path"}
            },
            "required": ["software_name"]
        }

    async def execute(self, software_name: str = "", version: str = "", **kwargs) -> ToolResult:
        from backend.tools.search import WebSearchTool
        web = WebSearchTool()
        q = f"{software_name} {version} release notes changelog migration guide"
        res = await web.execute(query=q)
        return ToolResult(success=res.success, data=res.data, error=res.error)
