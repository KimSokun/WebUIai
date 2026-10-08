import os
import sys
import shutil
import platform
import subprocess
from typing import Dict, Any
from backend.platform.manifest import PlatformTool, ToolManifest, ToolCategory, RiskLevel, ToolResult
from backend.config import SANDBOX_DIR

class TerminalDetectTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="terminal.detect",
            name="Terminal Shell Detect",
            category=ToolCategory.TERMINAL,
            description="Detect available system shells and terminal runtimes on the host machine.",
            tags=["terminal", "shell", "powershell", "cmd", "bash", "detect"],
            risk_level=RiskLevel.READ
        ))
    def get_input_schema(self):
        return {"type": "object", "properties": {}}
    async def execute(self, **kwargs) -> ToolResult:
        shells = {
            "os": platform.system(),
            "powershell": shutil.which("powershell.exe") is not None or shutil.which("pwsh") is not None,
            "cmd": shutil.which("cmd.exe") is not None,
            "bash": shutil.which("bash") is not None,
            "python": sys.executable
        }
        return ToolResult(success=True, data=shells)

class TerminalPowershellTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="terminal.powershell",
            name="Guarded PowerShell Execution",
            category=ToolCategory.TERMINAL,
            description="Executes guarded read-only PowerShell diagnostics in sandbox.",
            tags=["terminal", "powershell", "ps1", "execute"],
            risk_level=RiskLevel.OWNER_ONLY,
            requires_owner_auth=True,
            timeout_seconds=10.0
        ))
    def get_input_schema(self):
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "PowerShell command to execute"}
            },
            "required": ["command"]
        }
    async def execute(self, command: str = "", **kwargs) -> ToolResult:
        # Block dangerous or destructive operations
        forbidden = ["rmdir", "del ", "rm ", "format", "shutdown", "stop-process", "reg "]
        if any(f in command.lower() for f in forbidden):
            return ToolResult(success=False, data=None, error="Command rejected by Guarded Terminal policy.")
        try:
            res = subprocess.run(
                ["powershell", "-Command", command],
                cwd=str(SANDBOX_DIR),
                capture_output=True,
                text=True,
                timeout=8.0
            )
            return ToolResult(success=res.returncode == 0, data={
                "stdout": res.stdout.strip(),
                "stderr": res.stderr.strip(),
                "exit_code": res.returncode
            }, error=res.stderr.strip() if res.returncode != 0 else None)
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))

class TerminalCmdTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="terminal.cmd",
            name="Guarded CMD Execution",
            category=ToolCategory.TERMINAL,
            description="Executes guarded CMD diagnostics in sandbox with strict owner policy.",
            tags=["terminal", "cmd", "batch", "execute"],
            risk_level=RiskLevel.OWNER_ONLY,
            requires_owner_auth=True,
            timeout_seconds=10.0
        ))
    def get_input_schema(self):
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "CMD command to execute"}
            },
            "required": ["command"]
        }
    async def execute(self, command: str = "", **kwargs) -> ToolResult:
        forbidden = ["rmdir", "del ", "format", "shutdown", "reg "]
        if any(f in command.lower() for f in forbidden):
            return ToolResult(success=False, data=None, error="Command rejected by Guarded Terminal policy.")
        try:
            res = subprocess.run(
                ["cmd.exe", "/c", command],
                cwd=str(SANDBOX_DIR),
                capture_output=True,
                text=True,
                timeout=8.0
            )
            return ToolResult(success=res.returncode == 0, data={
                "stdout": res.stdout.strip(),
                "stderr": res.stderr.strip(),
                "exit_code": res.returncode
            }, error=res.stderr.strip() if res.returncode != 0 else None)
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))

class TerminalEnvironmentTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="terminal.environment",
            name="Sanitized Environment Inspection",
            category=ToolCategory.TERMINAL,
            description="Inspects host environment variables with strict redaction of sensitive credentials.",
            tags=["terminal", "environment", "env", "variables"],
            risk_level=RiskLevel.READ
        ))
    def get_input_schema(self):
        return {"type": "object", "properties": {}}
    async def execute(self, **kwargs) -> ToolResult:
        sensitive_keywords = ["key", "secret", "token", "password", "pass", "cred", "auth", "cert"]
        sanitized = {}
        for k, v in os.environ.items():
            k_lower = k.lower()
            if any(s in k_lower for s in sensitive_keywords):
                sanitized[k] = "[REDACTED_SECRET]"
            else:
                sanitized[k] = v
        return ToolResult(success=True, data={"count": len(sanitized), "variables": sanitized})
