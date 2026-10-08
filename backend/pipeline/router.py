import re
from typing import Optional, Tuple, Dict, Any, Set
from backend.config import system_config
from backend.research.error_diagnostic import error_diagnostic
from backend.research.research_planner import research_planner

TOOL_POLICY: Dict[str, Set[str]] = {
    "math": {"calculator"},
    "files": {
        "local_files", "search_files", "read_file_range", "file_hash",
        "fs.list", "fs_list", "fs.search", "fs_search", "fs.read", "fs_read",
        "fs.create", "fs_create", "fs.edit", "fs_edit", "fs.patch", "fs_patch",
        "fs.metadata", "fs_metadata",
        "fs.batch_create", "fs_batch_create", "fs.mkdir", "fs_mkdir", "fs.tree", "fs_tree", "fs.delete", "fs_delete",
        "project.scaffold", "project_scaffold", "memory.get", "memory_get", "memory.set", "memory_set",
        "memory.list", "memory_list", "memory.delete", "memory_delete",
        "sandbox.preview", "sandbox_preview"
    },
    "web": {"web_search", "web_fetch", "web.extract", "web_extract", "url.validate", "url_validate"},
    "code_execution": {
        "python_execute", "local_files", "terminal.detect", "terminal_detect",
        "terminal.environment", "terminal_environment", "code.syntax_lint", "code_syntax_lint",
        "code.self_heal", "code_self_heal"
    },
    "package_research": {"package_registry", "web_search", "github_search"},
    "doc_analysis": {
        "doc.analyze", "doc_analyze", "local_files", "fs.read", "fs_read",
        "rag.search", "rag_search", "rag.index", "rag_index", "rag.list_docs", "rag_list_docs"
    },
    "coding_research": {
        "web_search", "web_fetch", "github_search", "github_source_read", "package_registry",
        "find_definition", "find_callers", "detect_security_issue", "detect_unused_code",
        "docs.specification", "docs_specification", "github.license", "github_license",
        "doc.analyze", "doc_analyze", "code.syntax_lint", "code_syntax_lint",
        "code.self_heal", "code_self_heal"
    },
    "error_investigation": {
        "web_search", "web_fetch", "github_search", "codebase_search", "codebase_read",
        "python_execute", "traceback_analyzer", "code.syntax_lint", "code_syntax_lint",
        "code.self_heal", "code_self_heal"
    },
    "codebase_inspection": {
        "codebase_search", "codebase_read", "codebase_structure", "local_files",
        "git.status", "git_status", "git.diff", "git_diff", "fs.list", "fs_list", "fs.read", "fs_read"
    },
    "model_research": {
        "huggingface_search", "hardware_capability_detect", "gguf_metadata_inspect",
        "web_search", "cpu_info", "ram_info"
    },
    "multi": {
        "calculator", "local_files", "web_search", "web_fetch",
        "codebase_search", "codebase_read", "codebase_structure",
        "github_search", "github_source_read", "huggingface_search",
        "hardware_capability_detect", "gguf_metadata_inspect",
        "python_execute", "package_registry", "search_files", "read_file_range",
        "file_hash", "cpu_info", "ram_info", "traceback_analyzer",
        "benchmark_latency", "khmer_language_detect", "khmer_terminology_lookup",
        "fs.list", "fs.search", "fs.read", "fs.create", "fs.edit", "fs.patch", "fs.metadata",
        "fs_list", "fs_search", "fs_read", "fs_create", "fs_edit", "fs_patch", "fs_metadata",
        "fs.batch_create", "fs_batch_create", "fs.mkdir", "fs_mkdir", "fs.tree", "fs_tree", "fs.delete", "fs_delete",
        "terminal.detect", "terminal.powershell", "terminal.cmd", "terminal.environment",
        "terminal_detect", "terminal_powershell", "terminal_cmd", "terminal_environment",
        "git.status", "git.diff", "git_status", "git_diff",
        "web.extract", "web_extract", "url.validate", "url_validate",
        "docs.specification", "docs_specification", "github.license", "github_license",
        "doc.analyze", "doc_analyze",
        "fast_calc", "unit_convert", "text_compact", "regex_extract",
        "memory.get", "memory_get", "memory.set", "memory_set",
        "memory.list", "memory_list", "memory.delete", "memory_delete",
        "project.scaffold", "project_scaffold",
        "code.syntax_lint", "code_syntax_lint",
        "khmer.fast_helper", "khmer_fast_helper",
        "sandbox.preview", "sandbox_preview",
        "code.self_heal", "code_self_heal",
        "rag.search", "rag_search",
        "rag.index", "rag_index",
        "rag.list_docs", "rag_list_docs"
    },
    "general": set()
}

INJECTION_PATTERNS = [
    r'ignore\s+(all\s+|any\s+)?(previous|prior|above)\s+instructions?',
    r'disregard\s+(all\s+)?instructions?',
    r'system\s+prompt',
    r'execute\s+(shell|bash|cmd|powershell)',
    r'bypass\s+(sandbox|security|permission)',
    r'admin\s+mode',
    r'jailbreak'
]

class IntentRouter:
    """
    K-Jocker Intelligent Intent & Routing Engine:
    Analyzes queries, code, errors, and model tasks to bind explicit permissions
    and route execution to the optimal tool under strict TOOL_POLICY.
    """

    @classmethod
    def sanitize_injection(cls, text: str) -> Tuple[str, bool]:
        """
        Detects prompt injection attempts and isolates genuine user command from injected exploits.
        """
        has_injection = False
        clean_text = text
        for pat in INJECTION_PATTERNS:
            if re.search(pat, clean_text, re.IGNORECASE):
                has_injection = True
                clean_text = re.split(pat, clean_text, flags=re.IGNORECASE)[0]
        return clean_text.strip(), has_injection

    @classmethod
    def classify_intent(cls, user_msg: str) -> Tuple[str, Set[str]]:
        sanitized_msg, has_injection = cls.sanitize_injection(user_msg)
        target = sanitized_msg if sanitized_msg else user_msg
        clean_msg = target.strip()
        lower = clean_msg.lower()

        if not clean_msg:
            return "general", set()

        # Check conversational greetings
        greetings = [
            "hello", "hi", "hey", "how are you", "who are you", "what can you do",
            "good morning", "good afternoon", "good evening", "ជំរាបសួរ", "សួស្តី",
            "thanks", "thank you", "អរគុណ"
        ]
        if any(lower == g or lower.startswith(g + " ") or lower.startswith(g + ",") for g in greetings) and len(clean_msg) < 45:
            return "general", set()

        # Check domain-specific intents
        has_error = error_diagnostic.analyze_error(clean_msg).is_error
        has_doc_analysis = cls._is_doc_analysis(clean_msg, lower)
        has_codebase = cls._has_codebase_intent(clean_msg, lower)
        has_model = cls._has_model_research_intent(clean_msg, lower)
        has_code_exec = cls._has_code_exec_intent(clean_msg, lower)
        has_package_res = cls._has_package_intent(clean_msg, lower)
        has_math = cls._has_math_intent(clean_msg, lower)
        has_files = cls._has_files_intent(clean_msg, lower)
        has_web = cls._has_web_intent(clean_msg, lower)
        has_coding_res = research_planner.should_research(clean_msg) and not (has_math or has_files or has_code_exec or has_doc_analysis)

        intents_active = []
        if has_error:
            intents_active.append("error_investigation")
        if has_doc_analysis:
            intents_active.append("doc_analysis")
        if has_code_exec:
            intents_active.append("code_execution")
        if has_package_res:
            intents_active.append("package_research")
        if has_codebase:
            intents_active.append("codebase_inspection")
        if has_model:
            intents_active.append("model_research")
        if has_math:
            intents_active.append("math")
        if has_files:
            intents_active.append("files")
        if has_web and not (has_error or has_codebase or has_model or has_code_exec or has_doc_analysis):
            intents_active.append("web")
        elif has_coding_res and not (has_error or has_codebase or has_model or has_code_exec or has_doc_analysis):
            intents_active.append("coding_research")

        if len(intents_active) > 1:
            allowed = set()
            for it in intents_active:
                allowed.update(TOOL_POLICY.get(it, set()))
            return "multi", allowed

        if has_error:
            return "error_investigation", set(TOOL_POLICY["error_investigation"])
        if has_doc_analysis:
            return "doc_analysis", set(TOOL_POLICY["doc_analysis"])
        if has_code_exec:
            return "code_execution", set(TOOL_POLICY["code_execution"])
        if has_package_res:
            return "package_research", set(TOOL_POLICY["package_research"])
        if has_codebase:
            return "codebase_inspection", set(TOOL_POLICY["codebase_inspection"])
        if has_model:
            return "model_research", set(TOOL_POLICY["model_research"])
        if has_math:
            return "math", set(TOOL_POLICY["math"])
        if has_files:
            return "files", set(TOOL_POLICY["files"])
        if has_web:
            return "web", set(TOOL_POLICY["web"])
        if has_coding_res:
            return "coding_research", set(TOOL_POLICY["coding_research"])

        return "general", set(TOOL_POLICY["general"])

    @staticmethod
    def _is_doc_analysis(clean_msg: str, lower: str) -> bool:
        action_signals = [
            "analyze", "analay", "analysis", "review", "breakdown", "summarize",
            "explain this", "what does this mean", "parse this", "inspect this",
            "វិភាគ", "សង្ខេប", "ពន្យល់"
        ]
        doc_signals = [
            "master prompt", "specification", "architecture", "guidelines",
            "runtime integration", "upgrade", "overview", "system prompt"
        ]
        has_doc_header = clean_msg.startswith("# ") or "\n# " in clean_msg or "## " in clean_msg or ".md" in lower
        has_action = any(a in lower for a in action_signals)
        has_doc_kw = any(s in lower for s in doc_signals)

        if has_action and (has_doc_header or has_doc_kw or len(clean_msg) > 350):
            return True
        if has_doc_header and (len(clean_msg) > 400 or has_doc_kw):
            return True
        return False

    @staticmethod
    def _is_coding_or_doc_prompt(clean_msg: str, lower: str) -> bool:
        # Do not suppress math intent if explicit math keywords or calculations are present
        if any(m in lower for m in ["math", "calculator", "calculate", "គណនា", "equation", "សមីការ", "discount", "បញ្ចុះតម្លៃ", "area", "ផ្ទៃក្រឡា", "rectangle", "ចតុកោណកែង"]):
            return False

        coding_signals = [
            "def ", "class ", "import ", "from ", "```", "return ",
            "write a python", "write python", "write a function", "write a program",
            "fix my python", "fix my code", "debug this", "code review", "refactor",
            "find the bug", "syntax", "json", "function:", "def calculate",
            "explain what python", "explain what is python", "rules:\n", "rules:\r\n"
        ]
        if any(sig in lower for sig in coding_signals):
            return True
        if re.search(r'\b[a-zA-Z0-9_\-\.\/]+\.(?:py|js|ts|json|cpp|c|h|html|css)\b', clean_msg):
            return True
        return False

    @classmethod
    def _has_math_intent(cls, clean_msg: str, lower: str) -> bool:
        if cls._is_coding_or_doc_prompt(clean_msg, lower):
            return False
        if "calculator." in lower:
            return False

        math_explicit = any(k in lower for k in [
            "calculate", "calc", "គណនា", "sqrt(", "math.sqrt", "evaluate", "equation", "solve",
            "discount", "percentage", "បញ្ចុះតម្លៃ", "ផ្ទៃក្រឡា", "rectangle", "triangle", "circle",
            "ចតុកោណកែង", "ត្រីកោណ", "រង្វង់", "បណ្តោយ", "បណ្ដោយ", "ទទឹង", "កាំ", "ផលបូក", "ផលដក", "ផលគុណ", "ផលចែក"
        ])
        has_arithmetic = bool(re.search(r'\b\d+(?:\.\d+)?\s*[\+\-\*\/×÷−–—\^]\s*\d+(?:\.\d+)?\b', clean_msg))
        has_percent = bool(re.search(r'\b\d+(?:\.\d+)?%\s*(?:of)?\s*\d+(?:\.\d+)?\b', clean_msg))
        has_algebra = bool(re.search(r'\b\d*[a-zA-Z]\s*[\+\-\*\/×÷−=]\s*\d+', clean_msg))
        return math_explicit or has_arithmetic or has_percent or has_algebra

    @staticmethod
    def _has_files_intent(clean_msg: str, lower: str) -> bool:
        if not system_config.tools.local_files_enabled:
            return False
        file_keywords = [
            "list files", "show files", "sandbox files", "files in sandbox", "មើលឯកសារ",
            "បញ្ជីឯកសារ", "ls -l", "read file", "open file", "check file", "cat ", "runtime_test.txt"
        ]
        if any(k in lower for k in file_keywords):
            return True
        file_read_match = bool(re.search(r'(?:read|show|check|cat|open|បើក|អាន)\s+(?:file\s+)?([a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9]+)', clean_msg, re.IGNORECASE))
        return file_read_match

    @classmethod
    def _has_web_intent(cls, clean_msg: str, lower: str) -> bool:
        if re.search(r"https?://[^\s<>\"']+", clean_msg):
            return True
        if not system_config.tools.web_search_enabled:
            return False
        if cls._is_doc_analysis(clean_msg, lower):
            return False
        if cls._is_coding_or_doc_prompt(clean_msg, lower) and len(clean_msg) > 300:
            return False

        # Guard: For long text (>350 chars or multi-line), require explicit search command prefix
        if len(clean_msg) > 350 or clean_msg.count("\n") > 3:
            explicit_start = any(lower.startswith(p) for p in [
                "search for", "search", "google", "ស្វែងរក", "រកមើល", "/search", "find out"
            ])
            return explicit_start

        explicit_search = any(k in lower for k in [
            "search", "search for", "find out", "google", "look up", "ស្វែងរក", "រកមើល", "/search",
            "who is", "who won", "what is the latest", "what happened", "latest news", "price of",
            "weather", "bitcoin", "crypto", "stock", "today", "yesterday", "2024", "2025", "2026",
            "news", "documentation for", "docs for", "current status", "ceo of", "founder of",
            "release date", "what time", "where is", "how much does", "who created", "who made"
        ])
        is_pure_logic_puzzle = ("riddle" in lower or "test:" in lower) and not any(k in lower for k in ["search", "google", "ស្វែងរក", "latest", "news"])
        return explicit_search and not is_pure_logic_puzzle

    @staticmethod
    def _has_codebase_intent(clean_msg: str, lower: str) -> bool:
        triggers = [
            "search codebase", "search code", "find in codebase", "find callers",
            "where is function", "where is class", "where is method", "codebase structure",
            "project structure", "architecture of project", "list project files", "inspect codebase"
        ]
        return any(t in lower for t in triggers)

    @staticmethod
    def _has_model_research_intent(clean_msg: str, lower: str) -> bool:
        triggers = [
            "huggingface", "hugging face", "hf model", "search model", "find gguf",
            "inspect gguf", "gguf metadata", "detect hardware", "hardware specs",
            "hardware capabilities", "ram requirements", "quantization fit", "can my pc run"
        ]
        return any(t in lower for t in triggers)

    @staticmethod
    def _has_code_exec_intent(clean_msg: str, lower: str) -> bool:
        triggers = [
            "run python", "execute python", "run script", "execute script",
            "run this code", "execute this code", "test script", "run code",
            "run the code", "test python", "execute the code",
            "trace the output", "trace output", "trace the loop", "trace loop",
            "what will be printed", "what is printed", "what does this code output",
            "what is the output", "what will this print", "final value of total",
            "what is the final value", "trace:", "evaluate this code",
            "ដំណើរការកូដ", "តេស្តកូដ", "តើកូដនេះ print អ្វី", "តើកូដនេះបង្ហាញអ្វី",
            "តើវា print អ្វី", "លទ្ធផលនៃកូដ", "trace កូដ"
        ]
        for t in triggers:
            if re.search(r'(?<![a-zA-Z0-9_])' + re.escape(t) + r'(?![a-zA-Z0-9_])', lower):
                return True
        if ("print(" in clean_msg or "print (" in clean_msg) and any(q in lower for q in ["output", "printed", "print?", "result", "លទ្ធផល", "trace", "what"]):
            return True
        return False

    @staticmethod
    def _has_package_intent(clean_msg: str, lower: str) -> bool:
        triggers = [
            "pypi", "npm package", "crates.io", "package version", "check package",
            "pypi package", "crate version"
        ]
        return any(t in lower for t in triggers)

    @classmethod
    def _extract_runnable_code(cls, text: str) -> str:
        # 0. Strip leading execution commands (e.g. 'Execute python:', 'Run python:', etc.)
        text = re.sub(r'^(?:execute\s+python|run\s+python|python|eval)\s*:\s*', '', text.strip(), flags=re.IGNORECASE)

        # 1. Markdown fenced code
        fenced_match = re.search(r'```(?:python)?\s*([\s\S]+?)\s*```', text)
        if fenced_match:
            return fenced_match.group(1).strip()

        # 2. Bare Python statements inside mixed question text
        lines = text.splitlines()
        code_lines = []
        in_code_candidate = False

        is_code_pattern = re.compile(
            r'^(?:[a-zA-Z_]\w*\s*=\s*.+|'
            r'\s*(?:if|elif|else|for|while|try|except|finally|with|def|class)\b.*:|'
            r'\s*(?:print|return|import|from|assert|raise|break|continue|pass)\b.*|'
            r'\s{2,}.+)'
        )

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if in_code_candidate:
                    code_lines.append("")
                continue

            if stripped.lower() in ("python", "python:", "code:", "py") or stripped.endswith("?"):
                continue
            if any(h in stripped.lower() for h in ("trace the output", "trace the loop", "what will be printed", "what is the final value", "part ")):
                continue

            if is_code_pattern.match(line):
                in_code_candidate = True
                code_lines.append(line)
            elif in_code_candidate and (line.startswith(" ") or line.startswith("\t")):
                code_lines.append(line)
            else:
                if in_code_candidate and any("print" in l for l in code_lines):
                    break

        extracted = "\n".join(code_lines).strip()
        return extracted if extracted else text.strip()

    @classmethod
    def route(cls, user_msg: str) -> Tuple[Optional[str], Dict[str, Any]]:
        intent, allowed_tools = cls.classify_intent(user_msg)
        if intent == "general" or not allowed_tools:
            return None, {}

        sanitized_msg, _ = cls.sanitize_injection(user_msg)
        clean_msg = sanitized_msg.strip() if sanitized_msg else user_msg.strip()
        lower = clean_msg.lower()

        # Multi-part exams/benchmarks with mixed questions should not be blindly executed as a single script
        is_multi_part_test = (
            ("part 1" in lower and "part 2" in lower) or
            ("ai evaluation test" in lower) or
            (lower.count("question") > 2 and ("rules" in lower or "test" in lower))
        )
        if is_multi_part_test:
            return None, {}

        # 0. Fast Document & Architecture Analyzer (<50ms, Zero Network)
        if cls._is_doc_analysis(clean_msg, lower):
            if "doc.analyze" in allowed_tools or "doc_analyze" in allowed_tools:
                return "doc.analyze", {"text": clean_msg}

        # 1. Error Investigation -> Web Search with exact diagnostic query
        if intent == "error_investigation" or "error_investigation" in intent:
            diag = error_diagnostic.analyze_error(clean_msg)
            query = diag.suggested_queries[0] if diag.suggested_queries else clean_msg[:100]
            if "web_search" in allowed_tools:
                return "web_search", {"query": query}

        # 2. Python Code Execution
        if "python_execute" in allowed_tools and cls._has_code_exec_intent(clean_msg, lower):
            code = cls._extract_runnable_code(clean_msg)
            return "python_execute", {"code": code}

        # 3. Package Registry Research
        if "package_registry" in allowed_tools and cls._has_package_intent(clean_msg, lower):
            m = re.search(r'(?:package|crate|module|library)\s+([a-zA-Z0-9_\-\.]+)', clean_msg, re.IGNORECASE)
            pkg = m.group(1) if m else clean_msg.split()[-1]
            eco = "npm" if "npm" in lower else ("crates" if "crate" in lower else "pypi")
            return "package_registry", {"package_name": pkg, "ecosystem": eco}

        # 4. Codebase Inspection Tools
        if "codebase_search" in allowed_tools and cls._has_codebase_intent(clean_msg, lower):
            if any(k in lower for k in ["structure", "architecture", "layout"]):
                return "codebase_structure", {}
            m = re.search(r'(?:search|find|where is)\s+(?:codebase|in codebase\s+)?(?:for\s+)?([a-zA-Z0-9_\-\.]+)', clean_msg, re.IGNORECASE)
            query = m.group(1) if m else clean_msg.split()[-1]
            return "codebase_search", {"query": query}

        # 5. Model Research Tools
        if cls._has_model_research_intent(clean_msg, lower):
            if any(k in lower for k in ["hardware", "specs", "ram", "cores", "cpu", "detect hardware"]):
                if "hardware_capability_detect" in allowed_tools:
                    return "hardware_capability_detect", {}
            if any(k in lower for k in ["inspect", "metadata", "header"]):
                if "gguf_metadata_inspect" in allowed_tools:
                    m = re.search(r'([a-zA-Z0-9_\-\.]+\.gguf)', clean_msg, re.IGNORECASE)
                    fname = m.group(1) if m else "qwen3-1.7b-flashhead-q4_k_m.gguf"
                    return "gguf_metadata_inspect", {"filename": fname}
            if "huggingface_search" in allowed_tools:
                q = re.sub(r'^(?:search|find|lookup)\s+(?:huggingface|hf|models?)\s+(?:for\s+)?', '', clean_msg, flags=re.IGNORECASE).strip()
                return "huggingface_search", {"query": q or clean_msg}

        # 6. URL -> Web Fetch Tool
        url_match = re.search(r"https?://[^\s<>\"']+", clean_msg)
        if url_match and "web_fetch" in allowed_tools and system_config.tools.web_fetch_enabled:
            return "web_fetch", {"url": url_match.group(0)}

        # 7. Sandbox Files Tool
        if "local_files" in allowed_tools and system_config.tools.local_files_enabled:
            if any(k in lower for k in ["list files", "show files", "sandbox files", "files in sandbox", "មើលឯកសារ", "បញ្ជីឯកសារ", "ls -l"]):
                return "local_files", {"action": "list"}
            # Guard: Only trigger file read on direct, focused queries (avoid false positives on pasted docs/prompts)
            if len(clean_msg) <= 300 and clean_msg.count("\n") <= 3:
                file_read_match = re.search(r'(?:read|show|check|cat|open|បើក|អាន)\s+(?:file\s+)?([a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9]+)', clean_msg, re.IGNORECASE)
                if file_read_match:
                    return "local_files", {"action": "read", "filename": file_read_match.group(1)}

        # 8. Calculator Tool
        if "calculator" in allowed_tools and cls._has_math_intent(clean_msg, lower):
            lines = [l.strip() for l in clean_msg.splitlines() if l.strip()]
            math_candidates = [l for l in lines if not l.lower().startswith(("part ", "test ", "question "))]
            target_text = math_candidates[0] if len(math_candidates) == 1 else clean_msg
            if len(target_text) <= 250 and target_text.count("?") <= 1:
                expr = target_text
                expr = re.sub(r'^(?:calculate|calc|គណនា|what is|evaluate|how much is|solve(?:\s+for\s+[a-zA-Z])?)\s*[:=]?\s*', '', expr, flags=re.IGNORECASE).strip(" :,-?")
                if ", then" in expr:
                    expr = expr.split(", then")[0]
                elif " and " in expr and any(x in expr for x in ["read", "file"]):
                    expr = expr.split(" and ")[0]
                return "calculator", {"expression": expr.strip()}

        # 9. Coding Research / Web Search Tool
        if "web_search" in allowed_tools and not cls._is_doc_analysis(clean_msg, lower) and (cls._has_web_intent(clean_msg, lower) or intent == "coding_research"):
            clean = clean_msg
            for prefix in ["search for", "search", "ស្វែងរក", "រកមើល", "web search", "google", "find out", "look up"]:
                if clean.lower().startswith(prefix):
                    clean = clean[len(prefix):].strip(" :,-?")
            query = clean[:120].strip() or clean_msg[:120].strip()
            return "web_search", {"query": query}

        return None, {}

intent_router = IntentRouter()
