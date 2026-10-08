from typing import Any, Dict
from backend.platform.manifest import PlatformTool, ToolManifest, ToolCategory, RiskLevel
from backend.tools.base import ToolResult
from backend.khmer import khmer_glossary, code_switch_normalizer, explanation_engine

class KhmerLanguageDetectTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="khmer_language_detect",
            name="Khmer Script & Token Detector",
            category=ToolCategory.KHMER,
            description="Analyzes text to detect Khmer Unicode characters and developer code-switching.",
            tags=["khmer", "language", "script", "unicode", "detect"],
            risk_level=RiskLevel.ANALYZE,
            timeout_seconds=3.0
        ))

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Input text to analyze"}
            },
            "required": ["text"]
        }

    async def execute(self, text: str = "", **kwargs) -> ToolResult:
        analysis = code_switch_normalizer.parse(text)
        khmer_chars = sum(1 for c in text if 0x1780 <= ord(c) <= 0x17FF)
        ratio = round(khmer_chars / max(1, len(text)), 2)
        return ToolResult(success=True, data={
            "has_khmer": khmer_chars > 0,
            "khmer_char_count": khmer_chars,
            "khmer_ratio": ratio,
            "primary_intent": analysis["primary_intent"],
            "technical_terms": analysis["technical_terms"],
            "is_code_switching": analysis["is_code_switching"]
        })

class KhmerTerminologyLookupTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="khmer_terminology_lookup",
            name="Khmer Technical Terminology Lookup",
            category=ToolCategory.KHMER,
            description="Looks up dual-term format for English technical terms (Khmer explanation + English term).",
            tags=["terminology", "glossary", "khmer", "translate", "technical"],
            risk_level=RiskLevel.READ,
            timeout_seconds=3.0
        ))

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "english_term": {"type": "string", "description": "The English technical term (e.g. 'API', 'backend')"}
            },
            "required": ["english_term"]
        }

    async def execute(self, english_term: str = "", **kwargs) -> ToolResult:
        dual = khmer_glossary.get_dual_term(english_term)
        return ToolResult(success=True, data={"term": english_term, "dual_term": dual})
