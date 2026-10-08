import time
import json
import uuid
import re
import asyncio
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, List, Optional, Tuple, Set
from backend.config import system_config, MODELS_DIR
from backend.telemetry import TelemetryTracker
from backend.tools import tool_registry
from backend.pipeline.router import intent_router
from backend.runtime.model_adapter import model_adapter
from backend.runtime.events import runtime_logger

MAX_TOOL_ITERATIONS = 8

def get_tools_system_prompt(allowed_tools: Optional[Set[str]] = None, task_description: str = "") -> str:
    """Returns dynamic schema description for model-level tool calling empowered across 45+ tools"""
    from backend.platform.discovery import tool_discovery

    selected_tools = []
    if allowed_tools:
        for t_name in allowed_tools:
            t = tool_registry.get_tool(t_name)
            if t and t not in selected_tools:
                selected_tools.append(t)

    # Dynamic capability discovery from 45+ tools based on task query (both Khmer and English)
    if task_description and len(selected_tools) < 6:
        discovered = tool_discovery.discover_tools(task_description, max_tools=6)
        for d in discovered:
            if d not in selected_tools and len(selected_tools) < 8:
                selected_tools.append(d)

    # If still empty (e.g. greeting or general query), provide core safe tools so AI is never shackled
    if not selected_tools:
        for fallback_id in ["calculator", "web_search", "local_files", "codebase_search"]:
            t = tool_registry.get_tool(fallback_id)
            if t and t not in selected_tools:
                selected_tools.append(t)

    tools_desc = []
    for t in selected_tools:
        name = t.name
        desc = t.description
        schema = t.get_input_schema()
        params = schema.get("properties", {})
        req = schema.get("required", [])
        # Ultra-compact micro-schema to save tokens for small models
        params_str = ", ".join([f"{k}" + ("*" if k in req else "") for k in params.keys()])
        tools_desc.append(f"- {name}({params_str}): {desc}")

    return (
        "### Available K-Jocker Engineering & Research Tools:\n"
        "You are K-Jocker, an advanced local AI engineering and deep research assistant operating exclusively for Owner Kimsokun. "
        "You have full authority and freedom to invoke any of the following active tools whenever you need to search the web, inspect code, read/edit files, execute Python code, inspect hardware/models, or perform calculations:\n"
        + "\n".join(tools_desc) + "\n\n"
        "To invoke a tool, output a tool call block:\n"
        "<tool_call>{\"name\": \"<tool_name>\", \"arguments\": {<parameters>}}</tool_call>\n"
        "When you invoke a tool, the runtime executes it safely and returns the observation to you in the next turn so you can formulate the final answer for Owner Kimsokun.\n"
        "OPERATING GUIDELINES FOR ACCURATE, CLEAR & FAST REASONING:\n"
        "1. THINK CLEAR & ANSWER DIRECTLY: Provide immediate, high-value, factually accurate answers without generic filler.\n"
        "2. TOKEN EFFICIENCY: When invoking tools, pass only essential arguments to keep data small and response fast.\n"
        "3. HIGH-SPEED TOOLS FOR EXACT FACTS: Use 'fast_calc' for exact numbers/math, 'memory.*' for stored variables, and 'project.scaffold' for generating full apps without typing out boilerplate.\n"
        "4. ANTIGRAVITY WORKSPACE CAPABILITIES: You have full Antigravity-grade workspace access in the sandbox. You can create complex folder structures, nested subdirectories, and multiple files across any file extension (.html, .css, .js, .ts, .tsx, .py, .json, .yaml, .sql, .md, .env, etc.). Use 'fs.batch_create' or 'project.scaffold' to scaffold entire project architectures in one step.\n"
        "5. For multi-part examinations, questionnaires, and test evaluations, provide complete, step-by-step written calculations, explanations, and Python code blocks directly in your response.\n"
        "6. Always ground answers on verifiable logic and facts. Never hallucinate false evaluations.\n"
        "7. EMOTIONAL EXPRESSIVENESS & ADAPTIVE EMOJIS: Actively adapt your tone and emojis to match conversational feelings and context (e.g. celebratory 🎉 🚀 ✨ for wins/success, analytical 💻 ⚙️ 🧠 for engineering/code, loyal 🫡 🤝 🌟 for greetings/owner interaction, vigilant ⚠️ 🔍 for warnings, insightful 💡 📖 for explanations). Naturally integrate fitting emojis throughout your response to express warmth, enthusiasm, and devotion.\n"
        "8. MANDATORY SELF-VERIFICATION & ANTI-OVERCONFIDENCE: Never blindly assert 'All answers are 100% correct' or claim perfection without verified proof. Actively inspect your reasoning, calculations, and code for errors, edge cases, and arithmetic slips. If an error is found, immediately state the exact mistake and provide the corrected answer with epistemic humility."
    )

def format_display_result(tool_name: str, data: Any) -> str:
    """Formats raw tool output into clean, user-friendly Markdown."""
    if tool_name == "calculator":
        return f"**Calculation Result:** `{data}`"

    if tool_name == "web_search" and isinstance(data, list):
        if not data:
            return "No web search results found for this query."
        lines = ["### Live Search Results\n"]
        for idx, item in enumerate(data, 1):
            title = item.get("title", "Source")
            link = item.get("link", "")
            snippet = item.get("snippet", "")
            if link:
                lines.append(f"{idx}. **[{title}]({link})**\n   {snippet}\n")
            else:
                lines.append(f"{idx}. **{title}**\n   {snippet}\n")
        return "\n".join(lines)

    if tool_name == "web_fetch":
        if isinstance(data, dict):
            url = data.get("url", "")
            content = data.get("content", "")
            return f"### Web Page Content ({url})\n\n{content[:2000]}"
        return str(data)

    if tool_name == "local_files":
        if isinstance(data, list):
            items_str = "\n".join(f"- {item}" for item in data)
            return f"**Files in Sandbox:**\n\n{items_str}"
        return f"```\n{data}\n```"

    if tool_name == "codebase_search" and isinstance(data, list):
        if not data:
            return "No occurrences found in codebase."
        lines = ["### Codebase Search Matches\n"]
        for item in data[:10]:
            lines.append(f"- **`{item.get('file')}:{item.get('line')}`**: `{item.get('snippet')}`")
        return "\n".join(lines)

    if tool_name == "codebase_read" and isinstance(data, dict):
        return f"### File: `{data.get('file')}` (Lines {data.get('start_line')}-{data.get('end_line')} of {data.get('total_lines')})\n\n```python\n{data.get('content')}\n```"

    if tool_name == "codebase_structure" and isinstance(data, dict):
        lines = ["### Project Architecture Structure\n"]
        for folder, files in data.items():
            lines.append(f"- **`{folder}/`**: {', '.join(files[:8])}")
        return "\n".join(lines)

    if tool_name == "github_search" and isinstance(data, list):
        if not data:
            return "No GitHub repositories found."
        lines = ["### GitHub Repositories & References\n"]
        for item in data[:5]:
            url = item.get("url", "")
            title = item.get("full_name") or item.get("title", "GitHub Repo")
            stars = f" ⭐ {item.get('stars')}" if "stars" in item else ""
            desc = item.get("description") or item.get("snippet", "")
            lines.append(f"- **[{title}]({url})**{stars}\n  {desc}\n")
        return "\n".join(lines)

    if tool_name == "github_source_read" and isinstance(data, dict):
        return f"### GitHub Source (`{data.get('url')}`)\n\n```text\n{data.get('content')}\n```"

    if tool_name == "hardware_capability_detect" and isinstance(data, dict):
        return (
            "### 🖥️ Local Machine Hardware & Model Fit\n\n"
            f"- **CPU**: {data.get('cpu_physical_cores')} Physical Cores / {data.get('cpu_logical_cores')} Logical Cores\n"
            f"- **RAM**: {data.get('total_ram_gb')} GB Total | **{data.get('available_ram_gb')} GB Available** (Usage: {data.get('ram_usage_percent')}%)\n"
            f"- **Recommended GGUF Model**: `{data.get('recommended_model_tier')}`\n"
            f"- **Safe Context Limit**: `{data.get('safe_context_limit')}` tokens"
        )

    if tool_name == "gguf_metadata_inspect" and isinstance(data, dict):
        return (
            f"### 📦 GGUF Model Header (`{data.get('filename')}`)\n\n"
            f"- **Valid GGUF**: `{'YES' if data.get('is_valid_gguf') else 'NO'}` (Version {data.get('gguf_version')})\n"
            f"- **Tensor Count**: {data.get('tensor_count')}\n"
            f"- **Metadata Keys**: {data.get('metadata_kv_count')}\n"
            f"- **File Size**: {data.get('size_mb')} MB ({data.get('size_gb')} GB)"
        )

    if tool_name == "huggingface_search" and isinstance(data, list):
        if not data:
            return "No models found on Hugging Face."
        lines = ["### 🤗 Hugging Face Model Repositories\n"]
        for item in data[:5]:
            m_id = item.get("model_id", "")
            url = item.get("url", f"https://huggingface.co/{m_id}")
            dl = item.get("downloads", 0)
            likes = item.get("likes", 0)
            lines.append(f"- **[{m_id}]({url})** (📥 {dl:,} downloads | ❤️ {likes} likes)")
        return "\n".join(lines)

    if tool_name == "python_execute" and isinstance(data, dict):
        out = data.get("stdout", "")
        err = data.get("stderr", "")
        code = data.get("exit_code", 0)
        time_ms = data.get("execution_time_ms", 0)
        res = f"### 🐍 Python Execution (Exit code: `{code}` | Time: `{time_ms}ms`)\n\n"
        if out:
            res += f"**Output (stdout):**\n```\n{out}\n```\n"
        if err:
            res += f"**Errors / Warnings (stderr):**\n```\n{err}\n```\n"
        return res

    if tool_name == "package_registry" and isinstance(data, dict):
        doc_url = data.get("docs_url") or data.get("home_page") or data.get("homepage") or ""
        doc_link = f"[{doc_url}]({doc_url})" if doc_url else "N/A"
        recent = ", ".join(data.get("recent_versions", []))
        return (
            f"### 📦 Package: `{data.get('name')}` (`{data.get('ecosystem')}`)\n\n"
            f"- **Latest Version:** `{data.get('latest_version')}`\n"
            f"- **License:** `{data.get('license')}`\n"
            f"- **Summary:** {data.get('summary') or data.get('description')}\n"
            f"- **Documentation:** {doc_link}\n"
            + (f"- **Recent Releases:** {recent}\n" if recent else "")
        )
    if tool_name in ("fs.list", "fs_list") and isinstance(data, dict):
        entries = data.get("items") or data.get("entries", [])
        return f"**Directory Listing (`{data.get('path', '.')}`)**:\n" + "\n".join(f"- `{e.get('name')}` ({'dir' if e.get('is_dir') else 'file'})" for e in entries[:25])

    if tool_name in ("fs.batch_create", "fs_batch_create") and isinstance(data, dict):
        count = data.get("created_count", 0)
        exts = ", ".join(f"{k}: {v}" for k, v in data.get("extensions_summary", {}).items())
        files = data.get("files", [])
        lines = [f"### 📂 Batch File Creation ({count} Files Created | {exts})\n"]
        for f in files[:15]:
            lines.append(f"- **`{f.get('path')}`** ({f.get('language')}, {f.get('size_bytes')} bytes)")
        if len(files) > 15:
            lines.append(f"- *...and {len(files) - 15} more files*")
        return "\n".join(lines)

    if tool_name in ("fs.tree", "fs_tree") and isinstance(data, dict):
        tree_text = data.get("tree", "")
        count = data.get("total_files", 0)
        exts = ", ".join(f"{k}: {v}" for k, v in data.get("extension_breakdown", {}).items())
        return f"### 🌲 Sandbox Workspace Tree ({count} Files | {exts})\n```text\n{tree_text}\n```"

    if tool_name in ("fs.create", "fs_create") and isinstance(data, dict):
        return f"**File Created**: `{data.get('relative_path') or data.get('created_file')}` ({data.get('language') or 'File'}, {data.get('size_bytes')} bytes)"

    if tool_name in ("fs.mkdir", "fs_mkdir") and isinstance(data, dict):
        return f"**Directory Created**: `{data.get('relative_path') or data.get('created_dir')}`"

    if tool_name in ("fs.delete", "fs_delete") and isinstance(data, dict):
        return f"**Path Deleted**: `{data.get('deleted_path')}`"

    if tool_name in ("fs.read", "fs_read") and isinstance(data, dict):
        return f"**File Content (`{data.get('file_path') or data.get('path')}`)**:\n```\n{str(data.get('content', ''))[:3000]}\n```"

    if tool_name in ("git.status", "git_status") and isinstance(data, dict):
        return f"**Git Status** (Branch: `{data.get('branch', 'unknown')}`):\n- Modified: `{data.get('modified', [])}`\n- Untracked: `{data.get('untracked', [])}`"

    if tool_name in ("git.diff", "git_diff") and isinstance(data, dict):
        return f"**Git Diff**:\n```diff\n{str(data.get('diff', ''))[:3000]}\n```"

    if tool_name in ("terminal.detect", "terminal_detect") and isinstance(data, dict):
        return f"**Terminal Environment**:\n- OS: `{data.get('os')}`\n- Shells: `{data.get('available_shells')}`\n- Default: `{data.get('default_shell')}`"

    if tool_name in ("doc.analyze", "doc_analyze") and isinstance(data, dict):
        title = data.get("title", "Document Analysis")
        role = data.get("role_mission", "N/A")
        tokens = data.get("approx_tokens", 0)
        time_ms = data.get("analysis_time_ms", 0)
        headers = ", ".join(data.get("key_headers", [])[:5])
        tasks = "\n".join(f"- {t}" for t in data.get("action_tasks", [])[:6])
        rules = "\n".join(f"- {r}" for r in data.get("key_rules", [])[:5])
        res = (
            f"### 📑 Fast Document Analysis: {title} ({tokens:,} tokens | {time_ms}ms)\n\n"
            f"- **Core Role / Mission:** {role}\n"
            f"- **Structure:** {headers}\n"
        )
        if tasks:
            res += f"\n**Action Tasks Identified:**\n{tasks}\n"
        if rules:
            res += f"\n**Key Rules & Constraints:**\n{rules}\n"
        return res

    if tool_name in ("khmer_language_detect", "khmer_terminology_lookup"):
        return f"**Khmer Intelligence Result**:\n```json\n{json.dumps(data, ensure_ascii=False, indent=2)}\n```"

    if tool_name in ("fast_calc", "calculator") and isinstance(data, dict):
        res_val = data.get("formatted") or data.get("result") or str(data)
        return f"**Calculation Verified:** `{res_val}`"

    if tool_name == "unit_convert" and isinstance(data, dict):
        return f"**Conversion Verified:** `{data.get('from', '')}` ➔ `{data.get('to', data.get('result'))}`"

    if tool_name == "text_compact" and isinstance(data, dict):
        return f"**Compacted Text:**\n```\n{data.get('compacted_text', '')[:400]}\n```\n*(Token savings: {data.get('savings_percent', 0)}%)*"

    if tool_name == "regex_extract" and isinstance(data, dict):
        return f"**Pattern Matches ({data.get('count', 0)}):** `{data.get('matches', [])}`"

    if tool_name in ("memory.get", "memory_get", "memory.set", "memory_set") and isinstance(data, dict):
        status = "saved" if data.get("stored") else f"value: {data.get('value')}"
        return f"**Fast Memory:** Key `{data.get('key')}` ({status})"

    if tool_name in ("project.scaffold", "project_scaffold") and isinstance(data, dict):
        return f"**Scaffold Result:** {data.get('summary', '')}\n**Files Created:** {', '.join(data.get('files', []))}"

    if tool_name in ("code.syntax_lint", "code_syntax_lint") and isinstance(data, dict):
        status = "✅ Valid" if data.get("valid") else f"❌ Syntax Error: {data.get('error')} (line {data.get('line')})"
        return f"**Code Syntax Check ({data.get('language')}):** {status}"

    if tool_name in ("khmer.fast_helper", "khmer_fast_helper") and isinstance(data, dict):
        return f"**Khmer Fast Result:** `{data.get('result') or data.get('khmer') or data.get('matches')}`"

    if tool_name in ("sandbox.preview", "sandbox_preview") and isinstance(data, dict):
        return f"**Live Preview Available:** [{data.get('file_path')}]({data.get('preview_url')})\nClick to test: {data.get('markdown_link')}"

    if tool_name in ("code.self_heal", "code_self_heal") and isinstance(data, dict):
        diff_prev = data.get('diff', '')[:300]
        return f"**Autonomous Self-Healing Result:** Status: `{data.get('status')}` (Attempts: {data.get('attempts')})\n```diff\n{diff_prev}\n```"

    if tool_name in ("rag.search", "rag_search") and isinstance(data, dict):
        passages = data.get('passages', [])
        lines = [f"**Document Knowledge Base ({data.get('total_found', 0)} matches found):**"]
        for p in passages:
            lines.append(f"- **[{p.get('document')} #{p.get('chunk_index')} (Score: {p.get('score')}):** {p.get('content', '')[:140]}...")
        return "\n".join(lines)

    if tool_name in ("rag.index", "rag_index") and isinstance(data, dict):
        return f"**RAG Knowledge Base Indexed:** {data.get('files_indexed')} files ({data.get('total_chunks')} passages in {data.get('time_ms')}ms)"

    if tool_name in ("rag.list_docs", "rag_list_docs") and isinstance(data, dict):
        docs = data.get('documents', [])
        return f"**Indexed Documents ({len(docs)}):**\n" + "\n".join(f"- `{d.get('name')}` ({d.get('chunks')} passages)" for d in docs)

    if isinstance(data, (dict, list)):
        return f"```json\n{json.dumps(data, ensure_ascii=False, indent=2)}\n```"

    return str(data)

def compact_observation(tool_name: str, data: Any, max_chars: int = 1500) -> str:
    """Distills raw tool observations into dense, token-efficient text for small models."""
    if isinstance(data, dict):
        if "formatted" in data:
            return f"Verified Result: {data['formatted']}"
        elif "result" in data:
            return f"Verified Result: {data['result']}"
        elif "summary" in data:
            return f"Verified Summary: {data['summary']}"
        elif "compacted_text" in data:
            return str(data["compacted_text"])

    raw_str = json.dumps(data, ensure_ascii=False) if isinstance(data, (dict, list)) else str(data)
    if len(raw_str) > max_chars:
        return raw_str[:max_chars] + f"\n... [Distilled: Remaining {len(raw_str) - max_chars} characters trimmed to keep context small]"
    return raw_str

class LLMRuntime:
    """
    Model-Agnostic Agent Runtime:
    Runtime is the absolute authority; LLM output is merely a request.
    Enforces Intent routing, Permission gates, Schema validation, Loop limits, Timeouts,
    and Runtime evidence logging with request-level isolation.
    """
    def __init__(self):
        self.server_url = system_config.model.llama_server_url
        self.adapter = model_adapter
        self.logger = runtime_logger
        self._pipeline = None

    @property
    def pipeline(self):
        if self._pipeline is None:
            from backend.pipeline.tool_pipeline import tool_pipeline
            self._pipeline = tool_pipeline
        return self._pipeline

    async def check_connection(self) -> bool:
        caps = await self.adapter.detect_capabilities()
        return caps.server_online

    def has_local_gguf_models(self) -> bool:
        if not MODELS_DIR.exists():
            return False
        for p in MODELS_DIR.glob("*.gguf"):
            if p.stat().st_size > 5 * 1024 * 1024:
                return True
        return False

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = "",
        client_tools: Optional[List[Dict[str, Any]]] = None,
        request_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        start_time = time.time()
        token_count = 0
        req_id = request_id or f"req_{uuid.uuid4().hex[:12]}"
        raw_user_msg = messages[-1]["content"] if messages else ""
        if isinstance(raw_user_msg, list):
            user_msg = " ".join(p.get("text", "") for p in raw_user_msg if isinstance(p, dict) and p.get("type") == "text")
        else:
            user_msg = str(raw_user_msg)

        # Step 1: Intent Analysis & Dynamic Capability Discovery
        intent, allowed_tools = intent_router.classify_intent(user_msg)

        # AI Free & Fresh Control: Dynamically discover relevant tools from 45+ platform tools
        from backend.platform.discovery import tool_discovery
        discovered = tool_discovery.discover_tools(user_msg, max_tools=6)
        discovered_names = {t.name for t in discovered}
        for d in list(discovered_names):
            discovered_names.add(d.replace(".", "_"))
            discovered_names.add(d.replace("_", "."))

        if not allowed_tools or intent == "general":
            effective_allowed_tools = discovered_names
        else:
            effective_allowed_tools = allowed_tools.union(discovered_names)

        # Step 2: Proactive Pipeline Execution (Runtime is the Authority)
        detected_tool, tool_res, context_injection = await self.pipeline.process_user_query(
            user_msg=user_msg,
            request_id=req_id
        )

        if detected_tool and tool_res:
            yield {"type": "reasoning", "content": f"[TOOL: {detected_tool}] Pipeline Intent: {intent} -> Route: {detected_tool}\n"}
            if tool_res.success:
                yield {"type": "reasoning", "content": f"[OK] Validated & Authorized under Sandbox Policy ({tool_res.execution_time_ms:.1f}ms)\nObservation injected into Model context.\n\n"}
            else:
                yield {"type": "reasoning", "content": f"[NOTICE] Gate Notice: {tool_res.error}\nProceeding with local knowledge.\n\n"}

        # Step 3: Construct model synthesis prompt
        full_system_prompt = system_prompt or system_config.system_prompt
        tools_instruction = get_tools_system_prompt(effective_allowed_tools, task_description=user_msg)
        combined_system = f"{full_system_prompt}\n\n{tools_instruction}"

        # Dynamic emotional guidance based on user message and conversational context
        from backend.runtime.emotional_engine import emotional_engine
        emotional_cue = emotional_engine.get_emotional_prompt(user_msg)
        combined_system += f"\n\n{emotional_cue}"

        # Dynamic self-verification & anti-overconfidence protocol
        from backend.runtime.self_verification import self_verification_engine
        verification_cue = self_verification_engine.get_verification_prompt(user_msg)
        combined_system += f"\n\n{verification_cue}"

        # Strict instruction constraint & format guard
        from backend.runtime.constraint_guard import constraint_guard
        constraint_cue = constraint_guard.get_constraint_prompt(user_msg)
        combined_system += f"\n\n{constraint_cue}"

        if context_injection:
            combined_system += f"\n\n[Active Tool Observation]:\n{context_injection}"

        # Step 4: Ensure Server Liveness
        is_server_up = await self.check_connection()
        has_local = self.has_local_gguf_models()
        if has_local and not is_server_up:
            from backend.models_manager import models_manager
            models_manager.start_llama_server()
            for _ in range(8):
                await asyncio.sleep(1)
                if await self.check_connection():
                    is_server_up = True
                    break

        if is_server_up:
            # Step 5: Multi-Turn Autonomous Agentic Loop
            current_messages = list(messages)
            tool_iterations = 0
            MAX_TOOL_ITERATIONS = 12

            while tool_iterations < MAX_TOOL_ITERATIONS:
                tool_call_detected = False
                in_think = False
                tool_call_buffer = ""
                in_tool_call = False
                turn_text_buffer = ""

                async for chunk in self.adapter.stream_chat(
                    messages=current_messages,
                    system_prompt=combined_system,
                    temperature=system_config.model.temperature,
                    top_p=system_config.model.top_p,
                    max_tokens=4096
                ):
                    chunk_type = chunk.get("type")
                    if chunk_type == "error":
                        yield {"type": "token", "content": f"\n[Model Error: {chunk.get('content')}]\n"}
                        elapsed = max(0.001, time.time() - start_time)
                        yield {"type": "done", "tokens": token_count, "time": elapsed, "request_id": req_id}
                        return
                    elif chunk_type == "reasoning":
                        yield chunk
                        continue
                    elif chunk_type == "timings":
                        yield chunk
                        continue

                    content = chunk.get("content", "")
                    if not content:
                        continue

                    token_count += 1
                    remaining = content

                    while remaining:
                        if not in_think:
                            # Normalize function tags (<function=tool>{...}</function>) into <tool_call>
                            if "<function=" in remaining:
                                func_match = re.search(r'<function=([a-zA-Z0-9_\.\-]+)>\s*(\{[\s\S]*?\})\s*</function>', remaining)
                                if func_match:
                                    remaining = re.sub(
                                        r'<function=([a-zA-Z0-9_\.\-]+)>\s*(\{[\s\S]*?\})\s*</function>',
                                        r'<tool_call>{"name": "\1", "arguments": \2}</tool_call>',
                                        remaining
                                    )

                            # Intercept raw or markdown-fenced JSON tool calls emitted without <tool_call> tags
                            trimmed = remaining.strip()
                            if trimmed.startswith("```json") and trimmed.endswith("```"):
                                trimmed = trimmed[7:-3].strip()
                            elif trimmed.startswith("```") and trimmed.endswith("```"):
                                trimmed = trimmed[3:-3].strip()

                            if trimmed.startswith('{"name":') and '"arguments":' in trimmed and trimmed.endswith('}'):
                                try:
                                    raw_tc = json.loads(trimmed)
                                    if "name" in raw_tc and "arguments" in raw_tc:
                                        t_name = raw_tc.get("name", "")
                                        t_args = raw_tc.get("arguments", {})
                                        name_alt = t_name.replace(".", "_") if "." in t_name else t_name.replace("_", ".")
                                        if t_name not in effective_allowed_tools and name_alt not in effective_allowed_tools:
                                            rej_err = f"TOOL_REJECTED: Tool '{t_name}' is unauthorized for active intent '{intent}'."
                                            self.logger.log_event(
                                                request_id=req_id,
                                                event_type="tool_rejected",
                                                intent=intent,
                                                tool_name=t_name,
                                                arguments=t_args,
                                                authorized=False,
                                                executed=False,
                                                success=False,
                                                error=rej_err
                                            )
                                            yield {"type": "reasoning", "content": f"\n[REJECTED] Runtime Gate Rejection: {rej_err}\n\n"}
                                        else:
                                            tool_call_detected = True
                                            yield {"type": "tool_call", "tool": t_name, "args": t_args}
                                            yield {"type": "token", "content": f"\n\n> ⚙️ **Executing Tool:** `{t_name}`\n"}
                                            t_res = await self.pipeline.execute_pipeline(
                                                tool_name=t_name,
                                                params=t_args,
                                                allowed_tools=effective_allowed_tools,
                                                request_id=req_id,
                                                intent=intent,
                                                timeout=15.0
                                            )
                                            if t_res.success:
                                                disp = format_display_result(t_name, t_res.data)
                                                yield {"type": "token", "content": f"> ✅ **Tool Verified Result:**\n{disp}\n\n"}
                                                obs_text = compact_observation(t_name, t_res.data)
                                            else:
                                                yield {"type": "token", "content": f"> ⚠️ **Tool Notice:** {t_res.error}\n\n"}
                                                yield {"type": "reasoning", "content": f"[REJECTED] Runtime Gate Rejection: {t_res.error}\n\n"}
                                                obs_text = f"Error: {t_res.error}"

                                            current_messages.append({"role": "assistant", "content": f'<tool_call>{{"name": "{t_name}", "arguments": {json.dumps(t_args)}}}</tool_call>'})
                                            current_messages.append({"role": "user", "content": f"[Tool Observation for '{t_name}']:\n{obs_text}\n\nSynthesize the verified result above and provide a complete, helpful explanation for Owner Kimsokun."})
                                            remaining = ""
                                            break
                                except Exception:
                                    pass

                            if "<think>" in remaining:
                                pre, post = remaining.split("<think>", 1)
                                if pre:
                                    yield {"type": "token", "content": pre}
                                in_think = True
                                remaining = post
                            elif "<tool_call>" in remaining:
                                pre, post = remaining.split("<tool_call>", 1)
                                if pre:
                                    turn_text_buffer += pre
                                    yield {"type": "token", "content": pre}
                                in_tool_call = True
                                tool_call_buffer = ""
                                remaining = post
                            elif in_tool_call:
                                if "</tool_call>" in remaining:
                                    call_chunk, post = remaining.split("</tool_call>", 1)
                                    tool_call_buffer += call_chunk
                                    in_tool_call = False

                                    tool_iterations += 1
                                    if tool_iterations > MAX_TOOL_ITERATIONS:
                                        loop_err = f"TOOL_LOOP_LIMIT: Maximum allowed tool iterations ({MAX_TOOL_ITERATIONS}) exceeded."
                                        self.logger.log_event(
                                            request_id=req_id,
                                            event_type="tool_loop_limit",
                                            intent=intent,
                                            tool_name="loop_limit",
                                            arguments={},
                                            authorized=False,
                                            executed=False,
                                            success=False,
                                            error=loop_err
                                        )
                                        yield {"type": "reasoning", "content": f"\n[NOTICE] {loop_err}\n\n"}
                                        remaining = post.lstrip("\n")
                                        continue

                                    try:
                                        tc_data = json.loads(tool_call_buffer.strip())
                                        t_name = tc_data.get("name", "")
                                        t_args = tc_data.get("arguments", {})
                                        name_alt = t_name.replace(".", "_") if "." in t_name else t_name.replace("_", ".")

                                        yield {"type": "tool_call", "tool": t_name, "args": t_args}
                                        yield {"type": "token", "content": f"\n\n> ⚙️ **Executing Tool:** `{t_name}`\n"}
                                        yield {"type": "reasoning", "content": f"\n[CALL] Model Tool Call Requested: {t_name}({json.dumps(t_args)})\n"}

                                        t_res = await self.pipeline.execute_pipeline(
                                            tool_name=t_name,
                                            params=t_args,
                                            allowed_tools=effective_allowed_tools,
                                            request_id=req_id,
                                            intent=intent,
                                            timeout=15.0
                                        )

                                        if t_res.success:
                                            disp = format_display_result(t_name, t_res.data)
                                            yield {"type": "token", "content": f"> ✅ **Tool Verified Result:**\n{disp}\n\n"}
                                            obs_text = compact_observation(t_name, t_res.data)
                                        else:
                                            yield {"type": "token", "content": f"> ⚠️ **Tool Notice:** {t_res.error}\n\n"}
                                            yield {"type": "reasoning", "content": f"[REJECTED] Runtime Gate Rejection: {t_res.error}\n\n"}
                                            obs_text = f"Error: {t_res.error}"

                                        tool_call_detected = True
                                        turn_text_buffer += f'<tool_call>{{"name": "{t_name}", "arguments": {json.dumps(t_args)}}}</tool_call>'
                                        current_messages.append({"role": "assistant", "content": turn_text_buffer})
                                        current_messages.append({"role": "user", "content": f"[Tool Observation for '{t_name}']:\n{obs_text}\n\nContinue providing your complete answer for Owner Kimsokun."})

                                    except json.JSONDecodeError as jde:
                                        val_err = f"INVALID_TOOL_ARGUMENTS: Malformed tool call JSON ({str(jde)})"
                                        self.logger.log_event(
                                            request_id=req_id,
                                            event_type="validation_error",
                                            intent=intent,
                                            tool_name="unknown",
                                            arguments={},
                                            authorized=False,
                                            executed=False,
                                            success=False,
                                            error=val_err
                                        )
                                        yield {"type": "reasoning", "content": f"[ERROR] {val_err}\n\n"}
                                    except Exception as tc_err:
                                        yield {"type": "reasoning", "content": f"[ERROR] Tool Handling Error: {str(tc_err)}\n\n"}

                                    remaining = post.lstrip("\n")
                                    if tool_call_detected:
                                        break
                                else:
                                    tool_call_buffer += remaining
                                    remaining = ""
                            else:
                                turn_text_buffer += remaining
                                yield {"type": "token", "content": remaining}
                                remaining = ""
                        else:
                            if "</think>" in remaining:
                                pre, post = remaining.split("</think>", 1)
                                if pre:
                                    yield {"type": "reasoning", "content": pre}
                                in_think = False
                                remaining = post.lstrip("\n")
                            else:
                                yield {"type": "reasoning", "content": remaining}
                                remaining = ""

                    if tool_call_detected:
                        break

                tool_iterations += 1
                if not tool_call_detected:
                    break

            elapsed = max(0.001, time.time() - start_time)
            TelemetryTracker.update_generation_metrics(token_count, elapsed, len(str(messages)))
            yield {"type": "done", "tokens": token_count, "time": elapsed, "request_id": req_id}
            return

        # If local server is offline, output clean formatted tool result directly if a tool was executed
        if detected_tool and tool_res and tool_res.success:
            formatted_output = format_display_result(detected_tool, tool_res.data)
            yield {"type": "token", "content": formatted_output}
            elapsed = max(0.001, time.time() - start_time)
            yield {"type": "done", "tokens": len(formatted_output.split()), "time": elapsed, "request_id": req_id}
            return

        yield {"type": "token", "content": "Local model server (llama-server) មិនទាន់ដំណើរការ (Offline) ទេ ព្រោះពុំទាន់មាន file .gguf នៅក្នុងថត `./models` នៅឡើយ។\n\nសូម copy ឬដាក់ file model `.gguf` របស់អ្នកចូលទៅក្នុងថតខាងលើ ដើម្បីឱ្យប្រព័ន្ធដំណើរការ Local GGUF (Cloud API ត្រូវបានបិទទាំងស្រុង)។"}
        elapsed = max(0.001, time.time() - start_time)
        yield {"type": "done", "tokens": 30, "time": elapsed, "request_id": req_id}

llm_runtime = LLMRuntime()
