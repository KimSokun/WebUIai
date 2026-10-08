import re
from typing import Dict, Any
from backend.platform.manifest import PlatformTool, ToolManifest, ToolCategory, RiskLevel, ToolResult

class URLExtractTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="web.extract",
            name="Web Content Extractor",
            category=ToolCategory.WEB_RESEARCH,
            description="Extract text, headers, and code blocks from HTML or web snippets.",
            tags=["web", "extract", "html", "parser"],
            risk_level=RiskLevel.RESEARCH
        ))
    def get_input_schema(self):
        return {
            "type": "object",
            "properties": {
                "raw_html_or_text": {"type": "string", "description": "Raw HTML or web text content"}
            },
            "required": ["raw_html_or_text"]
        }
    async def execute(self, raw_html_or_text: str = "", **kwargs) -> ToolResult:
        clean = re.sub(r'<[^>]+>', ' ', raw_html_or_text)
        clean = re.sub(r'\s+', ' ', clean).strip()
        code_blocks = re.findall(r'```(?:[a-zA-Z]*)\n([\s\S]*?)```', raw_html_or_text)
        return ToolResult(success=True, data={"clean_text": clean[:2000], "code_blocks": code_blocks})

class URLValidateTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="url.validate",
            name="URL Security Validator",
            category=ToolCategory.WEB_RESEARCH,
            description="Validate and check safety of URLs prior to fetching.",
            tags=["url", "validate", "security", "http"],
            risk_level=RiskLevel.READ
        ))
    def get_input_schema(self):
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to validate"}
            },
            "required": ["url"]
        }
    async def execute(self, url: str = "", **kwargs) -> ToolResult:
        is_http = url.startswith("http://") or url.startswith("https://")
        is_local = "127.0.0.1" in url or "localhost" in url or "192.168." in url or "10." in url
        safe = is_http and not is_local
        return ToolResult(success=True, data={"url": url, "safe": safe, "is_private_ip": is_local})
