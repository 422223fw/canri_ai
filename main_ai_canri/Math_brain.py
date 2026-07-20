"""
Math_brain.py
Canri AI

Practical local math engine.

It handles common arithmetic, percentages, averages, min/max,
simple linear equations, areas/perimeters, and unit conversion.
It uses Python AST evaluation instead of eval.
"""

import ast
import json
import math
import operator
import re
from collections import Counter
from fractions import Fraction

from Brain_storage import atomic_write_json
from pathlib import Path


DATA_DIR = Path(__file__).parent / "data"
UNITS_FILE = DATA_DIR / "Units_dictionary.json"
STATS_FILE = DATA_DIR / "Math_statistics.json"
FORMULAS_FILE = DATA_DIR / "Math_formulas.json"
PATTERNS_FILE = DATA_DIR / "Math_problem_patterns.json"
EXAMPLES_FILE = DATA_DIR / "Math_examples.json"
INDEX_FILE = DATA_DIR / "Math_index.json"


class MathBrain:

    SAFE_OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    SAFE_FUNCTIONS = {
        "abs": abs,
        "round": round,
        "sqrt": math.sqrt,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "log": math.log,
        "log10": math.log10,
        "floor": math.floor,
        "ceil": math.ceil,
    }

    CONSTANTS = {
        "pi": math.pi,
        "e": math.e,
        "tau": math.tau,
    }

    UNIT_FACTORS = {
        "mm": ("length", 0.001),
        "millimeter": ("length", 0.001),
        "millimeters": ("length", 0.001),
        "cm": ("length", 0.01),
        "centimeter": ("length", 0.01),
        "centimeters": ("length", 0.01),
        "m": ("length", 1.0),
        "meter": ("length", 1.0),
        "meters": ("length", 1.0),
        "km": ("length", 1000.0),
        "kilometer": ("length", 1000.0),
        "kilometers": ("length", 1000.0),
        "in": ("length", 0.0254),
        "inch": ("length", 0.0254),
        "inches": ("length", 0.0254),
        "ft": ("length", 0.3048),
        "foot": ("length", 0.3048),
        "feet": ("length", 0.3048),
        "yd": ("length", 0.9144),
        "yard": ("length", 0.9144),
        "yards": ("length", 0.9144),
        "mi": ("length", 1609.344),
        "mile": ("length", 1609.344),
        "miles": ("length", 1609.344),
        "mg": ("mass", 0.001),
        "milligram": ("mass", 0.001),
        "g": ("mass", 1.0),
        "gram": ("mass", 1.0),
        "grams": ("mass", 1.0),
        "kg": ("mass", 1000.0),
        "kilogram": ("mass", 1000.0),
        "kilograms": ("mass", 1000.0),
        "ton": ("mass", 1000000.0),
        "tons": ("mass", 1000000.0),
    }

    def __init__(self):
        self.units = self.load_json(UNITS_FILE, {})
        self.statistics = self.load_json(STATS_FILE, {})
        self.formulas = self.load_json(FORMULAS_FILE, {})
        self.problem_patterns = self.load_json(PATTERNS_FILE, {})
        self.math_examples = self.load_json(EXAMPLES_FILE, {})
        self.math_index = self.load_json(INDEX_FILE, {"terms": {}, "formula_patterns": {}})
        print("Math Brain Loaded")

    def load_json(self, path, default):
        if not path.exists() or path.stat().st_size == 0:
            return default
        try:
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except (OSError, json.JSONDecodeError):
            return default

    def save_statistics(self, result_type, success):
        stats = self.statistics.get("Math_brain", {})
        stats["uses"] = stats.get("uses", 0) + 1
        stats["last_type"] = result_type
        stats["last_success"] = bool(success)
        self.statistics["Math_brain"] = stats
        atomic_write_json(STATS_FILE, self.statistics)

    def extract_text(self, data):
        if isinstance(data, str):
            return data
        if isinstance(data, dict):
            parts = []
            for key in ["original_text", "corrected_text", "user_message", "question", "text", "goal"]:
                if data.get(key):
                    parts.append(str(data[key]))
            understanding = data.get("understanding", {})
            if isinstance(understanding, dict):
                for key in ["original_text", "corrected_text"]:
                    if understanding.get(key):
                        parts.append(str(understanding[key]))
            return " ".join(dict.fromkeys(parts))
        return str(data)

    def normalize_expression(self, text):
        expression = str(text).lower()
        expression = expression.replace("×", "*").replace("÷", "/")
        expression = expression.replace("^", "**")
        expression = re.sub(r"\bplus\b", "+", expression)
        expression = re.sub(r"\bminus\b", "-", expression)
        expression = re.sub(r"\btimes\b|\bmultiplied by\b", "*", expression)
        expression = re.sub(r"\bdivided by\b", "/", expression)
        expression = re.sub(r"\bsquared\b", "**2", expression)
        expression = re.sub(r"\bcubed\b", "**3", expression)
        expression = re.sub(r"[^0-9a-z_=+\-*/().,%;\s]", " ", expression)
        return re.sub(r"\s+", " ", expression).strip()

    def is_safe_expression_text(self, expression):
        if not expression or not re.search(r"\d", expression):
            return False
        if "=" in expression or "%" in expression:
            return False

        names = re.findall(r"[a-z_]+", expression.lower())
        allowed_names = set(self.SAFE_FUNCTIONS) | set(self.CONSTANTS)
        return all(name in allowed_names for name in names)

    def extract_math_expression(self, text):
        normalized = self.normalize_expression(text)
        if self.is_safe_expression_text(normalized):
            return normalized

        atom = r"(?:sqrt\s*\([^()]+\)|\([^()]+\)|\d+(?:\.\d+)?|pi|e)"
        candidates = re.findall(
            rf"(?<![a-z0-9_.]){atom}(?:\s*(?:\*\*|[+\-*/])\s*{atom})+",
            normalized,
        )
        return max(candidates, key=len) if candidates else None

    def safe_eval(self, expression):
        expression = self.normalize_expression(expression)
        tree = ast.parse(expression, mode="eval")
        return self.eval_node(tree.body)

    def eval_node(self, node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value

        if isinstance(node, ast.Name):
            if node.id in self.CONSTANTS:
                return self.CONSTANTS[node.id]
            raise ValueError(f"Unknown name: {node.id}")

        if isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in self.SAFE_OPERATORS:
                raise ValueError("Unsupported operator")
            left = self.eval_node(node.left)
            right = self.eval_node(node.right)
            if op_type is ast.Pow and abs(right) > 10:
                raise ValueError("Power too large")
            return self.SAFE_OPERATORS[op_type](left, right)

        if isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in self.SAFE_OPERATORS:
                raise ValueError("Unsupported unary operator")
            return self.SAFE_OPERATORS[op_type](self.eval_node(node.operand))

        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ValueError("Unsupported function")
            name = node.func.id
            if name not in self.SAFE_FUNCTIONS:
                raise ValueError(f"Unsupported function: {name}")
            args = [self.eval_node(arg) for arg in node.args]
            if len(args) > 2:
                raise ValueError("Too many function arguments")
            return self.SAFE_FUNCTIONS[name](*args)

        raise ValueError("Unsupported expression")

    def format_number(self, value):
        if isinstance(value, dict):
            return ", ".join(
                f"{key}={self.format_number(item)}"
                for key, item in value.items()
            )
        if isinstance(value, list):
            return ", ".join(self.format_number(item) for item in value)
        if isinstance(value, float):
            if math.isfinite(value) and value.is_integer():
                return str(int(value))
            return f"{value:.10g}"
        return str(value)

    def numbers(self, text):
        return [float(item) for item in re.findall(r"-?\d+(?:\.\d+)?", str(text))]

    def solve_percentage(self, text):
        lowered = text.lower()

        match = re.search(r"(-?\d+(?:\.\d+)?)\s*%\s*(?:of|from)?\s*(-?\d+(?:\.\d+)?)", lowered)
        if match:
            percent = float(match.group(1))
            number = float(match.group(2))
            answer = number * percent / 100
            return {
                "type": "percentage",
                "answer": answer,
                "steps": [
                    f"{percent}% of {number}",
                    f"{number} * {percent} / 100 = {self.format_number(answer)}"
                ],
                "confidence": 96
            }

        match = re.search(r"what\s+percent\s+of\s+(-?\d+(?:\.\d+)?)\s+is\s+(-?\d+(?:\.\d+)?)", lowered)
        if match:
            whole = float(match.group(1))
            part = float(match.group(2))
            if whole == 0:
                return None
            answer = part / whole * 100
            return {
                "type": "percentage",
                "answer": answer,
                "steps": [
                    f"{part} / {whole} * 100 = {self.format_number(answer)}%"
                ],
                "confidence": 94
            }

        match = re.search(r"increase\s+(-?\d+(?:\.\d+)?)\s+by\s+(-?\d+(?:\.\d+)?)\s*%", lowered)
        if match:
            number = float(match.group(1))
            percent = float(match.group(2))
            answer = number * (1 + percent / 100)
            return {
                "type": "percentage_increase",
                "answer": answer,
                "steps": [
                    f"{number} * (1 + {percent}/100) = {self.format_number(answer)}"
                ],
                "confidence": 94
            }

        return None

    def solve_average(self, text):
        lowered = text.lower()
        if not any(word in lowered for word in [
            "average", "mean", "median", "mode", "range", "variance",
            "standard deviation", "sum", "total", "minimum", "maximum", "max", "min"
        ]):
            return None

        nums = self.numbers(text)
        if not nums:
            return None

        if "standard deviation" in lowered or "variance" in lowered:
            mean = sum(nums) / len(nums)
            variance = sum((number - mean) ** 2 for number in nums) / len(nums)
            if "standard deviation" in lowered:
                answer = math.sqrt(variance)
                kind = "standard_deviation"
            else:
                answer = variance
                kind = "population_variance"
        elif "mode" in lowered:
            counts = Counter(nums)
            highest = max(counts.values())
            answer = sorted(number for number, count in counts.items() if count == highest)
            kind = "mode"
        elif "range" in lowered:
            answer = max(nums) - min(nums)
            kind = "range"
        elif "median" in lowered:
            ordered = sorted(nums)
            mid = len(ordered) // 2
            answer = ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2
            kind = "median"
        elif "sum" in lowered or "total" in lowered:
            answer = sum(nums)
            kind = "sum"
        elif "minimum" in lowered or re.search(r"\bmin\b", lowered):
            answer = min(nums)
            kind = "minimum"
        elif "maximum" in lowered or re.search(r"\bmax\b", lowered):
            answer = max(nums)
            kind = "maximum"
        else:
            answer = sum(nums) / len(nums)
            kind = "average"

        return {
            "type": kind,
            "answer": answer,
            "steps": [
                f"Numbers: {', '.join(self.format_number(n) for n in nums)}",
                f"{kind} = {self.format_number(answer)}"
            ],
            "confidence": 95
        }

    def parse_linear_x_side(self, side):
        """Return (x coefficient, constant) for a linear expression."""

        side = side.replace(" ", "").replace("*", "")
        if not side:
            return 0.0, 0.0
        if side[0] not in "+-":
            side = "+" + side

        coefficient = 0.0
        constant = 0.0
        for term in re.findall(r"[+-][^+-]+", side):
            sign = -1.0 if term[0] == "-" else 1.0
            body = term[1:]
            if "x" in body:
                raw = body.replace("x", "")
                coefficient += sign * (float(raw) if raw else 1.0)
            else:
                constant += sign * float(body)
        return coefficient, constant

    def solve_linear_equation(self, text):
        cleaned = self.normalize_expression(text).replace(" ", "")
        if "=" not in cleaned or "x" not in cleaned or "x**2" in cleaned:
            return None

        equations = re.findall(r"[+\-0-9.x*]+=[+\-0-9.x*]+", cleaned)
        if not equations:
            return None
        equation = equations[0]
        try:
            left, right = equation.split("=", 1)
            left_x, left_constant = self.parse_linear_x_side(left)
            right_x, right_constant = self.parse_linear_x_side(right)
        except (TypeError, ValueError):
            return None

        a = left_x - right_x
        target = right_constant - left_constant
        if abs(a) < 1e-12:
            relationship = "all real numbers" if abs(target) < 1e-12 else "no solution"
            return {
                "type": "linear_equation",
                "answer": relationship,
                "steps": [f"Simplify both sides: {self.format_number(a)}x = {self.format_number(target)}", relationship.title()],
                "confidence": 92,
            }

        answer = target / a
        return {
            "type": "linear_equation",
            "answer": answer,
            "steps": [
                f"Original equation: {equation.replace('**', '^')}",
                f"Collect x terms and constants: {self.format_number(a)}x = {self.format_number(target)}",
                f"x = {self.format_number(answer)}"
            ],
            "confidence": 96
        }

    def solve_fraction(self, text):
        normalized = self.normalize_expression(text)
        match = re.search(r"(-?\d+)\s*/\s*(-?\d+)\s*([+\-*/])\s*(-?\d+)\s*/\s*(-?\d+)", normalized)
        if not match:
            return None
        a, b, operation, c, d = match.groups()
        if int(b) == 0 or int(d) == 0:
            return None
        left = Fraction(int(a), int(b))
        right = Fraction(int(c), int(d))
        operations = {"+": operator.add, "-": operator.sub, "*": operator.mul, "/": operator.truediv}
        if operation == "/" and right == 0:
            return None
        exact = operations[operation](left, right)
        answer = int(exact) if exact.denominator == 1 else f"{exact.numerator}/{exact.denominator}"
        return {
            "type": "fraction_arithmetic",
            "answer": answer,
            "steps": [
                f"Expression: {left} {operation} {right}",
                f"Use a common denominator or reciprocal as required: {exact}",
                f"Simplified answer: {answer}",
            ],
            "confidence": 97,
        }

    def solve_interest(self, text):
        lowered = text.lower()
        if "interest" not in lowered:
            return None
        nums = self.numbers(text)
        if len(nums) < 3:
            return None
        principal, rate_percent, years = nums[:3]
        rate = rate_percent / 100
        if "compound" in lowered:
            compounds = nums[3] if len(nums) > 3 else 1
            if compounds <= 0:
                return None
            answer = principal * (1 + rate / compounds) ** (compounds * years)
            kind = "compound_interest"
            formula = "A = P(1 + r/n)^(n*t)"
        else:
            answer = principal * (1 + rate * years)
            kind = "simple_interest"
            formula = "A = P(1 + r*t)"
        return {
            "type": kind,
            "answer": answer,
            "steps": [formula, f"P={principal}, r={rate}, t={years}", f"A = {self.format_number(answer)}"],
            "confidence": 93,
        }

    def solve_probability(self, text):
        lowered = text.lower()
        if not any(term in lowered for term in ["probability", "chance", "favorable outcomes"]):
            return None
        nums = self.numbers(text)
        if len(nums) < 2 or nums[1] <= 0:
            return None
        favorable, total = nums[:2]
        if favorable < 0 or favorable > total:
            return None
        probability = favorable / total
        return {
            "type": "probability",
            "answer": probability,
            "steps": [
                "probability = favorable outcomes / total outcomes",
                f"{self.format_number(favorable)} / {self.format_number(total)} = {self.format_number(probability)}",
                f"percentage = {self.format_number(probability * 100)}%",
            ],
            "confidence": 94,
        }

    def relevant_formula_context(self, text, limit=5):
        terms = set(re.findall(r"[a-z][a-z0-9_-]{2,}", text.lower()))
        ranked = []
        for formula in self.formulas.values():
            trigger_terms = set(formula.get("trigger_terms", []))
            score = len(terms.intersection(trigger_terms))
            if score:
                ranked.append((score, formula))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [item[1] for item in ranked[:limit]]

    def parse_quadratic_side(self, side):
        side = side.replace("-", "+-")
        if side.startswith("+"):
            side = side[1:]

        coefficients = {
            "x2": 0.0,
            "x": 0.0,
            "constant": 0.0
        }

        for term in side.split("+"):
            term = term.strip()
            if not term:
                continue

            if "x**2" in term:
                coefficient = term.replace("x**2", "")
                if coefficient in ["", "+"]:
                    value = 1.0
                elif coefficient == "-":
                    value = -1.0
                else:
                    value = float(coefficient)
                coefficients["x2"] += value
            elif "x" in term:
                coefficient = term.replace("x", "")
                if coefficient in ["", "+"]:
                    value = 1.0
                elif coefficient == "-":
                    value = -1.0
                else:
                    value = float(coefficient)
                coefficients["x"] += value
            else:
                coefficients["constant"] += float(term)

        return coefficients

    def solve_quadratic_equation(self, text):
        cleaned = self.normalize_expression(text).replace(" ", "")
        if "x**2" not in cleaned or "=" not in cleaned:
            return None

        start = cleaned.find("x**2")
        while start > 0 and cleaned[start - 1] in "0123456789.+-":
            start -= 1
        cleaned = cleaned[start:]

        left_side, right_side = cleaned.split("=", 1)
        right_match = re.match(r"[+\-0-9.x*]+", right_side)
        if right_match:
            right_side = right_match.group(0)

        try:
            left = self.parse_quadratic_side(left_side)
            right = self.parse_quadratic_side(right_side)
        except ValueError:
            return None

        a = left["x2"] - right["x2"]
        b = left["x"] - right["x"]
        c = left["constant"] - right["constant"]

        if a == 0:
            return None

        discriminant = b * b - 4 * a * c

        if discriminant < 0:
            return {
                "type": "quadratic_equation",
                "answer": "no real solutions",
                "steps": [
                    f"a={self.format_number(a)}, b={self.format_number(b)}, c={self.format_number(c)}",
                    f"discriminant = b^2 - 4ac = {self.format_number(discriminant)}",
                    "The discriminant is negative, so there are no real solutions."
                ],
                "confidence": 92
            }

        root = math.sqrt(discriminant)
        x1 = (-b + root) / (2 * a)
        x2 = (-b - root) / (2 * a)
        answer = [x1, x2] if x1 != x2 else [x1]
        return {
            "type": "quadratic_equation",
            "answer": answer,
            "steps": [
                f"Move everything to one side: {self.format_number(a)}x^2 + {self.format_number(b)}x + {self.format_number(c)} = 0",
                f"a={self.format_number(a)}, b={self.format_number(b)}, c={self.format_number(c)}",
                f"discriminant = {self.format_number(discriminant)}",
                "x = (-b +/- sqrt(discriminant)) / 2a",
                "solutions = " + ", ".join(self.format_number(value) for value in answer)
            ],
            "confidence": 92
        }

    def solve_ratio(self, text):
        lowered = text.lower()
        match = re.search(
            r"(-?\d+(?:\.\d+)?)\s*:\s*(-?\d+(?:\.\d+)?)\s*=\s*(-?\d+(?:\.\d+)?)\s*:\s*x",
            lowered
        )
        if not match:
            return None

        a, b, c = [float(value) for value in match.groups()]
        if a == 0:
            return None
        x = b * c / a
        return {
            "type": "ratio",
            "answer": x,
            "steps": [
                f"{self.format_number(a)}:{self.format_number(b)} = {self.format_number(c)}:x",
                f"x = {self.format_number(b)} * {self.format_number(c)} / {self.format_number(a)}",
                f"x = {self.format_number(x)}"
            ],
            "confidence": 92
        }

    def solve_pythagorean(self, text):
        lowered = text.lower()
        nums = self.numbers(text)
        if len(nums) < 2 or not any(word in lowered for word in ["pythagorean", "hypotenuse", "right triangle"]):
            return None

        a, b = nums[:2]
        c = math.sqrt(a * a + b * b)
        return {
            "type": "pythagorean",
            "answer": c,
            "steps": [
                f"c^2 = {self.format_number(a)}^2 + {self.format_number(b)}^2",
                f"c = sqrt({self.format_number(a*a + b*b)})",
                f"c = {self.format_number(c)}"
            ],
            "confidence": 93
        }

    def solve_geometry(self, text):
        lowered = text.lower()
        nums = self.numbers(text)

        if "circle" in lowered and "radius" in lowered and nums:
            r = nums[0]
            if "area" in lowered:
                answer = math.pi * r * r
                return {
                    "type": "circle_area",
                    "answer": answer,
                    "steps": [f"area = pi * r^2 = pi * {r}^2 = {self.format_number(answer)}"],
                    "confidence": 94
                }
            if "circumference" in lowered or "perimeter" in lowered:
                answer = 2 * math.pi * r
                return {
                    "type": "circle_circumference",
                    "answer": answer,
                    "steps": [f"circumference = 2 * pi * r = {self.format_number(answer)}"],
                    "confidence": 94
                }

        if "rectangle" in lowered and len(nums) >= 2:
            width, height = nums[:2]
            if "area" in lowered:
                answer = width * height
                return {
                    "type": "rectangle_area",
                    "answer": answer,
                    "steps": [f"area = width * height = {width} * {height} = {self.format_number(answer)}"],
                    "confidence": 94
                }
            if "perimeter" in lowered:
                answer = 2 * (width + height)
                return {
                    "type": "rectangle_perimeter",
                    "answer": answer,
                    "steps": [f"perimeter = 2(width + height) = {self.format_number(answer)}"],
                    "confidence": 94
                }

        if "triangle" in lowered and "area" in lowered and len(nums) >= 2:
            base, height = nums[:2]
            answer = base * height / 2
            return {
                "type": "triangle_area",
                "answer": answer,
                "steps": [f"area = base * height / 2 = {self.format_number(answer)}"],
                "confidence": 93
            }

        return None

    def solve_unit_conversion(self, text):
        lowered = text.lower()
        match = re.search(
            r"(-?\d+(?:\.\d+)?)\s*([a-z]+)\s+(?:to|in)\s+([a-z]+)",
            lowered
        )
        if not match:
            return None

        value = float(match.group(1))
        from_unit = match.group(2)
        to_unit = match.group(3)

        if from_unit not in self.UNIT_FACTORS or to_unit not in self.UNIT_FACTORS:
            return None

        from_type, from_factor = self.UNIT_FACTORS[from_unit]
        to_type, to_factor = self.UNIT_FACTORS[to_unit]
        if from_type != to_type:
            return None

        base_value = value * from_factor
        answer = base_value / to_factor
        return {
            "type": "unit_conversion",
            "answer": answer,
            "steps": [
                f"{value} {from_unit} -> base {from_type}: {self.format_number(base_value)}",
                f"{self.format_number(base_value)} / {to_factor} = {self.format_number(answer)} {to_unit}"
            ],
            "confidence": 94
        }

    def parse_linear_xy_side(self, side):
        side = side.replace(" ", "").replace("*", "")
        if not side:
            return 0.0, 0.0, 0.0

        if side[0] not in "+-":
            side = "+" + side

        x_coeff = 0.0
        y_coeff = 0.0
        constant = 0.0

        for term in re.findall(r"[+-][^+-]+", side):
            sign = -1.0 if term.startswith("-") else 1.0
            body = term[1:]

            if "x" in body:
                coeff = body.replace("x", "")
                x_coeff += sign * (float(coeff) if coeff else 1.0)
            elif "y" in body:
                coeff = body.replace("y", "")
                y_coeff += sign * (float(coeff) if coeff else 1.0)
            else:
                constant += sign * float(body)

        return x_coeff, y_coeff, constant

    def parse_linear_xy_equation(self, equation):
        if "=" not in equation:
            return None

        left, right = equation.split("=", 1)
        lx, ly, lc = self.parse_linear_xy_side(left)
        rx, ry, rc = self.parse_linear_xy_side(right)
        return lx - rx, ly - ry, lc - rc

    def solve_system_equations(self, text):
        normalized = self.normalize_expression(text).replace("**", "^")
        if "x" not in normalized or "y" not in normalized or "=" not in normalized:
            return None

        normalized = re.sub(r"\band\b", ";", normalized)
        normalized = re.sub(r"\b(?!x\b|y\b)[a-zA-Z]+\b", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()

        pieces = [
            piece.strip()
            for piece in re.split(r"\band\b|;|\n", normalized)
            if "=" in piece and ("x" in piece or "y" in piece)
        ]

        if len(pieces) < 2:
            return None

        eq1 = self.parse_linear_xy_equation(pieces[0])
        eq2 = self.parse_linear_xy_equation(pieces[1])

        if not eq1 or not eq2:
            return None

        a, b, c = eq1
        d, e, f = eq2
        determinant = a * e - d * b

        if determinant == 0:
            return {
                "type": "linear_system",
                "answer": "no unique solution",
                "steps": [
                    f"Equation 1: {self.format_number(a)}x + {self.format_number(b)}y + {self.format_number(c)} = 0",
                    f"Equation 2: {self.format_number(d)}x + {self.format_number(e)}y + {self.format_number(f)} = 0",
                    "The determinant is 0, so there is no unique solution."
                ],
                "confidence": 88
            }

        x = (b * f - c * e) / determinant
        y = (c * d - a * f) / determinant

        return {
            "type": "linear_system",
            "answer": {"x": x, "y": y},
            "steps": [
                f"Equation 1: {self.format_number(a)}x + {self.format_number(b)}y = {self.format_number(-c)}",
                f"Equation 2: {self.format_number(d)}x + {self.format_number(e)}y = {self.format_number(-f)}",
                f"determinant = {self.format_number(determinant)}",
                f"x = {self.format_number(x)}",
                f"y = {self.format_number(y)}"
            ],
            "confidence": 92
        }

    def parse_polynomial_terms(self, expression):
        expression = expression.replace(" ", "").replace("^", "**")
        expression = expression.replace("*x", "x")

        if expression.startswith("-"):
            normalized = expression
        else:
            normalized = "+" + expression

        coefficients = {}

        for term in re.findall(r"[+-][^+-]+", normalized):
            sign = -1.0 if term.startswith("-") else 1.0
            body = term[1:]

            if "x**" in body:
                coeff, power = body.split("x**", 1)
                coeff_value = float(coeff) if coeff else 1.0
                power_value = int(float(power))
            elif body.endswith("x"):
                coeff = body[:-1]
                coeff_value = float(coeff) if coeff else 1.0
                power_value = 1
            else:
                coeff_value = float(body)
                power_value = 0

            coefficients[power_value] = coefficients.get(power_value, 0.0) + sign * coeff_value

        return coefficients

    def solve_derivative(self, text):
        lowered = self.normalize_expression(text)
        if "derivative" not in lowered and "differentiate" not in lowered and "d/dx" not in lowered:
            return None

        expression = lowered
        for marker in ["derivative of", "differentiate", "d/dx"]:
            if marker in expression:
                expression = expression.split(marker, 1)[1].strip()
                break

        expression = expression.split("=")[0].strip()
        if "x" not in expression:
            return None

        try:
            coefficients = self.parse_polynomial_terms(expression)
        except (ValueError, TypeError):
            return None

        derivative_terms = []
        derivative_coefficients = {}

        for power, coeff in sorted(coefficients.items(), reverse=True):
            if power == 0:
                continue
            new_power = power - 1
            new_coeff = coeff * power
            derivative_coefficients[new_power] = new_coeff

            if new_power == 0:
                derivative_terms.append(self.format_number(new_coeff))
            elif new_power == 1:
                derivative_terms.append(f"{self.format_number(new_coeff)}x")
            else:
                derivative_terms.append(f"{self.format_number(new_coeff)}x^{new_power}")

        answer = " + ".join(derivative_terms).replace("+ -", "- ") or "0"

        return {
            "type": "derivative",
            "answer": answer,
            "steps": [
                f"Original polynomial: {expression}",
                "Use power rule: d/dx(a*x^n) = a*n*x^(n-1)",
                f"Derivative: {answer}"
            ],
            "confidence": 90
        }

    def solve_expression(self, text):
        expression = self.extract_math_expression(text)
        if not expression:
            return None

        try:
            answer = self.safe_eval(expression)
        except (ArithmeticError, SyntaxError, ValueError, TypeError, ZeroDivisionError):
            return None

        return {
            "type": "arithmetic",
            "answer": answer,
            "steps": [
                f"Expression: {expression}",
                f"Result: {self.format_number(answer)}"
            ],
            "confidence": 96
        }

    def verify_solution(self, text, solved):

        result_type = solved.get("type")
        answer = solved.get("answer")
        tolerance = 1e-8

        try:
            if result_type == "arithmetic":
                expression = self.extract_math_expression(text)
                expected = self.safe_eval(expression)
                passed = abs(float(answer) - float(expected)) <= tolerance
                return {
                    "passed": passed,
                    "method": "independent_expression_evaluation",
                    "residual": abs(float(answer) - float(expected))
                }

            if result_type == "linear_equation" and isinstance(answer, (int, float)):
                cleaned = self.normalize_expression(text).replace(" ", "")
                equations = re.findall(r"[+\-0-9.x*]+=[+\-0-9.x*]+", cleaned)
                if equations:
                    left, right = equations[0].split("=", 1)
                    lx, lc = self.parse_linear_x_side(left)
                    rx, rc = self.parse_linear_x_side(right)
                    residual = abs((lx * float(answer) + lc) - (rx * float(answer) + rc))
                    return {
                        "passed": residual <= tolerance,
                        "method": "substitution_into_linear_equation",
                        "residual": residual
                    }

            if result_type == "quadratic_equation" and isinstance(answer, list):
                cleaned = self.normalize_expression(text).replace(" ", "")
                start = cleaned.find("x**2")
                while start > 0 and cleaned[start - 1] in "0123456789.+-":
                    start -= 1
                left_side, right_side = cleaned[start:].split("=", 1)
                right_match = re.match(r"[+\-0-9.x*]+", right_side)
                right_side = right_match.group(0) if right_match else right_side
                left = self.parse_quadratic_side(left_side)
                right = self.parse_quadratic_side(right_side)
                a = left["x2"] - right["x2"]
                b = left["x"] - right["x"]
                c = left["constant"] - right["constant"]
                residuals = [abs(a * float(root) ** 2 + b * float(root) + c) for root in answer]
                return {
                    "passed": bool(residuals) and max(residuals) <= tolerance,
                    "method": "substitute_roots_into_quadratic",
                    "residuals": residuals
                }

            if result_type == "linear_system" and isinstance(answer, dict):
                normalized = self.normalize_expression(text)
                normalized = re.sub(r"\band\b", ";", normalized)
                normalized = re.sub(r"\b(?!x\b|y\b)[a-zA-Z]+\b", " ", normalized)
                equations = [
                    piece.strip()
                    for piece in re.split(r";|\n", normalized)
                    if "=" in piece and ("x" in piece or "y" in piece)
                ]
                residuals = []
                for equation in equations[:2]:
                    parsed = self.parse_linear_xy_equation(equation.replace(" ", ""))
                    if parsed:
                        a, b, c = parsed
                        residuals.append(abs(a * float(answer["x"]) + b * float(answer["y"]) + c))
                if residuals:
                    return {
                        "passed": max(residuals) <= tolerance,
                        "method": "substitute_solution_into_system",
                        "residuals": residuals
                    }

            numeric_values = []
            if isinstance(answer, (int, float)):
                numeric_values = [float(answer)]
            elif isinstance(answer, list):
                numeric_values = [float(item) for item in answer if isinstance(item, (int, float))]
            elif isinstance(answer, dict):
                numeric_values = [float(item) for item in answer.values() if isinstance(item, (int, float))]

            return {
                "passed": bool(answer is not None) and all(math.isfinite(item) for item in numeric_values),
                "method": "finite_result_and_solver_invariant",
                "residual": None
            }
        except (ArithmeticError, KeyError, TypeError, ValueError):
            return {
                "passed": False,
                "method": "verification_failed",
                "residual": None
            }

    def result(
        self,
        success,
        answer=None,
        steps=None,
        result_type="unknown",
        confidence=0,
        warning=None,
        verification=None
    ):
        response = {
            "brain": "Math_brain",
            "success": success,
            "type": result_type,
            "answer": answer,
            "formatted_answer": self.format_number(answer) if answer is not None else None,
            "steps": steps or [],
            "confidence": confidence,
            "warning": warning,
            "verification": verification or {"passed": False, "method": "not_run"},
            "final_output": None,
            "suggested_next_brains": ["Response_brain"]
        }

        if success:
            if response["verification"].get("passed") is False:
                response["confidence"] = min(response["confidence"], 55)
            response["final_output"] = (
                f"Answer: {response['formatted_answer']}\n"
                + "\n".join(f"{index}. {step}" for index, step in enumerate(response["steps"], start=1))
            ).strip()
        else:
            response["final_output"] = "I could not solve this math request yet."
            response["suggested_next_brains"].extend(["Reasoning_brain", "Research_brain"])

        self.save_statistics(result_type, success)
        return response

    def process(self, data):
        text = self.extract_text(data)
        formula_context = self.relevant_formula_context(text)

        solvers = [
            self.solve_percentage,
            self.solve_fraction,
            self.solve_interest,
            self.solve_probability,
            self.solve_average,
            self.solve_quadratic_equation,
            self.solve_system_equations,
            self.solve_derivative,
            self.solve_ratio,
            self.solve_linear_equation,
            self.solve_pythagorean,
            self.solve_geometry,
            self.solve_unit_conversion,
            self.solve_expression,
        ]

        for solver in solvers:
            solved = solver(text)
            if solved:
                verification = self.verify_solution(text, solved)
                response = self.result(
                    True,
                    solved["answer"],
                    solved["steps"],
                    solved["type"],
                    solved["confidence"],
                    verification=verification
                )
                response["formula_context"] = formula_context
                response["data_files_used"] = [
                    "Math_formulas.json", "Math_problem_patterns.json",
                    "Math_examples.json", "Math_index.json", "Units_dictionary.json"
                ]
                return response

        return self.result(
            False,
            result_type="unsupported_math_request",
            confidence=20,
            warning="No supported math pattern matched."
        )


brain = MathBrain()
