import os
import shutil
import subprocess
import signal
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from backend.config import BASE_DIR, MODELS_DIR, system_config, save_config

def resolve_model_path(model_path_str: Optional[str]) -> Path:
    """Resolves a model path to an absolute Path, supporting relative ./models paths and auto-relocation."""
    if not model_path_str:
        return MODELS_DIR
    p = Path(model_path_str)
    if not p.is_absolute():
        return (BASE_DIR / p).resolve()
    if not p.exists():
        # Auto-relocate if the model exists in the local MODELS_DIR
        local_cand = MODELS_DIR / p.name
        if local_cand.exists():
            return local_cand.resolve()
    return p.resolve()

class ModelsManager:
    def __init__(self):
        self._server_process: Optional[subprocess.Popen] = None
        self._job_object = self._create_job_object()
        self._find_llama_binaries()

    def _create_job_object(self):
        if os.name != "nt":
            return None
        try:
            import ctypes
            from ctypes import wintypes

            class IO_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ('ReadOperationCount', ctypes.c_uint64),
                    ('WriteOperationCount', ctypes.c_uint64),
                    ('OtherOperationCount', ctypes.c_uint64),
                    ('ReadTransferCount', ctypes.c_uint64),
                    ('WriteTransferCount', ctypes.c_uint64),
                    ('OtherTransferCount', ctypes.c_uint64),
                ]

            class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
                _fields_ = [
                    ('PerProcessUserTimeLimit', ctypes.c_int64),
                    ('PerJobUserTimeLimit', ctypes.c_int64),
                    ('LimitFlags', wintypes.DWORD),
                    ('MinimumWorkingSetSize', ctypes.c_size_t),
                    ('MaximumWorkingSetSize', ctypes.c_size_t),
                    ('ActiveProcessLimit', wintypes.DWORD),
                    ('Affinity', ctypes.c_size_t),
                    ('PriorityClass', wintypes.DWORD),
                    ('SchedulingClass', wintypes.DWORD),
                ]

            class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
                _fields_ = [
                    ('BasicLimitInformation', JOBOBJECT_BASIC_LIMIT_INFORMATION),
                    ('IoInfo', IO_COUNTERS),
                    ('ProcessMemoryLimit', ctypes.c_size_t),
                    ('JobMemoryLimit', ctypes.c_size_t),
                    ('PeakProcessMemoryLimit', ctypes.c_size_t),
                    ('PeakJobMemoryLimit', ctypes.c_size_t),
                ]

            JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
            JobObjectExtendedLimitInformation = 9

            job = ctypes.windll.kernel32.CreateJobObjectW(None, None)
            if not job:
                return None

            info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
            info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE

            res = ctypes.windll.kernel32.SetInformationJobObject(
                job,
                JobObjectExtendedLimitInformation,
                ctypes.byref(info),
                ctypes.sizeof(info)
            )
            if not res:
                ctypes.windll.kernel32.CloseHandle(job)
                return None
            return job
        except Exception:
            return None

    def _assign_process_to_job(self, proc_handle):
        if not self._job_object or os.name != "nt":
            return False
        try:
            import ctypes
            return bool(ctypes.windll.kernel32.AssignProcessToJobObject(self._job_object, proc_handle))
        except Exception:
            return False

    def _find_llama_binaries(self) -> Optional[Path]:
        candidates = [
            BASE_DIR / "bin" / "llama-server.exe",
            BASE_DIR / "bin" / "llama-server",
            BASE_DIR / "bin" / "llamafile.exe",
            BASE_DIR / "bin" / "llamafile",
            BASE_DIR / "llama-server.exe",
            BASE_DIR / "llamafile.exe",
            MODELS_DIR.parent / "bin" / "llama-server.exe",
            MODELS_DIR.parent / "bin" / "llamafile.exe",
            MODELS_DIR.parent / "llamafile.exe",
            Path("C:/llama.cpp/llama-server.exe")
        ]
        for c in candidates:
            if c.exists() and c.is_file():
                return c.resolve()
        for b_name in ["llama-server.exe", "llama-server", "llamafile.exe", "llamafile"]:
            found = shutil.which(b_name)
            if found:
                return Path(found).resolve()
        return None

    def find_mmproj_for_model(self, model_path: str) -> Optional[Path]:
        """Find corresponding multimodal projector (.gguf) for a vision model."""
        m_path = Path(model_path)
        m_name = m_path.name.lower()
        if not MODELS_DIR.exists():
            return None

        all_mmprojs = [p for p in MODELS_DIR.glob("*mmproj*.gguf") if not p.name.endswith(".tmp")]
        if not all_mmprojs:
            return None

        # 1. Family-specific matching
        if "gemma-3" in m_name or "gemma_3" in m_name or "gemma" in m_name:
            for p in all_mmprojs:
                if "gemma" in p.name.lower():
                    return p
        if "paligemma" in m_name:
            for p in all_mmprojs:
                if "paligemma" in p.name.lower():
                    return p
        if "qwen" in m_name and "vl" in m_name:
            for p in all_mmprojs:
                if "qwen" in p.name.lower():
                    return p

        # 2. Direct stem matching
        for p in all_mmprojs:
            if m_path.stem.lower() in p.name.lower():
                return p

        # 3. Fallback: single mmproj for any vision-capable model
        if len(all_mmprojs) == 1 and any(v in m_name for v in ["gemma", "vl", "vision", "pali", "llava"]):
            return all_mmprojs[0]

        return None

    def scan_models(self) -> List[Dict[str, Any]]:
        """
        Scans MODELS_DIR for all .gguf files (filtering out standalone projectors).
        """
        active_resolved = resolve_model_path(system_config.model.model_path)
        # If currently configured model does not exist on disk, auto-select first available
        if not active_resolved.exists():
            ggufs = [g for g in MODELS_DIR.glob("*.gguf") if not g.name.lower().startswith("mmproj") and not g.name.endswith(".tmp")]
            if ggufs:
                system_config.model.model_path = f"./models/{ggufs[0].name}"
                system_config.model.model_name = ggufs[0].stem
                save_config(system_config)
                active_resolved = ggufs[0].resolve()

        models = []
        if MODELS_DIR.exists():
            for p in sorted(MODELS_DIR.glob("*.gguf")):
                if p.name.lower().startswith("mmproj") or p.name.endswith(".tmp"):
                    continue

                size_bytes = p.stat().st_size
                size_gb = round(size_bytes / (1024 ** 3), 2)
                size_mb = round(size_bytes / (1024 ** 2), 1)
                
                # Deduce quantization from name
                name_upper = p.stem.upper()
                quant = "Unknown"
                for q in ["Q4_K_M", "Q5_K_M", "Q8_0", "Q4_0", "Q5_0", "Q6_K", "F16"]:
                    if q in name_upper:
                        quant = q
                        break

                mmproj_match = self.find_mmproj_for_model(str(p.resolve()))
                is_active = (
                    p.name == Path(system_config.model.model_path).name or
                    str(p.resolve()) == str(active_resolved)
                )

                models.append({
                    "filename": p.name,
                    "path": f"./models/{p.name}",
                    "absolute_path": str(p.resolve()),
                    "size_gb": size_gb,
                    "size_mb": size_mb,
                    "quantization": quant,
                    "has_vision": bool(mmproj_match),
                    "mmproj_filename": mmproj_match.name if mmproj_match else None,
                    "is_active": is_active
                })

        return models

    def select_model(self, model_filename: str) -> Dict[str, Any]:
        target = MODELS_DIR / model_filename
        if not target.exists() or not target.is_file():
            target_gguf = MODELS_DIR / f"{model_filename}.gguf"
            if target_gguf.exists() and target_gguf.is_file():
                target = target_gguf
            else:
                raise FileNotFoundError(f"Model file '{model_filename}' not found in {MODELS_DIR}")
        
        system_config.model.model_path = f"./models/{target.name}"
        system_config.model.model_name = target.stem
        save_config(system_config)
        return {
            "success": True,
            "active_model": system_config.model.model_name,
            "model_path": system_config.model.model_path
        }

    def is_server_listening(self, host: str = "127.0.0.1", port: int = 8080) -> bool:
        """Fast non-blocking TCP socket check to verify if llama-server is listening (<5ms)."""
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.15)
                return s.connect_ex((host, port)) == 0
        except Exception:
            return False

    def get_server_status(self) -> Dict[str, Any]:
        binary = self._find_llama_binaries()
        is_running = self.is_server_listening()
        if not is_running and self._server_process:
            is_running = (self._server_process.poll() is None)

        return {
            "llama_binary_found": bool(binary),
            "llama_binary_path": str(binary) if binary else None,
            "server_running": is_running,
            "is_listening": self.is_server_listening(),
            "models_dir": str(MODELS_DIR),
            "models_count": len(list(MODELS_DIR.glob("*.gguf"))),
            "active_model_path": system_config.model.model_path
        }

    def start_llama_server(self, model_path: Optional[str] = None) -> Dict[str, Any]:
        if self.is_server_listening():
            return {
                "success": True,
                "message": "llama-server is already active and healthy on port 8080",
                "listening": True
            }

        binary = self._find_llama_binaries()
        if not binary:
            return {"success": False, "error": "llama-server.exe not found on system."}

        target_model = model_path or system_config.model.model_path
        target_path = resolve_model_path(target_model)
        if not target_path.exists():
            ggufs = list(MODELS_DIR.glob("*.gguf"))
            if ggufs:
                target_path = ggufs[0].resolve()
                system_config.model.model_path = f"./models/{ggufs[0].name}"
                system_config.model.model_name = ggufs[0].stem
                save_config(system_config)
            else:
                return {
                    "success": False,
                    "error": f"No .gguf model found in '{MODELS_DIR}'. Please place your K-Jocker .gguf file there."
                }

        self.stop_llama_server()

        # Auto-detect multimodal projector for Vision models
        mmproj_file = self.find_mmproj_for_model(str(target_path))
        has_vision = bool(mmproj_file and mmproj_file.exists())

        # Multimodal vision models require significant RAM for KV cache & image graph tensors.
        # Cap slot context to 16,384 when mmproj is attached to prevent Windows RAM exhaustion (OOM crash)
        ctx_len = system_config.model.context_length
        if has_vision:
            ctx_len = min(ctx_len, 16384)

        cmd = [
            str(binary),
            "-m", str(target_path),
            "-c", str(ctx_len),
            "-np", "1",
            "-t", str(system_config.model.threads),
            "--port", "8080",
            "--host", "127.0.0.1",
            "--jinja",
            "-fa", "on",
            "-b", "2048",
            "-ub", "1024",
            "-tb", str(system_config.model.threads),
            "--cache-reuse", "256"
        ]
        if system_config.model.gpu_layers > 0:
            cmd.extend(["-ngl", str(system_config.model.gpu_layers)])

        if has_vision:
            cmd.extend(["--mmproj", str(mmproj_file.resolve())])
            print(f"[K-Jocker] Multimodal Projector linked: '{mmproj_file.name}' (Context: {ctx_len}, Slots: 1). Vision enabled.")

        try:
            log_file = open(MODELS_DIR.parent / "llama_server.log", "a", encoding="utf-8")
            creation_flags = 0
            if os.name == "nt":
                DETACHED_PROCESS = 0x00000008
                creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS

            self._server_process = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=log_file,
                cwd=str(binary.parent),
                creationflags=creation_flags
            )
            # Assign to Windows Job Object so child process terminates if parent exits
            if self._job_object and hasattr(self._server_process, "_handle"):
                self._assign_process_to_job(int(self._server_process._handle))

            return {
                "success": True,
                "message": f"llama-server started with model '{Path(target_model).name}' on port 8080",
                "pid": self._server_process.pid
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to start llama-server: {str(e)}"}

    def stop_llama_server(self) -> Dict[str, Any]:
        stopped = False
        if self._server_process and self._server_process.poll() is None:
            try:
                self._server_process.terminate()
                self._server_process.wait(timeout=2)
            except Exception:
                self._server_process.kill()
            self._server_process = None
            stopped = True

        # Ensure any orphan llama-server.exe or llamafile.exe process is terminated on Windows
        if os.name == "nt":
            for proc_name in ["llama-server.exe", "llamafile.exe"]:
                try:
                    res = subprocess.run(
                        ["taskkill", "/F", "/IM", proc_name],
                        capture_output=True,
                        text=True
                    )
                    if res.returncode == 0:
                        stopped = True
                except Exception:
                    pass

        return {
            "success": True,
            "message": "llama-server stopped" if stopped else "llama-server was not running"
        }

    def delete_model(self, filename: str) -> Dict[str, Any]:
        target = MODELS_DIR / filename
        if not target.exists() or not target.is_file():
            raise FileNotFoundError(f"Model file '{filename}' not found in '{MODELS_DIR}'")

        # Stop server if currently active/listening to release file lock
        self.stop_llama_server()
        import time
        time.sleep(0.6)

        is_active = (
            target.stem == system_config.model.model_name or
            target.name == Path(system_config.model.model_path).name or
            str(target.resolve()) == str(resolve_model_path(system_config.model.model_path)) or
            filename == system_config.model.model_name
        )
        try:
            target.unlink()
            if is_active:
                remaining = [p for p in MODELS_DIR.glob("*.gguf") if p.name != filename]
                if remaining:
                    self.select_model(remaining[0].name)
            return {
                "success": True,
                "message": f"Model '{filename}' deleted successfully.",
                "remaining_models": [m["filename"] for m in self.scan_models()]
            }
        except PermissionError as pe:
            # If still locked, force kill and retry once
            if os.name == "nt":
                for proc_name in ["llama-server.exe", "llamafile.exe"]:
                    subprocess.run(["taskkill", "/F", "/IM", proc_name], capture_output=True)
                time.sleep(0.8)
                target.unlink()
                if is_active:
                    remaining = [p for p in MODELS_DIR.glob("*.gguf") if p.name != filename]
                    if remaining:
                        self.select_model(remaining[0].name)
                return {
                    "success": True,
                    "message": f"Model '{filename}' deleted successfully after releasing lock.",
                    "remaining_models": [m["filename"] for m in self.scan_models()]
                }
            raise pe

models_manager = ModelsManager()
