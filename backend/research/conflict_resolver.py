from dataclasses import dataclass
from typing import List, Dict, Any, Optional

@dataclass
class EvidenceItem:
    claim: str
    source_url: str
    source_type: str  # SPEC, DOCS, REPO, RELEASE_NOTES, TESTS, REGISTRY, PAPER, ISSUES, STACKOVERFLOW, COMMUNITY
    priority_tier: int  # 1 (Highest) to 10 (Lowest)
    version_context: str = ""

class ConflictResolver:
    """
    10-Tier Source Priority Hierarchy:
    1. Official specification
    2. Official documentation
    3. Official source repository
    4. Official release notes
    5. Official tests/examples
    6. Package registry
    7. Technical papers
    8. GitHub issues/discussions
    9. Stack Overflow
    10. Community discussions
    """
    PRIORITY_MAP = {
        "SPEC": 1,
        "DOCS": 2,
        "REPO": 3,
        "RELEASE_NOTES": 4,
        "TESTS": 5,
        "REGISTRY": 6,
        "PAPER": 7,
        "ISSUES": 8,
        "STACKOVERFLOW": 9,
        "COMMUNITY": 10
    }

    def resolve(self, evidences: List[EvidenceItem]) -> Dict[str, Any]:
        """
        Cross-checks claims, resolves contradictions favoring higher-priority authoritative sources,
        and assigns verification classification.
        """
        if not evidences:
            return {
                "status": "UNCERTAIN",
                "conclusion": "No verifiable evidence found.",
                "confidence": "LOW",
                "best_evidence": None
            }

        # Sort by priority tier ascending (1 is best)
        sorted_ev = sorted(evidences, key=lambda x: x.priority_tier)
        best = sorted_ev[0]

        # Check for conflicting claims among top tiers
        conflicting = False
        conflict_detail = ""
        for item in sorted_ev[1:]:
            has_dep_item = ("deprecat" in item.claim.lower())
            has_dep_best = ("deprecat" in best.claim.lower())
            if item.priority_tier <= 4 and (has_dep_item != has_dep_best):
                conflicting = True
                conflict_detail = f"Discrepancy detected between Tier {best.priority_tier} ({best.source_type}) and Tier {item.priority_tier} ({item.source_type})"
                break

        if conflicting:
            return {
                "status": "CONFLICTING",
                "conclusion": best.claim,
                "conflict_note": conflict_detail,
                "confidence": "MEDIUM",
                "best_evidence": best
            }

        # Classification based on best source tier
        if best.priority_tier <= 2:
            status = "FACT"
            conf = "HIGH"
        elif best.priority_tier <= 5:
            status = "DOCUMENTED"
            conf = "HIGH"
        elif best.priority_tier <= 7:
            status = "INFERRED"
            conf = "MEDIUM"
        else:
            status = "UNCERTAIN"
            conf = "LOW"

        return {
            "status": status,
            "conclusion": best.claim,
            "confidence": conf,
            "best_evidence": best
        }

conflict_resolver = ConflictResolver()
