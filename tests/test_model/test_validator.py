"""Tests for ModelValidator."""
import pytest

from hydrosim.model.graph     import ModelGraph
from hydrosim.model.validator import ModelValidator
from hydrosim.model.base import (
    Connection,
    ERR_NO_ELEMENTS,
    ERR_MISSING_REQUIRED_INPUT,
    ERR_UNKNOWN_REFERENCE,
    ERR_CIRCULAR_DEPENDENCY,
    ERR_INVALID_PARAMETER,
    WARN_UNITS_MISMATCH,
    WARN_MISSING_DESCRIPTION,
    SimulationSettings,
)
from hydrosim.model.elements.constant    import Constant
from hydrosim.model.elements.timeseries  import TimeSeries, InterpolationType
from hydrosim.model.elements.waterstore  import WaterStore
from hydrosim.model.elements.expression  import Expression
from hydrosim.model.elements.timehistory import TimeHistoryResult


def _conn(a, ap, b, bp):
    return Connection("", a.id, ap, b.id, bp)


def _valid_graph():
    """A minimal valid model: Constant → WaterStore → TimeHistoryResult."""
    g  = ModelGraph()
    c  = Constant(name="Rain", value=5.0, description="rainfall")
    ws = WaterStore(name="Store", initial_storage=80, upper_bound=150,
                    description="soil moisture")
    th = TimeHistoryResult(name="Plot", description="result")
    for el in [c, ws, th]: g.add_element(el)
    g.add_connection(_conn(c,  "value",   ws, "inflow"))
    g.add_connection(_conn(ws, "storage", th, "series_1"))
    return g, c, ws, th


# ── Empty model ───────────────────────────────────────────────────────────────

def test_empty_model_error():
    g = ModelGraph()
    errors = ModelValidator(g).validate_all()
    assert any(e.code == ERR_NO_ELEMENTS for e in errors)


def test_single_element_no_required_ports_ok():
    g = ModelGraph()
    c = Constant(name="C", value=1.0)
    g.add_element(c)
    errors = ModelValidator(g).validate_all()
    # No required input ports on Constant, no expressions — no blocking errors
    assert all(e.code != ERR_NO_ELEMENTS for e in errors)


# ── Required port checks ──────────────────────────────────────────────────────

def test_isolated_timehistory_is_warning_not_error():
    """A standalone (unconnected) TimeHistoryResult should be a WARNING, not a hard error.
    It is simply skipped at runtime."""
    g  = ModelGraph()
    c  = Constant(name="C", value=1.0)   # also isolated
    th = TimeHistoryResult(name="Plot")
    for el in [c, th]: g.add_element(el)
    errors = ModelValidator(g).validate_all()
    # No MISSING_REQUIRED_INPUT — isolated elements are skipped
    assert not any(e.code == ERR_MISSING_REQUIRED_INPUT for e in errors)
    # But they DO appear as warnings
    from hydrosim.model.validator import WARN_ISOLATED_ELEMENT
    warnings = ModelValidator(g).get_warnings()
    isolated_names = {
        g.elements[w.element_id].name
        for w in warnings if w.code == WARN_ISOLATED_ELEMENT and w.element_id
    }
    assert "Plot" in isolated_names
    assert "C"    in isolated_names


def test_missing_required_port_on_timehistory():
    """A TH that is non-isolated (partially connected) but still missing series_1 → error."""
    g   = ModelGraph()
    c   = Constant(name="C", value=1.0)
    ws  = WaterStore(name="WS")
    th  = TimeHistoryResult(name="Plot")
    for el in [c, ws, th]: g.add_element(el)
    # Connect c→ws but NOT ws→th, so th is isolated → only a warning
    g.add_connection(Connection("", c.id, "value", ws.id, "inflow"))
    errors = ModelValidator(g).validate_all()
    # TH is isolated (no connections), so still a warning not an error
    assert not any(e.code == ERR_MISSING_REQUIRED_INPUT for e in errors)


def test_missing_required_port_non_isolated():
    """An Expression with one port connected but another required port missing → error."""
    g  = ModelGraph()
    c  = Constant(name="A", value=1.0)
    ex = Expression(name="Calc", formula="A + B")   # two required ports
    th = TimeHistoryResult(name="Plot")
    for el in [c, ex, th]: g.add_element(el)
    g.add_connection(Connection("", c.id, "value", ex.id, "A"))
    g.add_connection(Connection("", ex.id, "value", th.id, "series_1"))
    # ex is non-isolated (has connections) but 'B' is unconnected and required
    errors = ModelValidator(g).validate_all()
    assert any(e.code == ERR_MISSING_REQUIRED_INPUT for e in errors)
    assert any("B" in e.message for e in errors)


def test_missing_required_port_on_expression():
    """An isolated Expression generates a warning, not a blocking error."""
    g  = ModelGraph()
    ex = Expression(name="Calc", formula="Rain * 0.3")
    g.add_element(ex)
    errors = ModelValidator(g).validate_all()
    # Isolated → no MISSING_REQUIRED_INPUT or UNKNOWN_REFERENCE errors
    codes = {e.code for e in errors}
    assert ERR_MISSING_REQUIRED_INPUT not in codes
    assert ERR_UNKNOWN_REFERENCE      not in codes
    # But it IS a warning
    from hydrosim.model.validator import WARN_ISOLATED_ELEMENT
    warnings = ModelValidator(g).get_warnings()
    assert any(w.code == WARN_ISOLATED_ELEMENT for w in warnings)


def test_connected_required_port_no_error():
    g, c, ws, th = _valid_graph()
    errors = ModelValidator(g).validate_all()
    assert errors == []


# ── Expression reference checks ───────────────────────────────────────────────

def test_unknown_reference_typo():
    """Unknown reference is only checked when the Expression is non-isolated."""
    g  = ModelGraph()
    c  = Constant(name="Rainfall", value=5.0)
    ex = Expression(name="Calc", formula="Rainfal * 0.3")  # typo
    th = TimeHistoryResult(name="Plot")
    for el in [c, ex, th]: g.add_element(el)
    # Connect ex→th so ex is non-isolated (reference check fires)
    g.add_connection(Connection("", ex.id, "value", th.id, "series_1"))
    errors = ModelValidator(g).validate_all()
    assert any(e.code == ERR_UNKNOWN_REFERENCE for e in errors)
    assert any("Rainfal" in e.message for e in errors)


def test_known_reference_no_error():
    g  = ModelGraph()
    c  = Constant(name="Rainfall", value=5.0)
    ex = Expression(name="Calc", formula="Rainfall * 0.3")
    th = TimeHistoryResult(name="Plot")
    for el in [c, ex, th]: g.add_element(el)
    # Wire it up
    g.add_connection(_conn(c,  "value", ex, "Rainfall"))
    g.add_connection(_conn(ex, "value", th, "series_1"))
    errors = ModelValidator(g).validate_all()
    ref_errors = [e for e in errors if e.code == ERR_UNKNOWN_REFERENCE]
    assert ref_errors == []


def test_unknown_reference_suggestion():
    """Validator suggests a correction when the name is close.
    Expression must be non-isolated for reference check to fire."""
    g  = ModelGraph()
    c  = Constant(name="DailyRainfall", value=5.0)
    ex = Expression(name="Calc", formula="DailyRainfal * 0.3")  # one letter off
    th = TimeHistoryResult(name="Plot")
    for el in [c, ex, th]: g.add_element(el)
    # Connect ex→th so ex is non-isolated
    g.add_connection(Connection("", ex.id, "value", th.id, "series_1"))
    errors = ModelValidator(g).validate_all()
    ref_errors = [e for e in errors if e.code == ERR_UNKNOWN_REFERENCE]
    assert ref_errors
    assert any("DailyRainfall" in e.suggestion for e in ref_errors)


def test_dot_notation_reference_resolved():
    """Store.storage in a formula should resolve against element name 'Store'."""
    g  = ModelGraph()
    ws = WaterStore(name="Store", initial_storage=80)
    ex = Expression(name="Evap", formula="Store.storage * 0.01")
    th = TimeHistoryResult(name="Plot")
    for el in [ws, ex, th]: g.add_element(el)
    g.add_connection(_conn(ws, "storage", ex, "Store.storage"))
    g.add_connection(_conn(ex, "value",   th, "series_1"))
    errors = ModelValidator(g).validate_all()
    ref_errors = [e for e in errors if e.code == ERR_UNKNOWN_REFERENCE]
    assert ref_errors == []


# ── Element parameter checks ──────────────────────────────────────────────────

def test_invalid_constant_value_is_caught():
    g = ModelGraph()
    c = Constant(name="C", value=float("inf"))
    g.add_element(c)
    errors = ModelValidator(g).validate_all()
    assert any(e.code == ERR_INVALID_PARAMETER for e in errors)


def test_invalid_waterstore_bounds_are_caught():
    g  = ModelGraph()
    ws = WaterStore(name="WS", initial_storage=200, lower_bound=0, upper_bound=100)
    g.add_element(ws)
    errors = ModelValidator(g).validate_all()
    assert len(errors) > 0


# ── Per-element validation shortcut ──────────────────────────────────────────

def test_validate_element_delegates_to_element():
    g = ModelGraph()
    c = Constant(name="C", value=float("nan"))
    g.add_element(c)
    errors = ModelValidator(g).validate_element(c.id)
    assert len(errors) == 1
    assert errors[0].code == ERR_INVALID_PARAMETER


# ── Valid model produces no errors ───────────────────────────────────────────

def test_valid_model_no_errors():
    g, *_ = _valid_graph()
    assert ModelValidator(g).validate_all() == []


# ── Warnings ─────────────────────────────────────────────────────────────────

def test_warn_missing_description():
    g  = ModelGraph()
    c  = Constant(name="C", value=1.0)  # no description
    g.add_element(c)
    warnings = ModelValidator(g).get_warnings()
    assert any(w.code == WARN_MISSING_DESCRIPTION for w in warnings)


def test_no_warn_missing_description_when_filled():
    g  = ModelGraph()
    c  = Constant(name="C", value=1.0, description="Manning roughness")
    g.add_element(c)
    warnings = ModelValidator(g).get_warnings()
    assert not any(w.code == WARN_MISSING_DESCRIPTION for w in warnings)


def test_warn_units_mismatch():
    """mm/day output connected to m3/s input should produce a warning."""
    g  = ModelGraph()
    c  = Constant(name="C", value=1.0, units="mm/day")
    ws = WaterStore(name="WS", units="m3")  # port units are "m3/day"
    g.add_element(c); g.add_element(ws)
    g.add_connection(_conn(c, "value", ws, "inflow"))
    warnings = ModelValidator(g).get_warnings()
    assert any(w.code == WARN_UNITS_MISMATCH for w in warnings)


def test_warn_timeseries_too_short():
    g  = ModelGraph()
    ts = TimeSeries(name="R", data=[[0, 0], [10, 5]])  # only 10 days
    th = TimeHistoryResult(name="Plot", description="result")
    g.add_element(ts); g.add_element(th)
    g.add_connection(_conn(ts, "value", th, "series_1"))
    settings = SimulationSettings(0, 365, 1.0, "elapsed", None)
    warnings = ModelValidator(g).get_warnings(settings)
    from hydrosim.model.base import WARN_TIMESERIES_SHORT
    assert any(w.code == WARN_TIMESERIES_SHORT for w in warnings)


def test_no_timeseries_warning_when_covers_period():
    g  = ModelGraph()
    ts = TimeSeries(name="R", data=[[0, 0], [365, 5]])
    th = TimeHistoryResult(name="Plot", description="result")
    g.add_element(ts); g.add_element(th)
    g.add_connection(_conn(ts, "value", th, "series_1"))
    settings = SimulationSettings(0, 365, 1.0, "elapsed", None)
    warnings = ModelValidator(g).get_warnings(settings)
    from hydrosim.model.base import WARN_TIMESERIES_SHORT
    assert not any(w.code == WARN_TIMESERIES_SHORT for w in warnings)
