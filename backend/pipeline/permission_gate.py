from typing import Any, Dict, Tuple, Optional, Set
from backend.config import system_config

KNOWN_TOOLS = {
    "calculator", "local_files", "web_search", "web_fetch",
    "codebase_search", "codebase_read", "codebase_structure",
    "github_search", "github_source_read", "huggingface_search",
    "hardware_capability_detect", "gguf_metadata_inspect",
    "python_execute", "package_registry",
    "documentation_search", "rfc_search", "release_notes_search",
    "find_definition", "find_callers", "detect_security_issue", "detect_unused_code",
    "search_files", "read_file_range", "file_hash",
    "cpu_info", "ram_info", "traceback_analyzer", "benchmark_latency",
    "khmer_language_detect", "khmer_terminology_lookup",
    # Extended Core Suites (both dot and underscore aliases)
    "fs.list", "fs_list", "fs.search", "fs_search", "fs.read", "fs_read",
    "fs.create", "fs_create", "fs.edit", "fs_edit", "fs.patch", "fs_patch", "fs.metadata", "fs_metadata",
    "fs.batch_create", "fs_batch_create", "fs.mkdir", "fs_mkdir", "fs.tree", "fs_tree", "fs.delete", "fs_delete",
    "terminal.detect", "terminal_detect", "terminal.powershell", "terminal_powershell",
    "terminal.cmd", "terminal_cmd", "terminal.environment", "terminal_environment",
    "git.status", "git_status", "git.diff", "git_diff",
    "web.extract", "web_extract", "url.validate", "url_validate",
    "docs.specification", "docs_specification",
    "github.license", "github_license",
    "doc.analyze", "doc_analyze",
    # Fast Utilities & Optimization Suite
    "fast_calc", "unit_convert", "text_compact", "regex_extract",
    "memory.get", "memory_get", "memory.set", "memory_set",
    "memory.list", "memory_list", "memory.delete", "memory_delete",
    "project.scaffold", "project_scaffold",
    "code.syntax_lint", "code_syntax_lint",
    "khmer.fast_helper", "khmer_fast_helper",
    "sandbox.preview", "sandbox_preview",
    "code.self_heal", "code_self_heal",
    "rag.search", "rag_search", "rag.index", "rag_index", "rag.list_docs", "rag_list_docs"
}

class PermissionSandboxGate:
    """
    Permission & Sandbox Gate Layer:
    Centralized enforcer for Intent boundaries, Owner policy toggles, and sandbox security constraints.
    Validates whether the requested tool and action are authorized before execution.
    """
    @staticmethod
    def verify(
        tool_name: str,
        params: Dict[str, Any],
        allowed_tools: Optional[Set[str]] = None
    ) -> Tuple[bool, Optional[str]]:
        # 1. Unknown tool check (support both dot and underscore aliases)
        name_alt = tool_name.replace(".", "_") if "." in tool_name else tool_name.replace("_", ".")
        in_known = tool_name in KNOWN_TOOLS or name_alt in KNOWN_TOOLS
        if not in_known:
            return False, f"UNKNOWN_TOOL: Tool '{tool_name}' is not recognized in Sandbox Policy."

        # 2. Strict Intent Policy check: intent -> allowed_tools
        if allowed_tools is not None:
            if tool_name not in allowed_tools and name_alt not in allowed_tools:
                return False, f"TOOL_REJECTED: Tool '{tool_name}' is unauthorized for the active intent."

        cfg = system_config.tools

        # 3. Web Search policy checks
        if tool_name == "web_search":
            if not cfg.web_search_enabled:
                return False, "TOOL_UNAVAILABLE: Web search tool is disabled by Owner policy."
            if not cfg.web_search_allow_read:
                return False, "TOOL_UNAVAILABLE: Web search READ permission is disabled by Owner policy."

        # 4. Web Fetch policy checks
        elif tool_name == "web_fetch":
            if not cfg.web_fetch_enabled:
                return False, "TOOL_UNAVAILABLE: Web fetch tool is disabled by Owner policy."

        # 5. Sandbox Local Files checks
        elif tool_name == "local_files":
            if not cfg.local_files_enabled:
                return False, "TOOL_UNAVAILABLE: Local files sandbox tool is disabled by Owner policy."

            action = params.get("action", "list")
            if action in ["read", "list", "tree", "info", "stat"] and not cfg.sandbox_read_enabled:
                return False, "TOOL_UNAVAILABLE: Sandbox READ permission is disabled by Owner policy."
            elif action in ["write", "batch_write", "batch_create", "mkdir", "delete"] and not cfg.sandbox_write_enabled:
                return False, "TOOL_UNAVAILABLE: Sandbox WRITE permission is disabled by Owner policy."

        # 6. Project scaffold check
        elif tool_name in ["project.scaffold", "project_scaffold"]:
            if not cfg.sandbox_write_enabled:
                return False, "TOOL_UNAVAILABLE: Sandbox WRITE permission is disabled by Owner policy."

        # 7. Calculator and fast utility checks
        elif tool_name in ["calculator", "fast_calc", "unit_convert", "text_compact", "regex_extract", "code.syntax_lint", "code_syntax_lint", "khmer.fast_helper", "khmer_fast_helper"]:
            pass

        return True, None

permission_gate = PermissionSandboxGate()
