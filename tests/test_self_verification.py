"""
Unit Tests for K-Jocker Autonomous Self-Verification & Anti-Overconfidence Engine
=================================================================================
Tests verification intent recognition (EN & KM), anti-overconfidence protocol
injection, epistemic humility rules, and overconfidence pattern scanning.
"""

import unittest
from backend.runtime.self_verification import self_verification_engine
from backend.config import system_config

class TestSelfVerificationEngine(unittest.TestCase):

    def test_english_verification_triggers(self):
        """Test detection of English verification and audit queries."""
        cases = [
            ("Please verify if 15 * 12 = 180", True),
            ("Can you double check my code for errors?", True),
            ("Audit this database migration script", True),
            ("Is this solution right or wrong?", True),
            ("Find bugs in this python implementation", True),
            ("Critique my architecture and evaluate flaws", True),
            ("What is the weather in Phnom Penh?", False),
            ("Tell me a story about robots", False)
        ]
        for query, expected in cases:
            with self.subTest(query=query):
                self.assertEqual(self_verification_engine.is_verification_query(query), expected)

    def test_khmer_verification_triggers(self):
        """Test detection of Khmer verification and error-checking queries."""
        cases = [
            ("ត្រួតពិនិត្យ និងកែតម្រូវចម្លើយរបស់ខ្លួនឯង", True),
            ("តើចម្លើយនេះត្រឹមត្រូវទេ?", True),
            ("ជួយផ្ទៀងផ្ទាត់ការគណនានេះបន្តិច", True),
            ("កូដនេះមានកំហុសអ្វីខ្លះ?", True),
            ("ជួយរកកំហុស និងដោះស្រាយ", True),
            ("តើពិតទេដែល 10 + 5 = 20?", True),
            ("ជម្រាបសួរលោកម្ចាស់ K-Jocker", False),
            ("ថ្ងៃនេះខ្ញុំសប្បាយចិត្តណាស់", False)
        ]
        for query, expected in cases:
            with self.subTest(query=query):
                self.assertEqual(self_verification_engine.is_verification_query(query), expected)

    def test_math_expression_verification_trigger(self):
        """Test mathematical expressions paired with verification keywords."""
        self.assertTrue(self_verification_engine.is_verification_query("Is 25 + 75 = 100?"))
        self.assertTrue(self_verification_engine.is_verification_query("12 * 12 = 144 ត្រូវទេ?"))
        self.assertFalse(self_verification_engine.is_verification_query("just the number 12345"))

    def test_verification_prompt_generation(self):
        """Test generated prompt contains critical adversarial directives."""
        prompt = self_verification_engine.get_verification_prompt("Verify this calculation")
        self.assertIn("[MANDATORY SELF-VERIFICATION & ANTI-OVERCONFIDENCE PROTOCOL]:", prompt)
        self.assertIn("ADVERSARIAL SELF-CRITIQUE", prompt)
        self.assertIn("STEP-BY-STEP PROOF", prompt)
        self.assertIn("HONEST ERROR DETECTION", prompt)
        self.assertIn("EPISTEMIC HUMILITY", prompt)

    def test_baseline_epistemic_humility_prompt(self):
        """Test prompt for general queries still contains baseline truthfulness directive."""
        prompt = self_verification_engine.get_verification_prompt("What is Python?")
        self.assertIn("[EPISTEMIC HUMILITY & TRUTHFULNESS DIRECTIVE]:", prompt)
        self.assertIn("Never make blind claims of 100% certainty without proof", prompt)

    def test_scan_overconfidence(self):
        """Test detection of sycophantic false certainty phrases."""
        self.assertTrue(self_verification_engine.scan_overconfidence("All answers are completely correct and perfect!"))
        self.assertTrue(self_verification_engine.scan_overconfidence("There are no errors whatsoever."))
        self.assertTrue(self_verification_engine.scan_overconfidence("ចម្លើយទាំងអស់សុទ្ធតែត្រឹមត្រូវ ១០០% គ្មានកំហុសទាល់តែសោះ"))
        self.assertTrue(self_verification_engine.scan_overconfidence("ត្រឹមត្រូវទាំងអស់ ១០០%"))
        
        # Valid analytical reasoning should NOT trigger false positive
        self.assertFalse(self_verification_engine.scan_overconfidence("In step 1, 15 * 12 equals 180, which differs from 170. Hence step 1 is incorrect."))
        self.assertFalse(self_verification_engine.scan_overconfidence("Here is the corrected calculation with verified steps."))

    def test_system_config_has_rule_7(self):
        """Verify Rule 7 is embedded in active system_config."""
        self.assertIn("7. EPISTEMIC HUMILITY & RIGOROUS SELF-CORRECTION", system_config.system_prompt)


if __name__ == "__main__":
    unittest.main()
