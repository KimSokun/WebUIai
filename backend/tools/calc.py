import ast
import operator
import re
import math
import time
from typing import Any, Dict, Optional, Tuple
from backend.tools.base import BaseTool, ToolResult

def _safe_pow(a, b):
    if abs(b) > 1000:
        raise ValueError("Exponent too large (maximum allowed exponent is 1000)")
    return operator.pow(a, b)

SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: _safe_pow,
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

SAFE_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "pow": pow,
    "sqrt": math.sqrt,
}

class CalculatorTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="calculator",
            description="Calculate mathematical expressions, percentages, and financial numbers accurately without code execution.",
            risk_level="LOW",
            requires_confirmation=False
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The math expression to evaluate, e.g. '24 * 17', '1/2 + 1/4', '20% of 350', or '3x + 7 = 22'"
                }
            },
            "required": ["expression"]
        }

    @staticmethod
    def normalize_math_text(text: str) -> str:
        s = text.strip()
        s = re.sub(r'^(?:solve(?:\s+for\s+[a-zA-Z])?|calculate|calc|evaluate|what is|គណនា)\s*[:=]?\s*', '', s, flags=re.IGNORECASE).strip()
        # Normalize unicode math symbols
        s = s.replace("×", "*").replace("✕", "*").replace("✖", "*")
        s = s.replace("÷", "/")
        s = s.replace("−", "-").replace("–", "-").replace("—", "-")

        # Implicit multiplication for variable terms (e.g. 3x -> 3*x)
        s = re.sub(r'(\d+(?:\.\d+)?)\s*([a-zA-Z])', r'\1*\2', s)

        # Percentage normalization: 20% of 350 -> (20 / 100 * 350)
        s = re.sub(r'(\d+(?:\.\d+)?)\s*%\s*(?:of)?\s*(\d+(?:\.\d+)?)', r'(\1 / 100 * \2)', s)
        # Standalone percentage: 20% -> (20 / 100)
        s = re.sub(r'(\d+(?:\.\d+)?)\s*%', r'(\1 / 100)', s)
        return s.strip()

    @classmethod
    def _eval_ast_node(cls, node: ast.AST, var_dict: Optional[dict] = None) -> float:
        if var_dict is None:
            var_dict = {}

        if isinstance(node, ast.Expression):
            return cls._eval_ast_node(node.body, var_dict)
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return float(node.value)
            raise ValueError(f"Unsupported constant type: {type(node.value)}")
        elif isinstance(node, ast.Name):
            if node.id in var_dict:
                return float(var_dict[node.id])
            elif node.id in SAFE_FUNCTIONS:
                return SAFE_FUNCTIONS[node.id]
            raise ValueError(f"Undefined variable or unauthorized identifier: {node.id}")
        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in SAFE_OPERATORS:
                raise ValueError(f"Unsupported binary operator: {op_type}")
            left = cls._eval_ast_node(node.left, var_dict)
            right = cls._eval_ast_node(node.right, var_dict)
            if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
                raise ZeroDivisionError("Division by zero")
            return float(SAFE_OPERATORS[op_type](left, right))
        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in SAFE_OPERATORS:
                raise ValueError(f"Unsupported unary operator: {op_type}")
            operand = cls._eval_ast_node(node.operand, var_dict)
            return float(SAFE_OPERATORS[op_type](operand))
        elif isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in SAFE_FUNCTIONS:
                raise ValueError(f"Unauthorized function call: {ast.dump(node)}")
            func = SAFE_FUNCTIONS[node.func.id]
            args = [cls._eval_ast_node(arg, var_dict) for arg in node.args]
            return float(func(*args))
        else:
            raise ValueError(f"Disallowed syntax node: {type(node).__name__}")

    @classmethod
    def _solve_word_problem(cls, text: str) -> Optional[str]:
        lower = text.lower().strip()

        # 1. Discount / Percentage off (e.g. "$80 with 15% discount", "costs 80$ and has 15% discount", "បញ្ចុះតម្លៃ 15% លើ 80")
        discount_match = re.search(r'(?:cost|price|is|costs)?\s*[\$]?\s*(\d+(?:\.\d+)?)\s*(?:[\$]|usd|ដុល្លារ)?[\w\s,]*?(?:has\s+a\s+)?(\d+(?:\.\d+)?)\s*%\s*(?:discount|off|បញ្ចុះតម្លៃ)', lower)
        if not discount_match:
            discount_match = re.search(r'(?:discount\s+of|discount|បញ្ចុះតម្លៃ)\s*(\d+(?:\.\d+)?)\s*%\s*(?:on|off|លើ)?\s*[\$]?\s*(\d+(?:\.\d+)?)\s*(?:[\$]|usd|ដុល្លារ)?', lower)
            if discount_match:
                disc_pct, price = float(discount_match.group(1)), float(discount_match.group(2))
            else:
                disc_pct, price = None, None
        else:
            price, disc_pct = float(discount_match.group(1)), float(discount_match.group(2))

        if price is not None and disc_pct is not None:
            discount_amount = price * (disc_pct / 100.0)
            final_price = price - discount_amount
            final_str = str(int(round(final_price))) if abs(final_price - round(final_price)) < 1e-9 else f"{final_price:.2f}"
            return f"${final_str} (Original: ${price:g}, Discount: {disc_pct:g}% / -${discount_amount:g})"

        # 2. Geometry - Rectangle Area (e.g. "rectangle length 12 cm width 5 cm", "ចតុកោណកែង បណ្តោយ 12 ទទឹង 5")
        if "rectangle" in lower or "ចតុកោណកែង" in lower or "ចតុកោណ" in lower or ("length" in lower and "width" in lower) or ("បណ្តោយ" in lower and "ទទឹង" in lower) or ("បណ្ដោយ" in lower and "ទទឹង" in lower):
            len_match = re.search(r'(?:length|បណ្តោយ|បណ្ដោយ)\s*(?:of|is|:|=|ស្មើ)?\s*(\d+(?:\.\d+)?)', lower)
            wid_match = re.search(r'(?:width|ទទឹង)\s*(?:of|is|:|=|ស្មើ)?\s*(\d+(?:\.\d+)?)', lower)
            if len_match and wid_match:
                l = float(len_match.group(1))
                w = float(wid_match.group(1))
                area = l * w
                area_str = str(int(round(area))) if abs(area - round(area)) < 1e-9 else f"{area:g}"
                return f"{area_str} (Length: {l:g}, Width: {w:g})"

        # 3. Geometry - Triangle Area
        if "triangle" in lower or "ត្រីកោណ" in lower:
            base_match = re.search(r'(?:base|បាត)\s*(?:of|is|:|=|ស្មើ)?\s*(\d+(?:\.\d+)?)', lower)
            h_match = re.search(r'(?:height|កម្ពស់)\s*(?:of|is|:|=|ស្មើ)?\s*(\d+(?:\.\d+)?)', lower)
            if base_match and h_match:
                b = float(base_match.group(1))
                h = float(h_match.group(1))
                area = 0.5 * b * h
                area_str = str(int(round(area))) if abs(area - round(area)) < 1e-9 else f"{area:g}"
                return f"{area_str} (Base: {b:g}, Height: {h:g})"

        # 4. Geometry - Circle Area
        if "circle" in lower or "រង្វង់" in lower:
            r_match = re.search(r'(?:radius|កាំ)\s*(?:of|is|:|=|ស្មើ)?\s*(\d+(?:\.\d+)?)', lower)
            if r_match:
                r = float(r_match.group(1))
                area = math.pi * (r ** 2)
                return f"{area:.2f} (Radius: {r:g})"

        return None

    @classmethod
    def _solve_linear_equation(cls, raw_eq: str) -> Optional[str]:
        if "=" not in raw_eq:
            return None
        parts = raw_eq.split("=")
        if len(parts) != 2:
            return None

        left_str = cls.normalize_math_text(parts[0])
        right_str = cls.normalize_math_text(parts[1])

        var_matches = list(set(re.findall(r'\b([a-zA-Z])\b', left_str + " " + right_str)))
        var_matches = [v for v in var_matches if v not in SAFE_FUNCTIONS]
        if len(var_matches) != 1:
            return None

        var_name = var_matches[0]
        try:
            left_tree = ast.parse(left_str, mode='eval')
            right_tree = ast.parse(right_str, mode='eval')

            # f(0) = c
            c = cls._eval_ast_node(left_tree, {var_name: 0.0}) - cls._eval_ast_node(right_tree, {var_name: 0.0})
            # f(1) = m + c
            f1 = cls._eval_ast_node(left_tree, {var_name: 1.0}) - cls._eval_ast_node(right_tree, {var_name: 1.0})
            m = f1 - c

            if abs(m) < 1e-12:
                return None

            x_val = -c / m
            if abs(x_val - round(x_val)) < 1e-9:
                val_str = str(int(round(x_val)))
            else:
                val_str = f"{round(x_val, 6):g}"
            return f"{var_name} = {val_str}"
        except Exception:
            return None

    async def execute(self, expression: str = "", **kwargs) -> ToolResult:
        start_time = time.time()
        if not expression or not isinstance(expression, str):
            err_struct = {
                "success": False,
                "tool": "calculator",
                "error_code": "INVALID_EXPRESSION",
                "message": "Invalid mathematical expression"
            }
            return ToolResult(
                success=False,
                data=err_struct,
                error="Invalid mathematical expression",
                execution_time_ms=(time.time() - start_time) * 1000
            )

        # 1. Check natural language word problems (discounts, geometry area)
        wp_res = self._solve_word_problem(expression)
        if wp_res:
            return ToolResult(
                success=True,
                data=wp_res,
                execution_time_ms=(time.time() - start_time) * 1000
            )

        norm = self.normalize_math_text(expression)

        # 2. Check for linear algebraic equation
        eq_res = self._solve_linear_equation(norm)
        if eq_res:
            return ToolResult(
                success=True,
                data=eq_res,
                execution_time_ms=(time.time() - start_time) * 1000
            )

        # 2. Deterministic AST arithmetic evaluation
        try:
            tree = ast.parse(norm, mode='eval')
            num = self._eval_ast_node(tree)
            if abs(num - round(num)) < 1e-9:
                val_str = str(int(round(num)))
            else:
                val_str = f"{round(num, 6):g}"

            return ToolResult(
                success=True,
                data=val_str,
                execution_time_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            err_struct = {
                "success": False,
                "tool": "calculator",
                "error_code": "INVALID_EXPRESSION",
                "message": "Invalid mathematical expression"
            }
            return ToolResult(
                success=False,
                data=err_struct,
                error="Invalid mathematical expression",
                execution_time_ms=(time.time() - start_time) * 1000
            )
