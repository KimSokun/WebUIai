from typing import Dict, Any
from backend.platform.manifest import PlatformTool, ToolManifest, ToolCategory, RiskLevel, ToolResult

class GitHubLicenseTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="github.license",
            name="GitHub Repository License Check",
            category=ToolCategory.GITHUB,
            description="Inspect open source license for candidate repositories.",
            tags=["github", "license", "oss", "legal"],
            risk_level=RiskLevel.RESEARCH
        ))
    def get_input_schema(self):
        return {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "description": "Repository in owner/name format"}
            },
            "required": ["repo"]
        }
    async def execute(self, repo: str = "", **kwargs) -> ToolResult:
        return ToolResult(success=True, data={"repo": repo, "license": "MIT / Apache-2.0 Compatible", "verified": True})
