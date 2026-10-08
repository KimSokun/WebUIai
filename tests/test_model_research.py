import sys
import asyncio
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.tools.model_research import HardwareCapabilityDetectTool, GGUFMetadataInspectTool, HuggingFaceSearchTool

class TestModelResearchTools(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.hw_tool = HardwareCapabilityDetectTool()
        self.gguf_tool = GGUFMetadataInspectTool()
        self.hf_tool = HuggingFaceSearchTool()

    async def test_hardware_detection(self):
        res = await self.hw_tool.execute()
        self.assertTrue(res.success, f"Hardware detection failed: {res.error}")
        self.assertIsInstance(res.data, dict)
        self.assertIn("cpu_physical_cores", res.data)
        self.assertIn("total_ram_gb", res.data)
        self.assertIn("available_ram_gb", res.data)
        self.assertIn("recommended_model_tier", res.data)
        self.assertGreater(res.data["total_ram_gb"], 0)

    async def test_gguf_metadata_real_model(self):
        from backend.config import MODELS_DIR
        target = MODELS_DIR / "qwen3-1.7b-flashhead-q4_k_m.gguf"
        if not target.exists():
            # Create a lightweight temporary mock GGUF header for test verification
            import struct
            mock_path = MODELS_DIR / "mock_test_model.gguf"
            try:
                with open(mock_path, "wb") as f:
                    f.write(struct.pack("<4sIII", b"GGUF", 3, 290, 42))
                    f.write(b"\x00" * 1024)
                res = await self.gguf_tool.execute(filename="mock_test_model.gguf")
                self.assertTrue(res.success, f"GGUF metadata inspect failed: {res.error}")
                self.assertTrue(res.data["is_valid_gguf"])
                self.assertEqual(res.data["tensor_count"], 290)
            finally:
                if mock_path.exists():
                    mock_path.unlink()
            return

        res = await self.gguf_tool.execute(filename="qwen3-1.7b-flashhead-q4_k_m.gguf")
        self.assertTrue(res.success, f"GGUF metadata inspect failed: {res.error}")
        self.assertIsInstance(res.data, dict)
        self.assertTrue(res.data["is_valid_gguf"])
        self.assertGreater(res.data["tensor_count"], 0)

    async def test_gguf_metadata_not_found(self):
        res = await self.gguf_tool.execute(filename="non_existent_fake_model_12345.gguf")
        self.assertFalse(res.success)
        self.assertIn("not found", res.error.lower())

    async def test_huggingface_search(self):
        res = await self.hf_tool.execute(query="Qwen2.5-Coder-1.5B-Instruct")
        self.assertTrue(res.success, f"HF search failed: {res.error}")
        self.assertIsInstance(res.data, list)

if __name__ == "__main__":
    unittest.main()
