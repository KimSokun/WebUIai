import re
import time
from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field

from backend.research.citation_manager import citation_manager, Citation, EngineeringReport
from backend.research.error_diagnostic import error_diagnostic, DiagnosticResult

class ResearchQuery(BaseModel):
    query_text: str
    target_tier: str  # "LEVEL_1_AUTHORITATIVE", "LEVEL_2_TECHNICAL", "LEVEL_3_COMMUNITY"
    purpose: str

class ResearchFinding(BaseModel):
    claim: str
    status: str = "DOCUMENTED"  # "FACT", "DOCUMENTED", "INFERRED", "UNCERTAIN", "CONFLICTING"
    source_url: str
    source_title: str
    confidence: str = "HIGH"

class ResearchPlan(BaseModel):
    topic: str
    is_error: bool = False
    queries: List[ResearchQuery] = Field(default_factory=list)
    findings: List[ResearchFinding] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    confidence: str = "HIGH"

class ResearchPlanner:
    """
    Intelligent Research Planner:
    When K-Jocker encounters an unknown API, library, error, or model inquiry,
    this engine plans and executes multi-source investigations across authoritative
    documentation and code repositories rather than guessing.
    """
    API_INDICATORS = [
        "how to use", "how do i use", "api for", "parameter for", "function for",
        "documentation for", "syntax for", "method for", "breaking change",
        "deprecated", "difference between", "version compatibility", "compatible with"
    ]

    def should_research(self, user_msg: str) -> bool:
        """
        Determines whether a user query requires technical research instead of direct answers.
        """
        lower = user_msg.lower()

        # Check for error tracebacks or exception syntax
        diag = error_diagnostic.analyze_error(user_msg)
        if diag.is_error:
            return True

        # Check for explicit API/library questions
        if any(ind in lower for ind in self.API_INDICATORS):
            return True

        # Check for technical library / runtime queries
        technical_terms = [
            "fastapi", "pydantic", "httpx", "llama.cpp", "gguf", "transformers",
            "pytorch", "torch", "quantization", "q4_k_m", "q5_k_m", "vulkan", "cuda",
            "pyside6", "ffmpeg", "github", "hugging face", "huggingface"
        ]
        term_count = sum(1 for t in technical_terms if t in lower)
        if term_count >= 1 and any(q in lower for q in ["what", "how", "why", "error", "support", "does", "which", "version"]):
            return True

        return False

    def create_plan(self, user_msg: str) -> ResearchPlan:
        """
        Constructs a prioritized multi-source research plan following the 3-tier hierarchy.
        """
        diag = error_diagnostic.analyze_error(user_msg)
        queries: List[ResearchQuery] = []

        if diag.is_error:
            # Plan for Error Diagnostic
            for q in diag.suggested_queries[:2]:
                queries.append(ResearchQuery(
                    query_text=f"{q} official documentation",
                    target_tier="LEVEL_1_AUTHORITATIVE",
                    purpose="Find official documentation on root cause"
                ))
            queries.append(ResearchQuery(
                query_text=f"{diag.faulting_library or 'python'} {diag.error_type} github issues",
                target_tier="LEVEL_3_COMMUNITY",
                purpose="Inspect known GitHub issues and community resolutions"
            ))
            return ResearchPlan(topic=f"Error: {diag.symptom}", is_error=True, queries=queries)

        # Plan for General Technical / API / Library inquiry
        clean_query = re.sub(r'^(?:what is|how to|explain|tell me about|how do i)\s+', '', user_msg, flags=re.IGNORECASE).strip(" ?.")
        
        # Tier 1: Authoritative official documentation
        queries.append(ResearchQuery(
            query_text=f"{clean_query} official documentation",
            target_tier="LEVEL_1_AUTHORITATIVE",
            purpose="Retrieve official API specifications and docs"
        ))

        # Tier 1/2: GitHub repository and source references
        queries.append(ResearchQuery(
            query_text=f"{clean_query} github",
            target_tier="LEVEL_2_TECHNICAL",
            purpose="Inspect official GitHub repository and implementation"
        ))

        return ResearchPlan(topic=clean_query, is_error=False, queries=queries)

    async def execute_plan(self, plan: ResearchPlan, search_executor) -> EngineeringReport:
        """
        Executes the research plan using the available search tool and compiles findings.
        """
        all_citations: List[Citation] = []
        authoritative_evidence: List[str] = []
        important_findings: List[str] = []

        for rq in plan.queries:
            try:
                search_res = await search_executor(query=rq.query_text)
                if not search_res.success or not search_res.data:
                    continue

                for item in search_res.data[:3]:
                    url = item.get("link", "")
                    title = item.get("title", "")
                    snippet = item.get("snippet", "")

                    # Classify source type
                    source_type = "web"
                    if "github.com" in url:
                        source_type = "github_source" if "/blob/" in url or "/tree/" in url else "github_issue"
                    elif any(d in url for d in ["docs.", "documentation", "api.", "readthedocs", "huggingface.co"]):
                        source_type = "official_docs"

                    cit = Citation(
                        source_url=url,
                        source_type=source_type,
                        title=title,
                        snippet=snippet
                    )
                    all_citations.append(cit)

                    finding_text = f"{title}: {snippet}"
                    if source_type in ("official_docs", "github_source"):
                        authoritative_evidence.append(finding_text)
                    else:
                        important_findings.append(finding_text)

            except Exception:
                continue

        confidence = "HIGH" if authoritative_evidence else ("MEDIUM" if important_findings else "LOW")
        conclusion = "Technical evidence retrieved from official and community sources." if all_citations else "Online research was unable to find verified external sources."

        report = EngineeringReport(
            question=plan.topic,
            conclusion=conclusion,
            confidence=confidence,
            authoritative_evidence=authoritative_evidence[:4],
            important_findings=important_findings[:4],
            citations=all_citations[:6]
        )

        return report

research_planner = ResearchPlanner()
