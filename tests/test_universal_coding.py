import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.coding import language_detector, language_profiles, syntax_checker, evidence_tracker

class TestUniversalCoding(unittest.TestCase):
    def test_language_profile_registry(self):
        langs = language_profiles.list_languages()
        self.assertGreaterEqual(len(langs), 36)
        self.assertIn("Python", langs)
        self.assertIn("Rust", langs)
        self.assertIn("CUDA", langs)
        self.assertIn("QML", langs)

    def test_language_detection_extensions(self):
        cases = [
            ("script.py", "Python"),
            ("main.rs", "Rust"),
            ("kernel.cu", "CUDA"),
            ("UI.qml", "QML"),
            ("app.ts", "TypeScript"),
            ("schema.sql", "SQL")
        ]
        for fname, expected in cases:
            name, prof, ok = language_detector.detect(filename=fname)
            self.assertTrue(ok, f"Failed to detect {fname}")
            self.assertEqual(name, expected)

    def test_language_detection_shebang(self):
        snippet = "#!/usr/bin/env python3\nprint('hello')"
        name, prof, ok = language_detector.detect(code_snippet=snippet)
        self.assertTrue(ok)
        self.assertEqual(name, "Python")

    def test_syntax_checker_python_valid(self):
        valid_code = "def add(a: int, b: int) -> int:\n    return a + b"
        ok, msg = syntax_checker.check_syntax("python", valid_code)
        self.assertTrue(ok)
        self.assertEqual(msg, "")

    def test_syntax_checker_python_invalid(self):
        invalid_code = "def bad_func(:\n    print('broken')"
        ok, msg = syntax_checker.check_syntax("python", invalid_code)
        self.assertFalse(ok)
        self.assertIn("SyntaxError", msg)

    def test_evidence_tracker(self):
        evidence_tracker.record_evidence("FastAPI.lifespan", "Python", "https://fastapi.tiangolo.com/advanced/events/", "0.110.0")
        items = evidence_tracker.get_evidence_for_symbol("lifespan")
        self.assertGreater(len(items), 0)
        self.assertEqual(items[0]["version"], "0.110.0")

if __name__ == "__main__":
    unittest.main()
