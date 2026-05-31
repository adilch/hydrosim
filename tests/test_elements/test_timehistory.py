"""Tests for TimeHistoryResult element."""
import pytest
from hydrosim.model.elements.timehistory import TimeHistoryResult
from hydrosim.model.base import SimState, ERR_INVALID_PARAMETER, PortType


def _state():
    return SimState(t=0, dt=1, step=0, values={}, storage={})


# ── Ports ─────────────────────────────────────────────────────────────────────

def test_starts_with_series_1_port():
    th = TimeHistoryResult(name="Plot")
    assert "series_1" in th.input_ports
    assert th.input_ports["series_1"].required is True


def test_no_output_ports():
    th = TimeHistoryResult(name="Plot")
    assert len(th.output_ports) == 0


def test_add_series_port():
    th = TimeHistoryResult(name="Plot")
    name = th.add_series_port()
    assert name == "series_2"
    assert "series_2" in th.input_ports


def test_add_series_ports_up_to_max():
    th = TimeHistoryResult(name="Plot")
    for i in range(2, TimeHistoryResult.MAX_SERIES + 1):
        name = th.add_series_port()
        assert name == f"series_{i}"
    assert len(th.input_ports) == TimeHistoryResult.MAX_SERIES


def test_add_series_port_beyond_max_raises():
    th = TimeHistoryResult(name="Plot")
    for _ in range(TimeHistoryResult.MAX_SERIES - 1):
        th.add_series_port()
    with pytest.raises(ValueError, match="Maximum"):
        th.add_series_port()


# ── compute is a no-op ────────────────────────────────────────────────────────

def test_compute_is_noop():
    th    = TimeHistoryResult(name="Plot")
    state = _state()
    th.compute(state, {"series_1": 42.0})
    # Nothing written to state
    assert state.get(th.id, "series_1") == pytest.approx(0.0)


# ── Validation ────────────────────────────────────────────────────────────────

def test_validate_ok_no_axis_limits():
    th = TimeHistoryResult(name="Plot")
    assert th.validate() == []


def test_validate_ok_valid_axis_limits():
    th = TimeHistoryResult(name="Plot", y_min=0.0, y_max=150.0)
    assert th.validate() == []


def test_validate_y_min_equals_y_max_error():
    th = TimeHistoryResult(name="Plot", y_min=50.0, y_max=50.0)
    errors = th.validate()
    assert any(e.code == ERR_INVALID_PARAMETER for e in errors)


def test_validate_y_min_greater_than_y_max_error():
    th = TimeHistoryResult(name="Plot", y_min=100.0, y_max=50.0)
    errors = th.validate()
    assert any(e.code == ERR_INVALID_PARAMETER for e in errors)


def test_validate_only_y_min_ok():
    th = TimeHistoryResult(name="Plot", y_min=0.0, y_max=None)
    assert th.validate() == []


# ── Serialisation ─────────────────────────────────────────────────────────────

def test_to_dict_structure():
    th = TimeHistoryResult(name="Storage_Plot", title="Soil Moisture",
                           y_axis_label="Storage", y_axis_units="mm",
                           show_grid=True, y_min=0.0, y_max=150.0)
    d  = th.to_dict()
    assert d["type"] == "TimeHistoryResult"
    assert d["parameters"]["title"]        == "Soil Moisture"
    assert d["parameters"]["y_axis_units"] == "mm"
    assert d["parameters"]["y_min"]        == pytest.approx(0.0)
    assert d["parameters"]["y_max"]        == pytest.approx(150.0)


def test_to_dict_none_axis_limits():
    th = TimeHistoryResult(name="Plot", y_min=None, y_max=None)
    d  = th.to_dict()
    assert d["parameters"]["y_min"] is None
    assert d["parameters"]["y_max"] is None


def test_from_dict_roundtrip():
    th = TimeHistoryResult(name="Storage_Plot", title="Soil Moisture",
                           y_axis_label="Storage", y_axis_units="mm",
                           show_grid=False, y_min=0.0, y_max=150.0,
                           description="result viewer",
                           position=(600.0, 300.0))
    th2 = TimeHistoryResult.from_dict(th.to_dict())
    assert th2.name         == th.name
    assert th2.title        == th.title
    assert th2.y_axis_units == th.y_axis_units
    assert th2.show_grid    == th.show_grid
    assert th2.y_min        == pytest.approx(th.y_min)
    assert th2.y_max        == pytest.approx(th.y_max)
    assert th2.id           == th.id
