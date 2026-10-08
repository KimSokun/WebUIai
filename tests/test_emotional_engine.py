"""
Unit Tests for K-Jocker Emotional Awareness & Adaptive Emoji Engine
===================================================================
Tests emotion classification for English & Khmer, dynamic prompt injection,
and token efficiency.
"""

import unittest
from backend.runtime.emotional_engine import emotional_engine, EmotionProfile

class TestEmotionalEngine(unittest.TestCase):

    def test_english_emotion_classification(self):
        """Test standard English queries across emotional categories."""
        cases = [
            ("Great job! That was amazing and perfect!", "ENTHUSIASTIC_SUCCESS"),
            ("Thank you so much, awesome work!", "ENTHUSIASTIC_SUCCESS"),
            ("We won the competition, celebrating today!", "ENTHUSIASTIC_SUCCESS"),
            ("Please debug this python function and build the test", "FOCUSED_ENGINEER"),
            ("Fix the backend API endpoint and compile the code", "FOCUSED_ENGINEER"),
            ("Deploy docker container and refactor the architecture", "FOCUSED_ENGINEER"),
            ("Hello K-Jocker, report your current status", "LOYAL_DEDICATION"),
            ("Good morning, Owner Kimsokun is here", "LOYAL_DEDICATION"),
            ("Why does the context gauge show 100%?", "EMPATHIC_GUIDANCE"),
            ("How do I use this tool? Can you explain the difference?", "EMPATHIC_GUIDANCE"),
            ("Critical security error! The system crashed with a fatal bug", "ALERT_VIGILANCE"),
            ("Warning: memory leak detected and process is stuck", "ALERT_VIGILANCE"),
        ]
        for query, expected_category in cases:
            with self.subTest(query=query):
                profile = emotional_engine.analyze_emotion(query)
                self.assertEqual(profile.category, expected_category)
                self.assertTrue(len(profile.emojis) >= 4)

    def test_khmer_emotion_classification(self):
        """Test Khmer queries across emotional categories."""
        cases = [
            ("អរគុណច្រើនមេ ធ្វើបានល្អណាស់ ជោគជ័យហើយ", "ENTHUSIASTIC_SUCCESS"),
            ("អស្ចារ្យមែនទែន ខ្ញុំសប្បាយចិត្តណាស់", "ENTHUSIASTIC_SUCCESS"),
            ("ជួយកូដ និងកែសម្រួលប្រព័ន្ធ backend ផង", "FOCUSED_ENGINEER"),
            ("តម្លើងប្រព័ន្ធ និងសាកល្បងម៉ូឌែលថ្មី", "FOCUSED_ENGINEER"),
            ("ជម្រាបសួរលោកម្ចាស់ K-Jocker តើឯងរួចរាល់ហើយឬនៅ?", "LOYAL_DEDICATION"),
            ("សួស្តីមេ តើមានរបាយការណ៍អ្វីខ្លះ?", "LOYAL_DEDICATION"),
            ("ហេតុអ្វីបានជា token ពេញ? តើវាមានន័យដូចម្តេច?", "EMPATHIC_GUIDANCE"),
            ("ជួយពន្យល់ខ្ញុំបន្តិច តើអ្វីទៅជា llama.cpp?", "EMPATHIC_GUIDANCE"),
            ("មានបញ្ហាធ្ងន់ធ្ងរ កូដខូច និងគាំងហើយ ប្រយ័ត្នផង", "ALERT_VIGILANCE"),
        ]
        for query, expected_category in cases:
            with self.subTest(query=query):
                profile = emotional_engine.analyze_emotion(query)
                self.assertEqual(profile.category, expected_category)
                self.assertTrue(len(profile.emojis) >= 4)

    def test_emotional_prompt_generation(self):
        """Test generated prompt cue structure, tone directives, and emojis."""
        prompt = emotional_engine.get_emotional_prompt("Awesome achievement! Thank you!")
        self.assertIn("[AI Emotional State & Persona]:", prompt)
        self.assertIn("Joyful, Proud & Energized", prompt)
        self.assertIn("🎉", prompt)
        self.assertIn("🚀", prompt)
        self.assertIn("Owner Kimsokun", prompt)

        # Check token efficiency: should be under 250 characters (~40-50 tokens)
        self.assertLess(len(prompt), 450)

    def test_fallback_casual_friendly(self):
        """Test empty or neutral input defaults to warm friendly profile."""
        profile_empty = emotional_engine.analyze_emotion("")
        self.assertEqual(profile_empty.category, "CASUAL_FRIENDLY")
        self.assertIn("😊", profile_empty.emojis)

        profile_neutral = emotional_engine.analyze_emotion("12345 67890")
        self.assertEqual(profile_neutral.category, "CASUAL_FRIENDLY")

    def test_system_config_has_emotional_rule(self):
        """Verify system_config and owner_settings contain the emotional rule."""
        from backend.config import system_config
        self.assertIn("EMOTIONAL ADAPTIVITY & EMOJIS", system_config.system_prompt)
        self.assertIn("EXECUTIVE & EXPRESSIVE TONE", system_config.system_prompt)

if __name__ == "__main__":
    unittest.main()
