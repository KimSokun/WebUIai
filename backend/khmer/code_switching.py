import re
from typing import Dict, List, Any

class KhmerCodeSwitchNormalizer:
    """
    Normalizes mixed Khmer-English developer communication:
    - "backend នេះ error ត្រង់ណា?" -> intent: error_investigation, terms: [backend, error]
    - "ជួយ fix API នេះ" -> intent: code_fix, terms: [API, fix]
    - "ធ្វើ UI ឲ្យ clean ជាងនេះ" -> intent: ui_clean, terms: [UI, clean]
    - "function នេះ slow" -> intent: performance, terms: [function, slow]
    - "why model load មិនបាន?" -> intent: model_loading, terms: [model, load]
    - "ជួយ research library នេះ" -> intent: research, terms: [research, library]
    - "រកវិធី optimize CPU" -> intent: optimization, terms: [optimize, CPU]
    """
    PATTERNS = [
        (re.compile(r"error|កំហុស|fail|exception|bug", re.IGNORECASE), "error_investigation"),
        (re.compile(r"fix|ជួយ\s*fix|កែ|ជួសជុល", re.IGNORECASE), "code_fix"),
        (re.compile(r"slow|យឺត|optimize|ល្បឿន|cpu|ram|memory", re.IGNORECASE), "performance_optimization"),
        (re.compile(r"research|ស្រាវជ្រាវ|ស្វែងរក|library|package", re.IGNORECASE), "research_library"),
        (re.compile(r"model|gguf|load|ទាញយក", re.IGNORECASE), "model_management"),
        (re.compile(r"ui|clean|ស្អាត|ទម្រង់|webui", re.IGNORECASE), "ui_refinement"),
    ]

    ENGLISH_WORD_PATTERN = re.compile(r"[A-Za-z0-9_\.\-]+")

    def parse(self, query: str) -> Dict[str, Any]:
        detected_intents: List[str] = []
        for pat, intent in self.PATTERNS:
            if pat.search(query):
                detected_intents.append(intent)

        if not detected_intents:
            detected_intents.append("general_coding")

        english_terms = self.ENGLISH_WORD_PATTERN.findall(query)
        # Filter out numbers only
        technical_terms = [t for t in english_terms if not t.isdigit() and len(t) > 1]

        return {
            "primary_intent": detected_intents[0],
            "all_intents": detected_intents,
            "technical_terms": technical_terms,
            "is_code_switching": any(ord(c) >= 0x1780 and ord(c) <= 0x17FF for c in query) and len(technical_terms) > 0,
            "original_query": query
        }

code_switch_normalizer = KhmerCodeSwitchNormalizer()
