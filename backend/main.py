import json
import time
import asyncio
from pathlib import Path
from fastapi import FastAPI, Request, Depends, HTTPException, Body
from fastapi.responses import StreamingResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from backend.config import system_config, save_config, BASE_DIR, MODELS_DIR, SANDBOX_DIR, DOCUMENTS_DIR
from backend.auth import OwnerAuthority
from backend.telemetry import TelemetryTracker
from backend.tools import tool_registry
from contextlib import asynccontextmanager
from backend.agent import agent_controller
from backend.runtime import llm_runtime
from backend.models_manager import models_manager, resolve_model_path
from backend.openai_router import router as openai_router
from backend.conversations import conversation_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    models = models_manager.scan_models()
    if models:
        if not resolve_model_path(system_config.model.model_path).exists():
            models_manager.select_model(models[0]["filename"])
        active_filename = Path(system_config.model.model_path).name
        print(f"[K-Jocker] Local GGUF model detected: '{active_filename}'. Launching llama-server...")
        models_manager.start_llama_server(system_config.model.model_path)
    yield
    models_manager.stop_llama_server()

app = FastAPI(
    title="K-Jocker Owner AI API",
    version="1.5.0",
    description="Local Owner AI & Online Tool Assistant Operating Environment",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register OpenAI & Llama.cpp compatible router
app.include_router(openai_router)

LLAMA_FRONTEND_DIR = BASE_DIR / "frontend"

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]

class ModelSelectRequest(BaseModel):
    filename: str

@app.get("/icon.png", include_in_schema=False)
async def get_icon_png():
    for candidate in [
        BASE_DIR / "icon.png",
        LLAMA_FRONTEND_DIR / "icon.png"
    ]:
        if candidate.exists() and candidate.is_file():
            return FileResponse(candidate, media_type="image/png")
    raise HTTPException(status_code=404, detail="icon.png not found")

@app.get("/apple-touch-icon-180x180.png", include_in_schema=False)
@app.get("/apple-touch-icon.png", include_in_schema=False)
async def get_apple_touch_icon():
    apple_file = LLAMA_FRONTEND_DIR / "apple-touch-icon-180x180.png"
    if apple_file.exists():
        return FileResponse(apple_file, media_type="image/png")
    return FileResponse(BASE_DIR / "icon.png", media_type="image/png")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon_ico():
    fav_ico = LLAMA_FRONTEND_DIR / "favicon.ico"
    if fav_ico.exists():
        return FileResponse(fav_ico, media_type="image/x-icon")
    return {"status": "no favicon"}

@app.get("/favicon.svg", include_in_schema=False)
@app.get("/favicon-dark.svg", include_in_schema=False)
async def favicon_svg():
    fav_file = LLAMA_FRONTEND_DIR / "favicon.svg"
    if fav_file.exists():
        return FileResponse(fav_file, media_type="image/svg+xml")
    return {"status": "no favicon"}

@app.get("/api/health")
async def health():
    return {"status": "ok", "app": "K-Jocker Owner AI", "version": "1.5.0"}

@app.get("/api/status")
async def status():
    return {
        "owner": system_config.owner.owner_name,
        "model": system_config.model.model_name,
        "runtime": system_config.model.runtime,
        "mode": "LOCAL",
        "tools_active": True,
        "models_dir": str(MODELS_DIR)
    }

@app.get("/api/telemetry")
async def get_telemetry(request: Request):
    auth = OwnerAuthority.is_authenticated_owner(request)
    return TelemetryTracker.get_snapshot(owner_auth=auth)

@app.get("/api/models")
async def list_models():
    models = models_manager.scan_models()
    server_status = models_manager.get_server_status()
    return {
        "models": models,
        "models_dir": str(MODELS_DIR),
        "active_model": system_config.model.model_name,
        "server_status": server_status
    }

@app.post("/api/models/select")
async def select_model(request: Request, req: ModelSelectRequest):
    OwnerAuthority.require_owner(request)
    try:
        res = models_manager.select_model(req.filename)
        return res
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/api/models/start-server")
async def start_server(request: Request):
    OwnerAuthority.require_owner(request)
    res = models_manager.start_llama_server()
    return res

@app.post("/api/models/stop-server")
async def stop_server(request: Request):
    OwnerAuthority.require_owner(request)
    res = models_manager.stop_llama_server()
    return res

@app.delete("/api/models/{filename}")
async def delete_model(request: Request, filename: str):
    OwnerAuthority.require_owner(request)
    try:
        res = models_manager.delete_model(filename)
        return res
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tools")
async def list_tools():
    return {
        "tools": tool_registry.list_tools(),
        "policy": system_config.tools.model_dump()
    }

@app.post("/api/tools/toggle")
async def toggle_tool(request: Request, tool_id: str, enabled: bool):
    OwnerAuthority.require_owner(request)
    normalized_id = tool_id.lower().replace("-", "_")
    if normalized_id in ["web_search", "web_search_enabled"]:
        system_config.tools.web_search_enabled = enabled
    elif normalized_id in ["web_search_read", "web_search_allow_read"]:
        system_config.tools.web_search_allow_read = enabled
    elif normalized_id in ["web_search_write", "web_search_allow_write"]:
        system_config.tools.web_search_allow_write = enabled
    elif normalized_id in ["web_fetch", "web_fetch_enabled"]:
        system_config.tools.web_fetch_enabled = enabled
    elif normalized_id in ["local_files", "local_files_enabled"]:
        system_config.tools.local_files_enabled = enabled
    elif normalized_id in ["sandbox_read", "sandbox_read_enabled"]:
        system_config.tools.sandbox_read_enabled = enabled
    elif normalized_id in ["sandbox_write", "sandbox_write_enabled"]:
        system_config.tools.sandbox_write_enabled = enabled
    elif normalized_id in ["sandbox_strict", "online_sandbox_strict_mode"]:
        system_config.tools.online_sandbox_strict_mode = enabled
    else:
        raise HTTPException(status_code=400, detail=f"Unknown tool or policy setting '{tool_id}'")
    save_config(system_config)
    return {"success": True, "setting": normalized_id, "enabled": enabled, "policy": system_config.tools.model_dump()}

@app.get("/api/settings")
async def get_settings(request: Request):
    OwnerAuthority.require_owner(request)
    return system_config.model_dump()

@app.patch("/api/settings")
async def update_settings(request: Request, payload: Dict[str, Any]):
    OwnerAuthority.require_owner(request)
    
    # Protected boundary: AI or external callers cannot change security locks
    if "system_prompt" in payload:
        system_config.system_prompt = payload["system_prompt"]
    if "model" in payload:
        system_config.model = system_config.model.model_copy(update=payload["model"])
    if "tools" in payload:
        system_config.tools = system_config.tools.model_copy(update=payload["tools"])
        
    save_config(system_config)
    return {"success": True, "settings": system_config.model_dump()}

@app.post("/api/chat/stream")
async def chat_stream(request: Request, chat_req: ChatRequest):
    msgs = [{"role": m.role, "content": m.content} for m in chat_req.messages]

    async def event_generator():
        try:
            async for event in agent_controller.handle_chat_stream(msgs):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            err_event = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(err_event)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# --- Conversation Management Endpoints ---

class BulkDeletePayload(BaseModel):
    ids: List[str]

@app.get("/api/conversations")
async def list_conversations_endpoint():
    from backend.conversations import conversation_manager
    return {"conversations": conversation_manager.list_conversations()}

@app.get("/api/conversations/{conv_id}")
async def get_conversation_endpoint(conv_id: str):
    from backend.conversations import conversation_manager
    conv = conversation_manager.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail=f"Conversation '{conv_id}' not found.")
    return conv

@app.post("/api/conversations")
async def save_conversation_endpoint(payload: Dict[str, Any]):
    from backend.conversations import conversation_manager
    conv_id = payload.get("id") or f"conv_{int(time.time()*1000)}"
    saved = conversation_manager.save_conversation(conv_id, payload)
    return {"success": True, "conversation": saved}

@app.delete("/api/conversations/{conv_id}")
async def delete_conversation_endpoint(conv_id: str):
    from backend.conversations import conversation_manager
    deleted = conversation_manager.delete_conversation(conv_id)
    return {"success": True, "deleted": deleted, "id": conv_id}

@app.post("/api/conversations/bulk-delete")
async def bulk_delete_conversations_endpoint(payload: BulkDeletePayload):
    from backend.conversations import conversation_manager
    count = conversation_manager.bulk_delete_conversations(payload.ids)
    return {"success": True, "deleted_count": count}

@app.delete("/api/conversations")
async def delete_all_conversations_endpoint():
    from backend.conversations import conversation_manager
    count = conversation_manager.delete_all_conversations()
    return {"success": True, "deleted_count": count}

# --- Next-Gen Engineering Endpoints ---

@app.get("/api/knowledge")
async def query_knowledge(q: str = "", category: str = ""):
    from backend.knowledge import knowledge_store
    results = knowledge_store.search(query=q, category=category if category else None)
    return {
        "query": q,
        "category": category,
        "count": len(results),
        "results": [
            {
                "topic": r.topic,
                "category": r.category,
                "content": r.content,
                "source": r.source,
                "source_type": r.source_type,
                "version": r.version,
                "verification_status": r.verification_status,
                "confidence": r.confidence
            }
            for r in results
        ]
    }

class CodeExecutionRequest(BaseModel):
    code: str
    timeout_seconds: float = 5.0

@app.post("/api/coding/execute")
async def execute_code(request: Request, req: CodeExecutionRequest):
    OwnerAuthority.require_owner(request)
    from backend.tools.python_executor import python_executor_tool
    res = await python_executor_tool.execute(code=req.code, timeout_seconds=req.timeout_seconds)
    return res.model_dump()

@app.get("/api/languages")
async def list_supported_languages():
    from backend.coding import language_profiles
    langs = language_profiles.list_languages()
    profiles = []
    for l in langs:
        p = language_profiles.get_profile(l)
        if p:
            profiles.append({
                "name": p.name,
                "category": p.category,
                "extensions": p.extensions,
                "package_manager": p.package_manager,
                "package_registry": p.package_registry,
                "docs_url": p.official_docs_url,
                "test_framework": p.test_framework
            })
    return {"count": len(profiles), "languages": profiles}

@app.get("/api/khmer/terms")
async def list_khmer_terms(q: str = ""):
    from backend.khmer import khmer_glossary
    terms = khmer_glossary.TERMS
    if q:
        filtered = {k: v for k, v in terms.items() if q.lower() in k or q in v}
    else:
        filtered = terms
    return {"count": len(filtered), "terms": filtered}

# --- Tool Platform Endpoints ---

class DiscoverRequest(BaseModel):
    task: str
    max_tools: int = 6

class PlatformExecuteRequest(BaseModel):
    tool_id: str
    arguments: Dict[str, Any]

@app.get("/api/platform/tools")
async def list_platform_tools(category: str = ""):
    from backend.platform.registry import tool_platform
    if category:
        tools = tool_platform.get_tools_by_category(category)
        return {
            "category": category,
            "count": len(tools),
            "tools": [
                {
                    "id": t.name,
                    "name": t.name.replace("_", " ").title(),
                    "category": category,
                    "description": t.description,
                    "risk_level": t.risk_level,
                    "schema": t.get_input_schema()
                }
                for t in tools
            ]
        }
    all_tools = tool_platform.list_all_tools()
    return {"count": len(all_tools), "tools": all_tools}

@app.get("/api/platform/categories")
async def list_platform_categories():
    from backend.platform.registry import tool_platform
    return {"categories": tool_platform.list_categories()}

@app.post("/api/platform/discover")
async def discover_tools_endpoint(req: DiscoverRequest):
    from backend.platform.discovery import tool_discovery
    discovered = tool_discovery.discover_tools(req.task, max_tools=req.max_tools)
    return {
        "task": req.task,
        "count": len(discovered),
        "tools": [
            {
                "id": t.name,
                "description": t.description,
                "risk_level": t.risk_level,
                "schema": t.get_input_schema()
            }
            for t in discovered
        ]
    }

@app.post("/api/platform/execute")
async def execute_platform_tool(request: Request, req: PlatformExecuteRequest):
    is_owner = OwnerAuthority.is_authenticated_owner(request)
    from backend.platform.executor import tool_execution_manager
    res = await tool_execution_manager.execute_tool(req.tool_id, req.arguments, is_owner=is_owner)
    return res.model_dump()

# --- Production Engine Alpha Endpoints ---

class EngineRunRequest(BaseModel):
    task: str
    context_files: Optional[List[str]] = None

class WorkflowCodingRequest(BaseModel):
    problem_description: str
    relative_file: str
    original_code: str
    patched_code: str
    test_script: str

class WorkflowResearchRequest(BaseModel):
    library_or_topic: str
    version: str
    question: str

class WorkflowModelRequest(BaseModel):
    task_type: str = "coding_and_khmer"

@app.post("/api/engine/run")
async def run_production_engine(request: Request, req: EngineRunRequest):
    is_owner = OwnerAuthority.is_authenticated_owner(request)
    from backend.engine.coordinator import production_engine
    result = await production_engine.execute_task(
        task=req.task,
        context_files=req.context_files,
        is_owner=is_owner
    )
    return result.model_dump()

@app.post("/api/engine/workflows/coding")
async def workflow_coding_endpoint(request: Request, req: WorkflowCodingRequest):
    is_owner = OwnerAuthority.is_authenticated_owner(request)
    from backend.engine.workflows import alpha_workflows
    res = await alpha_workflows.run_coding_workflow(
        problem_description=req.problem_description,
        relative_file=req.relative_file,
        original_code=req.original_code,
        patched_code=req.patched_code,
        test_script=req.test_script,
        is_owner=is_owner
    )
    return res

@app.post("/api/engine/workflows/research")
async def workflow_research_endpoint(req: WorkflowResearchRequest):
    from backend.engine.workflows import alpha_workflows
    res = await alpha_workflows.run_research_workflow(
        library_or_topic=req.library_or_topic,
        version=req.version,
        question=req.question
    )
    return res

@app.post("/api/engine/workflows/model")
async def workflow_model_endpoint(request: Request, req: WorkflowModelRequest):
    is_owner = OwnerAuthority.is_authenticated_owner(request)
    from backend.engine.workflows import alpha_workflows
    res = await alpha_workflows.run_model_workflow(
        task_type=req.task_type,
        is_owner=is_owner
    )
    return res

@app.get("/api/engine/evidence")
async def get_engine_evidence():
    from backend.engine.evidence import evidence_store
    return evidence_store.get_summary()

# --- Feature 1: Live Sandbox Preview ---
@app.get("/api/sandbox/apps")
async def list_sandbox_apps():
    """Lists all runnable web applications and HTML files in the sandbox."""
    apps = []
    if SANDBOX_DIR.exists():
        for p in SANDBOX_DIR.iterdir():
            if p.is_dir():
                if (p / "index.html").exists():
                    apps.append({
                        "name": p.name,
                        "preview_url": f"/sandbox/{p.name}/index.html",
                        "full_url": f"http://127.0.0.1:8000/sandbox/{p.name}/index.html"
                    })
                for sub in p.iterdir():
                    if sub.is_dir() and (sub / "index.html").exists():
                        rel = f"{p.name}/{sub.name}"
                        apps.append({
                            "name": sub.name,
                            "preview_url": f"/sandbox/{rel}/index.html",
                            "full_url": f"http://127.0.0.1:8000/sandbox/{rel}/index.html"
                        })
            elif p.is_file() and p.suffix.lower() in [".html", ".htm"]:
                apps.append({
                    "name": p.name,
                    "preview_url": f"/sandbox/{p.name}",
                    "full_url": f"http://127.0.0.1:8000/sandbox/{p.name}"
                })
    return {"success": True, "apps": apps, "total": len(apps)}

# --- Feature 2: Autonomous Self-Healing Coding Loop ---
class SelfHealRequest(BaseModel):
    code: str
    test_script: Optional[str] = None
    filename: Optional[str] = "script.py"
    max_retries: Optional[int] = 3

@app.post("/api/engine/self-heal")
async def run_self_heal(req: SelfHealRequest):
    """Executes iterative self-healing repair on code with unit test validation."""
    from backend.engine.self_healing import self_healing_engine
    res = await self_healing_engine.auto_heal_code(
        code=req.code,
        test_script=req.test_script,
        filename=req.filename or "script.py",
        max_retries=req.max_retries or 3
    )
    return {"success": True, "data": res}

# --- Feature 3: Local Semantic Vector RAG ---
class RAGSearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 3

@app.get("/api/rag/documents")
async def list_rag_documents():
    """Lists indexed documents in the local knowledge base."""
    from backend.knowledge.rag_engine import local_rag
    docs = local_rag.list_documents()
    return {"success": True, "documents": docs, "total": len(docs)}

@app.post("/api/rag/search")
async def search_rag(req: RAGSearchRequest):
    """Searches local knowledge base using hybrid BM25 + Vector cosine similarity."""
    from backend.knowledge.rag_engine import local_rag
    passages = local_rag.search(query=req.query, top_k=req.top_k or 3)
    context = "\n\n".join(p.get("content", "") for p in passages)
    return {
        "success": True,
        "query": req.query,
        "passages": passages,
        "total": len(passages),
        "data": {"context": context, "passages": passages}
    }

@app.post("/api/rag/index")
async def index_rag():
    """Re-indexes all documents in workspace/documents/."""
    from backend.knowledge.rag_engine import local_rag
    res = local_rag.index_documents()
    return {"success": True, "data": res}

# --- Feature 4: Local Voice & Speech Web Assistant ---
class VoiceConfigRequest(BaseModel):
    enabled: Optional[bool] = None
    stt_enabled: Optional[bool] = None
    tts_enabled: Optional[bool] = None
    auto_speak: Optional[bool] = None
    language: Optional[str] = None
    rate: Optional[float] = None
    pitch: Optional[float] = None
    volume: Optional[float] = None

@app.get("/api/voice/status")
async def get_voice_status():
    """Returns current voice settings and speech synthesis capabilities."""
    from backend.voice import voice_manager
    return {"success": True, "config": voice_manager.settings.model_dump()}

@app.post("/api/voice/config")
async def update_voice_config(req: VoiceConfigRequest):
    """Updates voice assistant configuration."""
    from backend.voice import voice_manager
    updated = voice_manager.update_settings(req.model_dump(exclude_unset=True))
    return {"success": True, "config": updated.model_dump()}

# Mount Sandbox for Live Web App Preview
if SANDBOX_DIR.exists():
    app.mount("/sandbox", StaticFiles(directory=str(SANDBOX_DIR), html=True), name="sandbox_preview")

# Mount Llama Server WebUI exclusively at /
if (LLAMA_FRONTEND_DIR / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(LLAMA_FRONTEND_DIR), html=True), name="llama_webui")

