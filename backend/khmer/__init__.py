"""
K-Jocker Khmer Intelligence Engine Package
High-priority Khmer linguistic, technical terminology, developer code-switching, and 7-step explanation pipelines.
"""
from backend.khmer.glossary import khmer_glossary, KhmerGlossary
from backend.khmer.code_switching import code_switch_normalizer, KhmerCodeSwitchNormalizer
from backend.khmer.explanation_engine import explanation_engine, KhmerTechnicalExplanationEngine
from backend.khmer.term_preserver import term_preserver, TermPreserver

__all__ = [
    "khmer_glossary",
    "KhmerGlossary",
    "code_switch_normalizer",
    "KhmerCodeSwitchNormalizer",
    "explanation_engine",
    "KhmerTechnicalExplanationEngine",
    "term_preserver",
    "TermPreserver"
]
