import os
import shutil
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from backend.platform.manifest import PlatformTool, ToolManifest, ToolCategory, RiskLevel, ToolResult
from backend.config import SANDBOX_DIR, BASE_DIR, system_config
from backend.tools.extension_registry import extension_registry

def get_active_sandbox_root() -> Path:
    if system_config.tools.allowed_workspace:
        p = Path(system_config.tools.allowed_workspace)
        if not p.is_absolute():
            p = BASE_DIR / p
        p = p.resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p
    SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
    return SANDBOX_DIR.resolve()

def resolve_safe_sandbox_path(rel_path: str) -> Path:
    root = get_active_sandbox_root()
    clean = rel_path.strip().lstrip('/\\')
    target = (root / clean).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        raise PermissionError(f'Access denied: Path traversal outside sandbox workspace: {rel_path}')
    return target

class FSListTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="fs.list",
            name="Filesystem List",
            category=ToolCategory.FILESYSTEM,
            description="List files and directories within the workspace or sandbox with recursive options.",
            tags=["fs", "filesystem", "list", "dir", "directory", "subpath"],
            risk_level=RiskLevel.READ
        ))

    def get_input_schema(self):
        return {
            "type": "object",
            "properties": {
                "subpath": {"type": "string", "description": "Subdirectory to list (default: root)", "default": ""},
                "directory": {"type": "string", "description": "Alias for subpath", "default": ""},
                "path": {"type": "string", "description": "Alias for subpath", "default": ""},
                "recursive": {"type": "boolean", "description": "List recursively across subdirectories", "default": False}
            }
        }

    async def execute(self, subpath: str = "", directory: str = "", path: str = "", recursive: bool = False, **kwargs) -> ToolResult:
        rel = subpath or directory or path or ""
        root = get_active_sandbox_root()
        if rel in (".", "./", ""):
            target = root
        else:
            target = (root / rel).resolve()
            if not target.exists() and (BASE_DIR / rel).exists():
                target = (BASE_DIR / rel).resolve()
        
        try:
            if not str(target).startswith(str(BASE_DIR.resolve())) and not str(target).startswith(str(root)):
                return ToolResult(success=False, data=None, error="Target path is outside allowed root directory.")
        except Exception:
            return ToolResult(success=False, data=None, error="Target path is outside allowed root directory.")

        if not target.exists():
            return ToolResult(success=False, data=None, error=f"Path '{rel}' does not exist.")

        items = []
        if recursive:
            for p in sorted(target.rglob("*")):
                if any(x in p.parts for x in [".git", "__pycache__"]):
                    continue
                items.append({
                    "name": p.name,
                    "path": str(p.relative_to(target)).replace("\\", "/"),
                    "is_dir": p.is_dir(),
                    "size_bytes": p.stat().st_size if p.is_file() else 0,
                    "extension": p.suffix.lower() if p.is_file() else ""
                })
        else:
            for p in sorted(target.iterdir()):
                items.append({
                    "name": p.name,
                    "path": p.name,
                    "is_dir": p.is_dir(),
                    "size_bytes": p.stat().st_size if p.is_file() else 0,
                    "extension": p.suffix.lower() if p.is_file() else ""
                })
        return ToolResult(success=True, data={"path": str(target), "count": len(items), "items": items})

class FSSearchTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="fs.search",
            name="Filesystem Search",
            category=ToolCategory.FILESYSTEM,
            description="Search for files by glob pattern within the workspace.",
            tags=["fs", "search", "glob", "find"],
            risk_level=RiskLevel.READ
        ))
    def get_input_schema(self):
        return {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Glob pattern (e.g. *.py, *.json)"}
            },
            "required": ["pattern"]
        }
    async def execute(self, pattern: str = "*", **kwargs) -> ToolResult:
        matches = [str(p.relative_to(BASE_DIR)).replace("\\", "/") for p in BASE_DIR.glob(pattern)][:50]
        return ToolResult(success=True, data={"pattern": pattern, "count": len(matches), "matches": matches})

class FSReadTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="fs.read",
            name="Filesystem Read",
            category=ToolCategory.FILESYSTEM,
            description="Read complete file contents safely.",
            tags=["fs", "read", "file"],
            risk_level=RiskLevel.READ
        ))
    def get_input_schema(self):
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to file"}
            },
            "required": ["file_path"]
        }
    async def execute(self, file_path: str = "", **kwargs) -> ToolResult:
        root = get_active_sandbox_root()
        clean = file_path.strip().lstrip("/\\")
        target = (root / clean).resolve()
        if not target.is_file() and (BASE_DIR / clean).is_file():
            target = (BASE_DIR / clean).resolve()

        if not target.is_file():
            return ToolResult(success=False, data=None, error=f"File not found: {file_path}")

        try:
            content = target.read_text(encoding="utf-8", errors="replace")
            ext_info = extension_registry.get_info(str(target))
            return ToolResult(
                success=True,
                data={
                    "file_path": file_path,
                    "content": content,
                    "size_chars": len(content),
                    "extension": ext_info["extension"],
                    "language": ext_info["language"]
                }
            )
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))

class FSCreateTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="fs.create",
            name="Filesystem Create",
            category=ToolCategory.FILESYSTEM,
            description="Create a new file in the sandbox workspace supporting nested directory paths like Antigravity.",
            tags=["fs", "create", "write", "new", "nested", "antigravity"],
            risk_level=RiskLevel.WRITE
        ))
    def get_input_schema(self):
        return {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Filename or relative path inside sandbox (e.g. src/app.ts)"},
                "content": {"type": "string", "description": "Initial text content"}
            },
            "required": ["filename", "content"]
        }
    async def execute(self, filename: str = "", content: str = "", **kwargs) -> ToolResult:
        try:
            target = resolve_safe_sandbox_path(filename)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            root = get_active_sandbox_root()
            ext_info = extension_registry.get_info(str(target))
            return ToolResult(
                success=True,
                data={
                    "created_file": str(target),
                    "relative_path": str(target.relative_to(root)).replace("\\", "/"),
                    "size_bytes": len(content.encode("utf-8")),
                    "extension": ext_info["extension"],
                    "language": ext_info["language"],
                    "category": ext_info["category"]
                }
            )
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))

class FSEditTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="fs.edit",
            name="Filesystem Edit",
            category=ToolCategory.FILESYSTEM,
            description="Edit or overwrite a file in the sandbox workspace supporting nested directory paths.",
            tags=["fs", "edit", "overwrite", "modify", "nested"],
            risk_level=RiskLevel.WRITE
        ))
    def get_input_schema(self):
        return {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Filename or relative path in sandbox"},
                "content": {"type": "string", "description": "Updated file content"}
            },
            "required": ["filename", "content"]
        }
    async def execute(self, filename: str = "", content: str = "", **kwargs) -> ToolResult:
        try:
            target = resolve_safe_sandbox_path(filename)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            root = get_active_sandbox_root()
            ext_info = extension_registry.get_info(str(target))
            return ToolResult(
                success=True,
                data={
                    "edited_file": str(target),
                    "relative_path": str(target.relative_to(root)).replace("\\", "/"),
                    "size_bytes": len(content.encode("utf-8")),
                    "extension": ext_info["extension"]
                }
            )
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))

class FSPatchTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="fs.patch",
            name="Filesystem Patch",
            category=ToolCategory.FILESYSTEM,
            description="Apply string replacement patch to a file in sandbox.",
            tags=["fs", "patch", "replace"],
            risk_level=RiskLevel.WRITE
        ))
    def get_input_schema(self):
        return {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Filename or relative path in sandbox"},
                "target_text": {"type": "string", "description": "Exact text to replace"},
                "replacement_text": {"type": "string", "description": "Replacement text"}
            },
            "required": ["filename", "target_text", "replacement_text"]
        }
    async def execute(self, filename: str = "", target_text: str = "", replacement_text: str = "", **kwargs) -> ToolResult:
        try:
            target = resolve_safe_sandbox_path(filename)
            if not target.is_file():
                root = get_active_sandbox_root()
                if (root / Path(filename).name).is_file():
                    target = root / Path(filename).name
                else:
                    return ToolResult(success=False, data=None, error=f"File not found: {filename}")
            orig = target.read_text(encoding="utf-8")
            if target_text not in orig:
                return ToolResult(success=False, data=None, error="target_text not found in file")
            updated = orig.replace(target_text, replacement_text, 1)
            target.write_text(updated, encoding="utf-8")
            return ToolResult(success=True, data={"patched_file": str(target), "replacements": 1})
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))

class FSBatchCreateTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="fs.batch_create",
            name="Filesystem Batch Create",
            category=ToolCategory.FILESYSTEM,
            description="Create multiple files in batch across nested directories in the sandbox workspace like Antigravity.",
            tags=["fs", "batch", "create", "multi-file", "scaffold", "workspace", "antigravity"],
            risk_level=RiskLevel.WRITE
        ))
    def get_input_schema(self):
        return {
            "type": "object",
            "properties": {
                "files": {
                    "description": "List of {path, content} or dictionary of {path: content} to create in batch",
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Relative file path inside sandbox"},
                            "content": {"type": "string", "description": "File text content"}
                        },
                        "required": ["path", "content"]
                    }
                }
            },
            "required": ["files"]
        }

    async def execute(self, files: Union[List[Dict[str, str]], Dict[str, str]] = None, **kwargs) -> ToolResult:
        if not files:
            return ToolResult(success=False, data=None, error="'files' parameter is required and cannot be empty.")
        
        file_entries = []
        if isinstance(files, dict):
            for path, content in files.items():
                file_entries.append({"path": str(path), "content": str(content)})
        elif isinstance(files, list):
            file_entries = files
        else:
            return ToolResult(success=False, data=None, error="Invalid 'files' format. Must be a list or dict.")

        root = get_active_sandbox_root()
        created_files = []
        ext_summary = {}

        for item in file_entries:
            p_str = item.get("path", "").strip()
            c_str = item.get("content", "")
            if not p_str:
                continue
            try:
                target = resolve_safe_sandbox_path(p_str)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(c_str, encoding="utf-8")
                rel = str(target.relative_to(root)).replace("\\", "/")
                ext_info = extension_registry.get_info(str(target))
                ext = ext_info["extension"]
                ext_summary[ext] = ext_summary.get(ext, 0) + 1
                created_files.append({
                    "path": rel,
                    "size_bytes": len(c_str.encode("utf-8")),
                    "extension": ext,
                    "language": ext_info["language"]
                })
            except Exception as e:
                return ToolResult(success=False, data={"created_so_far": created_files}, error=f"Failed to create '{p_str}': {str(e)}")

        return ToolResult(
            success=True,
            data={
                "created_count": len(created_files),
                "files": created_files,
                "extensions_summary": ext_summary,
                "sandbox_root": str(root)
            }
        )

class FSMkdirTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="fs.mkdir",
            name="Filesystem Make Directory",
            category=ToolCategory.FILESYSTEM,
            description="Create one or more directories / folder structures in the sandbox workspace.",
            tags=["fs", "mkdir", "directory", "folder", "workspace", "antigravity"],
            risk_level=RiskLevel.WRITE
        ))
    def get_input_schema(self):
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path to create relative to sandbox (e.g. src/components)"}
            },
            "required": ["path"]
        }
    async def execute(self, path: str = "", **kwargs) -> ToolResult:
        if not path:
            return ToolResult(success=False, data=None, error="'path' parameter is required.")
        try:
            target = resolve_safe_sandbox_path(path)
            target.mkdir(parents=True, exist_ok=True)
            root = get_active_sandbox_root()
            return ToolResult(success=True, data={"created_dir": str(target), "relative_path": str(target.relative_to(root)).replace("\\", "/")})
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))

class FSTreeTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="fs.tree",
            name="Filesystem Tree",
            category=ToolCategory.FILESYSTEM,
            description="Generate a visual ASCII directory tree of the sandbox workspace with extension statistics.",
            tags=["fs", "tree", "structure", "explorer", "hierarchy", "antigravity"],
            risk_level=RiskLevel.READ
        ))
    def get_input_schema(self):
        return {
            "type": "object",
            "properties": {
                "subpath": {"type": "string", "description": "Subdirectory to build tree from (default: sandbox root)", "default": ""},
                "max_depth": {"type": "integer", "description": "Maximum tree depth", "default": 5}
            }
        }
    async def execute(self, subpath: str = "", max_depth: int = 5, **kwargs) -> ToolResult:
        root = get_active_sandbox_root()
        clean = subpath.strip().lstrip("/\\")
        target = (root / clean).resolve() if clean else root
        if not target.exists():
            return ToolResult(success=False, data=None, error=f"Path '{subpath}' does not exist.")
        
        lines = [f"{target.name}/"]
        def _build_tree(curr: Path, prefix: str = "", depth: int = 0):
            if depth >= max_depth:
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
            }
        )

class FSDeleteTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="fs.delete",
            name="Filesystem Delete",
            category=ToolCategory.FILESYSTEM,
            description="Safely delete a file or directory in the sandbox workspace.",
            tags=["fs", "delete", "remove", "unlink", "workspace"],
            risk_level=RiskLevel.WRITE
        ))
    def get_input_schema(self):
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path to delete inside sandbox"},
                "recursive": {"type": "boolean", "description": "Recursively delete directories", "default": False}
            },
            "required": ["path"]
        }
    async def execute(self, path: str = "", recursive: bool = False, **kwargs) -> ToolResult:
        clean = path.strip().lstrip("/\\")
        if not clean:
            return ToolResult(success=False, data=None, error="Path is required.")
        try:
            target = resolve_safe_sandbox_path(clean)
            root = get_active_sandbox_root()
            if target == root:
                return ToolResult(success=False, data=None, error="Cannot delete the sandbox root directory.")
            if not target.exists():
                return ToolResult(success=False, data=None, error=f"Path '{clean}' not found.")
            
            if target.is_dir():
                if recursive:
                    shutil.rmtree(target)
                else:
                    try:
                        target.rmdir()
                    except OSError:
                        return ToolResult(success=False, data=None, error="Directory is not empty. Set recursive=True to delete.")
            else:
                target.unlink()
            return ToolResult(success=True, data={"deleted_path": clean})
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))

class FSMetadataTool(PlatformTool):
    def __init__(self):
        super().__init__(ToolManifest(
            id="fs.metadata",
            name="Filesystem Metadata",
            category=ToolCategory.FILESYSTEM,
            description="Inspect size, timestamps, extension metadata, and permissions of a file.",
            tags=["fs", "metadata", "stat", "info"],
            risk_level=RiskLevel.READ
        ))
    def get_input_schema(self):
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to file"}
            },
            "required": ["file_path"]
        }
    async def execute(self, file_path: str = "", **kwargs) -> ToolResult:
        clean = file_path.strip().lstrip("/\\")
        root = get_active_sandbox_root()
        target = (root / clean).resolve()
        if not target.exists() and (BASE_DIR / clean).exists():
            target = (BASE_DIR / clean).resolve()

        if not target.exists():
            return ToolResult(success=False, data=None, error="File not found")
        stat = target.stat()
        ext_info = extension_registry.get_info(str(target))
        return ToolResult(success=True, data={
            "file_path": file_path,
            "size_bytes": stat.st_size,
            "modified_time": stat.st_mtime,
            "is_dir": target.is_dir(),
            "extension": ext_info["extension"],
            "language": ext_info["language"],
            "category": ext_info["category"],
            "mime": ext_info["mime"]
        })
