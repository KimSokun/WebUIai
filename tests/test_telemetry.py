import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.telemetry import TelemetryTracker

def test_telemetry():
    print("Testing Telemetry Snapshot...")
    snap = TelemetryTracker.get_snapshot(owner_auth=True)
    assert snap.cpu_percent >= 0.0
    assert snap.ram_used_gb > 0.0
    assert snap.ram_total_gb > 0.0
    from backend.config import system_config
    assert snap.context_max == system_config.model.context_length
    assert snap.owner_authenticated is True
    print(f" - CPU: {snap.cpu_percent}%")
    print(f" - RAM: {snap.ram_used_gb} / {snap.ram_total_gb} GB")
    print(f" - Speed: {snap.tokens_per_sec} tok/s")
    print(f" - Context: {snap.context_used} / {snap.context_max}")
    print(f" - Internet Connected: {snap.internet_connected}")
    print("ALL TELEMETRY TESTS PASSED [PASS]!")

if __name__ == "__main__":
    test_telemetry()
