"""Tests for WaterStore element — the most critical element in HydroSim."""
import pytest
import numpy as np
from hydrosim.model.elements.waterstore import WaterStore
from hydrosim.model.base import SimState, ERR_INVALID_PARAMETER, ERR_BOUNDS_VIOLATION


def _state(dt=1.0):
    return SimState(t=0.0, dt=dt, step=0, values={}, storage={})


def _run(ws, inflow, outflow, dt=1.0, steps=1):
    """Helper: initialise and run ws for `steps` steps with constant in/out."""
    state = _state(dt)
    ws.initialise(state)
    for i in range(steps):
        state.t    = float(i) * dt
        state.step = i
        ws.compute(state, {"inflow": inflow, "outflow": outflow})
    return state


# ── Basic integration ─────────────────────────────────────────────────────────

def test_basic_integration_grows():
    """inflow=5, outflow=2, dt=1 → +3/step → after 10 steps: 100+30=130"""
    ws    = WaterStore(name="S", initial_storage=100, lower_bound=0, upper_bound=200)
    state = _run(ws, inflow=5.0, outflow=2.0, steps=10)
    assert state.get(ws.id, "storage") == pytest.approx(130.0, abs=1e-9)


def test_basic_integration_shrinks():
    ws    = WaterStore(name="S", initial_storage=100, lower_bound=0, upper_bound=200)
    state = _run(ws, inflow=0.0, outflow=5.0, steps=10)
    assert state.get(ws.id, "storage") == pytest.approx(50.0, abs=1e-9)


def test_zero_flux_storage_unchanged():
    ws    = WaterStore(name="S", initial_storage=80, lower_bound=0, upper_bound=150)
    state = _run(ws, inflow=0.0, outflow=0.0, steps=5)
    assert state.get(ws.id, "storage") == pytest.approx(80.0)


def test_initial_storage_written_on_initialise():
    ws    = WaterStore(name="S", initial_storage=80)
    state = _state()
    ws.initialise(state)
    assert state.get(ws.id, "storage") == pytest.approx(80.0)
    assert state.get(ws.id, "overflow") == pytest.approx(0.0)
    assert state.get(ws.id, "deficit")  == pytest.approx(0.0)


# ── Upper bound / overflow ────────────────────────────────────────────────────

def test_overflow_when_upper_bound_exceeded():
    ws    = WaterStore(name="S", initial_storage=198, upper_bound=200, lower_bound=0)
    state = _run(ws, inflow=5.0, outflow=0.0, steps=1)
    assert state.get(ws.id, "storage")  == pytest.approx(200.0)
    assert state.get(ws.id, "overflow") == pytest.approx(3.0)   # 3 mm/day spilled


def test_no_overflow_when_below_upper_bound():
    ws    = WaterStore(name="S", initial_storage=100, upper_bound=200, lower_bound=0)
    state = _run(ws, inflow=5.0, outflow=0.0, steps=1)
    assert state.get(ws.id, "overflow") == pytest.approx(0.0)


def test_unbounded_never_overflows():
    ws    = WaterStore(name="S", initial_storage=0, upper_bound=None, lower_bound=0)
    state = _run(ws, inflow=1000.0, outflow=0.0, steps=10)
    assert state.get(ws.id, "overflow") == pytest.approx(0.0)
    assert state.get(ws.id, "storage")  == pytest.approx(10000.0)


# ── Lower bound / deficit ─────────────────────────────────────────────────────

def test_deficit_when_lower_bound_hit():
    ws    = WaterStore(name="S", initial_storage=2, lower_bound=0, upper_bound=None)
    state = _run(ws, inflow=0.0, outflow=5.0, steps=1)
    assert state.get(ws.id, "storage") == pytest.approx(0.0)
    assert state.get(ws.id, "deficit") == pytest.approx(3.0)  # 3 mm/day unmet


def test_no_deficit_when_above_lower_bound():
    ws    = WaterStore(name="S", initial_storage=100, lower_bound=0)
    state = _run(ws, inflow=0.0, outflow=5.0, steps=1)
    assert state.get(ws.id, "deficit") == pytest.approx(0.0)


# ── Water balance (mass conservation) ────────────────────────────────────────

def test_water_balance_closes_no_bounds():
    """ΔS = (inflow - outflow) * dt must hold for 100 random steps."""
    rng = np.random.default_rng(42)
    ws    = WaterStore(name="S", initial_storage=50, lower_bound=0, upper_bound=None)
    state = _state()
    ws.initialise(state)

    inflows  = rng.uniform(0, 10, 100)
    outflows = rng.uniform(0, 8,  100)
    total_overflow = 0.0
    total_deficit  = 0.0

    for i in range(100):
        state.t    = float(i)
        state.step = i
        ws.compute(state, {"inflow": inflows[i], "outflow": outflows[i]})
        total_overflow += state.get(ws.id, "overflow")
        total_deficit  += state.get(ws.id, "deficit")

    delta_s  = state.get(ws.id, "storage") - 50.0
    net_flux = inflows.sum() - outflows.sum() - total_overflow + total_deficit
    assert delta_s == pytest.approx(net_flux, rel=1e-6)


def test_water_balance_closes_with_overflow():
    """Mass conservation must hold even when overflow occurs."""
    rng = np.random.default_rng(99)
    ws    = WaterStore(name="S", initial_storage=50, lower_bound=0, upper_bound=100)
    state = _state()
    ws.initialise(state)

    inflows  = rng.uniform(0, 15, 100)
    outflows = rng.uniform(0, 5,  100)
    total_overflow = 0.0
    total_deficit  = 0.0

    for i in range(100):
        state.t    = float(i)
        state.step = i
        ws.compute(state, {"inflow": inflows[i], "outflow": outflows[i]})
        total_overflow += state.get(ws.id, "overflow")
        total_deficit  += state.get(ws.id, "deficit")

    delta_s  = state.get(ws.id, "storage") - 50.0
    net_flux = inflows.sum() - outflows.sum() - total_overflow + total_deficit
    assert delta_s == pytest.approx(net_flux, rel=1e-6)


def test_water_balance_helper():
    ws = WaterStore(name="S", initial_storage=100, upper_bound=200)
    err = ws.get_water_balance_error(
        s_prev=100, s_new=103, inflow=5, outflow=2,
        overflow=0, deficit=0, dt=1.0
    )
    assert err == pytest.approx(0.0, abs=1e-12)


# ── Validation ────────────────────────────────────────────────────────────────

def test_validate_bounds_ok():
    ws = WaterStore(name="S", initial_storage=80, lower_bound=0, upper_bound=150)
    assert ws.validate() == []


def test_validate_upper_less_than_lower():
    ws = WaterStore(name="S", initial_storage=0, lower_bound=100, upper_bound=50)
    errors = ws.validate()
    assert any(e.code == ERR_INVALID_PARAMETER for e in errors)


def test_validate_initial_above_upper():
    ws = WaterStore(name="S", initial_storage=200, lower_bound=0, upper_bound=150)
    errors = ws.validate()
    assert any(e.code == ERR_BOUNDS_VIOLATION for e in errors)


def test_validate_initial_below_lower():
    ws = WaterStore(name="S", initial_storage=-5, lower_bound=0, upper_bound=None)
    errors = ws.validate()
    assert any(e.code == ERR_BOUNDS_VIOLATION for e in errors)


def test_validate_unbounded_ok():
    ws = WaterStore(name="S", initial_storage=0, lower_bound=0, upper_bound=None)
    assert ws.validate() == []


# ── is_stock ──────────────────────────────────────────────────────────────────

def test_is_stock_true():
    ws = WaterStore(name="S")
    assert ws.is_stock() is True


# ── Serialisation ─────────────────────────────────────────────────────────────

def test_to_dict_structure():
    ws = WaterStore(name="SM", initial_storage=80, lower_bound=0,
                    upper_bound=150, units="mm")
    d  = ws.to_dict()
    assert d["type"] == "WaterStore"
    assert d["parameters"]["initial_storage"] == pytest.approx(80.0)
    assert d["parameters"]["upper_bound"]     == pytest.approx(150.0)


def test_to_dict_unbounded_is_none():
    ws = WaterStore(name="S", upper_bound=None)
    d  = ws.to_dict()
    assert d["parameters"]["upper_bound"] is None


def test_from_dict_roundtrip():
    ws = WaterStore(name="SM", initial_storage=80, lower_bound=0,
                    upper_bound=150, units="mm", description="soil moisture",
                    position=(400.0, 300.0))
    ws2 = WaterStore.from_dict(ws.to_dict())
    assert ws2.name            == ws.name
    assert ws2.initial_storage == pytest.approx(ws.initial_storage)
    assert ws2.lower_bound     == pytest.approx(ws.lower_bound)
    assert ws2.upper_bound     == pytest.approx(ws.upper_bound)
    assert ws2.units           == ws.units
    assert ws2.id              == ws.id


def test_from_dict_roundtrip_unbounded():
    ws  = WaterStore(name="S", upper_bound=None)
    ws2 = WaterStore.from_dict(ws.to_dict())
    assert ws2.upper_bound is None
