"""
K-Jocker Universal Coding Intelligence Package
Multi-language detection, architectural profiles, AST syntax checks, and evidence tracking.
"""
from backend.coding.language_detector import language_detector, LanguageDetector
from backend.coding.language_profiles import language_profiles, LanguageProfileRegistry
from backend.coding.syntax_checker import syntax_checker, SyntaxChecker
from backend.coding.evidence_tracker import evidence_tracker, EvidenceTracker

__all__ = [
    "language_detector",
    "LanguageDetector",
    "language_profiles",
    "LanguageProfileRegistry",
    "syntax_checker",
    "SyntaxChecker",
    "evidence_tracker",
    "EvidenceTracker"
]
