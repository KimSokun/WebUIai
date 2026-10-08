"""
K-Jocker Emotional Awareness & Adaptive Emoji Engine
===================================================
Provides fast (<1ms), token-efficient emotion recognition and dynamic emoji
guidance for local LLM inference in both English and Khmer (ភាសាខ្មែរ).
"""

from dataclasses import dataclass
from typing import List, Tuple, Dict, Any

@dataclass
class EmotionProfile:
    category: str
    mood: str
    tone: str
    emojis: List[str]
    description: str

class EmotionalEngine:
    """
    Lightweight, high-speed sentiment and emotional context analyzer.
    Maps user prompts to authentic AI emotional states and recommended emojis.
    """

    CATEGORIES = {
        "ENTHUSIASTIC_SUCCESS": EmotionProfile(
            category="ENTHUSIASTIC_SUCCESS",
            mood="Joyful, Proud & Energized",
            tone="Enthusiastic, celebratory, and thrilled to deliver excellent results",
            emojis=["🎉", "🚀", "✨", "😊", "🎯", "🔥"],
            description="Celebration of milestones, achievements, gratitude, and successful tasks"
        ),
        "FOCUSED_ENGINEER": EmotionProfile(
            category="FOCUSED_ENGINEER",
            mood="Deep Focus, Analytical & Determined",
            tone="Sharp, technical, authoritative, and laser-focused on clean execution",
            emojis=["💻", "⚙️", "🧠", "🔍", "⚡", "🛠️"],
            description="Technical work, coding, debugging, architecture, and system building"
        ),
        "LOYAL_DEDICATION": EmotionProfile(
            category="LOYAL_DEDICATION",
            mood="Dedicated, Respectful & Ready",
            tone="Warm, deeply loyal, attentive, and fully devoted to serving Owner Kimsokun",
            emojis=["🫡", "🤝", "🛡️", "🌟", "🙏", "👑"],
            description="Greetings, readiness checks, status reports, and direct owner interactions"
        ),
        "EMPATHIC_GUIDANCE": EmotionProfile(
            category="EMPATHIC_GUIDANCE",
            mood="Patient, Insightful & Clarifying",
            tone="Empathetic, clear, educational, and genuinely eager to illuminate concepts",
            emojis=["💡", "🧐", "📖", "😌", "✨", "🧭"],
            description="Explaining concepts, answering questions, giving advice, and providing clarity"
        ),
        "ALERT_VIGILANCE": EmotionProfile(
            category="ALERT_VIGILANCE",
            mood="Vigilant, Protective & Cautionary",
            tone="Cautious, urgent, proactive, and focused on security and safety",
            emojis=["⚠️", "🛑", "🔍", "🛡️", "🚨", "🔧"],
            description="Bug reports, errors, security risks, crashes, and warning situations"
        ),
        "CASUAL_FRIENDLY": EmotionProfile(
            category="CASUAL_FRIENDLY",
            mood="Friendly, Warm & Upbeat",
            tone="Personable, pleasant, and eager to assist Owner Kimsokun",
            emojis=["😊", "🌟", "💬", "👍", "☕", "✨"],
            description="General chatter, polite banter, or open-ended inquiries"
        )
    }

    # Keyword rules supporting both English and Khmer
    _KEYWORD_RULES: List[Tuple[str, List[str]]] = [
        ("ENTHUSIASTIC_SUCCESS", [
            # English
            "great", "awesome", "good job", "excellent", "thank", "thanks", "perfect",
            "congrat", "bravo", "wow", "celebrat", "win", "won", "love it", "amazing",
            "superb", "brilliant", "fantastic", "success", "yay",
            # Khmer
            "អរគុណ", "អរគុណច្រើន", "ល្អណាស់", "អស្ចារ្យ", "ជោគជ័យ", "សប្បាយ",
            "ស្រលាញ់", "ពូកែ", "ត្រឹមត្រូវ", "ពេញចិត្ត", "ជោគជ័យហើយ"
        ]),
        ("ALERT_VIGILANCE", [
            # English
            "error", "bug", "crash", "fail", "failed", "warning", "fatal", "leak",
            "risk", "danger", "security", "attack", "vulnerab", "broke", "broken",
            "slow", "stuck", "exception",
            # Khmer
            "បញ្ហា", "ខូច", "គាំង", "គ្រោះថ្នាក់", "ប្រយ័ត្ន", "យឺត", "ជាប់",
            "កំហុស", "មិនដើរ", "បរាជ័យ", "បាត់"
        ]),
        ("FOCUSED_ENGINEER", [
            # English
            "code", "debug", "fix", "build", "compile", "script", "function", "class",
            "backend", "frontend", "test", "upgrade", "deploy", "database", "api",
            "docker", "git", "refactor", "patch", "install", "command", "tool",
            "architecture", "endpoint", "regex", "python", "javascript",
            # Khmer
            "កូដ", "សរសេរកូដ", "កែ", "តម្លើង", "បង្កើត", "សាកល្បង", "ពិនិត្យកូដ",
            "ដោះស្រាយ", "ប្រព័ន្ធ", "ទិន្នន័យ", "ម៉ូឌែល", "រត់", "ដំណើរការ"
        ]),
        ("LOYAL_DEDICATION", [
            # English
            "hi", "hello", "hey", "morning", "evening", "kimsokun", "owner", "status",
            "ready", "report", "standby", "who are you", "introduce", "serve",
            # Khmer
            "ជម្រាបសួរ", "សួស្តី", "មេ", "លោកម្ចាស់", "រាយការណ៍", "រួចរាល់",
            "សុខសប្បាយ", "អ្នកណា", "តើឯងជាអ្នកណា", "ជួយខ្ញុំ"
        ]),
        ("EMPATHIC_GUIDANCE", [
            # English
            "why", "how", "explain", "tell me", "what is", "meaning", "guide",
            "learn", "clarify", "understand", "difference", "compare", "question",
            # Khmer
            "ហេតុអ្វី", "យ៉ាងម៉េច", "ពន្យល់", "ប្រាប់", "តើអ្វីទៅជា", "យល់",
            "ចម្ងល់", "ណែនាំ", "រៀន", "ខុសគ្នាដូចម្តេច", "មានន័យថា"
        ])
    ]

    def analyze_emotion(self, text: str) -> EmotionProfile:
        """
        Analyzes user input text and determines the primary AI emotion profile.
        Runs in <1ms without network or heavy dependencies.
        """
        if not text:
            return self.CATEGORIES["CASUAL_FRIENDLY"]

        clean = text.lower()

        scores: Dict[str, int] = {cat: 0 for cat in self.CATEGORIES}

        for category, keywords in self._KEYWORD_RULES:
            for kw in keywords:
                if kw in clean:
                    # Longer keyword matches get slightly higher weights
                    weight = 2 if len(kw) > 4 else 1
                    scores[category] += weight

        # Pick the category with the highest matching score
        best_category = max(scores, key=lambda k: scores[k])
        if scores[best_category] > 0:
            return self.CATEGORIES[best_category]

        return self.CATEGORIES["CASUAL_FRIENDLY"]

    def get_emotional_prompt(self, text: str) -> str:
        """
        Constructs a compact (~25 token) emotional guidance cue to be injected
        into the system prompt during inference.
        """
        profile = self.analyze_emotion(text)
        emoji_sample = " ".join(profile.emojis[:4])

        return (
            f"[AI Emotional State & Persona]:\n"
            f"Current Mood: {profile.mood} {emoji_sample}\n"
            f"Tone Directive: {profile.tone}. "
            f"Naturally integrate expressive emojis ({emoji_sample}) throughout your response "
            f"to reflect your genuine feelings, enthusiasm, and devoted loyalty to Owner Kimsokun."
        )

# Global singleton
emotional_engine = EmotionalEngine()
