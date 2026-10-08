import re
from typing import Tuple, Dict

class TermPreserver:
    """
    Protects technical terms, code symbols, versions, and paths from being
    corrupted or mistranslated during multilingual processing.
    """
    PROTECTION_PATTERN = re.compile(
        r"(`[^`]+`)|"                          # Backticked code
        r"(\b[A-Za-z_][A-Za-z0-9_]*\.[a-z]{1,4}\b)|"  # Filenames (e.g. config.py)
        r"(\bv?\d+\.\d+(?:\.\d+)?(?:-[a-zA-Z0-9]+)?\b)|" # Version numbers (e.g. 1.5.0, v3.2)
        r"(\bhttps?://[^\s\)\]]+)|"         # URLs
        r"(\b[A-Z][a-zA-Z0-9]+(?:Error|Exception|Engine|Adapter|Tool|Router|Pipeline)\b)|" # Class names
        r"(\bdef\s+[a-zA-Z0-9_]+|\bclass\s+[a-zA-Z0-9_]+)" # Definitions
    )

    def mask_terms(self, text: str) -> Tuple[str, Dict[str, str]]:
        mapping = {}
        counter = 0

        def repl(match):
            nonlocal counter
            val = match.group(0)
            token = f"__KJOCKER_TECH_TOKEN_{counter}__"
            mapping[token] = val
            counter += 1
            return token

        masked = self.PROTECTION_PATTERN.sub(repl, text)
        return masked, mapping

    def unmask_terms(self, text: str, mapping: Dict[str, str]) -> str:
        unmasked = text
        for token, val in mapping.items():
            unmasked = unmasked.replace(token, val)
        return unmasked

term_preserver = TermPreserver()
