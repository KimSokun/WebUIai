import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional
from backend.platform.manifest import PlatformTool, ToolManifest, ToolCategory, RiskLevel, ToolResult
from backend.config import SANDBOX_DIR, BASE_DIR

class PythonExecuteTool(PlatformTool):
    """
    Executes Python scripts safely inside the isolated workspace sandbox.
    Includes strict timeout guard and stdout/stderr capture.
    """
    def __init__(self):
        super().__init__(ToolManifest(
            id="python_execute",
            name="Python Code Executor",
            category=ToolCategory.PROGRAMMING,
            description="Execute Python code in an isolated sandbox to run algorithms, verify tests, and check outputs.",
            tags=["python", "execute", "run", "code", "programming", "script"],
            risk_level=RiskLevel.OWNER_ONLY,
            requires_owner_auth=True,
            timeout_seconds=15.0
        ))

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "The complete Python code string to execute"},
                "timeout_seconds": {"type": "number", "description": "Max execution time in seconds (default: 5.0)", "default": 5.0},
                "filename": {"type": "string", "description": "Optional script name (default: run_sandbox.py)", "default": "run_sandbox.py"}
            },
            "required": ["code"]
        }

    async def execute(self, code: str = "", timeout_seconds: float = 5.0, filename: str = "run_sandbox.py", **kwargs) -> ToolResult:
        start_time = time.time()
        if not code or not code.strip():
            return ToolResult(success=False, data=None, error="Code string cannot be empty.")

        # Cap timeout between 1.0s and 15.0s
        timeout = max(1.0, min(15.0, float(timeout_seconds)))
        clean_filename = Path(filename).name
        script_path = SANDBOX_DIR / clean_filename

        try:
            # Sanitize and normalize code string
            clean_code = code.strip()
            # Strip markdown code fences if present
            if clean_code.startswith("```"):
                fenced_lines = clean_code.splitlines()
                if fenced_lines[0].startswith("```"):
                    fenced_lines = fenced_lines[1:]
                if fenced_lines and fenced_lines[-1].strip() == "```":
                    fenced_lines = fenced_lines[:-1]
                clean_code = "\n".join(fenced_lines)

            # Unescape literal escaped newlines/tabs from JSON or raw payloads
            if "\\n" in clean_code:
                clean_code = clean_code.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\t", "    ")

            # Convert bare scratch math expressions (e.g., "37 * 2 = 74") into comments so they don't break Python
            import re
            sanitized_lines = []
            for line in clean_code.split("\n"):
                stripped = line.strip()
                if re.match(r'^\d+[\s\+\-\*\/\%]+\d+\s*=\s*\d+', stripped):
                    sanitized_lines.append(f"# Math note: {stripped}")
                else:
                    sanitized_lines.append(line)
            clean_code = "\n".join(sanitized_lines)

            # Write script to sandbox
            script_path.write_text(clean_code, encoding="utf-8")

            # Execute with active Python interpreter in isolated subprocess
            python_exe = sys.executable
            proc = subprocess.run(
                [python_exe, clean_filename],
                cwd=str(SANDBOX_DIR),
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace"
            )

            elapsed_ms = (time.time() - start_time) * 1000
            success = (proc.returncode == 0)
            
            output_data = {
                "exit_code": proc.returncode,
                "stdout": proc.stdout.strip(),
                "stderr": proc.stderr.strip(),
                "execution_time_ms": round(elapsed_ms, 2),
                "script_path": str(script_path.relative_to(BASE_DIR)).replace("\\", "/")
            }

            return ToolResult(
                success=success,
                data=output_data,
                error=proc.stderr.strip() if not success else None,
                execution_time_ms=elapsed_ms
            )

        except subprocess.TimeoutExpired:
            elapsed_ms = (time.time() - start_time) * 1000
            return ToolResult(
                success=False,
                data=None,
                error=f"Execution timed out after {timeout} seconds (infinite loop or hang prevented).",
                execution_time_ms=elapsed_ms
            )
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            return ToolResult(
                success=False,
                data=None,
                error=f"Sandbox execution error: {str(e)}",
                execution_time_ms=elapsed_ms
            )

python_executor_tool = PythonExecuteTool()
