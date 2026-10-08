import time
import json
import uuid
import httpx
import asyncio
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

from backend.config import system_config, MODELS_DIR
from backend.models_manager import models_manager
from backend.runtime import llm_runtime
from backend.tools import tool_registry
from backend.runtime.token_counter import count_messages_tokens, count_tokens

router = APIRouter(tags=["OpenAI & Llama.cpp Compatibility"])

class OpenAIChatMessage(BaseModel):
    role: str
    content: Any

class OpenAIChatRequest(BaseModel):
    model: Optional[str] = None
    messages: List[OpenAIChatMessage]
    stream: Optional[bool] = True
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.9
    max_tokens: Optional[int] = 4096
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Any] = None

@router.get("/v1/models")
async def get_openai_models():
    scanned = models_manager.scan_models()
    active_has_vision = any(m.get("has_vision") for m in scanned if m.get("is_active"))
    
    # Sort models: active model first, then the rest
    sorted_scanned = sorted(scanned, key=lambda m: 0 if m.get("is_active") else 1)
    
    model_list = []
    for m in sorted_scanned:
        has_vis = bool(m.get("has_vision"))
        is_act = bool(m.get("is_active"))
        stem = Path(m["filename"]).stem
        model_list.append({
            "id": stem,
            "object": "model",
            "created": 1740000000,
            "owned_by": system_config.owner.owner_name,
            "permission": [],
            "root": stem,
            "parent": None,
            "status": {"value": "loaded" if is_act else "unloaded"},
            "architecture": {
                "input_modalities": ["image", "text"] if has_vis else ["text"]
            },
            "modalities": {
                "vision": has_vis,
                "audio": False,
                "video": False
            }
        })
        
    if not model_list:
        active_name = Path(system_config.model.model_path).stem if system_config.model.model_path else system_config.model.model_name
        model_list.append({
            "id": active_name or "local-model",
            "object": "model",
            "created": 1740000000,
            "owned_by": system_config.owner.owner_name,
            "permission": [],
            "root": active_name or "local-model",
            "parent": None,
            "status": {"value": "loaded"},
            "architecture": {
                "input_modalities": ["text"]
            },
            "modalities": {
                "vision": active_has_vision,
                "audio": False,
                "video": False
            }
        })
        
    return {"object": "list", "data": model_list}

class ToolExecuteRequest(BaseModel):
    tool: Optional[str] = "web_search"
    params: Optional[Dict[str, Any]] = {}
    stream: Optional[bool] = False

class StreamLookupRequest(BaseModel):
    conversation_ids: Optional[List[str]] = []

class ModelLoadRequest(BaseModel):
    model: str
    extra_args: Optional[List[str]] = None

@router.get("/props")
async def get_llama_props(model: Optional[str] = None, autoload: Optional[bool] = False):
    scanned_models = models_manager.scan_models()
    target_has_vision = any(m.get("has_vision") for m in scanned_models if m.get("is_active"))
    if model:
        for m in scanned_models:
            if m["filename"] == model or m["path"] == model:
                target_has_vision = bool(m.get("has_vision"))
                break

    # Try fetching real runtime props from local llama-server on port 8080
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            resp = await client.get(f"{system_config.model.llama_server_url}/props")
            if resp.status_code == 200:
                props = resp.json()
                # Ensure alias and path are aligned with system config
                active_stem = Path(system_config.model.model_path).stem if system_config.model.model_path else system_config.model.model_name
                props["model_alias"] = active_stem
                props["model_path"] = system_config.model.model_path
                # Ensure modalities is explicitly populated for frontend recognition
                if "modalities" not in props or not props["modalities"]:
                    props["modalities"] = {
                        "vision": target_has_vision,
                        "audio": False,
                        "video": False
                    }
                elif target_has_vision:
                    props["modalities"]["vision"] = True
                
                props["architecture"] = {
                    "input_modalities": ["image", "text"] if target_has_vision else ["text"]
                }
                return props
    except Exception:
        pass

    scanned = [Path(m["filename"]).stem for m in scanned_models] + [m["filename"] for m in scanned_models]
    active_stem = Path(system_config.model.model_path).stem if system_config.model.model_path else system_config.model.model_name
    if model and (model in scanned or model == active_stem or model == system_config.model.model_name):
        active_model = Path(model).stem
    else:
        active_model = active_stem

    return {
        "default_generation_settings": {
          "n_ctx": system_config.model.context_length,
          "n_predict": 4096,
          "temperature": system_config.model.temperature,
          "top_k": 40,
          "top_p": system_config.model.top_p,
          "min_p": 0.05
        },
        "total_slots": 1,
        "model_alias": active_model,
        "model_path": system_config.model.model_path,
        "modalities": {
            "vision": target_has_vision,
            "audio": False,
            "video": False
        },
        "architecture": {
            "input_modalities": ["image", "text"] if target_has_vision else ["text"]
        }
    }

@router.get("/health")
async def get_llama_health():
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            resp = await client.get(f"{system_config.model.llama_server_url}/health")
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return {"status": "ok", "slots_idle": 1, "slots_processing": 0}

@router.get("/slots")
async def get_llama_slots():
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            resp = await client.get(f"{system_config.model.llama_server_url}/slots")
            if resp.status_code == 200:
                slots = resp.json()
                for s in slots:
                    if "id_task" not in s:
                        s["id_task"] = s.get("id", 0) + 1
                    if "n_ctx" not in s:
                        s["n_ctx"] = system_config.model.context_length
                return slots
    except Exception:
        pass
    return [
        {
            "id": 0,
            "id_task": 1,
            "state": 0,
            "model": system_config.model.model_name,
            "n_ctx": system_config.model.context_length,
            "is_processing": False,
            "next_token": {
                "has_next_token": False,
                "n_remain": system_config.model.context_length,
                "n_decoded": 0
            }
        }
    ]

class TokenizeRequest(BaseModel):
    content: str

class DetokenizeRequest(BaseModel):
    tokens: List[int]

@router.post("/tokenize")
async def tokenize_endpoint(req: TokenizeRequest):
    """Proxy / local tokenization endpoint matching llama.cpp server specification."""
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            resp = await client.post(f"{system_config.model.llama_server_url}/tokenize", json={"content": req.content})
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    from backend.runtime.token_counter import TOKEN_PATTERN
    words = TOKEN_PATTERN.findall(req.content)
    fake_token_ids = [abs(hash(w)) % 32000 for w in words]
    return {"tokens": fake_token_ids}

@router.post("/detokenize")
async def detokenize_endpoint(req: DetokenizeRequest):
    """Proxy / local detokenization endpoint matching llama.cpp server specification."""
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            resp = await client.post(f"{system_config.model.llama_server_url}/detokenize", json={"tokens": req.tokens})
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return {"content": ""}

@router.get("/tools")
async def get_tools():
    defs = tool_registry.get_tools_definitions()
    result = []
    for d in defs:
        name = d["function"]["name"]
        result.append({
            "tool": name,
            "definition": d,
            "uses_cwd": (name == "local_files")
        })
    return result

@router.post("/tools")
async def execute_tool(req: Optional[ToolExecuteRequest] = None):
    if not req or not req.tool:
        return {"content": "Missing tool parameter", "isError": True}

    params = req.params or {}
    try:
        from backend.platform.executor import tool_execution_manager
        from backend.pipeline import tool_pipeline
        # Try platform executor first (supports all 47 tools + owner authorization)
        res = await tool_execution_manager.execute_tool(req.tool, params, is_owner=True)
        if res.success:
            if isinstance(res.data, (dict, list)):
                content_str = json.dumps(res.data, ensure_ascii=False)
            else:
                content_str = str(res.data)
            return {"content": content_str, "isError": False}
        else:
            # Fallback to pipeline execution
            p_res = await tool_pipeline.execute_pipeline(req.tool, params)
            if p_res.success:
                if isinstance(p_res.data, (dict, list)):
                    content_str = json.dumps(p_res.data, ensure_ascii=False)
                else:
                    content_str = str(p_res.data)
                return {"content": content_str, "isError": False}
            return {"content": f"Tool execution notice: {res.error or p_res.error}", "isError": True}
    except Exception as e:
        return {"content": f"Pipeline exception: {str(e)}", "isError": True}

@router.post("/v1/streams/lookup")
async def streams_lookup(req: Optional[StreamLookupRequest] = None):
    return []

@router.post("/v1/chat/completions/control")
async def completions_control(payload: Optional[Dict[str, Any]] = None):
    return {"success": True}

@router.get("/v1/stream")
async def get_stream_reconnect(conv_id: Optional[str] = None):
    async def empty_events():
        yield "data: [DONE]\n\n"
    return StreamingResponse(empty_events(), media_type="text/event-stream")

@router.post("/models/load")
async def load_model(req: ModelLoadRequest):
    try:
        models_manager.select_model(req.model)
    except Exception:
        pass
    return {"success": True, "model": req.model}

@router.post("/models/unload")
async def unload_model(payload: Optional[Dict[str, Any]] = None):
    return {"success": True}

@router.get("/models/sse")
async def models_sse():
    async def event_generator():
        yield ": keep-alive\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.post("/v1/chat/completions")
async def openai_chat_completions(request: Request, body: OpenAIChatRequest):
    chat_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created_ts = int(time.time())
    real_active = Path(system_config.model.model_path).stem if system_config.model.model_path else system_config.model.model_name
    active_model = body.model if (body.model and body.model != "K-Jocker 1.5Flash") else real_active
    if active_model:
        active_model = re.sub(r'\.(gguf|ggml|bin|safetensors)$', '', active_model, flags=re.I)

    clean_messages = []
    for m in body.messages:
        content = m.content
        if isinstance(content, list):
            # Check if multimodal (contains image_url)
            has_image = any(isinstance(p, dict) and p.get("type") == "image_url" for p in content)
            if has_image:
                clean_messages.append({"role": m.role, "content": content})
            else:
                text_parts = [p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"]
                clean_messages.append({"role": m.role, "content": " ".join(text_parts)})
        else:
            clean_messages.append({"role": m.role, "content": str(content)})

    # Determine user text for logging / routing
    last_msg = clean_messages[-1]["content"] if clean_messages else ""
    if isinstance(last_msg, list):
        user_msg = " ".join(p.get("text", "") for p in last_msg if isinstance(p, dict) and p.get("type") == "text")
    else:
        user_msg = str(last_msg)

    # Calculate prompt tokens using token_counter
    prompt_tokens = count_messages_tokens(clean_messages, system_config.system_prompt)
    start_time = time.perf_counter()

    if body.stream:
        async def event_generator():
            first_token_time = None
            predicted_tokens = 0
            raw_timings = None

            def compute_current_timings():
                now = time.perf_counter()
                f_time = first_token_time if first_token_time is not None else now
                p_ms = max(0.1, (f_time - start_time) * 1000)
                gen_ms = max(0.1, (now - f_time) * 1000)
                
                # If native timings was received from llama-server, merge its counters
                if raw_timings and isinstance(raw_timings, dict):
                    p_n = raw_timings.get("prompt_n", prompt_tokens)
                    p_ms_val = raw_timings.get("prompt_ms", p_ms)
                    pred_n = raw_timings.get("predicted_n", predicted_tokens)
                    pred_ms_val = raw_timings.get("predicted_ms", gen_ms)
                    c_n = raw_timings.get("cache_n", 0)
                else:
                    p_n = prompt_tokens
                    p_ms_val = p_ms
                    pred_n = predicted_tokens
                    pred_ms_val = gen_ms
                    c_n = 0

                pred_speed = round(pred_n / max(pred_ms_val / 1000.0, 0.001), 1)
                p_speed = round(p_n / max(p_ms_val / 1000.0, 0.001), 1)

                return {
                    "prompt_n": p_n,
                    "prompt_ms": round(p_ms_val, 2),
                    "prompt_per_token_ms": round(p_ms_val / max(p_n, 1), 2),
                    "prompt_per_second": p_speed,
                    "predicted_n": pred_n,
                    "predicted_ms": round(pred_ms_val, 2),
                    "predicted_per_token_ms": round(pred_ms_val / max(pred_n, 1), 2),
                    "predicted_per_second": pred_speed,
                    "cache_n": c_n
                }

            # Initial role delta chunk
            initial_timings = compute_current_timings()
            first_chunk = {
                "id": chat_id,
                "object": "chat.completion.chunk",
                "created": created_ts,
                "model": active_model,
                "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
                "timings": initial_timings,
                "usage": {
                    "prompt_tokens": initial_timings["prompt_n"],
                    "completion_tokens": initial_timings["predicted_n"],
                    "total_tokens": initial_timings["prompt_n"] + initial_timings["predicted_n"]
                }
            }
            yield f"data: {json.dumps(first_chunk)}\n\n"

            # Stream from local GGUF agent with real-time tool calling and multi-turn feedback
            async for event in llm_runtime.stream_chat(clean_messages, system_prompt=system_config.system_prompt, client_tools=body.tools, request_id=chat_id):
                event_type = event.get("type")
                if event_type == "timings":
                    raw_timings = event.get("timings")
                elif event_type == "reasoning":
                    if first_token_time is None:
                        first_token_time = time.perf_counter()
                    reasoning_content = event.get("content", "")
                    if reasoning_content:
                        t_obj = compute_current_timings()
                        yield f"data: {json.dumps({'id': chat_id, 'object': 'chat.completion.chunk', 'created': created_ts, 'model': active_model, 'choices': [{'index': 0, 'delta': {'reasoning_content': reasoning_content}, 'finish_reason': None}], 'timings': t_obj, 'usage': {'prompt_tokens': t_obj['prompt_n'], 'completion_tokens': t_obj['predicted_n'], 'total_tokens': t_obj['prompt_n'] + t_obj['predicted_n']}})}\n\n"
                elif event_type in ("token", "content"):
                    if first_token_time is None:
                        first_token_time = time.perf_counter()
                    token_content = event.get("content", "")
                    if token_content:
                        from backend.runtime.constraint_guard import constraint_guard
                        token_content = constraint_guard.filter_stream_token(token_content)
                        predicted_tokens += count_tokens(token_content)
                        t_obj = compute_current_timings()
                        yield f"data: {json.dumps({'id': chat_id, 'object': 'chat.completion.chunk', 'created': created_ts, 'model': active_model, 'choices': [{'index': 0, 'delta': {'content': token_content}, 'finish_reason': None}], 'timings': t_obj, 'usage': {'prompt_tokens': t_obj['prompt_n'], 'completion_tokens': t_obj['predicted_n'], 'total_tokens': t_obj['prompt_n'] + t_obj['predicted_n']}})}\n\n"
                elif event_type == "tool_call":
                    t_name = event.get("tool", "")
                    t_args = event.get("args", {})
                    t_obj = compute_current_timings()
                    tc_chunk = {
                        "id": chat_id,
                        "object": "chat.completion.chunk",
                        "created": created_ts,
                        "model": active_model,
                        "choices": [{
                            "index": 0,
                            "delta": {
                                "tool_calls": [{
                                    "index": 0,
                                    "id": f"call_{uuid.uuid4().hex[:8]}",
                                    "type": "function",
                                    "function": {
                                        "name": t_name,
                                        "arguments": json.dumps(t_args, ensure_ascii=False)
                                    }
                                }]
                            },
                            "finish_reason": None
                        }],
                        "timings": t_obj,
                        "usage": {
                            "prompt_tokens": t_obj["prompt_n"],
                            "completion_tokens": t_obj["predicted_n"],
                            "total_tokens": t_obj["prompt_n"] + t_obj["predicted_n"]
                        }
                    }
                    yield f"data: {json.dumps(tc_chunk)}\n\n"

            # Final DONE chunk with full telemetry
            final_timings = compute_current_timings()
            stop_chunk = {
                "id": chat_id,
                "object": "chat.completion.chunk",
                "created": created_ts,
                "model": active_model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                "timings": final_timings,
                "usage": {
                    "prompt_tokens": final_timings["prompt_n"],
                    "completion_tokens": final_timings["predicted_n"],
                    "total_tokens": final_timings["prompt_n"] + final_timings["predicted_n"]
                }
            }
            yield f"data: {json.dumps(stop_chunk)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    else:
        # Non-streaming mode: accumulate full completion response
        first_token_time = None
        predicted_tokens = 0
        raw_timings = None
        full_tokens = []
        full_reasoning = []
        async for event in llm_runtime.stream_chat(
            clean_messages,
            system_prompt=system_config.system_prompt,
            client_tools=body.tools,
            request_id=chat_id
        ):
            event_type = event.get("type")
            if event_type == "timings":
                raw_timings = event.get("timings")
            elif event_type in ("token", "content"):
                if first_token_time is None:
                    first_token_time = time.perf_counter()
                c_txt = event.get("content", "")
                full_tokens.append(c_txt)
                predicted_tokens += count_tokens(c_txt)
            elif event_type == "reasoning":
                if first_token_time is None:
                    first_token_time = time.perf_counter()
                full_reasoning.append(event.get("content", ""))

        final_content = "".join(full_tokens)
        raw_user_msg = clean_messages[-1]["content"] if clean_messages else ""
        if isinstance(raw_user_msg, list):
            raw_user_msg = " ".join(p.get("text", "") for p in raw_user_msg if isinstance(p, dict) and p.get("type") == "text")
        from backend.runtime.constraint_guard import constraint_guard
        final_content = constraint_guard.sanitize_response(str(raw_user_msg), final_content)
        final_reasoning = "".join(full_reasoning)
        now = time.perf_counter()
        f_time = first_token_time if first_token_time is not None else now
        p_ms = max(0.1, (f_time - start_time) * 1000)
        gen_ms = max(0.1, (now - f_time) * 1000)
        p_n = raw_timings.get("prompt_n", prompt_tokens) if raw_timings else prompt_tokens
        pred_n = raw_timings.get("predicted_n", predicted_tokens) if raw_timings else predicted_tokens
        pred_speed = round(pred_n / max(gen_ms / 1000.0, 0.001), 1)

        timings_obj = {
            "prompt_n": p_n,
            "prompt_ms": round(p_ms, 2),
            "prompt_per_second": round(p_n / max(p_ms / 1000.0, 0.001), 1),
            "predicted_n": pred_n,
            "predicted_ms": round(gen_ms, 2),
            "predicted_per_second": pred_speed,
            "cache_n": raw_timings.get("cache_n", 0) if raw_timings else 0
        }

        msg_dict: Dict[str, Any] = {
            "role": "assistant",
            "content": final_content
        }
        if final_reasoning:
            msg_dict["reasoning_content"] = final_reasoning

        return JSONResponse({
            "id": chat_id,
            "object": "chat.completion",
            "created": created_ts,
            "model": active_model,
            "choices": [{
                "index": 0,
                "message": msg_dict,
                "finish_reason": "stop"
            }],
            "timings": timings_obj,
            "usage": {
                "prompt_tokens": p_n,
                "completion_tokens": pred_n,
                "total_tokens": p_n + pred_n
            }
        })
