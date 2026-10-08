from typing import Dict, Any
from backend.platform.manifest import PlatformTool, ToolManifest, ToolCategory, RiskLevel, ToolResult
OFFICIAL_DOCS = {
    "python": {"name": "Python Standard Library", "docs_url": "https://docs.python.org/3/", "spec_type": "PEP Standards"},
    "rust": {"name": "Rust Reference", "docs_url": "https://doc.rust-lang.org/reference/", "spec_type": "Rust RFCs"},
    "go": {"name": "Go Language Specification", "docs_url": "https://go.dev/ref/spec", "spec_type": "Go Spec"},
    "javascript": {"name": "ECMAScript Language Specification", "docs_url": "https://tc39.es/ecma262/", "spec_type": "ECMA-262"},
    "c++": {"name": "ISO C++ Standard", "docs_url": "https://en.cppreference.com/w/cpp", "spec_type": "ISO/IEC 14882"}
}

class DocsSpecificationTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="docs.specification",
            name="Documentation Specification Search",
            category=ToolCategory.DOCUMENTATION,
            description="Lookup official language and standard library specification references.",
            tags=["docs", "spec", "standards", "rfc", "specification"],
            risk_level=RiskLevel.READ
        ))
    def get_input_schema(self):
        return {
            "type": "object",
            "properties": {
                "standard": {"type": "string", "description": "Language or spec standard (e.g. python, rust, c++)"}
            },
            "required": ["standard"]
        }
    async def execute(self, standard: str = "", **kwargs) -> ToolResult:
        spec_info = OFFICIAL_DOCS.get(standard.lower(), {
            "name": standard,
            "docs_url": f"https://devdocs.io/{standard}",
            "spec_type": "Universal Technical Standard"
        })
        return ToolResult(success=True, data=spec_info)
