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
from pathlib import Path


DATA_DIR = Path(__file__).parent / "data"
UNITS_FILE = DATA_DIR / "Units_dictionary.json"
STATS_FILE = DATA_DIR / "Math_statistics.json"


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
        with STATS_FILE.open("w", encoding="utf-8") as file:
            json.dump(self.statistics, file, ensure_ascii=False, indent=2)
            file.write("\n")

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
            return " ".join(parts)
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
        expression = re.sub(r"[^0-9a-z_=+\-*/().,%\s]", " ", expression)
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

        candidates = re.findall(
            r"(?:sqrt\s*\([^)]+\)|[0-9pi e+\-*/().\s]{3,}(?:\*\*[0-9]+)?)",
            normalized
        )
        candidates = [
            candidate.strip()
            for candidate in candidates
            if re.search(r"\d", candidate)
            and any(op in candidate for op in ["+", "-", "*", "/", "sqrt", "**", "(", ")"])
        ]
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
        if not any(word in lowered for word in ["average", "mean", "median", "sum", "total", "minimum", "maximum", "max", "min"]):
            return None

        nums = self.numbers(text)
        if not nums:
            return None

        if "median" in lowered:
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

    def solve_linear_equation(self, text):
        cleaned = self.normalize_expression(text).replace(" ", "")
        if "=" not in cleaned or "x" not in cleaned:
            return None

        match = re.fullmatch(r"([+-]?\d*(?:\.\d+)?)x([+-]\d+(?:\.\d+)?)?=([+-]?\d+(?:\.\d+)?)", cleaned)
        if not match:
            match = re.fullmatch(r"([+-]?\d+(?:\.\d+)?)=([+-]?\d*(?:\.\d+)?)x([+-]\d+(?:\.\d+)?)?", cleaned)
            if not match:
                return None
            c = float(match.group(1))
            a_text = match.group(2)
            b = float(match.group(3) or 0)
        else:
            a_text = match.group(1)
            b = float(match.group(2) or 0)
            c = float(match.group(3))

        if a_text in ["", "+"]:
            a = 1.0
        elif a_text == "-":
            a = -1.0
        else:
            a = float(a_text)

        if a == 0:
            return None

        answer = (c - b) / a
        return {
            "type": "linear_equation",
            "answer": answer,
            "steps": [
                f"{self.format_number(a)}x + {self.format_number(b)} = {self.format_number(c)}",
                f"{self.format_number(a)}x = {self.format_number(c - b)}",
                f"x = {self.format_number(answer)}"
            ],
            "confidence": 96
        }

    def solve_quadratic_equation(self, text):
        cleaned = self.normalize_expression(text).replace(" ", "")
        if "x**2" not in cleaned or "=" not in cleaned:
            return None

        match = re.search(
            r"([+-]?\d*(?:\.\d+)?)x\*\*2([+-]\d*(?:\.\d+)?)x([+-]\d+(?:\.\d+)?)=0(?:\.0)?",
            cleaned
        )
        if not match:
            return None

        a_text, b_text, c_text = match.groups()
        a = 1.0 if a_text in ["", "+"] else -1.0 if a_text == "-" else float(a_text)
        b = 1.0 if b_text == "+" else -1.0 if b_text == "-" else float(b_text)
        c = float(c_text)
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

    def result(self, success, answer=None, steps=None, result_type="unknown", confidence=0, warning=None):
        response = {
            "brain": "Math_brain",
            "success": success,
            "type": result_type,
            "answer": answer,
            "formatted_answer": self.format_number(answer) if answer is not None else None,
            "steps": steps or [],
            "confidence": confidence,
            "warning": warning,
            "final_output": None,
            "suggested_next_brains": ["Response_brain"]
        }

        if success:
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

        solvers = [
            self.solve_percentage,
            self.solve_average,
            self.solve_quadratic_equation,
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
                return self.result(
                    True,
                    solved["answer"],
                    solved["steps"],
                    solved["type"],
                    solved["confidence"]
                )

        return self.result(
            False,
            result_type="unsupported_math_request",
            confidence=20,
            warning="No supported math pattern matched."
        )


brain = MathBrain()
