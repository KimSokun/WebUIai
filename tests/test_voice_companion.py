import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from fastapi.testclient import TestClient
from backend.main import app
from backend.voice import voice_manager

class TestVoiceCompanion(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_voice_manager_config_read_update(self):
        orig_config = voice_manager.get_config()
        self.assertIn("enabled", orig_config)
        self.assertIn("language", orig_config)
        self.assertIn("auto_speak", orig_config)

        # Update config
        updated = voice_manager.update_config(language="km-KH", rate=0.95, auto_speak=True)
        self.assertEqual(updated["language"], "km-KH")
        self.assertEqual(updated["rate"], 0.95)
        self.assertTrue(updated["auto_speak"])

    def test_api_voice_endpoints(self):
        # GET /api/voice/status
        resp_status = self.client.get("/api/voice/status")
        self.assertEqual(resp_status.status_code, 200)
        data = resp_status.json()
        self.assertTrue(data["success"])
        self.assertIn("config", data)

        # POST /api/voice/config
        update_payload = {
            "enabled": True,
            "stt_enabled": True,
            "tts_enabled": True,
            "language": "en-US",
            "volume": 0.8
        }
        resp_update = self.client.post("/api/voice/config", json=update_payload)
        self.assertEqual(resp_update.status_code, 200)
        res_json = resp_update.json()
        self.assertTrue(res_json["success"])
        self.assertEqual(res_json["config"]["language"], "en-US")
        self.assertEqual(res_json["config"]["volume"], 0.8)

if __name__ == "__main__":
    unittest.main()
