import re
from pathlib import Path
from typing import Optional, Tuple
from backend.coding.language_profiles import language_profiles, LanguageProfile

class LanguageDetector:
    """
    Detects programming language from filename, code snippet, shebang, or keywords.
    Refuses to pretend; flags unknown languages for research.
    """
    SHEBANG_PATTERNS = [
        (re.compile(r"^#!\s*/usr/bin/env\s+python|^#!\s*/usr/bin/python"), "Python"),
        (re.compile(r"^#!\s*/usr/bin/env\s+node|^#!\s*/usr/bin/node"), "JavaScript"),
        (re.compile(r"^#!\s*/usr/bin/env\s+bash|^#!\s*/bin/bash|^#!\s*/bin/sh"), "Bash"),
        (re.compile(r"^#!\s*/usr/bin/env\s+perl|^#!\s*/usr/bin/perl"), "Perl"),
        (re.compile(r"^#!\s*/usr/bin/env\s+ruby|^#!\s*/usr/bin/ruby"), "Ruby"),
        (re.compile(r"^#!\s*/usr/bin/env\s+pwsh"), "PowerShell"),
    ]

    SIGNATURE_PATTERNS = [
        (re.compile(r"\bdef\s+\w+\s*\(.*\):|\bimport\s+\w+|\bfrom\s+\w+\s+import"), "Python"),
        (re.compile(r"\bpublic\s+class\s+\w+|\bpublic\s+static\s+void\s+main\s*\("), "Java"),
        (re.compile(r"\bfn\s+main\s*\(|\blet\s+mut\s+|\buse\s+std::"), "Rust"),
        (re.compile(r"\bpackage\s+main|\bfunc\s+main\s*\("), "Go"),
        (re.compile(r"#include\s+<iostream>|\bstd::cout\b|\btemplate\s*<"), "C++"),
        (re.compile(r"#include\s+<stdio\.h>|\bprintf\s*\("), "C"),
        (re.compile(r"\busing\s+System;|\bnamespace\s+\w+;|\bConsole\.WriteLine\b"), "C#"),
        (re.compile(r"\binterface\s+\w+\s*\{|\btype\s+\w+\s*=|:\s*(string|number|boolean)\b"), "TypeScript"),
        (re.compile(r"\bconst\s+\w+\s*=\s*require\(|\bconsole\.log\s*\("), "JavaScript"),
        (re.compile(r"\bSELECT\s+.+\s+FROM\s+\w+|\bCREATE\s+TABLE\b", re.IGNORECASE), "SQL"),
        (re.compile(r"<!DOCTYPE\s+html>|<html|<div\b|<head\b", re.IGNORECASE), "HTML"),
        (re.compile(r'^\s*\{\s*"[^"]+"\s*:\s*', re.MULTILINE), "JSON"),
        (re.compile(r"\b__global__\s+void\b|\bcudaMalloc\b"), "CUDA"),
        (re.compile(r"\bimport\s+QtQuick\b|\bItem\s*\{|\bRectangle\s*\{"), "QML"),
        (re.compile(r"\bsection\s+\.text|\bglobal\s+_start|\bmov\s+(eax|rax)"), "Assembly")
    ]

    def detect(self, filename: Optional[str] = None, code_snippet: Optional[str] = None) -> Tuple[str, Optional[LanguageProfile], bool]:
        """
        Returns (language_name, profile, is_recognized)
        """
        # 1. By filename extension
        if filename:
            ext = Path(filename).suffix.lower()
            if ext:
                profile = language_profiles.get_profile(ext)
                if profile:
                    return (profile.name, profile, True)

        # 2. By Shebang
        if code_snippet:
            first_line = code_snippet.strip().splitlines()[0] if code_snippet.strip() else ""
            if first_line.startswith("#!"):
                for pat, lang in self.SHEBANG_PATTERNS:
                    if pat.search(first_line):
                        profile = language_profiles.get_profile(lang)
                        return (lang, profile, True)

            # 3. By structural syntax pattern
            for pat, lang in self.SIGNATURE_PATTERNS:
                if pat.search(code_snippet):
                    profile = language_profiles.get_profile(lang)
                    return (lang, profile, True)

        return ("Unknown", None, False)

language_detector = LanguageDetector()
