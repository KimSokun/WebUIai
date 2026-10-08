import ast
import json
from typing import Dict, Any, Tuple

class SyntaxChecker:
    """
    Validates AST and syntax correctness for supported languages before presenting code.
    Prevents presenting malformed syntax to Owner Kimsokun.
    """
    def check_syntax(self, language: str, code: str) -> Tuple[bool, str]:
        """
        Returns (is_valid, error_message_or_empty)
        """
        lang = language.lower().strip()
        if not code or not code.strip():
            return (True, "")

        if lang in ("python", "py"):
            try:
                ast.parse(code)
                return (True, "")
            except SyntaxError as e:
                return (False, f"Python SyntaxError at line {e.lineno}: {e.msg}")

        if lang in ("json",):
            try:
                json.loads(code)
                return (True, "")
            except json.JSONDecodeError as e:
                return (False, f"JSON DecodeError at line {e.lineno}, col {e.colno}: {e.msg}")

        # Basic balanced braces/brackets check for C/C++/Java/Rust/JS/TS/Go
        if lang in ("javascript", "typescript", "c", "c++", "cpp", "c#", "csharp", "java", "rust", "go"):
            stack = []
            brackets = {"(": ")", "{": "}", "[": "]"}
            in_str = False
            str_char = ""
            for idx, ch in enumerate(code):
                if ch in ("'", '"', '`') and (idx == 0 or code[idx-1] != '\\'):
                    if in_str and ch == str_char:
                        in_str = False
                    elif not in_str:
                        in_str = True
                        str_char = ch
                if not in_str:
                    if ch in brackets:
                        stack.append((ch, idx))
                    elif ch in brackets.values():
                        if not stack:
                            return (False, f"Unmatched closing brace '{ch}' at character position {idx}")
                        last, _ = stack.pop()
                        if brackets[last] != ch:
                            return (False, f"Mismatched brace: opened '{last}' but found '{ch}'")
            if stack:
                last, idx = stack[-1]
                return (False, f"Unclosed brace '{last}' from character position {idx}")
            return (True, "")

        return (True, "")

syntax_checker = SyntaxChecker()
