from typing import Dict, Any, Optional

class KhmerTechnicalExplanationEngine:
    """
    Formats code explanations according to the required 7-step engineering standard:
    1. What it does (តើកូដនេះធ្វើអ្វី?)
    2. Why it works (ហេតុអ្វីបានជាវាដំណើរការ?)
    3. Important technical terms (ពាក្យបច្ចេកទេសសំខាន់ៗ)
    4. Explain errors (ការពន្យល់កំហុស)
    5. Show relevant code (បង្ហាញកូដជាក់ស្ដែង)
    6. Explain risks (ហានិភ័យដែលអាចកើតមាន)
    7. How to test it (វិធីសាស្ត្រតេស្តផ្ទៀងផ្ទាត់)
    """
    def format_7step_explanation(
        self,
        what_it_does: str,
        why_it_works: str,
        technical_terms: str,
        errors_explained: str,
        code_snippet: str,
        language: str = "python",
        risks: str = "គ្មានហានិភ័យប៉ះពាល់ដល់ប្រព័ន្ធក្រៅពី sandbox ឡើយ។",
        how_to_test: str = "ដំណើរការ unit test ដើម្បីផ្ទៀងផ្ទាត់។"
    ) -> str:
        lines = [
            "### ១. តើកូដនេះធ្វើអ្វី? (What it does)",
            what_it_does.strip(),
            "",
            "### ២. ហេតុអ្វីបានជាវាដំណើរការ? (Why it works)",
            why_it_works.strip(),
            "",
            "### ៣. ពាក្យបច្ចេកទេសសំខាន់ៗ (Important Technical Terms)",
            technical_terms.strip(),
            "",
            "### ៤. ការពន្យល់កំហុស (Error Analysis)",
            errors_explained.strip(),
            "",
            "### ៥. បង្ហាញកូដជាក់ស្ដែង (Relevant Implementation)",
            f"```{language}\n{code_snippet.strip()}\n```",
            "",
            "### ៦. ហានិភ័យដែលអាចកើតមាន (Risks & Edge Cases)",
            risks.strip(),
            "",
            "### ៧. វិធីសាស្ត្រតេស្តផ្ទៀងផ្ទាត់ (How to Test)",
            how_to_test.strip(),
            ""
        ]
        return "\n".join(lines)

explanation_engine = KhmerTechnicalExplanationEngine()
