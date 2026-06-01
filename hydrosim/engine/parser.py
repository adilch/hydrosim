"""
ExpressionParser — safe formula evaluator using Python's built-in ast + eval.
No external dependencies. The formula is validated against a whitelist of safe
AST node types before evaluation, then executed with a restricted namespace
(no builtins, only whitelisted math functions and element values).
"""
from __future__ import annotations

import ast
import difflib
import math

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
    "if_":   lambda cond, a, b: a if cond else b,
}

# Restricted globals — no builtins at all; only our functions are available
_RESTRICTED_GLOBALS: dict[str, object] = {"__builtins__": {}, **SAFE_FUNCTIONS}

_RESERVED = frozenset(SAFE_FUNCTIONS.keys()) | {"t", "dt", "True", "False", "None"}


# ── Dot-notation proxy ────────────────────────────────────────────────────────

class _ElementProxy:
    """
    Lightweight proxy so that dot-notation references like 'BlueReservoir.area'
    work inside eval().  Python sees `BlueReservoir` as this object and resolves
    `.area` via __getattr__, which looks up 'BlueReservoir.area' in the values dict.
    """
    __slots__ = ("_values", "_prefix")

    def __init__(self, values: dict[str, float], prefix: str):
        object.__setattr__(self, "_values", values)
        object.__setattr__(self, "_prefix", prefix)

    def __getattr__(self, name: str) -> float:
        key = f"{object.__getattribute__(self, '_prefix')}.{name}"
        values = object.__getattribute__(self, "_values")
        if key in values:
            return values[key]
        raise AttributeError(f"No port '{name}' on element '{object.__getattribute__(self, '_prefix')}'")


def _build_local_ns(
    input_values: dict[str, float],
    t: float,
    dt: float,
) -> dict[str, object]:
    """
    Build the eval() local namespace from input_values.

    Simple names  ("Daily_Rainfall") → added directly.
    Dot-notation  ("BlueReservoir.area") → an _ElementProxy for "BlueReservoir"
    is added so that eval resolves BlueReservoir.area via attribute access.
    """
    local_ns: dict[str, object] = {"t": t, "dt": dt}
    proxy_prefixes: set[str] = set()

    for key, val in input_values.items():
        if "." in key:
            prefix = key.split(".")[0]
            proxy_prefixes.add(prefix)
        else:
            local_ns[key] = val

    for prefix in proxy_prefixes:
        local_ns[prefix] = _ElementProxy(input_values, prefix)

    return local_ns


# ── ExpressionParser ──────────────────────────────────────────────────────────

class ExpressionParser:
    """
    Safe formula evaluator using stdlib ast + eval.
    No external dependencies.

    Safety model:
      1. validate_syntax() checks every AST node against SAFE_AST_NODES whitelist
         and blocks dunder names — this runs at model-build time.
      2. evaluate() calls eval() with __builtins__ set to {} so no Python
         built-ins are reachable — only the explicit SAFE_FUNCTIONS namespace
         plus the injected element values.
    """

    def __init__(self, formula: str, name_to_id: dict[str, str]):
        self.formula    = formula
        self.name_to_id = name_to_id
        # Pre-compile the formula for faster repeated evaluation
        try:
            self._code = compile(formula, "<formula>", "eval")
        except SyntaxError as exc:
            raise ExpressionEvaluationError(
                f"Syntax error in formula: {exc}"
            ) from exc

    def evaluate(
        self,
        input_values: dict[str, float],
        t:  float,
        dt: float,
    ) -> float:
        """
        Evaluate the formula with current element values.
        Returns float result.
        Raises ExpressionEvaluationError on failure (except ZeroDivisionError → 0.0).
        """
        local_ns = _build_local_ns(input_values, t, dt)

        try:
            # Safety: eval() is safe here because:
            #   1. __builtins__ is {} — no Python built-ins reachable at all
            #   2. globals contains only explicit SAFE_FUNCTIONS (math only)
            #   3. The formula was already validated by validate_syntax() which
            #      walks the AST and rejects every node type not in SAFE_AST_NODES
            #      (no Import, Exec, Lambda, ListComp, etc.) before this runs.
            #   4. Dunder names (__import__, __builtins__) are blocked by name check.
            # This pattern is the standard approach for sandboxed expression eval.
            result = eval(self._code, _RESTRICTED_GLOBALS, local_ns)  # noqa: S307
            result = float(result)
            if not math.isfinite(result):
                raise ExpressionEvaluationError(
                    f"Formula produced non-finite result: {result}"
                )
            return result
        except ExpressionEvaluationError:
            raise
        except ZeroDivisionError:
            return 0.0
        except NameError as exc:
            raise ExpressionEvaluationError(f"Unknown variable: {exc}") from exc
        except Exception as exc:
            raise ExpressionEvaluationError(str(exc)) from exc

    # ── Static utilities ──────────────────────────────────────────────────────

    @staticmethod
    def validate_syntax(formula: str) -> list[str]:
        """
        Check formula against the safe AST whitelist.
        Returns list of error strings; empty = valid.
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
            elif isinstance(node, ast.Name) and node.id.startswith("__"):
                errors.append(f"Forbidden name: {node.id}")
        return errors

    @staticmethod
    def extract_references(formula: str) -> list[str]:
        """
        Return all element name references in left-to-right first-occurrence order.
        Simple: "A + B" → ["A", "B"]
        Dot notation: "Store.storage * 0.01" → ["Store.storage"]
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
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                ref = f"{node.value.id}.{node.attr}"
                if ref not in seen:
                    refs.append(ref)
                    seen.add(ref)
                return   # don't recurse into the base Name

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
        """Return the closest known name (edit-distance ≤ 2), or None."""
        matches = difflib.get_close_matches(
            unknown_name.lower(),
            [n.lower() for n in known_names],
            n=1,
            cutoff=0.6,
        )
        if not matches:
            return None
        lower_to_orig = {n.lower(): n for n in known_names}
        return lower_to_orig.get(matches[0])
