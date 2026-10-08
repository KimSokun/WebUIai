import re
import math
import time
import datetime
from typing import Any, Dict, Optional
from backend.tools.base import BaseTool, ToolResult

class FastCalcTool(BaseTool):
    """Deterministic ultra-fast math, arithmetic, percentages, and date calculations (<0.1ms)."""
    def __init__(self):
        super().__init__(
            name="fast_calc",
            description="Ultra-fast deterministic arithmetic, percentage, discount, and date calculations (<0.1ms).",
            risk_level="LOW",
            requires_confirmation=False
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Math expression (e.g. '15 + 27', '20% of 100', '100 - 15%', 'today + 3 days', 'circle area r=5')"
                }
            },
            "required": ["expression"]
        }

    async def execute(self, **kwargs) -> ToolResult:
        expr = str(kwargs.get("expression", "")).strip()
        if not expr:
            return ToolResult(success=False, data=None, error="Expression parameter is required.")

        start_t = time.perf_counter()

        # 1. Percentage 'X% of Y'
        pct_of = re.search(r'([0-9\.]+)\s*%\s*(?:of|\*)\s*([0-9\.]+)', expr, re.IGNORECASE)
        if pct_of:
            p = float(pct_of.group(1))
            val = float(pct_of.group(2))
            res = (p / 100.0) * val
            elapsed = (time.perf_counter() - start_t) * 1000
            return ToolResult(success=True, data={"result": res, "type": "percentage", "formatted": f"{p}% of {val} = {res}"}, execution_time_ms=elapsed)

        # 2. Discount 'Y - X%' or 'Y with X% off'
        disc = re.search(r'([0-9\.]+)\s*(?:-|with)\s*([0-9\.]+)\s*%\s*(?:off|discount)?', expr, re.IGNORECASE)
        if disc:
            base = float(disc.group(1))
            pct = float(disc.group(2))
            savings = base * (pct / 100.0)
            final_price = base - savings
            elapsed = (time.perf_counter() - start_t) * 1000
            return ToolResult(success=True, data={"result": final_price, "savings": savings, "type": "discount", "formatted": f"{base} with {pct}% off = {final_price}"}, execution_time_ms=elapsed)

        # 3. Date math 'today + N days' or 'after N days'
        date_m = re.search(r'(today|now)?\s*\+?\s*(?:after\s+)?([0-9]+)\s*days?', expr, re.IGNORECASE)
        if date_m and ("day" in expr.lower() or "today" in expr.lower() or "after" in expr.lower()):
            n_days = int(date_m.group(2))
            today = datetime.date.today()
            target_date = today + datetime.timedelta(days=n_days)
            days_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            day_name = days_names[target_date.weekday()]
            elapsed = (time.perf_counter() - start_t) * 1000
            return ToolResult(success=True, data={
                "result": str(target_date),
                "day_of_week": day_name,
                "days_added": n_days,
                "formatted": f"After {n_days} days from today ({days_names[today.weekday()]}) will be {day_name} ({target_date})"
            }, execution_time_ms=elapsed)

        # 4. Geometry shapes
        circle_m = re.search(r'circle\s*area\s*(?:r|radius)?\s*=?\s*([0-9\.]+)', expr, re.IGNORECASE)
        if circle_m:
            r = float(circle_m.group(1))
            area = math.pi * (r ** 2)
            elapsed = (time.perf_counter() - start_t) * 1000
            return ToolResult(success=True, data={"result": round(area, 4), "radius": r, "type": "circle_area"}, execution_time_ms=elapsed)

        # 5. Standard clean arithmetic
        clean_expr = expr.replace("×", "*").replace("÷", "/").replace("^", "**").replace("x", "*")
        clean_expr = re.sub(r'[^0-9\+\-\*\/\(\)\.\s]', '', clean_expr).strip()
        if not clean_expr:
            return ToolResult(success=False, data=None, error=f"Invalid arithmetic expression: {expr}")

        try:
            # Safe eval with restricted globals
            val = eval(clean_expr, {"__builtins__": None, "math": math}, {})
            if isinstance(val, float) and val.is_integer():
                val = int(val)
            elapsed = (time.perf_counter() - start_t) * 1000
            return ToolResult(success=True, data={"result": val, "expression": clean_expr}, execution_time_ms=elapsed)
        except Exception as e:
            return ToolResult(success=False, data=None, error=f"Calculation error: {str(e)}")

class UnitConvertTool(BaseTool):
    """Instant conversion between digital storage, time, speed, temperature, and length units."""
    def __init__(self):
        super().__init__(
            name="unit_convert",
            description="Instant conversion between data storage, time, length, and temperature units.",
            risk_level="LOW",
            requires_confirmation=False
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "value": {"type": "number", "description": "Numeric value to convert"},
                "from_unit": {"type": "string", "description": "Source unit (e.g. 'MB', 'GB', 'ms', 's', 'C', 'F', 'km', 'mile')"},
                "to_unit": {"type": "string", "description": "Target unit (e.g. 'GB', 'MB', 's', 'ms', 'F', 'C', 'm', 'km')"}
            },
            "required": ["value", "from_unit", "to_unit"]
        }

    async def execute(self, **kwargs) -> ToolResult:
        try:
            val = float(kwargs.get("value", 0))
            from_u = str(kwargs.get("from_unit", "")).strip().lower()
            to_u = str(kwargs.get("to_unit", "")).strip().lower()

            start_t = time.perf_counter()

            # Data storage (bytes multiplier)
            storage_units = {
                "b": 1, "byte": 1, "bytes": 1,
                "kb": 1024, "mb": 1024**2, "gb": 1024**3, "tb": 1024**4
            }
            if from_u in storage_units and to_u in storage_units:
                bytes_val = val * storage_units[from_u]
                res = bytes_val / storage_units[to_u]
                elapsed = (time.perf_counter() - start_t) * 1000
                return ToolResult(success=True, data={"result": round(res, 4), "from": f"{val} {from_u}", "to": f"{round(res, 4)} {to_u}"}, execution_time_ms=elapsed)

            # Time units (seconds multiplier)
            time_units = {
                "ms": 0.001, "millisecond": 0.001, "s": 1.0, "sec": 1.0, "second": 1.0,
                "min": 60.0, "minute": 60.0, "hr": 3600.0, "hour": 3600.0, "day": 86400.0
            }
            if from_u in time_units and to_u in time_units:
                sec_val = val * time_units[from_u]
                res = sec_val / time_units[to_u]
                elapsed = (time.perf_counter() - start_t) * 1000
                return ToolResult(success=True, data={"result": round(res, 4), "from": f"{val} {from_u}", "to": f"{round(res, 4)} {to_u}"}, execution_time_ms=elapsed)

            # Temperature
            if from_u in ["c", "celsius"] and to_u in ["f", "fahrenheit"]:
                res = (val * 9.0 / 5.0) + 32.0
                elapsed = (time.perf_counter() - start_t) * 1000
                return ToolResult(success=True, data={"result": round(res, 2), "unit": "°F"}, execution_time_ms=elapsed)
            if from_u in ["f", "fahrenheit"] and to_u in ["c", "celsius"]:
                res = (val - 32.0) * 5.0 / 9.0
                elapsed = (time.perf_counter() - start_t) * 1000
                return ToolResult(success=True, data={"result": round(res, 2), "unit": "°C"}, execution_time_ms=elapsed)

            # Length (meters multiplier)
            length_units = {
                "mm": 0.001, "cm": 0.01, "m": 1.0, "meter": 1.0, "km": 1000.0,
                "inch": 0.0254, "foot": 0.3048, "ft": 0.3048, "mile": 1609.344
            }
            if from_u in length_units and to_u in length_units:
                m_val = val * length_units[from_u]
                res = m_val / length_units[to_u]
                elapsed = (time.perf_counter() - start_t) * 1000
                return ToolResult(success=True, data={"result": round(res, 4), "from": f"{val} {from_u}", "to": f"{round(res, 4)} {to_u}"}, execution_time_ms=elapsed)

            return ToolResult(success=False, data=None, error=f"Unsupported unit conversion from '{from_u}' to '{to_u}'")
        except Exception as e:
            return ToolResult(success=False, data=None, error=f"Conversion error: {str(e)}")

class TextCompactTool(BaseTool):
    """Compresses, strips boilerplate and whitespace from long text/data to keep model context small."""
    def __init__(self):
        super().__init__(
            name="text_compact",
            description="Compacts, strips extra lines, and summarizes text to minimize model context token footprint.",
            risk_level="LOW",
            requires_confirmation=False
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text or data to compact"},
                "max_chars": {"type": "integer", "description": "Maximum character limit (default 1000)"},
                "mode": {"type": "string", "description": "Mode: 'strip_whitespace', 'extract_lines', 'json_minify'"}
            },
            "required": ["text"]
        }

    async def execute(self, **kwargs) -> ToolResult:
        text = str(kwargs.get("text", "")).strip()
        max_chars = int(kwargs.get("max_chars", 1000))
        mode = str(kwargs.get("mode", "strip_whitespace")).lower()

        start_t = time.perf_counter()

        if mode == "json_minify":
            try:
                import json
                parsed = json.loads(text)
                compact = json.dumps(parsed, separators=(',', ':'), ensure_ascii=False)
            except Exception:
                compact = re.sub(r'\s+', ' ', text)
        else:
            # Strip excessive empty lines and spaces
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            compact = "\n".join(lines)

        original_len = len(text)
        if len(compact) > max_chars:
            compact = compact[:max_chars] + f"... [Truncated {len(compact)-max_chars} chars for token efficiency]"

        elapsed = (time.perf_counter() - start_t) * 1000
        return ToolResult(
            success=True,
            data={
                "compacted_text": compact,
                "original_chars": original_len,
                "compacted_chars": len(compact),
                "savings_percent": round((1.0 - len(compact)/max(original_len, 1)) * 100, 1)
            },
            execution_time_ms=elapsed
        )

class RegexExtractTool(BaseTool):
    """High-speed safe regular expression pattern extraction and matching from text."""
    def __init__(self):
        super().__init__(
            name="regex_extract",
            description="Extracts patterns (emails, URLs, IPs, dates, tokens) from text using regular expressions.",
            risk_level="LOW",
            requires_confirmation=False
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to search within"},
                "pattern": {"type": "string", "description": "Regex pattern or preset ('email', 'url', 'ip', 'date')"},
                "max_matches": {"type": "integer", "description": "Maximum matches to return (default 10)"}
            },
            "required": ["text", "pattern"]
        }

    async def execute(self, **kwargs) -> ToolResult:
        text = str(kwargs.get("text", ""))
        pattern = str(kwargs.get("pattern", "")).strip()
        max_m = int(kwargs.get("max_matches", 10))

        start_t = time.perf_counter()

        presets = {
            "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            "url": r"https?://[^\s<>\"']+|www\.[^\s<>\"']+",
            "ip": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
            "date": r"\b\d{4}[-/]\d{2}[-/]\d{2}\b|\b\d{2}[-/]\d{2}[-/]\d{4}\b"
        }
        regex_pat = presets.get(pattern.lower(), pattern)

        try:
            matches = re.findall(regex_pat, text)
            matches = matches[:max_m]
            elapsed = (time.perf_counter() - start_t) * 1000
            return ToolResult(
                success=True,
                data={"matches": matches, "count": len(matches), "pattern_used": regex_pat},
                execution_time_ms=elapsed
            )
        except Exception as e:
            return ToolResult(success=False, data=None, error=f"Regex execution error: {str(e)}")
