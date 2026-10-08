import time
from typing import Any, Dict, Optional
from backend.tools.base import BaseTool, ToolResult

KHMER_DIGITS = "០១២៣៤៥៦៧៨៩"
ARABIC_DIGITS = "0123456789"

EN_TO_KM_DIGITS = str.maketrans(ARABIC_DIGITS, KHMER_DIGITS)
KM_TO_EN_DIGITS = str.maketrans(KHMER_DIGITS, ARABIC_DIGITS)

TECH_GLOSSARY = {
    "variable": "អថេរ (Variable)",
    "function": "អនុគមន៍ (Function)",
    "class": "ថ្នាក់ / ក្លាស (Class)",
    "loop": "រង្វិលជុំ (Loop)",
    "memory": "អង្គចងចាំ (Memory)",
    "database": "មូលដ្ឋានទិន្នន័យ (Database)",
    "security": "សុវត្ថិភាព (Security)",
    "encryption": "ការអ៊ិនគ្រីប / បម្លែងកូដសម្ងាត់ (Encryption)",
    "server": "ម៉ាស៊ីនបម្រើ (Server)",
    "client": "ម៉ាស៊ីនកូន / ក្លាយអិន (Client)",
    "network": "បណ្តាញ (Network)",
    "algorithm": "ក្បួនដោះស្រាយ (Algorithm)",
    "thread": "ខ្សែស្រឡាយដំណើរការ (Thread)",
    "cache": "ឃ្លាំងសម្ងាត់បណ្តោះអាសន្ន (Cache)",
    "compiler": "កម្មវិធីបម្លែងកូដ (Compiler)",
    "interpreter": "កម្មវិធីបកប្រែកូដ (Interpreter)",
    "async": "អសមកាលកម្ម (Asynchronous)",
    "api": "ចំណុចប្រទាក់កម្មវិធី (API)",
    "framework": "ក្របខ័ណ្ឌការងារ (Framework)",
    "library": "បណ្ណាល័យកូដ (Library)"
}

DAYS_KM = {
    "monday": "ថ្ងៃច័ន្ទ", "tuesday": "ថ្ងៃអង្គារ", "wednesday": "ថ្ងៃពុធ",
    "thursday": "ថ្ងៃព្រហស្បតិ៍", "friday": "ថ្ងៃសុក្រ", "saturday": "ថ្ងៃសៅរ៍", "sunday": "ថ្ងៃអាទិត្យ"
}

class KhmerFastHelperTool(BaseTool):
    """Instant Khmer numerals conversion, date translation, and technical glossary lookup (<0.1ms)."""
    def __init__(self):
        super().__init__(
            name="khmer.fast_helper",
            description="Fast Khmer numeral converter (0-9 <-> ០-៩), calendar terms, and technical glossary lookup.",
            risk_level="LOW",
            requires_confirmation=False
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text, number, or English technical word to translate/convert"},
                "action": {"type": "string", "description": "Action: 'to_khmer_num', 'to_arabic_num', 'glossary', 'auto'"}
            },
            "required": ["text"]
        }

    async def execute(self, **kwargs) -> ToolResult:
        text = str(kwargs.get("text", "")).strip()
        action = str(kwargs.get("action", "auto")).lower().strip()

        if not text:
            return ToolResult(success=False, data=None, error="Text parameter is required.")

        start_t = time.perf_counter()

        # 1. Convert to Khmer numerals
        if action == "to_khmer_num" or (action == "auto" and any(c in ARABIC_DIGITS for c in text) and not any(c in KHMER_DIGITS for c in text)):
            converted = text.translate(EN_TO_KM_DIGITS)
            elapsed = (time.perf_counter() - start_t) * 1000
            return ToolResult(success=True, data={"result": converted, "original": text, "type": "khmer_numerals"}, execution_time_ms=elapsed)

        # 2. Convert from Khmer numerals
        if action == "to_arabic_num" or (action == "auto" and any(c in KHMER_DIGITS for c in text)):
            converted = text.translate(KM_TO_EN_DIGITS)
            elapsed = (time.perf_counter() - start_t) * 1000
            return ToolResult(success=True, data={"result": converted, "original": text, "type": "arabic_numerals"}, execution_time_ms=elapsed)

        # 3. Calendar terms
        low = text.lower()
        if low in DAYS_KM:
            elapsed = (time.perf_counter() - start_t) * 1000
            return ToolResult(success=True, data={"english": text, "khmer": DAYS_KM[low], "type": "calendar"}, execution_time_ms=elapsed)

        # 4. Tech glossary lookup
        glossary_match = TECH_GLOSSARY.get(low)
        if glossary_match:
            elapsed = (time.perf_counter() - start_t) * 1000
            return ToolResult(success=True, data={"term": text, "khmer": glossary_match, "type": "glossary"}, execution_time_ms=elapsed)

        # Partial search in glossary
        partial = {k: v for k, v in TECH_GLOSSARY.items() if k in low or low in k}
        elapsed = (time.perf_counter() - start_t) * 1000
        return ToolResult(
            success=True,
            data={"query": text, "matches": partial, "count": len(partial)},
            execution_time_ms=elapsed
        )
