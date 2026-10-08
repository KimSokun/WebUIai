from typing import Dict, Optional

class KhmerGlossary:
    """
    Persistent technical terminology dictionary.
    Formats technical terms as: 'Khmer explanation + original English technical term'
    """
    TERMS: Dict[str, str] = {
        "api": "អេភីអាយ (API)",
        "backend": "ផ្នែកខាងក្រោយ (Backend)",
        "frontend": "ផ្នែកខាងមុខ (Frontend)",
        "database": "មូលដ្ឋានទិន្នន័យ (Database)",
        "runtime": "បរិស្ថានប្រតិបត្តិការ (Runtime)",
        "dependency": "ភាពពឹងផ្អែក (Dependency)",
        "framework": "ក្របខណ្ឌ (Framework)",
        "repository": "ឃ្លាំងកូដ (Repository)",
        "model": "ម៉ូដែល (Model)",
        "inference": "ការសន្និដ្ឋាន (Inference)",
        "compiler": "កម្មវិធីបម្លែងកូដ (Compiler)",
        "debugger": "ឧបករណ៍កែកំហុស (Debugger)",
        "server": "ម៉ាស៊ីនបម្រើ (Server)",
        "client": "ម៉ាស៊ីនកូន (Client)",
        "authentication": "ការផ្ទៀងផ្ទាត់ភាពត្រឹមត្រូវ (Authentication)",
        "authorization": "ការអនុញ្ញាតសិទ្ធិ (Authorization)",
        "cache": "អង្គចងចាំបណ្ដោះអាសន្ន (Cache)",
        "asynchronous": "អសមកាល (Asynchronous)",
        "concurrency": "ការដំណើរការដំណាលគ្នា (Concurrency)",
        "thread": "ខ្សែដំណើរការ (Thread)",
        "process": "ដំណើរការ (Process)",
        "exception": "ករណីលើកលែង ឬកំហុស (Exception)",
        "syntax": "វេយ្យាករណ៍កូដ (Syntax)",
        "refactor": "ការកែលម្អរចនាសម្ព័ន្ធកូដ (Refactor)",
        "unit test": "ការតេស្តឯកតា (Unit Test)",
        "endpoint": "ចំណុចតភ្ជាប់ (Endpoint)",
        "payload": "បន្ទុកទិន្នន័យ (Payload)",
        "token": "ថូខឹន (Token)",
        "prompt": "ប្រអប់បញ្ចូលបញ្ជា (Prompt)",
        "context": "បរិបទ (Context)",
        "pipeline": "ខ្សែសង្វាក់ដំណើរការ (Pipeline)",
        "sandbox": "ប្រអប់ដាច់ដោយឡែក (Sandbox)",
        "middleware": "ស្រទាប់កណ្ដាល (Middleware)",
        "memory": "អង្គចងចាំ (Memory)",
        "latency": "ថិរវេលារង់ចាំ (Latency)",
        "throughput": "ទិន្នផលបញ្ជូន (Throughput)",
        "payload": "បន្ទុកទិន្នន័យ (Payload)",
        "buffer": "អង្គចងចាំទ្រនាប់ (Buffer)",
        "schema": "គ្រោងទម្រង់ទិន្នន័យ (Schema)",
        "serialization": "ការបម្លែងទិន្នន័យជាខ្សែអក្សរ (Serialization)"
    }

    def get_dual_term(self, english_term: str) -> str:
        key = english_term.lower().strip()
        if key in self.TERMS:
            return self.TERMS[key]
        return english_term

    def enrich_text(self, text: str) -> str:
        """Enriches English technical terms with dual Khmer equivalents"""
        enriched = text
        for term, dual in self.TERMS.items():
            # Match whole words only
            import re
            pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
            enriched = pattern.sub(dual, enriched)
        return enriched

khmer_glossary = KhmerGlossary()
