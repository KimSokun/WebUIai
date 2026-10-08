import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class Citation(BaseModel):
    source_url: str
    source_type: str = "web"  # "official_docs", "github_source", "github_issue", "technical_paper", "web"
    title: str
    retrieved_at: float = Field(default_factory=time.time)
    snippet: str = ""
    relevance_score: float = 1.0

class EngineeringReport(BaseModel):
    question: str
    conclusion: str
    confidence: str = "HIGH"  # "HIGH", "MEDIUM", "LOW"
    authoritative_evidence: List[str] = Field(default_factory=list)
    important_findings: List[str] = Field(default_factory=list)
    version_context: Optional[str] = None
    recommended_implementation: Optional[str] = None
    risks: List[str] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)

class CitationManager:
    """
    Manages verified citations and structures compact engineering research reports.
    Ensures zero fabricated citations; every claim retains real provenance.
    """
    def __init__(self):
        self._citations_cache: Dict[str, List[Citation]] = {}

    def register_citations(self, request_id: str, citations: List[Citation]):
        self._citations_cache[request_id] = citations

    def get_citations(self, request_id: str) -> List[Citation]:
        return self._citations_cache.get(request_id, [])

    def format_engineering_report(self, report: EngineeringReport) -> str:
        """
        Formats report into standard production-grade markdown layout.
        """
        lines = []
        lines.append("### 🔬 RESEARCH RESULT & TECHNICAL ANALYSIS")
        lines.append(f"**Question**: {report.question}\n")
        lines.append(f"**Conclusion**: {report.conclusion}\n")
        lines.append(f"**Confidence**: `{report.confidence}`")
        if report.version_context:
            lines.append(f"**Version Context**: `{report.version_context}`")

        if report.authoritative_evidence:
            lines.append("\n**Authoritative Evidence (Level 1 Sources)**:")
            for ev in report.authoritative_evidence:
                lines.append(f"- {ev}")

        if report.important_findings:
            lines.append("\n**Important Findings**:")
            for f in report.important_findings:
                lines.append(f"- {f}")

        if report.recommended_implementation:
            lines.append(f"\n**Recommended Implementation**:\n```text\n{report.recommended_implementation}\n```")

        if report.risks:
            lines.append("\n**Risks & Breaking Change Caveats**:")
            for r in report.risks:
                lines.append(f"- ⚠️ {r}")

        if report.citations:
            lines.append("\n**Verified Sources**:")
            for c in report.citations:
                label = f"[{c.title}]({c.source_url})" if c.source_url.startswith("http") else c.title
                lines.append(f"- {label} (`{c.source_type}`)")

        return "\n".join(lines)

citation_manager = CitationManager()
