"""Tests for TimeSeries element."""
import pytest
from hydrosim.model.elements.timeseries import TimeSeries
from hydrosim.model.base import (
    SimState, InterpolationType, TimeSeriesType,
    ERR_EMPTY_TIMESERIES, ERR_INVALID_PARAMETER,
)


def _state(t=0.0):
    return SimState(t=t, dt=1, step=int(t), values={}, storage={})


# ── Step interpolation ────────────────────────────────────────────────────────

def test_step_returns_previous_value():
    ts = TimeSeries(name="R", data=[[0, 0], [1, 5], [2, 0], [3, 10]],
                    interpolation=InterpolationType.STEP)
    ts.prepare()
    # At t=1.5 the most recent data point is t=1 (value 5)
    state = _state(1.5)
    ts.compute(state, {})
    assert state.get(ts.id, "value") == pytest.approx(5.0)


def test_step_at_exact_time():
    ts = TimeSeries(name="R", data=[[0, 0], [1, 5], [2, 3]],
                    interpolation=InterpolationType.STEP)
    ts.prepare()
    state = _state(1.0)
    ts.compute(state, {})
    assert state.get(ts.id, "value") == pytest.approx(5.0)


# ── Linear interpolation ──────────────────────────────────────────────────────

def test_linear_midpoint():
    ts = TimeSeries(name="R", data=[[0, 0], [10, 10]],
                    interpolation=InterpolationType.LINEAR)
    ts.prepare()
    state = _state(5.0)
    ts.compute(state, {})
    assert state.get(ts.id, "value") == pytest.approx(5.0)


def test_linear_at_endpoint():
    ts = TimeSeries(name="R", data=[[0, 0], [10, 10]],
                    interpolation=InterpolationType.LINEAR)
    ts.prepare()
    state = _state(10.0)
    ts.compute(state, {})
    assert state.get(ts.id, "value") == pytest.approx(10.0)


# ── Flat extrapolation ────────────────────────────────────────────────────────

def test_extrapolation_before_first():
    ts = TimeSeries(name="R", data=[[5, 3], [10, 7]],
                    interpolation=InterpolationType.LINEAR)
    ts.prepare()
    state = _state(0.0)  # before first data point
    ts.compute(state, {})
    assert state.get(ts.id, "value") == pytest.approx(3.0)  # first value


def test_extrapolation_after_last():
    ts = TimeSeries(name="R", data=[[0, 3], [1, 5]],
                    interpolation=InterpolationType.LINEAR)
    ts.prepare()
    state = _state(999.0)
    ts.compute(state, {})
    assert state.get(ts.id, "value") == pytest.approx(5.0)  # last value


# ── get_value_at ──────────────────────────────────────────────────────────────

def test_get_value_at_calls_prepare():
    ts = TimeSeries(name="R", data=[[0, 10], [1, 20]],
                    interpolation=InterpolationType.LINEAR)
    # Not prepared — get_value_at should handle that internally
    assert ts.get_value_at(0.5) == pytest.approx(15.0)


# ── Validation ────────────────────────────────────────────────────────────────

def test_validate_empty_data():
    ts = TimeSeries(name="R", data=[])
    errors = ts.validate()
    assert any(e.code == ERR_EMPTY_TIMESERIES for e in errors)


def test_validate_non_monotonic_time():
    ts = TimeSeries(name="R", data=[[0, 1], [2, 2], [1, 3]])
    errors = ts.validate()
    assert any(e.code == ERR_INVALID_PARAMETER for e in errors)


def test_validate_single_row_ok():
    ts = TimeSeries(name="R", data=[[0, 5.0]])
    assert ts.validate() == []


def test_validate_good_data_no_errors():
    ts = TimeSeries(name="R", data=[[0, 0], [1, 10], [2, 5]])
    assert ts.validate() == []


def test_compute_raises_if_not_prepared():
    ts = TimeSeries(name="R", data=[[0, 1], [1, 2]])
    state = _state(0.0)
    with pytest.raises(RuntimeError, match="prepare"):
        ts.compute(state, {})


# ── Serialisation ─────────────────────────────────────────────────────────────

def test_to_dict_structure():
    ts = TimeSeries(name="Rain", units="mm/day",
                    data_type=TimeSeriesType.PERIOD_TOTAL,
                    interpolation=InterpolationType.STEP,
                    data=[[0, 0], [1, 12.3]])
    d = ts.to_dict()
    assert d["type"] == "TimeSeries"
    assert d["parameters"]["data_type"] == "period_total"
    assert d["parameters"]["interpolation"] == "step"
    assert d["parameters"]["data"] == [[0, 0], [1, 12.3]]


def test_from_dict_roundtrip():
    ts = TimeSeries(name="Rain", units="mm/day",
                    data_type=TimeSeriesType.PERIOD_TOTAL,
                    interpolation=InterpolationType.STEP,
                    data=[[0, 0], [1, 12.3], [2, 0.0]],
                    description="Daily rainfall",
                    position=(120.0, 240.0))
    ts2 = TimeSeries.from_dict(ts.to_dict())
    assert ts2.name          == ts.name
    assert ts2.units         == ts.units
    assert ts2.data_type     == ts.data_type
    assert ts2.interpolation == ts.interpolation
    assert ts2.data          == ts.data
    assert ts2.id            == ts.id
