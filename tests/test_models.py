import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import MODELS_DIR, system_config
from backend.models_manager import models_manager
from fastapi.testclient import TestClient
from backend.main import app

def test_models_scan_and_selection():
    print("Testing GGUF Models Scanner...")
    
    # 1. Create a dummy .gguf model for test
    dummy_model = MODELS_DIR / "k-jocker-1.5flash-test-q5_k_m.gguf"
    dummy_model.write_bytes(b"GGUF" + b"\x00" * 1024 * 1024) # 1MB dummy GGUF
    
    try:
        # 2. Scan models
        models = models_manager.scan_models()
        assert len(models) >= 1
        found = next((m for m in models if m["filename"] == dummy_model.name), None)
        assert found is not None
        assert found["quantization"] == "Q5_K_M"
        assert found["size_mb"] >= 1.0
        print(f" - Model scan detected: {found['filename']} ({found['quantization']}) [PASS]")

        # 3. Select model
        res = models_manager.select_model(dummy_model.name)
        assert res["success"] is True
        assert dummy_model.name in res["model_path"]
        print(" - Model selection [PASS]")

        # 4. Test API endpoint
        client = TestClient(app)
        api_res = client.get("/api/models")
        assert api_res.status_code == 200
        data = api_res.json()
        assert data["models_dir"] == str(MODELS_DIR)
        assert len(data["models"]) >= 1
        print(" - /api/models API endpoint [PASS]")

    finally:
        # Clean up test dummy file
        if dummy_model.exists():
            dummy_model.unlink()

    print("ALL MODEL MANAGEMENT TESTS PASSED [PASS]!")

if __name__ == "__main__":
    test_models_scan_and_selection()
