import sys
import asyncio
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.research.error_diagnostic import error_diagnostic
from backend.research.research_planner import research_planner
from backend.research.citation_manager import citation_manager, Citation, EngineeringReport

def test_error_diagnostic():
    print("=== Testing Error Diagnostic Engine ===")
    
    # 1. Full Python Traceback
    sample_tb = (
        'Traceback (most recent call last):\n'
        '  File "./backend/cloud_adapter.py", line 83, in _producer\n'
        '    response_stream = client.models.generate_content_stream(\n'
        'AttributeError: \'Client\' object has no attribute \'generate_content_stream\''
    )
    res = error_diagnostic.analyze_error(sample_tb)
    assert res.is_error, "Failed to detect traceback"
    assert res.error_type == "AttributeError", f"Expected AttributeError, got {res.error_type}"
    assert res.faulting_symbol == "generate_content_stream", f"Expected symbol generate_content_stream, got {res.faulting_symbol}"
    assert res.faulting_file == "./backend/cloud_adapter.py", f"File mismatch: {res.faulting_file}"
    assert len(res.suggested_queries) >= 2, "Expected at least 2 diagnostic search queries"
    print(" - Traceback parser & symbol extraction: [PASS]")

    # 2. Simple error
    simple_err = "TypeError: missing 1 required positional argument: 'request_id'"
    res_simple = error_diagnostic.analyze_error(simple_err)
    assert res_simple.is_error, "Failed to detect simple error"
    assert res_simple.error_type == "TypeError"
    print(" - Simple error classification: [PASS]")

    # 3. GGUF runtime error
    gguf_err = "llama_server error: CUDA out of memory / failed to load model"
    res_gguf = error_diagnostic.analyze_error(gguf_err)
    assert res_gguf.is_error
    assert res_gguf.faulting_library == "llama.cpp"
    print(" - GGUF runtime error detection: [PASS]")

def test_research_planner():
    print("\n=== Testing Multi-Source Research Planner ===")
    
    # Unknown API query
    q1 = "What is the correct API parameter for FastAPI lifespan contextmanager?"
    assert research_planner.should_research(q1), "Failed to detect unknown API inquiry"
    
    plan = research_planner.create_plan(q1)
    assert len(plan.queries) >= 2, "Expected multi-tier research queries"
    assert plan.queries[0].target_tier == "LEVEL_1_AUTHORITATIVE", "First tier must be authoritative"
    print(f" - Formulated {len(plan.queries)} multi-tier queries: [PASS]")
    for idx, q in enumerate(plan.queries, 1):
        print(f"   Tier {idx} [{q.target_tier}]: {q.query_text}")

    # General question should NOT trigger research
    q_general = "What is 25 + 25?"
    assert not research_planner.should_research(q_general), "Arithmetic question should not trigger research"
    print(" - Knowledge threshold check (no unnecessary research): [PASS]")

def test_citation_manager():
    print("\n=== Testing Citation Manager & Engineering Report ===")
    
    cits = [
        Citation(
            source_url="https://fastapi.tiangolo.com/advanced/events/",
            source_type="official_docs",
            title="FastAPI Lifespan Events",
            snippet="Use the lifespan parameter of the FastAPI app to define startup and shutdown logic."
        ),
        Citation(
            source_url="https://github.com/fastapi/fastapi/issues/5000",
            source_type="github_issue",
            title="Issue #5000 Lifespan Migration",
            snippet="on_event is deprecated, migrate to asynccontextmanager lifespan."
        )
    ]
    
    report = EngineeringReport(
        question="How to configure FastAPI lifespan without deprecated on_event?",
        conclusion="Pass an asynccontextmanager generator to the lifespan parameter of FastAPI.",
        confidence="HIGH",
        authoritative_evidence=["FastAPI official documentation specifies @asynccontextmanager lifespan(app: FastAPI)."],
        important_findings=["Deprecated @app.on_event('startup') triggers Starlette deprecation warnings."],
        version_context="FastAPI >= 0.93.0",
        recommended_implementation="asynccontextmanager\nasync def lifespan(app: FastAPI):\n    yield",
        risks=["Ensure yield is called exactly once."],
        citations=cits
    )
    
    md = citation_manager.format_engineering_report(report)
    assert "### 🔬 RESEARCH RESULT & TECHNICAL ANALYSIS" in md
    assert "FastAPI Lifespan Events" in md
    assert "`official_docs`" in md
    print(" - Compact engineering report with verified citations: [PASS]")

if __name__ == "__main__":
    test_error_diagnostic()
    test_research_planner()
    test_citation_manager()
    print("\nALL RESEARCH ENGINE UNIT TESTS PASSED [PASS]!")
