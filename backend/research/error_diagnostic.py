import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class DiagnosticResult(BaseModel):
    is_error: bool = False
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    faulting_library: Optional[str] = None
    faulting_symbol: Optional[str] = None
    faulting_file: Optional[str] = None
    line_number: Optional[int] = None
    symptom: str = ""
    suggested_queries: List[str] = Field(default_factory=list)

class ErrorDiagnosticEngine:
    """
    Automated diagnostic pipeline for code exceptions, Python tracebacks,
    compiler errors, dependency conflicts, and GGUF runtime errors.
    """
    TRACEBACK_REGEX = re.compile(
        r'File "(?P<file>[^"]+)", line (?P<line>\d+), in (?P<func>[^\n]+)\n(?P<code>[^\n]+\n)?(?P<err_type>[a-zA-Z0-9_\.]+(?:Error|Exception|Warning|Interrupt)):\s*(?P<err_msg>[^\n]+)'
    )

    SIMPLE_ERROR_REGEX = re.compile(
        r'\b(?P<err_type>[a-zA-Z0-9_\.]+(?:Error|Exception|Warning|Fault)):\s*(?P<err_msg>.+)'
    )

    KNOWN_LIBRARIES = [
        "fastapi", "uvicorn", "pydantic", "httpx", "google.genai", "transformers",
        "torch", "llama.cpp", "llama_cpp", "numpy", "bs4", "psutil", "asyncio",
        "urllib", "pytest", "scipy", "dotenv", "requests", "pyside6", "qt", "ffmpeg"
    ]

    def analyze_error(self, text: str) -> DiagnosticResult:
        """
        Extracts structured diagnostic data from an error text or user prompt.
        """
        # 1. Check for complete Python traceback
        tb_matches = list(self.TRACEBACK_REGEX.finditer(text))
        if tb_matches:
            last_match = tb_matches[-1]
            file_path = last_match.group("file")
            line_no = int(last_match.group("line"))
            func_name = last_match.group("func").strip()
            err_type = last_match.group("err_type").strip()
            err_msg = last_match.group("err_msg").strip()

            lib = self._detect_library(file_path, err_msg, text)
            symbol = self._detect_symbol(func_name, err_msg)
            queries = self._construct_queries(lib, err_type, err_msg, symbol)

            return DiagnosticResult(
                is_error=True,
                error_type=err_type,
                error_message=err_msg,
                faulting_library=lib,
                faulting_symbol=symbol,
                faulting_file=file_path,
                line_number=line_no,
                symptom=f"{err_type} in {func_name} at line {line_no}: {err_msg}",
                suggested_queries=queries
            )

        # 2. Check for simple Error: message
        simple_match = self.SIMPLE_ERROR_REGEX.search(text)
        if simple_match:
            err_type = simple_match.group("err_type").strip()
            err_msg = simple_match.group("err_msg").strip()
            lib = self._detect_library("", err_msg, text)
            symbol = self._detect_symbol("", err_msg)
            queries = self._construct_queries(lib, err_type, err_msg, symbol)

            return DiagnosticResult(
                is_error=True,
                error_type=err_type,
                error_message=err_msg,
                faulting_library=lib,
                faulting_symbol=symbol,
                symptom=f"{err_type}: {err_msg}",
                suggested_queries=queries
            )

        # 3. Check for GGUF / Llama runtime errors
        if any(term in text.lower() for term in ["llama_server", "gguf", "failed to load model", "cuda out of memory", "kv cache", "context length exceeded"]):
            return DiagnosticResult(
                is_error=True,
                error_type="GGUFRuntimeError",
                error_message=text.strip()[:150],
                faulting_library="llama.cpp",
                symptom="Local GGUF / llama-server runtime execution error",
                suggested_queries=[
                    f"llama.cpp {text[:60].strip()}",
                    "llama.cpp server error troubleshooting"
                ]
            )

        return DiagnosticResult(is_error=False)

    def _detect_library(self, file_path: str, err_msg: str, full_text: str) -> Optional[str]:
        combined = f"{file_path} {err_msg} {full_text}".lower()
        for lib in self.KNOWN_LIBRARIES:
            if lib in combined:
                return lib
        # Inspect module in traceback
        mod_match = re.search(r"site-packages[/\\]([a-zA-Z0-9_\-]+)", file_path)
        if mod_match:
            return mod_match.group(1)
        return None

    def _detect_symbol(self, func_name: str, err_msg: str) -> Optional[str]:
        # If "has no attribute 'Y'", prioritize the missing attribute
        attr_match = re.search(r"has no attribute ['\"]([a-zA-Z0-9_]+)['\"]", err_msg)
        if attr_match:
            return attr_match.group(1)
        quotes = re.findall(r"['\"]([a-zA-Z0-9_]+)['\"]", err_msg)
        if quotes:
            return quotes[-1]
        if func_name and func_name not in ["<module>", "<lambda>"]:
            return func_name
        return None

    def _construct_queries(
        self,
        lib: Optional[str],
        err_type: str,
        err_msg: str,
        symbol: Optional[str]
    ) -> List[str]:
        queries = []
        clean_msg = re.sub(r"['\"\[\]\(\)]", " ", err_msg)[:60].strip()

        # Query 1: Official Documentation / API search
        if lib and symbol:
            queries.append(f"{lib} {symbol} {err_type}")
        elif lib:
            queries.append(f"{lib} {err_type} {clean_msg}")
        else:
            queries.append(f"{err_type} {clean_msg}")

        # Query 2: GitHub issues and fixes
        if lib:
            queries.append(f"{lib} {err_type} github issues")
        else:
            queries.append(f"{err_type} python solution github")

        return queries

error_diagnostic = ErrorDiagnosticEngine()
