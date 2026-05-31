"""Tests for Constant element."""
import pytest
from hydrosim.model.elements.constant import Constant
from hydrosim.model.base import SimState, ERR_INVALID_PARAMETER


def _state():
    return SimState(t=0, dt=1, step=0, values={}, storage={})


def test_compute_returns_value():
    el = Constant(name="C", value=3.14)
    state = _state()
    el.compute(state, {})
    assert state.get(el.id, "value") == pytest.approx(3.14)


def test_compute_zero():
    el = Constant(name="C", value=0.0)
    state = _state()
    el.compute(state, {})
    assert state.get(el.id, "value") == pytest.approx(0.0)


def test_compute_negative():
    el = Constant(name="C", value=-5.5)
    state = _state()
    el.compute(state, {})
    assert state.get(el.id, "value") == pytest.approx(-5.5)


def test_compute_same_value_every_timestep():
    el = Constant(name="C", value=42.0)
    for t in [0.0, 1.0, 100.0, 364.0]:
        state = SimState(t=t, dt=1, step=int(t), values={}, storage={})
        el.compute(state, {})
        assert state.get(el.id, "value") == pytest.approx(42.0)


def test_validate_finite_value_ok():
    el = Constant(name="C", value=0.035)
    assert el.validate() == []


def test_validate_inf_is_error():
    el = Constant(name="C", value=float("inf"))
    errors = el.validate()
    assert len(errors) == 1
    assert errors[0].code == ERR_INVALID_PARAMETER


def test_validate_neg_inf_is_error():
    el = Constant(name="C", value=float("-inf"))
    errors = el.validate()
    assert len(errors) == 1


def test_validate_nan_is_error():
    el = Constant(name="C", value=float("nan"))
    errors = el.validate()
    assert len(errors) == 1


def test_has_one_output_port():
    el = Constant(name="C", value=1.0)
    assert "value" in el.output_ports
    assert len(el.input_ports) == 0


def test_output_port_units_matches():
    el = Constant(name="C", value=1.0, units="mm/day")
    assert el.output_ports["value"].units == "mm/day"


def test_to_dict_structure():
    el = Constant(name="Manning_n", value=0.035, units="s/m^(1/3)",
                  description="Manning roughness")
    d = el.to_dict()
    assert d["type"] == "Constant"
    assert d["name"] == "Manning_n"
    assert d["parameters"]["value"] == pytest.approx(0.035)
    assert d["parameters"]["units"] == "s/m^(1/3)"


def test_from_dict_roundtrip():
    el = Constant(name="Manning_n", value=0.035, units="s/m^(1/3)",
                  description="roughness", position=(100.0, 200.0))
    el2 = Constant.from_dict(el.to_dict())
    assert el2.name        == el.name
    assert el2.value       == pytest.approx(el.value)
    assert el2.units       == el.units
    assert el2.description == el.description
    assert el2.position    == pytest.approx(el.position)
    assert el2.id          == el.id


def test_from_dict_preserves_id():
    el  = Constant(name="C", value=1.0)
    el2 = Constant.from_dict(el.to_dict())
    assert el2.id == el.id
