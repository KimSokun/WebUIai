"""
Unit Tests for K-Jocker Instruction Constraint Guard & Output Sanitizer
=======================================================================
Tests single-word constraints, exact word-count constraints, calculation-only
constraints, Khmer translation slip correction, and fake score elimination.
"""

import unittest
from backend.runtime.constraint_guard import constraint_guard

class TestConstraintGuard(unittest.TestCase):

    def test_has_constraints_detection(self):
        """Test detection of formatting and length constraints."""
        self.assertTrue(constraint_guard.has_constraints("Question 21: only one word"))
        self.assertTrue(constraint_guard.has_constraints("exactly 3 words"))
        self.assertTrue(constraint_guard.has_constraints("calculation only, no explanation"))
        self.assertTrue(constraint_guard.has_constraints("បកប្រែជាភាសាខ្មែរ"))
        self.assertTrue(constraint_guard.has_constraints("Questionnaire evaluation exam"))
        self.assertFalse(constraint_guard.has_constraints("hello how are you"))

    def test_khmer_translation_correction(self):
        """Test hallucinated translation 'កាត់សេវាកម្ម Python' is corrected to 'រៀន Python'."""
        faulty = 'Question 19: "I want to learn Python." -> "ខ្ញុំចង់កាត់សេវាកម្ម Python"'
        fixed = constraint_guard.sanitize_response("translation test", faulty)
        self.assertNotIn("កាត់សេវាកម្ម", fixed)
        self.assertIn("ខ្ញុំចង់រៀន Python", fixed)

    def test_fake_score_elimination(self):
        """Test sycophantic 'Score: 100/100' and 'Mistakes found: 0' are removed."""
        faulty = (
            "Score: 100/100\n"
            "Mistakes found: 0\n"
            "Overall level: Advanced\n\n"
            "Self-Verification:\n"
            "All answers were verified for accuracy. No mistakes were found. "
            "The response adheres to the instructions and is free from errors."
        )
        fixed = constraint_guard.sanitize_response("exam", faulty)
        self.assertNotIn("Score: 100/100", fixed)
        self.assertNotIn("Mistakes found: 0", fixed)
        self.assertNotIn("All answers were verified for accuracy. No mistakes were found.", fixed)
        self.assertIn("Answers have been reviewed", fixed)

    def test_single_word_constraint_sanitization(self):
        """Test 'Grass is green.' trimmed to 'Green' for single-word questions."""
        faulty = "Question 21: Grass is green."
        user_prompt = "Question 21: Answer with ONLY one word"
        fixed = constraint_guard.sanitize_response(user_prompt, faulty)
        self.assertIn("Question 21: Green", fixed)
        self.assertNotIn("Grass is green", fixed)

    def test_exact_word_count_sanitization(self):
        """Test 'Python is a programming language.' adjusted to 3 words."""
        faulty = "Question 22: Python is a programming language."
        user_prompt = "Question 22: exactly 3 words"
        fixed = constraint_guard.sanitize_response(user_prompt, faulty)
        self.assertIn("Question 22: Python is programming", fixed)
        words = "Python is programming".split()
        self.assertEqual(len(words), 3)

    def test_calculation_only_sanitization(self):
        """Test calculation only trims equation to pure number."""
        faulty = "Question 23: 123 + 456 = 579"
        user_prompt = "Question 23: calculation only, no explanation"
        fixed = constraint_guard.sanitize_response(user_prompt, faulty)
        self.assertIn("Question 23: 579", fixed)
        self.assertNotIn("123 + 456 =", fixed)

    def test_filter_stream_token(self):
        """Test live streaming token filter."""
        self.assertEqual(constraint_guard.filter_stream_token("កាត់សេវាកម្ម"), "រៀន")
        self.assertIn("Score: Multi-Question Evaluation", constraint_guard.filter_stream_token("Score: 100/100"))
        self.assertEqual(constraint_guard.filter_stream_token("Hello World"), "Hello World")

if __name__ == "__main__":
    unittest.main()
