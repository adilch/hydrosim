"""
ExpressionParser — safe formula evaluator using simpleeval + ast.
Full implementation for Phase 5; this version is complete and used by Phase 2 tests.
"""
from __future__ import annotations

import ast
import difflib
import math

from simpleeval import SimpleEval, NameNotDefined

from hydrosim.model.base import ExpressionEvaluationError


# ── Safe AST node whitelist ───────────────────────────────────────────────────

SAFE_AST_NODES = frozenset({
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Call,
    ast.Constant, ast.Name, ast.IfExp, ast.Compare,
    ast.BoolOp, ast.Attribute,
    # Operators
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod,
    ast.USub, ast.UAdd,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.And, ast.Or, ast.Not,
    # Context nodes that appear when walking Name/Attribute nodes
    ast.Load,
})

# ── Math function namespace ───────────────────────────────────────────────────

SAFE_FUNCTIONS: dict[str, object] = {
    "abs":   abs,
    "sqrt":  math.sqrt,
    "exp":   math.exp,
    "log":   math.log,
    "log10": math.log10,
    "sin":   math.sin,
    "cos":   math.cos,
    "tan":   math.tan,
    "min":   min,
    "max":   max,
    "round": round,
    "floor": math.floor,
    "ceil":  math.ceil,
    # 'if' is a keyword — users write if_() in formulas
    "if_":   lambda cond, a, b: a if cond else b,
}

_RESERVED = frozenset(SAFE_FUNCTIONS.keys()) | {"t", "dt", "True", "False", "None"}


# ── ExpressionParser ──────────────────────────────────────────────────────────

class ExpressionParser:
    """
    Safe formula evaluator. Constructed once per Expression element during
    prepare(); evaluate() is called at every timestep.
    """

    def __init__(self, formula: str, name_to_id: dict[str, str]):
        """
        Args:
            formula:    e.g. "Daily_Rainfall * RunoffCoeff"
            name_to_id: lowercase element name → element UUID
                        e.g. {"daily_rainfall": "uuid-...", ...}
        """
        self.formula    = formula
        self.name_to_id = name_to_id
        self._evaluator = SimpleEval(functions=SAFE_FUNCTIONS)

    def evaluate(
        self,
        input_values: dict[str, float],
        t:  float,
        dt: float,
    ) -> float:
        """
        Evaluate the formula with current element values.

        Args:
            input_values: {element_name_as_in_formula: float_value}
            t:  current simulation time in days
            dt: current timestep in days

        Returns float result.
        Raises ExpressionEvaluationError on any failure except ZeroDivisionError
        (which returns 0.0 — logged by the caller).
        """
        names: dict[str, object] = dict(input_values)
        names["t"]  = t
        names["dt"] = dt

        self._evaluator.names = names
        try:
            result = self._evaluator.eval(self.formula)
            if not math.isfinite(float(result)):
                raise ExpressionEvaluationError(
                    f"Formula produced non-finite result: {result}"
                )
            return float(result)
        except ExpressionEvaluationError:
            raise
        except ZeroDivisionError:
            return 0.0
        except NameNotDefined as exc:
            raise ExpressionEvaluationError(f"Unknown variable: {exc}") from exc
        except Exception as exc:
            raise ExpressionEvaluationError(str(exc)) from exc

    # ── Static utilities (used by GUI and Expression element) ─────────────────

    @staticmethod
    def validate_syntax(formula: str) -> list[str]:
        """
        Check formula syntax without evaluating.
        Returns a list of error message strings; empty = valid.
        Does NOT check whether referenced element names exist in the graph.
        """
        if not formula.strip():
            return ["Formula is empty"]
        try:
            tree = ast.parse(formula, mode="eval")
        except SyntaxError as exc:
            return [f"Syntax error: {exc.msg} at position {exc.offset}"]

        errors = []
        for node in ast.walk(tree):
            if type(node) not in SAFE_AST_NODES:
                errors.append(f"Forbidden operation: {type(node).__name__}")
            # Block any dunder name (e.g. __import__, __builtins__)
            elif isinstance(node, ast.Name) and node.id.startswith("__"):
                errors.append(f"Forbidden name: {node.id}")
        return errors

    @staticmethod
    def extract_references(formula: str) -> list[str]:
        """
        Parse the formula and return all element name references in
        left-to-right, first-occurrence order, de-duplicated.

        Simple names: "Daily_Rainfall" → ["Daily_Rainfall"]
        Dot notation: "SoilMoisture.storage" → ["SoilMoisture.storage"]
        """
        if not formula.strip():
            return []
        try:
            tree = ast.parse(formula, mode="eval")
        except SyntaxError:
            return []

        refs: list[str] = []
        seen: set[str]  = set()

        def _visit(node: ast.AST) -> None:
            """Depth-first, left-to-right traversal."""
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                # Dot-notation reference like SoilMoisture.storage
                ref = f"{node.value.id}.{node.attr}"
                if ref not in seen:
                    refs.append(ref)
                    seen.add(ref)
                # Do NOT recurse into node.value — it's part of this ref
                return

            if isinstance(node, ast.Name):
                if node.id not in _RESERVED and node.id not in seen:
                    refs.append(node.id)
                    seen.add(node.id)
                return

            for child in ast.iter_child_nodes(node):
                _visit(child)

        _visit(tree)
        return refs

    @staticmethod
    def suggest_correction(unknown_name: str, known_names: list[str]) -> str | None:
        """
        Return the closest known name if edit-distance ≤ 2, else None.
        Used to generate 'did you mean X?' hints in validation messages.
        """
        matches = difflib.get_close_matches(
            unknown_name.lower(),
            [n.lower() for n in known_names],
            n=1,
            cutoff=0.6,
        )
        if not matches:
            return None
        # Return in original case
        lower_to_orig = {n.lower(): n for n in known_names}
        return lower_to_orig.get(matches[0])
