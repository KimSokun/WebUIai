import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.khmer import khmer_glossary, code_switch_normalizer, explanation_engine, term_preserver

class TestKhmerIntelligence(unittest.TestCase):
    def test_khmer_glossary_dual_terms(self):
        self.assertEqual(khmer_glossary.get_dual_term("api"), "អេភីអាយ (API)")
        self.assertEqual(khmer_glossary.get_dual_term("backend"), "ផ្នែកខាងក្រោយ (Backend)")
        self.assertEqual(khmer_glossary.get_dual_term("model"), "ម៉ូដែល (Model)")

    def test_code_switching_normalization(self):
        q1 = "backend នេះ error ត្រង់ណា?"
        res1 = code_switch_normalizer.parse(q1)
        self.assertEqual(res1["primary_intent"], "error_investigation")
        self.assertIn("backend", res1["technical_terms"])
        self.assertTrue(res1["is_code_switching"])

        q2 = "ជួយ fix API នេះ"
        res2 = code_switch_normalizer.parse(q2)
        self.assertEqual(res2["primary_intent"], "code_fix")
        self.assertIn("API", res2["technical_terms"])

    def test_7step_explanation_structure(self):
        explanation = explanation_engine.format_7step_explanation(
            what_it_does="កូដនេះគ្រប់គ្រងការតភ្ជាប់ទៅកាន់ម៉ាស៊ីនបម្រើ",
            why_it_works="ប្រើប្រាស់ connection pool ដើម្បីកាត់បន្ថយ latency",
            technical_terms="HTTP Connection Pooling, Timeout Guard",
            errors_explained="ដោះស្រាយបញ្ហា ReadTimeout",
            code_snippet="client = httpx.AsyncClient(timeout=10.0)",
            language="python",
            risks="គ្មានហានិភ័យ",
            how_to_test="python tests/test_runtime_audit.py"
        )
        self.assertIn("១. តើកូដនេះធ្វើអ្វី?", explanation)
        self.assertIn("២. ហេតុអ្វីបានជាវាដំណើរការ?", explanation)
        self.assertIn("៣. ពាក្យបច្ចេកទេសសំខាន់ៗ", explanation)
        self.assertIn("៤. ការពន្យល់កំហុស", explanation)
        self.assertIn("៥. បង្ហាញកូដជាក់ស្ដែង", explanation)
        self.assertIn("៦. ហានិភ័យដែលអាចកើតមាន", explanation)
        self.assertIn("៧. វិធីសាស្ត្រតេស្តផ្ទៀងផ្ទាត់", explanation)

    def test_term_preserver_masking_and_unmasking(self):
        raw_text = "Please check file `backend/config.py` with version v1.5.0 at https://github.com/test/repo"
        masked, mapping = term_preserver.mask_terms(raw_text)
        self.assertNotIn("v1.5.0", masked)
        self.assertNotIn("https://github.com", masked)

        restored = term_preserver.unmask_terms(masked, mapping)
        self.assertEqual(restored, raw_text)

if __name__ == "__main__":
    unittest.main()
