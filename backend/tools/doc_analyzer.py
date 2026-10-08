# Fast Document & Architecture Analyzer Tool for K-Jocker
# Instant local structural breakdown of Master Prompts, Software Specs, and Architecture Documents (<50ms, Zero Network)

import re
import time
from typing import Dict, Any, List, Optional
from backend.platform.manifest import PlatformTool, ToolManifest, ToolCategory, RiskLevel, ToolResult

class DocAnalyzeTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="doc.analyze",
            name="Document & Architecture Fast Analyzer",
            category=ToolCategory.DOCUMENTATION,
            description="Instantly analyze large Master Prompts, software specifications, architecture guidelines, or markdown documents into structured executive summaries.",
            tags=["doc", "analyze", "architecture", "prompt", "spec", "fast", "turbo"],
            risk_level=RiskLevel.READ,
            timeout_seconds=3.0
        ))

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The document, master prompt, or markdown text to analyze"},
                "focus": {"type": "string", "description": "Optional focus area: all, architecture, tasks, risks", "default": "all"}
            },
            "required": ["text"]
        }

    async def execute(self, text: str = "", focus: str = "all", **kwargs) -> ToolResult:
        start_time = time.time()
        if not text or not text.strip():
            return ToolResult(success=False, data=None, error="Document text cannot be empty.")

        clean_text = text.strip()
        lines = clean_text.splitlines()

        # 1. Extract Document Title & Headers
        title = "Untitled Document"
        headers = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("# ") and title == "Untitled Document":
                title = stripped.lstrip("# ").strip()
            elif stripped.startswith(("#", "##", "###")):
                headers.append(stripped)

        # 2. Extract Key Roles / Missions
        role_match = re.search(r'(?:you are|role|mission|objective)\s*[:—\-]?\s*([^\.\r\n]+)', clean_text, re.IGNORECASE)
        role_desc = role_match.group(0).strip() if role_match else "General System Specification"

        # 3. Detect Components / Files Mentioned
        file_matches = set(re.findall(r'\b[a-zA-Z0-9_\-\.\/]+\.(?:py|js|ts|tsx|jsx|json|yaml|yml|md|html|css|sql|bat|sh)\b', clean_text))
        
        # 4. Detect Key Constraints & Rules
        rules = []
        rule_section = False
        for line in lines:
            lower = line.lower()
            if any(k in lower for k in ["rule", "guideline", "constraint", "requirement", "don't", "must", "never"]):
                if len(line.strip()) > 5 and len(rules) < 10:
                    rules.append(line.strip().lstrip("-*0123456789. "))

        # 5. Detect Tasks & Action Items
        action_items = []
        for line in lines:
            stripped = line.strip()
            if re.match(r'^(?:[0-9]+\.|\-|\*|\[ \]|\[x\])\s+', stripped):
                if any(w in stripped.lower() for w in ["upgrade", "implement", "add", "fix", "create", "support", "ensure", "optimize"]):
                    if len(action_items) < 12:
                        action_items.append(re.sub(r'^(?:[0-9]+\.|\-|\*|\[ \]|\[x\])\s+', '', stripped))

        # 6. Assess Technical Complexity & Word Count
        word_count = len(clean_text.split())
        char_count = len(clean_text)
        approx_tokens = int(char_count / 3.8)

        elapsed_ms = (time.time() - start_time) * 1000

        result = {
            "title": title,
            "role_mission": role_desc,
            "approx_tokens": approx_tokens,
            "word_count": word_count,
            "char_count": char_count,
            "headers_count": len(headers),
            "key_headers": headers[:8],
            "referenced_files": sorted(list(file_matches))[:15],
            "key_rules": rules[:6],
            "action_tasks": action_items[:8],
            "analysis_time_ms": round(elapsed_ms, 2)
        }

        return ToolResult(
            success=True,
            data=result,
            execution_time_ms=elapsed_ms
        )
