from backend.tools.search import WebSearchTool
from backend.tools.fetch import WebFetchTool
from backend.tools.sandbox import LocalFilesSandboxTool
from backend.tools.calc import CalculatorTool
from backend.tools.codebase import CodebaseSearchTool, CodebaseReadTool, CodebaseStructureTool
from backend.tools.github_research import GitHubSearchTool, GitHubSourceReadTool
from backend.tools.model_research import HardwareCapabilityDetectTool, GGUFMetadataInspectTool, HuggingFaceSearchTool
from backend.tools.python_executor import PythonExecuteTool
from backend.tools.package_research import PackageRegistryTool

# Extended ecosystem tools
from backend.tools.documentation import DocumentationSearchTool, RFCSearchTool, ReleaseNotesSearchTool
from backend.tools.code_intelligence import FindDefinitionTool, FindCallersTool, DetectSecurityIssueTool, DetectUnusedCodeTool
from backend.tools.filesystem_tools import SearchFilesTool, ReadFileRangeTool, FileHashTool
from backend.tools.hardware_tools import CPUInfoTool, RAMInfoTool
from backend.tools.debugging_tools import TracebackAnalyzerTool
from backend.tools.khmer_tools import KhmerLanguageDetectTool, KhmerTerminologyLookupTool
from backend.tools.benchmark_tools import BenchmarkLatencyTool

# Extended Core Suites
from backend.tools.filesystem_suite import (
    FSListTool, FSSearchTool, FSReadTool, FSCreateTool, FSEditTool, FSPatchTool, FSMetadataTool,
    FSBatchCreateTool, FSMkdirTool, FSTreeTool, FSDeleteTool
)
from backend.tools.terminal_suite import TerminalDetectTool, TerminalPowershellTool, TerminalCmdTool, TerminalEnvironmentTool
from backend.tools.git_suite import GitStatusTool, GitDiffTool
from backend.tools.web_suite import URLExtractTool, URLValidateTool
from backend.tools.docs_suite import DocsSpecificationTool
from backend.tools.github_suite import GitHubLicenseTool
from backend.tools.doc_analyzer import DocAnalyzeTool
from backend.tools.fast_utility_suite import FastCalcTool, UnitConvertTool, TextCompactTool, RegexExtractTool
from backend.tools.fast_memory_suite import MemoryGetTool, MemorySetTool, MemoryListTool, MemoryDeleteTool
from backend.tools.project_scaffold import ProjectScaffoldTool
from backend.tools.code_lint_suite import CodeSyntaxLintTool
from backend.tools.khmer_fast_helper import KhmerFastHelperTool
from backend.tools.preview_tools import SandboxPreviewTool
from backend.tools.self_heal_tools import CodeSelfHealTool
from backend.tools.rag_tools import RAGSearchTool, RAGIndexTool, RAGListDocsTool

from backend.platform.registry import tool_platform

class ToolRegistry:
    """
    K-Jocker Tool Platform Registry (supporting backward compatibility & dynamic discovery).
    """
    def __init__(self):
        self._tools = {
            # Web Research
            "web_search": WebSearchTool(),
            "web_fetch": WebFetchTool(),
            
            # Documentation
            "documentation_search": DocumentationSearchTool(),
            "rfc_search": RFCSearchTool(),
            "release_notes_search": ReleaseNotesSearchTool(),

            # GitHub & Source Code
            "github_search": GitHubSearchTool(),
            "github_source_read": GitHubSourceReadTool(),

            # Package Ecosystems
            "package_registry": PackageRegistryTool(),

            # Code Intelligence & Execution
            "python_execute": PythonExecuteTool(),
            "codebase_search": CodebaseSearchTool(),
            "codebase_read": CodebaseReadTool(),
            "codebase_structure": CodebaseStructureTool(),
            "find_definition": FindDefinitionTool(),
            "find_callers": FindCallersTool(),
            "detect_security_issue": DetectSecurityIssueTool(),
            "detect_unused_code": DetectUnusedCodeTool(),

            # Filesystem
            "local_files": LocalFilesSandboxTool(),
            "search_files": SearchFilesTool(),
            "read_file_range": ReadFileRangeTool(),
            "file_hash": FileHashTool(),

            # Models & Hardware
            "hardware_capability_detect": HardwareCapabilityDetectTool(),
            "gguf_metadata_inspect": GGUFMetadataInspectTool(),
            "huggingface_search": HuggingFaceSearchTool(),
            "cpu_info": CPUInfoTool(),
            "ram_info": RAMInfoTool(),

            # Debugging & Benchmark
            "traceback_analyzer": TracebackAnalyzerTool(),
            "benchmark_latency": BenchmarkLatencyTool(),

            # Khmer Intelligence
            "khmer_language_detect": KhmerLanguageDetectTool(),
            "khmer_terminology_lookup": KhmerTerminologyLookupTool(),

            # Math / Utility
            "calculator": CalculatorTool(),

            # Extended Core Suites
            "fs.list": FSListTool(),
            "fs.search": FSSearchTool(),
            "fs.read": FSReadTool(),
            "fs.create": FSCreateTool(),
            "fs.edit": FSEditTool(),
            "fs.patch": FSPatchTool(),
            "fs.metadata": FSMetadataTool(),
            "fs.batch_create": FSBatchCreateTool(),
            "fs.mkdir": FSMkdirTool(),
            "fs.tree": FSTreeTool(),
            "fs.delete": FSDeleteTool(),
            "terminal.detect": TerminalDetectTool(),
            "terminal.powershell": TerminalPowershellTool(),
            "terminal.cmd": TerminalCmdTool(),
            "terminal.environment": TerminalEnvironmentTool(),
            "git.status": GitStatusTool(),
            "git.diff": GitDiffTool(),
            "web.extract": URLExtractTool(),
            "url.validate": URLValidateTool(),
            "docs.specification": DocsSpecificationTool(),
            "github.license": GitHubLicenseTool(),
            "doc.analyze": DocAnalyzeTool(),
            "doc_analyze": DocAnalyzeTool(),
            "fast_calc": FastCalcTool(),
            "unit_convert": UnitConvertTool(),
            "text_compact": TextCompactTool(),
            "regex_extract": RegexExtractTool(),
            "memory.get": MemoryGetTool(),
            "memory_get": MemoryGetTool(),
            "memory.set": MemorySetTool(),
            "memory_set": MemorySetTool(),
            "memory.list": MemoryListTool(),
            "memory_list": MemoryListTool(),
            "memory.delete": MemoryDeleteTool(),
            "memory_delete": MemoryDeleteTool(),
            "project.scaffold": ProjectScaffoldTool(),
            "project_scaffold": ProjectScaffoldTool(),
            "code.syntax_lint": CodeSyntaxLintTool(),
            "code_syntax_lint": CodeSyntaxLintTool(),
            "khmer.fast_helper": KhmerFastHelperTool(),
            "khmer_fast_helper": KhmerFastHelperTool(),
            "sandbox.preview": SandboxPreviewTool(),
            "sandbox_preview": SandboxPreviewTool(),
            "code.self_heal": CodeSelfHealTool(),
            "code_self_heal": CodeSelfHealTool(),
            "rag.search": RAGSearchTool(),
            "rag_search": RAGSearchTool(),
            "rag.index": RAGIndexTool(),
            "rag_index": RAGIndexTool(),
            "rag.list_docs": RAGListDocsTool(),
            "rag_list_docs": RAGListDocsTool()
        }
        self._register_in_platform()

    def _register_in_platform(self):
        cat_map = {
            "web_search": "web_research", "web_fetch": "web_research",
            "documentation_search": "documentation", "rfc_search": "documentation", "release_notes_search": "documentation",
            "github_search": "github", "github_source_read": "github",
            "package_registry": "package",
            "python_execute": "programming", "codebase_search": "code_intelligence", "codebase_read": "code_intelligence",
            "codebase_structure": "code_intelligence", "find_definition": "code_intelligence", "find_callers": "code_intelligence",
            "detect_security_issue": "security", "detect_unused_code": "code_intelligence",
            "local_files": "filesystem", "search_files": "filesystem", "read_file_range": "filesystem", "file_hash": "filesystem",
            "hardware_capability_detect": "hardware", "gguf_metadata_inspect": "gguf", "huggingface_search": "models",
            "cpu_info": "hardware", "ram_info": "hardware",
            "traceback_analyzer": "debugging", "benchmark_latency": "benchmark",
            "khmer_language_detect": "khmer", "khmer_terminology_lookup": "khmer",
            "calculator": "utility",
            "fs.list": "filesystem", "fs.search": "filesystem", "fs.read": "filesystem",
            "fs.create": "filesystem", "fs.edit": "filesystem", "fs.patch": "filesystem", "fs.metadata": "filesystem",
            "fs.batch_create": "filesystem", "fs.mkdir": "filesystem", "fs.tree": "filesystem", "fs.delete": "filesystem",
            "terminal.detect": "terminal", "terminal.powershell": "terminal",
            "terminal.cmd": "terminal", "terminal.environment": "terminal",
            "git.status": "git", "git.diff": "git",
            "web.extract": "web_research", "url.validate": "web_research",
            "docs.specification": "documentation", "github.license": "github",
            "doc.analyze": "documentation", "doc_analyze": "documentation",
            "fast_calc": "utility", "unit_convert": "utility", "text_compact": "utility", "regex_extract": "utility",
            "memory.get": "memory", "memory_get": "memory", "memory.set": "memory", "memory_set": "memory",
            "memory.list": "memory", "memory_list": "memory", "memory.delete": "memory", "memory_delete": "memory",
            "project.scaffold": "scaffold", "project_scaffold": "scaffold",
            "code.syntax_lint": "programming", "code_syntax_lint": "programming",
            "khmer.fast_helper": "khmer", "khmer_fast_helper": "khmer",
            "sandbox.preview": "preview", "sandbox_preview": "preview",
            "code.self_heal": "programming", "code_self_heal": "programming",
            "rag.search": "rag", "rag_search": "rag",
            "rag.index": "rag", "rag_index": "rag",
            "rag.list_docs": "rag", "rag_list_docs": "rag"
        }
        for name, tool in self._tools.items():
            cat = cat_map.get(name, "utility")
            tool_platform.register(tool, category=cat, tags=[name, cat, name.replace(".", "_")])

    def get_tool(self, name: str):
        if name in self._tools:
            return self._tools[name]
        alt = name.replace("_", ".")
        if alt in self._tools:
            return self._tools[alt]
        alt2 = name.replace(".", "_")
        if alt2 in self._tools:
            return self._tools[alt2]
        return None

    def list_tools(self):
        return [
            {
                "id": t.name,
                "name": t.name.replace("_", " ").title(),
                "description": t.description,
                "risk_level": t.risk_level,
                "requires_confirmation": t.requires_confirmation,
                "schema": t.get_input_schema()
            }
            for t in self._tools.values()
        ]

    def get_tools_definitions(self, allowed_tools=None):
        defs = []
        for name, t in self._tools.items():
            if allowed_tools is not None and name not in allowed_tools:
                continue
            defs.append({
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.get_input_schema()
                }
            })
        return defs

tool_registry = ToolRegistry()
