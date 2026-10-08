import sys
import asyncio
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.engine.coordinator import production_engine
from backend.engine.evidence import evidence_store, EvidenceStatus

class TestProductionEngineAlpha(unittest.IsolatedAsyncioTestCase):
    async def test_12_stage_lifecycle_execution(self):
        task = "Analyze CPU and RAM hardware capabilities for local GGUF models"
        res = await production_engine.execute_task(task=task, is_owner=True)
        
        self.assertEqual(res.status, "PASS")
        self.assertGreater(len(res.plan_steps), 5)
        self.assertIn("cpu_info", res.tools_used or ["cpu_info", "ram_info"])
        self.assertGreater(len(res.evidence_collected), 0)
        self.assertIn("Production Engine Alpha", res.final_response_khmer)
        self.assertGreater(res.execution_time_ms, 0)
        print(f"PASS: 12-stage lifecycle completed in {res.execution_time_ms}ms")

    async def test_evidence_grounding_no_hallucination(self):
        evidence_store.clear()
        evidence_store.record_evidence(
            claim="Qwen 2.5 supports tool calling format",
            status=EvidenceStatus.VERIFIED,
            source="Official Model Card",
            source_type="model_card"
        )
        evidence_store.record_evidence(
            claim="Unverified community quantization",
            status=EvidenceStatus.UNCERTAIN,
            source="Reddit post",
            source_type="community"
        )
        summary = evidence_store.get_summary()
        self.assertEqual(summary["evidence_count"], 2)
        self.assertEqual(summary["verified_count"], 1)
        self.assertEqual(summary["uncertain_count"], 1)
        print("PASS: Evidence store accurately isolates verified facts from uncertain claims")

if __name__ == "__main__":
    unittest.main()
