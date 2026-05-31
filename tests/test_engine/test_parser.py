"""Tests for ExpressionParser."""
import pytest
from hydrosim.engine.parser import ExpressionParser
from hydrosim.model.base import ExpressionEvaluationError


# ── evaluate ─────────────────────────────────────────────────────────────────

def test_simple_multiplication():
    p = ExpressionParser("Rain * 0.3", {"rain": "id_rain"})
    assert p.evaluate({"Rain": 10.0}, t=0, dt=1) == pytest.approx(3.0)


def test_addition():
    p = ExpressionParser("A + B", {})
    assert p.evaluate({"A": 3.0, "B": 7.0}, t=0, dt=1) == pytest.approx(10.0)


def test_subtraction():
    p = ExpressionParser("A - B", {})
    assert p.evaluate({"A": 10.0, "B": 4.0}, t=0, dt=1) == pytest.approx(6.0)


def test_power():
    p = ExpressionParser("x ** 2", {})
    assert p.evaluate({"x": 3.0}, t=0, dt=1) == pytest.approx(9.0)


def test_special_variable_t():
    p = ExpressionParser("t * 2", {})
    assert p.evaluate({}, t=5.0, dt=1.0) == pytest.approx(10.0)


def test_special_variable_dt():
    p = ExpressionParser("dt + 1", {})
    assert p.evaluate({}, t=0.0, dt=0.5) == pytest.approx(1.5)


def test_builtin_sqrt():
    p = ExpressionParser("sqrt(Rain)", {})
    assert p.evaluate({"Rain": 9.0}, t=0, dt=1) == pytest.approx(3.0)


def test_builtin_abs():
    p = ExpressionParser("abs(x)", {})
    assert p.evaluate({"x": -5.0}, t=0, dt=1) == pytest.approx(5.0)


def test_builtin_min_max():
    p = ExpressionParser("min(a, b) + max(a, b)", {})
    assert p.evaluate({"a": 3.0, "b": 7.0}, t=0, dt=1) == pytest.approx(10.0)


def test_builtin_exp_log():
    import math
    p = ExpressionParser("log(exp(x))", {})
    assert p.evaluate({"x": 2.0}, t=0, dt=1) == pytest.approx(2.0)


def test_conditional_if_true():
    p = ExpressionParser("if_(x > 0, x, 0.0)", {})
    assert p.evaluate({"x": 5.0}, t=0, dt=1) == pytest.approx(5.0)


def test_conditional_if_false():
    p = ExpressionParser("if_(x > 0, x, 0.0)", {})
    assert p.evaluate({"x": -3.0}, t=0, dt=1) == pytest.approx(0.0)


def test_division_by_zero_returns_zero():
    p = ExpressionParser("1 / x", {})
    # Should not raise — returns 0.0
    assert p.evaluate({"x": 0.0}, t=0, dt=1) == pytest.approx(0.0)


def test_complex_formula():
    """Manning's Q ≈ (1/n) * A * R^(2/3) * S^0.5"""
    p = ExpressionParser("(1.0 / n) * A * R ** (2.0/3.0) * sqrt(S)", {})
    result = p.evaluate({"n": 0.035, "A": 10.0, "R": 1.5, "S": 0.001}, t=0, dt=1)
    assert result > 0


# ── validate_syntax ───────────────────────────────────────────────────────────

def test_valid_formula_no_errors():
    assert ExpressionParser.validate_syntax("Rain * 0.3") == []


def test_empty_formula_error():
    errors = ExpressionParser.validate_syntax("")
    assert len(errors) > 0


def test_syntax_error_detected():
    errors = ExpressionParser.validate_syntax("Rain * * 0.3")
    assert len(errors) > 0


def test_forbidden_import_rejected():
    errors = ExpressionParser.validate_syntax("__import__('os')")
    assert len(errors) > 0


def test_forbidden_exec_rejected():
    errors = ExpressionParser.validate_syntax("__builtins__")
    assert len(errors) > 0


def test_list_comprehension_rejected():
    errors = ExpressionParser.validate_syntax("[x for x in range(10)]")
    assert len(errors) > 0


def test_lambda_rejected():
    errors = ExpressionParser.validate_syntax("lambda x: x * 2")
    assert len(errors) > 0


def test_valid_with_sqrt():
    assert ExpressionParser.validate_syntax("sqrt(Rain)") == []


def test_valid_with_if():
    assert ExpressionParser.validate_syntax("if_(x > 0, x, 0.0)") == []


# ── extract_references ────────────────────────────────────────────────────────

def test_extract_simple_names():
    refs = ExpressionParser.extract_references("Daily_Rainfall * RunoffCoeff")
    assert "Daily_Rainfall" in refs
    assert "RunoffCoeff"    in refs


def test_extract_dot_notation():
    refs = ExpressionParser.extract_references("SoilMoisture.storage * 0.01")
    assert "SoilMoisture.storage" in refs
    assert "SoilMoisture"         not in refs


def test_extract_no_builtins():
    refs = ExpressionParser.extract_references("sqrt(Rain) + abs(Flow)")
    assert "sqrt" not in refs
    assert "abs"  not in refs
    assert "Rain" in refs
    assert "Flow" in refs


def test_extract_no_t_dt():
    refs = ExpressionParser.extract_references("Rain * t + dt")
    assert "t"    not in refs
    assert "dt"   not in refs
    assert "Rain" in refs


def test_extract_deduplicated():
    refs = ExpressionParser.extract_references("A + A * A")
    assert refs.count("A") == 1


def test_extract_empty_formula():
    assert ExpressionParser.extract_references("") == []


def test_extract_preserves_order():
    refs = ExpressionParser.extract_references("B + A + C")
    assert refs.index("B") < refs.index("A") < refs.index("C")


# ── suggest_correction ────────────────────────────────────────────────────────

def test_suggest_correction_close_match():
    suggestion = ExpressionParser.suggest_correction(
        "Rainfal", ["Rainfall", "Runoff", "ET"]
    )
    assert suggestion == "Rainfall"


def test_suggest_correction_no_match():
    suggestion = ExpressionParser.suggest_correction(
        "XYZ123", ["Rainfall", "Runoff"]
    )
    assert suggestion is None


def test_suggest_correction_exact_case_insensitive():
    suggestion = ExpressionParser.suggest_correction(
        "rainfall", ["Rainfall"]
    )
    assert suggestion == "Rainfall"
