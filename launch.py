import os
import sys
import time
import signal
import atexit
import subprocess
import webbrowser
from pathlib import Path

# Add current folder to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

def auto_kill_llama():
    """Guarantees both llama-server.exe and llamafile.exe are terminated on exit."""
    if sys.platform == "win32":
        for proc in ["llama-server.exe", "llamafile.exe"]:
            try:
                subprocess.run(["taskkill", "/F", "/IM", proc], capture_output=True)
            except Exception:
                pass

# Register atexit handler
atexit.register(auto_kill_llama)

# Register Windows console close handler (X button on console window)
if sys.platform == "win32":
    try:
        import ctypes
        from ctypes import wintypes

        PHANDLER_ROUTINE = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.DWORD)

        def _console_ctrl_handler(dwCtrlType):
            auto_kill_llama()
            return False

        _global_handler = PHANDLER_ROUTINE(_console_ctrl_handler)
        ctypes.windll.kernel32.SetConsoleCtrlHandler(_global_handler, True)
    except Exception:
        pass

# Register standard POSIX/Python signal handlers
try:
    signal.signal(signal.SIGINT, lambda s, f: (auto_kill_llama(), sys.exit(0)))
    signal.signal(signal.SIGTERM, lambda s, f: (auto_kill_llama(), sys.exit(0)))
except Exception:
    pass

def open_browser():
    time.sleep(1.2)
    url = "http://127.0.0.1:8000"
    print(f"\n[K-Jocker] Opening Web Operating Environment at {url} ...")
    webbrowser.open(url)

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from backend.config import system_config
    active_m = system_config.model.model_name
    print("=" * 60)
    print(" [>>] K-JOCKER OWNER AI -- OPERATING ENVIRONMENT")
    print(f" Owner: Kimsokun | Model: {active_m} (Local)")
    print(" Pure Llama Server WebUI | Auto-Kill on Exit Active")
    print("=" * 60)

    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    import uvicorn
    try:
        uvicorn.run(
            "backend.main:app",
            host="127.0.0.1",
            port=8000,
            log_level="info",
            reload=True,
            reload_dirs=[str(BASE_DIR / "backend")]
        )
    finally:
        auto_kill_llama()

