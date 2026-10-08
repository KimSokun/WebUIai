import unittest
from pathlib import Path
from backend.models_manager import ModelsManager
from backend.config import system_config

class TestVisionMultimodalIntegration(unittest.TestCase):
    def setUp(self):
        self.mgr = ModelsManager()

    def test_find_mmproj_for_gemma(self):
        matched = self.mgr.find_mmproj_for_model("./models/gemma-3-4b-it-Q4_K_M.gguf")
        from backend.config import MODELS_DIR
        mmproj_path = MODELS_DIR / "mmproj-gemma-3-4b-f16.gguf"
        if mmproj_path.exists():
            self.assertIsNotNone(matched)
            self.assertEqual(matched.name, "mmproj-gemma-3-4b-f16.gguf")

    def test_scan_models_filters_mmproj(self):
        models = self.mgr.scan_models()
        for m in models:
            self.assertFalse(m["filename"].lower().startswith("mmproj"), f"Projector {m['filename']} should not be in selectable model list")

    def test_multimodal_payload_preservation(self):
        sample_messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What is in this picture?"},
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="}}
                ]
            }
        ]

        raw_user_msg = sample_messages[-1]["content"]
        if isinstance(raw_user_msg, list):
            user_msg = " ".join(p.get("text", "") for p in raw_user_msg if isinstance(p, dict) and p.get("type") == "text")
        else:
            user_msg = str(raw_user_msg)

        self.assertEqual(user_msg, "What is in this picture?")
        from backend.pipeline.router import intent_router
        intent, _ = intent_router.classify_intent(user_msg)
        self.assertIsNotNone(intent)

if __name__ == "__main__":
    unittest.main()
