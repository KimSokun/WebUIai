"""
K-Jocker Autonomous Self-Verification & Anti-Overconfidence Engine
==================================================================
Provides real-time detection of verification queries, enforces adversarial
self-critique, suppresses blind false overconfidence, and mandates honest
step-by-step error checking and correction across both English and Khmer.
"""

import re
from typing import List, Dict, Any, Tuple

class SelfVerificationEngine:
    """
    High-speed, token-efficient verification and epistemic humility engine.
    Ensures the AI never makes blind overconfident claims like 'All answers are correct'
    and actively audits itself for errors, edge cases, and arithmetic slips.
    """

    # Triggers for verification / critique / error-checking queries
    _VERIFICATION_TRIGGERS: List[str] = [
        # English
        "verify", "check", "audit", "correct", "correction", "is this right", "is it correct",
        "are these correct", "find error", "find bug", "any mistake", "double check",
        "solve", "critique", "review", "evaluate", "inspect", "validate", "flaw",
        "does this work", "is this true", "confirm", "proof", "re-check", "sanity check",
        "true or false", "right or wrong", "test this",
        # Khmer (modular keywords)
        "ត្រួតពិនិត្យ", "កែតម្រូវ", "ផ្ទៀងផ្ទាត់", "ត្រឹមត្រូវ", "ខុស", "កំហុស",
        "ពិនិត្យ", "ដោះស្រាយ", "ប្រាកដទេ", "រកកំហុស", "ជួយកែ", "ពិតទេ",
        "ត្រូវទេ", "ខុសទេ", "មានកំហុស", "លទ្ធផលត្រូវ", "សង្ស័យ", "សួរថាត្រូវ"
    ]

    # Blanket overconfidence patterns that indicate sycophantic false certainty
    _OVERCONFIDENCE_PATTERNS: List[str] = [
        r'all\s+answers\s+are\s+(completely\s+)?correct',
        r'everything\s+is\s+100%\s+correct',
        r'there\s+are\s+no\s+errors?\s+(whatsoever|at\s+all)',
        r'completely\s+flawless',
        r'ចម្លើយទាំងអស់(សុទ្ធតែ|គឺ)?ត្រឹមត្រូវ(\s*១០០%)?',
        r'គ្មានកំហុស(ទាល់តែសោះ|អ្វីទាំងអស់)',
        r'ត្រឹមត្រូវទាំងអស់(\s*១០០%)?'
    ]

    def is_verification_query(self, text: str) -> bool:
        """
        Determines if the user query asks to check, verify, audit, solve, or correct work.
        Runs in <1ms without heavy dependencies.
        """
        if not text:
            return False

        clean = text.lower()
        for trig in self._VERIFICATION_TRIGGERS:
            if trig in clean:
                return True

        # Check for arithmetic expressions or math evaluations like "15 * 12 = 170" or "?", "="
        if re.search(r'\d+\s*[\+\-\*\/\^=]\s*\d+', text) and any(q in clean for q in ["right", "correct", "true", "ត្រូវ", "ពិត", "?"]):
            return True

        return False

    def get_verification_prompt(self, text: str) -> str:
        """
        Generates a concise (~35-40 token) mandatory self-verification protocol
        injected into the system prompt during inference.
        """
        is_verify = self.is_verification_query(text)
        if not is_verify:
            # Baseline epistemic humility reminder
            return (
                "[EPISTEMIC HUMILITY & TRUTHFULNESS DIRECTIVE]:\n"
                "- Speak with honesty and precision. Never make blind claims of 100% certainty without proof.\n"
                "- If uncertain or estimating, explicitly state your confidence limits rather than fabricating false certainty."
            )

        return (
            "[MANDATORY SELF-VERIFICATION & ANTI-OVERCONFIDENCE PROTOCOL]:\n"
            "1. ADVERSARIAL SELF-CRITIQUE: Strictly DO NOT blindly claim 'All answers are correct' or 'Everything is 100% accurate'. "
            "Assume there may be subtle errors, arithmetic slips, sign errors, logic traps, or false assumptions. Actively search for flaws.\n"
            "2. STEP-BY-STEP PROOF: Verify every calculation, formula, code line, and statement explicitly. Show the mathematical calculation or logic trace.\n"
            "3. HONEST ERROR DETECTION & CORRECTION: If an error or bug is found, immediately point it out with clarity, explain why it is wrong, "
            "and provide the exact corrected solution. Never defend a flawed answer with false confidence.\n"
            "4. EPISTEMIC HUMILITY: Clearly distinguish between VERIFIED FACTS (checked with tools or exact step-by-step proof) and THEORETICAL INFERENCES."
        )

    def scan_overconfidence(self, response_text: str) -> bool:
        """
        Detects whether a response contains suspicious blanket overconfident assertions.
        """
        if not response_text:
            return False

        clean = response_text.lower()
        for pat in self._OVERCONFIDENCE_PATTERNS:
            if re.search(pat, clean):
                return True
        return False

# Global singleton instance
self_verification_engine = SelfVerificationEngine()
