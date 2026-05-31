"""Tests for TimeStepSolver."""
import pytest

from hydrosim.model.graph   import ModelGraph
from hydrosim.model.base    import Connection, SimState
from hydrosim.engine.solver import TimeStepSolver
from hydrosim.model.elements import Constant, WaterStore, Expression, TimeHistoryResult


def _conn(a, ap, b, bp):
    return Connection("", a.id, ap, b.id, bp)


def _state_with(element_id, port_name, value):
    state = SimState(t=0, dt=1, step=0, values={}, storage={})
    state.set(element_id, port_name, value)
    return state


# ── Basic resolution ──────────────────────────────────────────────────────────

def test_resolves_single_input():
    g  = ModelGraph()
    c  = Constant(name="C", value=5.0)
    ws = WaterStore(name="WS")
    g.add_element(c); g.add_element(ws)
    g.add_connection(_conn(c, "value", ws, "inflow"))

    state = _state_with(c.id, "value", 5.0)
    solver = TimeStepSolver(g)
    inputs = solver.resolve_inputs(ws, state)
    assert inputs["inflow"] == pytest.approx(5.0)


def test_unconnected_optional_port_omitted():
    g  = ModelGraph()
    c  = Constant(name="C", value=1.0)
    ws = WaterStore(name="WS")
    g.add_element(c); g.add_element(ws)
    # Only inflow connected; outflow is optional and left unconnected
    g.add_connection(_conn(c, "value", ws, "inflow"))

    state  = _state_with(c.id, "value", 1.0)
    solver = TimeStepSolver(g)
    inputs = solver.resolve_inputs(ws, state)

    assert "inflow"  in inputs
    assert "outflow" not in inputs   # omitted — element defaults to 0.0


def test_no_connections_returns_empty():
    g  = ModelGraph()
    ws = WaterStore(name="WS")
    g.add_element(ws)
    state  = SimState(t=0, dt=1, step=0, values={}, storage={})
    solver = TimeStepSolver(g)
    inputs = solver.resolve_inputs(ws, state)
    assert inputs == {}


def test_fan_in_sums_values():
    """Two Constant outputs feeding the same inflow port → values are summed."""
    g  = ModelGraph()
    c1 = Constant(name="C1", value=3.0)
    c2 = Constant(name="C2", value=4.0)
    ws = WaterStore(name="WS")
    g.add_element(c1); g.add_element(c2); g.add_element(ws)

    # Both connect to inflow — this tests fan-in (normally blocked by graph,
    # but TimeStepSolver sums whatever it finds via get_connections_to_port)
    # We bypass graph validation by manually inserting connections
    conn1 = Connection("conn1", c1.id, "value", ws.id, "inflow")
    conn2 = Connection("conn2", c2.id, "value", ws.id, "inflow")
    # Add them directly to bypass the "already connected" check
    g._connections[conn1.id] = conn1
    g._connections[conn2.id] = conn2

    state = SimState(t=0, dt=1, step=0, values={}, storage={})
    state.set(c1.id, "value", 3.0)
    state.set(c2.id, "value", 4.0)

    solver = TimeStepSolver(g)
    inputs = solver.resolve_inputs(ws, state)
    assert inputs["inflow"] == pytest.approx(7.0)


def test_expression_input_uses_element_name_as_port():
    """Expression port names are element names; solver maps source value correctly."""
    g  = ModelGraph()
    c  = Constant(name="Rain", value=10.0)
    ex = Expression(name="Rate", formula="Rain * 0.3")
    g.add_element(c); g.add_element(ex)
    g.add_connection(_conn(c, "value", ex, "Rain"))

    state = _state_with(c.id, "value", 10.0)
    solver = TimeStepSolver(g)
    inputs = solver.resolve_inputs(ex, state)
    assert inputs["Rain"] == pytest.approx(10.0)


def test_source_value_zero_included():
    """A connected port whose source value is 0.0 must still appear in the dict."""
    g  = ModelGraph()
    c  = Constant(name="C", value=0.0)
    ws = WaterStore(name="WS")
    g.add_element(c); g.add_element(ws)
    g.add_connection(_conn(c, "value", ws, "inflow"))

    state  = _state_with(c.id, "value", 0.0)
    solver = TimeStepSolver(g)
    inputs = solver.resolve_inputs(ws, state)
    assert "inflow" in inputs
    assert inputs["inflow"] == pytest.approx(0.0)


def test_resolves_stock_output_for_downstream():
    """Stock output (storage) is already in state; solver reads it correctly."""
    g  = ModelGraph()
    ws = WaterStore(name="WS")
    th = TimeHistoryResult(name="Plot")
    g.add_element(ws); g.add_element(th)
    g.add_connection(_conn(ws, "storage", th, "series_1"))

    state = SimState(t=0, dt=1, step=0, values={}, storage={})
    state.set(ws.id, "storage", 80.0)

    solver = TimeStepSolver(g)
    inputs = solver.resolve_inputs(th, state)
    assert inputs["series_1"] == pytest.approx(80.0)
