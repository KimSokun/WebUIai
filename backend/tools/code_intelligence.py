import re
import ast
from pathlib import Path
from typing import Any, Dict, List
from backend.platform.manifest import PlatformTool, ToolManifest, ToolCategory, RiskLevel
from backend.tools.base import ToolResult
from backend.config import BASE_DIR

class FindDefinitionTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="find_definition",
            name="Find Code Definition",
            category=ToolCategory.CODE_INTELLIGENCE,
            description="Locate class, function, or symbol definition in the local project codebase.",
            tags=["definition", "class", "function", "symbol", "codebase"],
            risk_level=RiskLevel.ANALYZE,
            timeout_seconds=5.0
        ))

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symbol_name": {"type": "string", "description": "Name of the function, class, or variable to find"}
            },
            "required": ["symbol_name"]
        }

    async def execute(self, symbol_name: str = "", **kwargs) -> ToolResult:
        if not symbol_name:
            return ToolResult(success=False, data=[], error="Symbol name cannot be empty.")
        pattern = re.compile(rf"^\s*(?:def|class|async\s+def)\s+{re.escape(symbol_name)}\b")
        matches = []
        for p in BASE_DIR.rglob("*.py"):
            if any(x in p.parts for x in ["__pycache__", ".git", "sandbox"]):
                continue
            try:
                for idx, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
                    if pattern.search(line):
                        matches.append({
                            "file": str(p.relative_to(BASE_DIR)).replace("\\", "/"),
                            "line": idx,
                            "definition": line.strip()
                        })
            except Exception:
                continue
        return ToolResult(success=True, data=matches)

class FindCallersTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="find_callers",
            name="Find Symbol Callers",
            category=ToolCategory.CODE_INTELLIGENCE,
            description="Find all occurrences and callers of a function or method across the codebase.",
            tags=["callers", "references", "usages", "codebase"],
            risk_level=RiskLevel.ANALYZE,
            timeout_seconds=5.0
        ))

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "function_name": {"type": "string", "description": "Name of function to find callers for"}
            },
            "required": ["function_name"]
        }

    async def execute(self, function_name: str = "", **kwargs) -> ToolResult:
        pattern = re.compile(rf"\b{re.escape(function_name)}\s*\(")
        callers = []
        for p in BASE_DIR.rglob("*.py"):
            if any(x in p.parts for x in ["__pycache__", ".git", "sandbox"]):
                continue
            try:
                for idx, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
                    if pattern.search(line) and not line.strip().startswith(("def ", "async def ")):
                        callers.append({
                            "file": str(p.relative_to(BASE_DIR)).replace("\\", "/"),
                            "line": idx,
                            "snippet": line.strip()[:150]
                        })
                        if len(callers) >= 20:
                            break
            except Exception:
                continue
        return ToolResult(success=True, data=callers)

class DetectSecurityIssueTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="detect_security_issue",
            name="Detect Security Issues",
            category=ToolCategory.SECURITY,
            description="Scans code for dangerous patterns, hardcoded secrets, unsafe eval/exec, or command injection.",
            tags=["security", "vulnerability", "audit", "secret", "injection"],
            risk_level=RiskLevel.ANALYZE,
            timeout_seconds=5.0
        ))

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code_or_file": {"type": "string", "description": "Code string or relative path to file"}
            },
            "required": ["code_or_file"]
        }

    async def execute(self, code_or_file: str = "", **kwargs) -> ToolResult:
        text = code_or_file
        if (BASE_DIR / code_or_file).exists() and (BASE_DIR / code_or_file).is_file():
            text = (BASE_DIR / code_or_file).read_text(encoding="utf-8", errors="replace")

        findings = []
        risks = [
            (re.compile(r"\beval\s*\("), "CRITICAL: Use of eval() detected (arbitrary code execution risk)"),
            (re.compile(r"\bexec\s*\("), "CRITICAL: Use of exec() detected (arbitrary code execution risk)"),
            (re.compile(r"shell\s*=\s*True"), "HIGH: subprocess with shell=True detected (command injection risk)"),
            (re.compile(r"""['"][a-zA-Z0-9_-]{20,}['"]"""), "MEDIUM: Potential hardcoded secret or token detected")
        ]
        for pat, desc in risks:
            for idx, line in enumerate(text.splitlines(), start=1):
                if pat.search(line) and not line.strip().startswith("#"):
                    findings.append({"line": idx, "issue": desc, "snippet": line.strip()[:120]})
        return ToolResult(success=True, data={"issues_found": len(findings), "findings": findings})

class DetectUnusedCodeTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="detect_unused_code",
            name="Detect Unused Imports & Dead Code",
            category=ToolCategory.CODE_INTELLIGENCE,
            description="Finds unused imports and dead symbols in Python code using AST analysis.",
            tags=["unused", "lint", "clean", "dead code", "ast"],
            risk_level=RiskLevel.ANALYZE,
            timeout_seconds=5.0
        ))

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python code snippet to analyze"}
            },
            "required": ["code"]
        }

    async def execute(self, code: str = "", **kwargs) -> ToolResult:
        try:
            tree = ast.parse(code)
            imports = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for n in node.names:
                        imports.add(n.asname or n.name)
                elif isinstance(node, ast.ImportFrom):
                    for n in node.names:
                        imports.add(n.asname or n.name)

            names_used = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
            unused = [imp for imp in imports if imp not in names_used]
            return ToolResult(success=True, data={"unused_imports": unused, "count": len(unused)})
        except Exception as e:
            return ToolResult(success=False, data=None, error=f"AST parse error: {str(e)}")
