"""Tests for Expression element."""
import pytest
from hydrosim.model.elements.expression import Expression
from hydrosim.model.base import SimState, ERR_INVALID_FORMULA, PortType


def _state(t=0.0, dt=1.0):
    return SimState(t=t, dt=dt, step=0, values={}, storage={})


def _prepared_expr(formula, name_to_id=None):
    ex = Expression(name="E", formula=formula, output_units="-")
    ex.prepare(name_to_id or {})
    return ex


# ── Dynamic input ports ───────────────────────────────────────────────────────

def test_no_ports_for_empty_formula():
    ex = Expression(name="E", formula="")
    assert len(ex.input_ports) == 0


def test_input_ports_created_from_formula():
    ex = Expression(name="E", formula="Rain * Coeff")
    assert "Rain"  in ex.input_ports
    assert "Coeff" in ex.input_ports


def test_dot_notation_creates_single_port():
    ex = Expression(name="E", formula="Store.storage * 0.01")
    assert "Store.storage" in ex.input_ports
    assert "Store" not in ex.input_ports


def test_set_formula_rebuilds_ports():
    ex = Expression(name="E", formula="A + B")
    assert "A" in ex.input_ports
    ex.set_formula("X * Y * Z")
    assert "A" not in ex.input_ports
    assert "X" in ex.input_ports
    assert "Y" in ex.input_ports
    assert "Z" in ex.input_ports


def test_builtins_not_added_as_ports():
    ex = Expression(name="E", formula="sqrt(Rain) + abs(Flow)")
    assert "sqrt" not in ex.input_ports
    assert "abs"  not in ex.input_ports
    assert "Rain" in ex.input_ports
    assert "Flow" in ex.input_ports


def test_t_and_dt_not_added_as_ports():
    ex = Expression(name="E", formula="Rain * t + dt")
    assert "t"  not in ex.input_ports
    assert "dt" not in ex.input_ports
    assert "Rain" in ex.input_ports


# ── Validation ────────────────────────────────────────────────────────────────

def test_validate_empty_formula_error():
    ex = Expression(name="E", formula="")
    errors = ex.validate()
    assert any(e.code == ERR_INVALID_FORMULA for e in errors)


def test_validate_valid_formula_ok():
    ex = Expression(name="E", formula="Rain * 0.3")
    assert ex.validate() == []


def test_validate_syntax_error():
    ex = Expression(name="E", formula="Rain * * 0.3")
    errors = ex.validate()
    assert len(errors) > 0


def test_validate_forbidden_import():
    ex = Expression(name="E", formula="__import__('os')")
    errors = ex.validate()
    assert len(errors) > 0


# ── compute ───────────────────────────────────────────────────────────────────

def test_compute_simple_multiplication():
    ex    = _prepared_expr("Rain * 0.3")
    state = _state()
    ex.compute(state, {"Rain": 10.0})
    assert state.get(ex.id, "value") == pytest.approx(3.0)


def test_compute_addition():
    ex    = _prepared_expr("A + B")
    state = _state()
    ex.compute(state, {"A": 3.0, "B": 7.0})
    assert state.get(ex.id, "value") == pytest.approx(10.0)


def test_compute_uses_t():
    ex    = _prepared_expr("t * 2")
    state = _state(t=5.0)
    ex.compute(state, {})
    assert state.get(ex.id, "value") == pytest.approx(10.0)


def test_compute_uses_dt():
    ex    = _prepared_expr("dt + 1")
    state = _state(dt=0.5)
    ex.compute(state, {})
    assert state.get(ex.id, "value") == pytest.approx(1.5)


def test_compute_builtin_sqrt():
    ex    = _prepared_expr("sqrt(Rain)")
    state = _state()
    ex.compute(state, {"Rain": 9.0})
    assert state.get(ex.id, "value") == pytest.approx(3.0)


def test_compute_raises_if_not_prepared():
    ex = Expression(name="E", formula="Rain * 0.3")
    state = _state()
    with pytest.raises(RuntimeError, match="prepare"):
        ex.compute(state, {"Rain": 5.0})


def test_compute_division_by_zero_returns_zero():
    ex    = _prepared_expr("1 / Rain")
    state = _state()
    ex.compute(state, {"Rain": 0.0})
    # Should not raise — returns 0.0 and logs a warning
    assert state.get(ex.id, "value") == pytest.approx(0.0)


# ── evaluate_test ─────────────────────────────────────────────────────────────

def test_evaluate_test():
    ex = Expression(name="E", formula="Rain * Coeff")
    result = ex.evaluate_test({"Rain": 10.0, "Coeff": 0.3})
    assert result == pytest.approx(3.0)


# ── Serialisation ─────────────────────────────────────────────────────────────

def test_to_dict_structure():
    ex = Expression(name="RunoffRate", formula="Rain * 0.3",
                    output_units="mm/day", description="runoff calc")
    d  = ex.to_dict()
    assert d["type"] == "Expression"
    assert d["parameters"]["formula"]      == "Rain * 0.3"
    assert d["parameters"]["output_units"] == "mm/day"


def test_from_dict_roundtrip():
    ex  = Expression(name="RunoffRate", formula="Rain * Coeff",
                     output_units="mm/day", position=(280.0, 380.0))
    ex2 = Expression.from_dict(ex.to_dict())
    assert ex2.name         == ex.name
    assert ex2.formula      == ex.formula
    assert ex2.output_units == ex.output_units
    assert ex2.id           == ex.id
    # Dynamic ports are rebuilt from formula on load
    assert "Rain"  in ex2.input_ports
    assert "Coeff" in ex2.input_ports
