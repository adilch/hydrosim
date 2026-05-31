"""Tests for ModelGraph (Phase 3) — includes Phase 1 data-structure tests."""
import pytest

from hydrosim.model.base import (
    Connection,
    SimState,
    SimulationSettings,
    Port,
    PortType,
    ValidationError,
    CircularDependencyError,
    ERR_INVALID_PARAMETER,
)
from hydrosim.model.graph import ModelGraph
from hydrosim.model.elements.constant    import Constant
from hydrosim.model.elements.timeseries  import TimeSeries
from hydrosim.model.elements.waterstore  import WaterStore
from hydrosim.model.elements.expression  import Expression
from hydrosim.model.elements.timehistory import TimeHistoryResult


# ── Helpers ───────────────────────────────────────────────────────────────────

def _conn(from_el, from_port, to_el, to_port):
    return Connection("", from_el.id, from_port, to_el.id, to_port)


def _simple_graph():
    """Constant → WaterStore → TimeHistoryResult"""
    g  = ModelGraph()
    c  = Constant(name="Rain", value=5.0)
    ws = WaterStore(name="Store", initial_storage=80, upper_bound=150)
    th = TimeHistoryResult(name="Plot")
    for el in [c, ws, th]:
        g.add_element(el)
    g.add_connection(_conn(c,  "value",   ws, "inflow"))
    g.add_connection(_conn(ws, "storage", th, "series_1"))
    return g, c, ws, th


# ── Phase 1 data-structure tests (kept here) ─────────────────────────────────

def test_simulation_settings_n_steps():
    s = SimulationSettings(0, 365, 1.0, "elapsed", None)
    assert s.n_steps == 365
    assert len(s.timesteps) == 365


def test_connection_auto_id():
    c = Connection("", "a", "value", "b", "inflow")
    assert len(c.id) == 36


def test_simstate_get_missing():
    st = SimState(t=0, dt=1, step=0, values={}, storage={})
    assert st.get("nope", "x") == 0.0


def test_simstate_set_get():
    st = SimState(t=0, dt=1, step=0, values={}, storage={})
    st.set("el", "storage", 42.5)
    assert st.get("el", "storage") == pytest.approx(42.5)


# ── Element CRUD ──────────────────────────────────────────────────────────────

def test_add_and_get_element():
    g = ModelGraph()
    c = Constant(name="C", value=1.0)
    g.add_element(c)
    assert g.get_element(c.id) is c
    assert g.element_count == 1


def test_add_duplicate_id_raises():
    g  = ModelGraph()
    c  = Constant(name="C", value=1.0)
    g.add_element(c)
    with pytest.raises(ValueError, match="already exists"):
        g.add_element(c)


def test_remove_element():
    g = ModelGraph()
    c = Constant(name="C", value=1.0)
    g.add_element(c)
    g.remove_element(c.id)
    assert g.element_count == 0


def test_remove_nonexistent_element_raises():
    g = ModelGraph()
    with pytest.raises(KeyError):
        g.remove_element("nonexistent-id")


def test_remove_element_removes_its_connections():
    g, c, ws, th = _simple_graph()
    assert len(g.connections) == 2
    # Removing c deletes only the c→ws connection; ws→th remains
    g.remove_element(c.id)
    assert len(g.connections) == 1
    remaining = list(g.connections.values())[0]
    assert remaining.from_element_id == ws.id


def test_get_element_by_name_case_insensitive():
    g = ModelGraph()
    c = Constant(name="DailyRainfall", value=5.0)
    g.add_element(c)
    assert g.get_element_by_name("dailyrainfall") is c
    assert g.get_element_by_name("DAILYRAINFALL") is c


def test_get_element_by_name_not_found():
    g = ModelGraph()
    assert g.get_element_by_name("nope") is None


def test_elements_property_returns_copy():
    g = ModelGraph()
    c = Constant(name="C", value=1.0)
    g.add_element(c)
    copy = g.elements
    copy["fake"] = None
    assert "fake" not in g.elements  # original unaffected


# ── Connection validation ─────────────────────────────────────────────────────

def test_add_valid_connection():
    g, c, ws, th = _simple_graph()
    assert len(g.connections) == 2


def test_connect_nonexistent_source_raises():
    g  = ModelGraph()
    ws = WaterStore(name="WS")
    g.add_element(ws)
    conn = Connection("", "nonexistent", "value", ws.id, "inflow")
    with pytest.raises(ValueError, match="Source element"):
        g.add_connection(conn)


def test_connect_nonexistent_dest_raises():
    g = ModelGraph()
    c = Constant(name="C", value=1.0)
    g.add_element(c)
    conn = Connection("", c.id, "value", "nonexistent", "inflow")
    with pytest.raises(ValueError, match="Destination element"):
        g.add_connection(conn)


def test_connect_wrong_output_port_raises():
    g  = ModelGraph()
    c  = Constant(name="C", value=1.0)
    ws = WaterStore(name="WS")
    g.add_element(c); g.add_element(ws)
    conn = Connection("", c.id, "nonexistent_port", ws.id, "inflow")
    with pytest.raises(ValueError, match="no output port"):
        g.add_connection(conn)


def test_connect_wrong_input_port_raises():
    g  = ModelGraph()
    c  = Constant(name="C", value=1.0)
    ws = WaterStore(name="WS")
    g.add_element(c); g.add_element(ws)
    conn = Connection("", c.id, "value", ws.id, "nonexistent_port")
    with pytest.raises(ValueError, match="no input port"):
        g.add_connection(conn)


def test_connect_self_loop_raises():
    g  = ModelGraph()
    ws = WaterStore(name="WS")
    g.add_element(ws)
    conn = Connection("", ws.id, "storage", ws.id, "inflow")
    with pytest.raises(ValueError, match="itself"):
        g.add_connection(conn)


def test_input_port_accepts_only_one_connection():
    g  = ModelGraph()
    c1 = Constant(name="C1", value=1.0)
    c2 = Constant(name="C2", value=2.0)
    ws = WaterStore(name="WS")
    g.add_element(c1); g.add_element(c2); g.add_element(ws)
    g.add_connection(_conn(c1, "value", ws, "inflow"))
    with pytest.raises(ValueError, match="already connected"):
        g.add_connection(_conn(c2, "value", ws, "inflow"))


def test_output_port_allows_multiple_connections():
    """Fan-out: one output → multiple inputs."""
    g  = ModelGraph()
    c  = Constant(name="C", value=1.0)
    w1 = WaterStore(name="W1")
    w2 = WaterStore(name="W2")
    g.add_element(c); g.add_element(w1); g.add_element(w2)
    g.add_connection(_conn(c, "value", w1, "inflow"))
    g.add_connection(_conn(c, "value", w2, "inflow"))
    assert len(g.connections) == 2


def test_remove_connection():
    g, c, ws, th = _simple_graph()
    conn_id = list(g.connections.keys())[0]
    g.remove_connection(conn_id)
    assert len(g.connections) == 1


def test_remove_nonexistent_connection_raises():
    g = ModelGraph()
    with pytest.raises(KeyError):
        g.remove_connection("nonexistent")


# ── Connection query helpers ──────────────────────────────────────────────────

def test_get_connections_from():
    g, c, ws, th = _simple_graph()
    assert len(g.get_connections_from(c.id)) == 1
    assert len(g.get_connections_from(ws.id)) == 1
    assert len(g.get_connections_from(th.id)) == 0


def test_get_connections_to():
    g, c, ws, th = _simple_graph()
    assert len(g.get_connections_to(ws.id)) == 1
    assert len(g.get_connections_to(th.id)) == 1
    assert len(g.get_connections_to(c.id))  == 0


def test_get_connections_to_port():
    g, c, ws, th = _simple_graph()
    conns = g.get_connections_to_port(ws.id, "inflow")
    assert len(conns) == 1
    assert conns[0].from_element_id == c.id


# ── Topological sort ──────────────────────────────────────────────────────────

def test_execution_order_simple_chain():
    """
    Constant → Expression → WaterStore → TimeHistoryResult.
    Hard ordering requirements (from nx edges):
      Rain < Rate  (Constant feeds Expression)
      Rate < Store (Expression feeds WaterStore inflow)
    TH has no nx edge from WS (stock output), so its position is not constrained —
    only check that all four elements are present.
    """
    g  = ModelGraph()
    c  = Constant(name="Rain", value=5.0)
    ex = Expression(name="Rate", formula="Rain * 0.3")
    ws = WaterStore(name="Store")
    th = TimeHistoryResult(name="Plot")
    for el in [c, ex, ws, th]:
        g.add_element(el)
    g.add_connection(_conn(c,  "value",   ex, "Rain"))
    g.add_connection(_conn(ex, "value",   ws, "inflow"))
    g.add_connection(_conn(ws, "storage", th, "series_1"))

    order = g.get_execution_order()
    names = [el.name for el in order]

    # Hard dependencies enforced by nx edges
    assert names.index("Rain") < names.index("Rate")
    assert names.index("Rate") < names.index("Store")
    # All elements present
    assert set(names) == {"Rain", "Rate", "Store", "Plot"}


def test_execution_order_includes_isolated_elements():
    """An element with no connections must still appear in the execution order."""
    g  = ModelGraph()
    c1 = Constant(name="A", value=1.0)
    c2 = Constant(name="B", value=2.0)  # isolated
    g.add_element(c1)
    g.add_element(c2)
    order = g.get_execution_order()
    ids   = [el.id for el in order]
    assert c1.id in ids
    assert c2.id in ids


def test_stock_output_does_not_create_cycle():
    """
    WaterStore.storage → Expression.input is a valid connection.
    Even though it looks like a cycle, the stock breaks it by providing
    its previous-timestep value.
    """
    g  = ModelGraph()
    ws = WaterStore(name="Store", initial_storage=100)
    ex = Expression(name="Evap", formula="Store.storage * 0.01")
    g.add_element(ws)
    g.add_element(ex)
    # This should NOT raise — stock outputs don't add nx edges
    g.add_connection(_conn(ws, "storage", ex, "Store.storage"))
    assert not g.has_cycle()


def test_circular_dependency_detected():
    """Two Expressions referencing each other → ValueError on second connection."""
    g  = ModelGraph()
    e1 = Expression(name="A", formula="B * 2")
    e2 = Expression(name="B", formula="A * 2")
    g.add_element(e1); g.add_element(e2)
    g.add_connection(_conn(e1, "value", e2, "A"))
    with pytest.raises(ValueError, match="circular"):
        g.add_connection(_conn(e2, "value", e1, "B"))


def test_has_cycle_false_for_valid_graph():
    g, *_ = _simple_graph()
    assert g.has_cycle() is False


# ── TimeHistoryResult auto-port ───────────────────────────────────────────────

def test_timehistory_auto_adds_series_port():
    """When series_1 is connected, series_2 is automatically added."""
    g  = ModelGraph()
    c  = Constant(name="C", value=1.0)
    th = TimeHistoryResult(name="Plot")
    g.add_element(c); g.add_element(th)
    g.add_connection(_conn(c, "value", th, "series_1"))
    assert "series_2" in th.input_ports


# ── Name → ID map ─────────────────────────────────────────────────────────────

def test_build_name_to_id_map():
    g, c, ws, th = _simple_graph()
    m = g.build_name_to_id_map()
    assert m["rain"]  == c.id
    assert m["store"] == ws.id
    assert m["plot"]  == th.id


def test_build_name_to_id_map_is_lowercase():
    g = ModelGraph()
    c = Constant(name="DailyRainfall", value=1.0)
    g.add_element(c)
    m = g.build_name_to_id_map()
    assert "dailyrainfall" in m
    assert "DailyRainfall" not in m


# ── Upstream elements ─────────────────────────────────────────────────────────

def test_get_upstream_elements():
    g  = ModelGraph()
    c  = Constant(name="Rain", value=5.0)
    ex = Expression(name="Rate", formula="Rain * 0.3")
    ws = WaterStore(name="Store")
    for el in [c, ex, ws]: g.add_element(el)
    g.add_connection(_conn(c,  "value", ex, "Rain"))
    g.add_connection(_conn(ex, "value", ws, "inflow"))

    upstream_ws = {el.id for el in g.get_upstream_elements(ws.id)}
    assert c.id  in upstream_ws
    assert ex.id in upstream_ws
