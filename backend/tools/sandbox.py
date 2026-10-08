import os
import time
import base64
import shutil
from pathlib import Path
from typing import Any, Dict, List, Union
from backend.tools.base import BaseTool, ToolResult
from backend.config import WORKSPACE_DIR, SANDBOX_DIR, BASE_DIR, system_config
from backend.tools.extension_registry import extension_registry

class LocalFilesSandboxTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="local_files",
            description="Read, list, write, batch-write, inspect tree, or manage files and directories inside the sandbox workspace like Antigravity.",
            risk_level="HIGH",
            requires_confirmation=False
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "read", "write", "batch_write", "mkdir", "tree", "info", "delete"],
                    "description": "Action to perform in sandbox"
                },
                "filename": {"type": "string", "description": "Relative path to target file/folder inside sandbox"},
                "content": {"type": "string", "description": "File content for write action"},
                "files": {
                    "description": "List or dictionary of {path: content} for batch_write action",
                    "type": "array"
                },
                "is_base64": {"type": "boolean", "description": "Set to True if content is base64 encoded binary data", "default": False},
                "recursive": {"type": "boolean", "description": "Whether action (list/delete) should be recursive", "default": False}
            },
            "required": ["action"]
        }

    def _get_sandbox_root(self) -> Path:
        """
        Returns the active isolated sandbox root directory.
        When online_sandbox_strict_mode is True, locks strictly to allowed_workspace or SANDBOX_DIR.
        """
        if system_config.tools.online_sandbox_strict_mode:
            root = Path(system_config.tools.allowed_workspace) if system_config.tools.allowed_workspace else SANDBOX_DIR
            if not root.is_absolute():
                root = BASE_DIR / root
            root.mkdir(parents=True, exist_ok=True)
            return root
        return WORKSPACE_DIR

    def _resolve_and_validate(self, relative_path: str) -> Path:
        """
        Ensures target path cannot escape the active sandbox directory.
        Blocks directory traversal attacks ('..', '/..', '\..', absolute OS paths, root paths).
        """
        root = self._get_sandbox_root().resolve()
        raw_path = Path(relative_path.strip())

        # If an absolute path or leading slash is provided, check if it is within root
        if raw_path.is_absolute() or relative_path.strip().startswith(("/", "\\")):
            try:
                target = raw_path.resolve()
                target.relative_to(root)
                return target
            except ValueError:
                raise PermissionError(f"Security Alert: Path traversal blocked. Access outside sandbox '{root}' is forbidden.")

        clean_rel = relative_path.strip().lstrip("/\\")
        target = (root / clean_rel).resolve()
        
        # Check that target is strictly a child of root
        try:
            target.relative_to(root)
        except ValueError:
            raise PermissionError(f"Security Alert: Path traversal blocked. Access outside sandbox '{root}' is forbidden.")

        return target

    async def execute(
        self,
        action: str = "list",
        filename: str = "",
        content: str = "",
        files: Union[List[Dict[str, str]], Dict[str, str]] = None,
        is_base64: bool = False,
        recursive: bool = False,
        **kwargs
    ) -> ToolResult:
        if not system_config.tools.local_files_enabled:
            return ToolResult(success=False, data=None, error="Local file sandbox is disabled by Owner policy.")

        start_time = time.time()
        try:
            root = self._get_sandbox_root()

            # 1. LIST
            if action == "list":
                if not system_config.tools.sandbox_read_enabled:
                    return ToolResult(
                        success=False,
                        data=None,
                        error="Security Alert: Sandbox READ permission is disabled by Owner policy."
                    )
                target_dir = self._resolve_and_validate(filename) if filename else root
                if not target_dir.exists():
                    return ToolResult(success=False, data=None, error=f"Path '{filename}' does not exist.")

                file_list = []
                scan_iter = target_dir.rglob("*") if recursive else target_dir.iterdir()
                for p in sorted(scan_iter):
                    if any(x in p.parts for x in [".git", "__pycache__"]):
                        continue
                    if p.is_file():
                        ext_info = extension_registry.get_info(str(p))
                        file_list.append({
                            "name": p.name,
                            "path": str(p.relative_to(root)).replace("\\", "/"),
                            "size": p.stat().st_size,
                            "extension": ext_info["extension"],
                            "language": ext_info["language"],
                            "is_dir": False
                        })
                    elif p.is_dir():
                        file_list.append({
                            "name": p.name,
                            "path": str(p.relative_to(root)).replace("\\", "/"),
                            "is_dir": True
                        })
                return ToolResult(
                    success=True,
                    data={"sandbox_root": str(root), "files": file_list, "count": len(file_list)},
                    execution_time_ms=(time.time() - start_time) * 1000
                )

            # 2. READ
            elif action == "read":
                if not system_config.tools.sandbox_read_enabled:
                    return ToolResult(
                        success=False,
                        data=None,
                        error="Security Alert: Sandbox READ permission is disabled by Owner policy."
                    )
                if not filename:
                    return ToolResult(success=False, data=None, error="Filename is required for read action.")
                target = self._resolve_and_validate(filename)
                if not target.exists() or not target.is_file():
                    err_struct = {
                        "success": False,
                        "tool": "local_files",
                        "error_code": "FILE_NOT_FOUND",
                        "message": f"File '{filename}' not found."
                    }
                    return ToolResult(
                        success=False,
                        data=err_struct,
                        error=f"FILE_NOT_FOUND: File '{filename}' not found.",
                        execution_time_ms=(time.time() - start_time) * 1000
                    )
                
                ext_info = extension_registry.get_info(str(target))
                if ext_info["is_binary"]:
                    raw_bytes = target.read_bytes()
                    b64 = base64.b64encode(raw_bytes).decode("utf-8")
                    return ToolResult(
                        success=True,
                        data={
                            "filename": filename,
                            "is_binary": True,
                            "content_base64": b64,
                            "size_bytes": len(raw_bytes),
                            "extension": ext_info["extension"],
                            "mime": ext_info["mime"]
                        },
                        execution_time_ms=(time.time() - start_time) * 1000
                    )
                else:
                    text = target.read_text(encoding="utf-8", errors="replace")
                    return ToolResult(
                        success=True,
                        data={
                            "filename": filename,
                            "content": text,
                            "size_bytes": len(text.encode("utf-8")),
                            "extension": ext_info["extension"],
                            "language": ext_info["language"]
                        },
                        execution_time_ms=(time.time() - start_time) * 1000
                    )

            # 3. WRITE
            elif action == "write":
                if not system_config.tools.sandbox_write_enabled:
                    return ToolResult(
                        success=False,
                        data=None,
                        error="Security Alert: Sandbox WRITE permission is disabled by Owner policy."
                    )
                if not filename:
                    return ToolResult(success=False, data=None, error="Filename is required for write action.")
                target = self._resolve_and_validate(filename)
                target.parent.mkdir(parents=True, exist_ok=True)
                if is_base64:
                    raw_bytes = base64.b64decode(content)
                    target.write_bytes(raw_bytes)
                    bytes_written = len(raw_bytes)
                else:
                    target.write_text(content, encoding="utf-8")
                    bytes_written = len(content.encode("utf-8"))

                ext_info = extension_registry.get_info(str(target))
                return ToolResult(
                    success=True,
                    data={
                        "filename": filename,
                        "relative_path": str(target.relative_to(root)).replace("\\", "/"),
                        "bytes_written": bytes_written,
                        "extension": ext_info["extension"],
                        "language": ext_info["language"],
                        "category": ext_info["category"]
                    },
                    execution_time_ms=(time.time() - start_time) * 1000
                )

            # 4. BATCH_WRITE (Antigravity-Grade Multi-File Scaffolding)
            elif action in ["batch_write", "batch_create"]:
                if not system_config.tools.sandbox_write_enabled:
                    return ToolResult(
                        success=False,
                        data=None,
                        error="Security Alert: Sandbox WRITE permission is disabled by Owner policy."
                    )
                if not files:
                    return ToolResult(success=False, data=None, error="'files' parameter is required for batch_write.")

                file_entries = []
                if isinstance(files, dict):
                    for p, c in files.items():
                        file_entries.append({"path": str(p), "content": str(c)})
                elif isinstance(files, list):
                    file_entries = files
                else:
                    return ToolResult(success=False, data=None, error="Invalid files format.")

                created = []
                ext_summary = {}
                for entry in file_entries:
                    p_str = entry.get("path") or entry.get("filename") or ""
                    c_str = entry.get("content", "")
                    if not p_str:
                        continue
                    tgt = self._resolve_and_validate(p_str)
                    tgt.parent.mkdir(parents=True, exist_ok=True)
                    tgt.write_text(c_str, encoding="utf-8")
                    rel = str(tgt.relative_to(root)).replace("\\", "/")
                    ext_info = extension_registry.get_info(str(tgt))
                    ext = ext_info["extension"]
                    ext_summary[ext] = ext_summary.get(ext, 0) + 1
                    created.append({
                        "path": rel,
                        "size_bytes": len(c_str.encode("utf-8")),
                        "extension": ext,
                        "language": ext_info["language"]
                    })

                return ToolResult(
                    success=True,
                    data={
                        "created_count": len(created),
                        "files": created,
                        "extensions_summary": ext_summary,
                        "sandbox_root": str(root)
                    },
                    execution_time_ms=(time.time() - start_time) * 1000
                )

            # 5. MKDIR
            elif action == "mkdir":
                if not system_config.tools.sandbox_write_enabled:
                    return ToolResult(
                        success=False,
                        data=None,
                        error="Security Alert: Sandbox WRITE permission is disabled by Owner policy."
                    )
                if not filename:
                    return ToolResult(success=False, data=None, error="Directory path (filename) is required.")
                target = self._resolve_and_validate(filename)
                target.mkdir(parents=True, exist_ok=True)
                return ToolResult(
                    success=True,
                    data={"created_directory": str(target), "relative_path": str(target.relative_to(root)).replace("\\", "/")},
                    execution_time_ms=(time.time() - start_time) * 1000
                )

            # 6. TREE
            elif action == "tree":
                if not system_config.tools.sandbox_read_enabled:
                    return ToolResult(
                        success=False,
                        data=None,
                        error="Security Alert: Sandbox READ permission is disabled by Owner policy."
                    )
                target = self._resolve_and_validate(filename) if filename else root
                if not target.exists():
                    return ToolResult(success=False, data=None, error=f"Path '{filename}' not found.")
                
                lines = [f"{target.name}/"]
                def _build_tree(curr: Path, prefix: str = "", depth: int = 0):
                    if depth >= 5:
                        return
                    entries = sorted(list(curr.iterdir()), key=lambda e: (not e.is_dir(), e.name.lower()))
                    for i, entry in enumerate(entries):
                        if any(x in entry.parts for x in [".git", "__pycache__"]):
                            continue
                        is_last = (i == len(entries) - 1)
                        connector = "└── " if is_last else "├── "
                        sub_prefix = "    " if is_last else "│   "
                        if entry.is_dir():
                            lines.append(f"{prefix}{connector}{entry.name}/")
                            _build_tree(entry, prefix + sub_prefix, depth + 1)
                        else:
                            size_kb = round(entry.stat().st_size / 1024, 2)
                            lines.append(f"{prefix}{connector}{entry.name} ({size_kb} KB)")

                _build_tree(target)
                summary = extension_registry.summarize_directory(target)
                return ToolResult(
                    success=True,
                    data={
                        "tree": "\n".join(lines),
                        "total_files": summary["total_files"],
                        "total_bytes": summary["total_bytes"],
                        "extension_breakdown": summary["extension_breakdown"]
                    },
                    execution_time_ms=(time.time() - start_time) * 1000
                )

            # 7. INFO / STAT
            elif action in ["info", "stat"]:
                if not filename:
                    return ToolResult(success=False, data=None, error="Filename is required for info action.")
                target = self._resolve_and_validate(filename)
                if not target.exists():
                    return ToolResult(success=False, data=None, error=f"File '{filename}' not found.")
                st = target.stat()
                ext_info = extension_registry.get_info(str(target))
                line_count = 0
                if not ext_info["is_binary"] and target.is_file():
                    try:
                        line_count = len(target.read_text(encoding="utf-8", errors="replace").splitlines())
                    except Exception:
                        pass
                return ToolResult(
                    success=True,
                    data={
                        "filename": filename,
                        "relative_path": str(target.relative_to(root)).replace("\\", "/"),
                        "size_bytes": st.st_size,
                        "line_count": line_count,
                        "is_dir": target.is_dir(),
                        "modified_time": st.st_mtime,
                        "extension": ext_info["extension"],
                        "language": ext_info["language"],
                        "category": ext_info["category"],
                        "mime": ext_info["mime"]
                    },
                    execution_time_ms=(time.time() - start_time) * 1000
                )

            # 8. DELETE
            elif action == "delete":
                if not system_config.tools.sandbox_write_enabled:
                    return ToolResult(
                        success=False,
                        data=None,
                        error="Security Alert: Sandbox WRITE permission is disabled by Owner policy."
                    )
                if not filename:
                    return ToolResult(success=False, data=None, error="Filename is required for delete action.")
                target = self._resolve_and_validate(filename)
                if target == root:
                    return ToolResult(success=False, data=None, error="Cannot delete the sandbox root directory.")
                if not target.exists():
                    return ToolResult(success=False, data=None, error=f"File '{filename}' not found.")
                
                if target.is_dir():
                    if recursive:
                        shutil.rmtree(target)
                    else:
                        target.rmdir()
                else:
                    target.unlink()
                return ToolResult(
                    success=True,
                    data={"deleted_path": filename},
                    execution_time_ms=(time.time() - start_time) * 1000
                )

            else:
                return ToolResult(success=False, data=None, error=f"Unknown action '{action}'")

        except PermissionError as pe:
            return ToolResult(
                success=False,
                data=None,
                error=str(pe),
                execution_time_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"Filesystem error: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000
            )
