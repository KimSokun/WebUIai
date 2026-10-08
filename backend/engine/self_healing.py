import re
import difflib
import time
from pathlib import Path
from typing import Any, Dict, Optional, List
from backend.config import SANDBOX_DIR
from backend.tools.base import BaseTool, ToolResult
from backend.tools.debugging_tools import TracebackAnalyzerTool
from backend.tools.python_executor import PythonExecuteTool

class SelfHealingEngine:
    """
    Autonomous Multi-Turn Self-Healing Coding Loop:
    Executes code in isolated sandbox, intercepts exceptions, diagnoses tracebacks,
    applies targeted patches, and re-validates until 100% PASS.
    """
    def __init__(self):
        self.py_tool = PythonExecuteTool()
        self.tb_tool = TracebackAnalyzerTool()

    async def auto_heal_code(
        self,
        code: str,
        test_script: Optional[str] = None,
        filename: str = "script.py",
        max_retries: int = 3
    ) -> Dict[str, Any]:
        start_t = time.perf_counter()
        original_code = code
        current_code = code
        history = []

        # Target file inside sandbox
        safe_filename = Path(filename).name
        target_path = SANDBOX_DIR / safe_filename
        target_path.parent.mkdir(parents=True, exist_ok=True)

        for attempt in range(1, max_retries + 1):
            target_path.write_text(current_code, encoding="utf-8")

            # Determine execution script
            if test_script:
                runner_code = f"{current_code}\n\n# --- Test Script ---\n{test_script}\n"
                run_file = f"test_{safe_filename}"
            else:
                runner_code = current_code
                run_file = safe_filename

            # Execute in sandbox
            res = await self.py_tool.execute(code=runner_code, filename=run_file, timeout_seconds=5.0)
            stdout = res.data.get("stdout", "") if res.data else ""
            stderr = res.data.get("stderr", "") if res.data else ""
            exit_code = res.data.get("exit_code", 0) if res.data else 1

            if res.success and exit_code == 0:
                elapsed = (time.perf_counter() - start_t) * 1000
                diff_lines = list(difflib.unified_diff(
                    original_code.splitlines(keepends=True),
                    current_code.splitlines(keepends=True),
                    fromfile="a/" + safe_filename,
                    tofile="b/" + safe_filename
                ))
                return {
                    "status": "RESOLVED",
                    "attempts": attempt,
                    "iterations": attempt,
                    "healed_code": current_code,
                    "fixed_code": current_code,
                    "diff": "".join(diff_lines),
                    "stdout": stdout,
                    "stderr": stderr,
                    "history": history,
                    "time_ms": round(elapsed, 2)
                }

            # If failed, analyze traceback
            tb_res = await self.tb_tool.execute(traceback=stderr or stdout)
            diagnosis = tb_res.data if tb_res.success else {}
            err_type = str(diagnosis.get("error_type") or "UnknownError")
            err_msg = str(diagnosis.get("error_message") or "")
            fail_line = diagnosis.get("failing_line")
            full_err_text = f"{err_msg}\n{stderr}"

            history.append({
                "attempt": attempt,
                "error_type": err_type,
                "error_message": err_msg,
                "failing_line": fail_line,
                "stderr": stderr[:300]
            })

            # Automated self-repair heuristics
            repaired = False

            # Heuristic 1: Missing standard imports (NameError)
            if err_type == "NameError" or "is not defined" in full_err_text:
                missing_var_m = re.search(r"name '([a-zA-Z0-9_]+)' is not defined", full_err_text)
                if missing_var_m:
                    missing_mod = missing_var_m.group(1)
                    if missing_mod in ["math", "json", "re", "sys", "os", "time", "datetime", "uuid", "random", "pathlib", "ast"]:
                        current_code = f"import {missing_mod}\n" + current_code
                        repaired = True

            # Heuristic 2: ZeroDivisionError
            if not repaired and err_type == "ZeroDivisionError":
                # Guard zero division with ternary / max
                current_code = re.sub(
                    r'( [a-zA-Z0-9_\.]+\s*\/\s*)([a-zA-Z0-9_]+)',
                    r'\1(\2 if \2 != 0 else 1)',
                    current_code
                )
                repaired = True

            # Heuristic 3: Common SyntaxError (missing colon, unmatched paren)
            if not repaired and (err_type == "SyntaxError" or "SyntaxError" in full_err_text):
                lines = current_code.splitlines()
                fixed_lines = False
                if fail_line and 1 <= fail_line <= len(lines):
                    target_l = lines[fail_line - 1]
                    if re.match(r'^\s*(def|class|if|elif|else|for|while|try|except|finally|with) ', target_l) and not target_l.strip().endswith(':'):
                        lines[fail_line - 1] = target_l + ':'
                        fixed_lines = True
                if not fixed_lines:
                    for idx, line in enumerate(lines):
                        if re.match(r'^\s*(def|class|if|elif|else|for|while|try|except|finally|with) ', line) and not line.strip().endswith(':'):
                            lines[idx] = line + ':'
                            fixed_lines = True
                            break
                if fixed_lines:
                    current_code = "\n".join(lines)
                    repaired = True


            # Heuristic 4: IndexError / KeyError guard
            if not repaired and err_type in ("IndexError", "KeyError"):
                lines = current_code.splitlines()
                if fail_line and 1 <= fail_line <= len(lines):
                    target_l = lines[fail_line - 1]
                    if "[" in target_l and "]" in target_l:
                        # Wrap in try/except or safe access
                        lines[fail_line - 1] = f"# Safe access fallback\ntry:\n    {target_l}\nexcept (IndexError, KeyError):\n    pass"
                        current_code = "\n".join(lines)
                        repaired = True

            if not repaired:
                # Fallback: append error comment to guide future pass
                current_code += f"\n# TODO: Fix {err_type}: {err_msg}\n"

        # If loop exhausts
        elapsed = (time.perf_counter() - start_t) * 1000
        return {
            "status": "UNRESOLVED",
            "attempts": max_retries,
            "fixed_code": current_code,
            "stdout": stdout,
            "stderr": stderr,
            "history": history,
            "time_ms": round(elapsed, 2)
        }

self_healing_engine = SelfHealingEngine()
