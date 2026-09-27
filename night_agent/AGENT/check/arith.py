"""METHOD sum: Dispatch redoes the arithmetic itself (spec 2: arithmetic is one of the three things
Dispatch may execute). Evaluation is an AST whitelist, never eval()."""
import ast
import re
from fractions import Fraction

EQUATION = re.compile(
    r"((?:\(?\s*-?\d[\d,]*(?:\.\d+)?\s*\)?\s*(?:[+\-*/^×x]|\bover\b|\bdivided by\b|\btimes\b|\bplus\b|\bminus\b)\s*)+\(?\s*-?\d[\d,]*(?:\.\d+)?\s*\)?)"
    r"\s*(?:=|equals|is|gives?|makes?)\s*(-?\d[\d,]*(?:\.\d+)?)\s*(percent|%)?", re.I)
WORDS = {"over": "/", "divided by": "/", "times": "*", "plus": "+", "minus": "-"}
MAX_EXP = 64


class ArithError(ValueError):
    pass


def _normalise(expr: str) -> str:
    e = expr.lower()
    for w, s in WORDS.items():
        e = re.sub(rf"\b{w}\b", s, e)
    e = e.replace("^", "**").replace("×", "*").replace(",", "")
    e = re.sub(r"(?<=\d)\s*x\s*(?=[\d(])", "*", e)
    return e.strip()


def evaluate(expr: str) -> Fraction:
    tree = ast.parse(_normalise(expr), mode="eval")

    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return Fraction(str(node.value))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            v = ev(node.operand)
            return -v if isinstance(node.op, ast.USub) else v
        if isinstance(node, ast.BinOp):
            a, b = ev(node.left), ev(node.right)
            if isinstance(node.op, ast.Add):
                return a + b
            if isinstance(node.op, ast.Sub):
                return a - b
            if isinstance(node.op, ast.Mult):
                return a * b
            if isinstance(node.op, ast.Div):
                if b == 0:
                    raise ArithError("division by zero")
                return a / b
            if isinstance(node.op, ast.FloorDiv):
                return Fraction(a // b)
            if isinstance(node.op, ast.Mod):
                return a % b
            if isinstance(node.op, ast.Pow):
                if b.denominator != 1 or abs(b) > MAX_EXP:
                    raise ArithError("exponent must be a small integer")
                return a ** int(b)
        raise ArithError(f"unsupported expression element {type(node).__name__}")

    return ev(tree)


def _decimals(s: str) -> int:
    return len(s.split(".")[1]) if "." in s else 0


def find_equations(text: str) -> list:
    """[(expression, written result, percent flag)] for every 'a op b = c' the text states."""
    out = []
    for m in EQUATION.finditer(text):
        out.append((m.group(1).strip(), m.group(2).replace(",", ""), bool(m.group(3))))
    return out


def check_sum(text: str) -> tuple:
    """(result, retrieved, settle). PASSED and FAILED carry the recomputation; NOT TESTABLE when no equation is written."""
    eqs = find_equations(text)
    if not eqs:
        return ("NOT TESTABLE", "", "write the sum as an expression and its result, for example 21600 / 12 = 1800")
    parts, ok = [], True
    for expr, written, pct in eqs:
        try:
            val = evaluate(expr)
        except (ArithError, SyntaxError, ValueError, RecursionError) as e:
            return ("NOT TESTABLE", "", f"the expression {expr!r} could not be evaluated ({e}); write plain arithmetic")
        dec = _decimals(written)
        got = round(float(val), dec)
        want = float(written)
        same = abs(got - want) < 10 ** (-dec) / 2 + 1e-12
        shown = f"{val.numerator}" if val.denominator == 1 else f"{float(val):.{max(dec, 4)}f}".rstrip("0").rstrip(".")
        parts.append(f"{_normalise(expr)} = {shown}{' percent' if pct else ''} (written {written}{' percent' if pct else ''})")
        ok = ok and same
    return ("PASSED" if ok else "FAILED", "recomputed: " + "; ".join(parts), "")
