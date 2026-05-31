"""Tests for ModelSerialiser — save/load round-trips."""
import json
import pytest
from pathlib import Path
from datetime import date

from hydrosim.model.graph      import ModelGraph
from hydrosim.model.serialiser import ModelSerialiser
from hydrosim.model.base import (
    Connection,
    SimulationSettings,
    ModelFileError,
    VersionMismatchError,
)
from hydrosim.model.elements.constant    import Constant
from hydrosim.model.elements.timeseries  import TimeSeries, TimeSeriesType, InterpolationType
from hydrosim.model.elements.waterstore  import WaterStore
from hydrosim.model.elements.expression  import Expression
from hydrosim.model.elements.timehistory import TimeHistoryResult


def _conn(a, ap, b, bp):
    return Connection("", a.id, ap, b.id, bp)


def _default_settings():
    return SimulationSettings(0.0, 365.0, 1.0, "elapsed", None)


def _full_graph():
    """All 5 element types wired together."""
    g  = ModelGraph()
    c  = Constant(name="RunoffCoeff", value=0.3,   units="-")
    ts = TimeSeries(name="Daily_Rainfall", units="mm/day",
                    data_type=TimeSeriesType.PERIOD_TOTAL,
                    interpolation=InterpolationType.STEP,
                    data=[[0,0],[1,12.3],[2,0],[3,45.2]])
    ex = Expression(name="RunoffRate", formula="Daily_Rainfall * RunoffCoeff",
                    output_units="mm/day")
    ws = WaterStore(name="SoilMoisture", initial_storage=80,
                    lower_bound=0, upper_bound=150, units="mm")
    th = TimeHistoryResult(name="Storage_Plot", title="Soil Moisture",
                           y_axis_units="mm", y_min=0, y_max=150)
    for el in [c, ts, ex, ws, th]: g.add_element(el)
    g.add_connection(_conn(ts, "value",   ex, "Daily_Rainfall"))
    g.add_connection(_conn(c,  "value",   ex, "RunoffCoeff"))
    g.add_connection(_conn(ex, "value",   ws, "inflow"))
    g.add_connection(_conn(ws, "storage", th, "series_1"))
    return g, c, ts, ex, ws, th


# ── to_dict / from_dict ───────────────────────────────────────────────────────

def test_to_dict_top_level_keys():
    g, *_ = _full_graph()
    d = ModelSerialiser.to_dict(g, _default_settings())
    assert d["hydrosim_version"]    == "1.0"
    assert d["file_format_version"] == "1"
    assert "metadata"            in d
    assert "simulation_settings" in d
    assert "elements"            in d
    assert "connections"         in d
    assert "canvas_state"        in d


def test_to_dict_element_count():
    g, *_ = _full_graph()
    d = ModelSerialiser.to_dict(g, _default_settings())
    assert len(d["elements"])    == 5
    assert len(d["connections"]) == 4


def test_to_dict_simulation_settings():
    s = SimulationSettings(0.0, 365.0, 1.0, "elapsed", None)
    g = ModelGraph()
    g.add_element(Constant(name="C", value=1.0))
    d = ModelSerialiser.to_dict(g, s)
    ss = d["simulation_settings"]
    assert ss["start_time"] == pytest.approx(0.0)
    assert ss["end_time"]   == pytest.approx(365.0)
    assert ss["dt"]         == pytest.approx(1.0)
    assert ss["time_mode"]  == "elapsed"
    assert ss["start_date"] is None


def test_to_dict_calendar_settings():
    s = SimulationSettings(0.0, 366.0, 1.0, "calendar", date(2020, 1, 1))
    g = ModelGraph()
    g.add_element(Constant(name="C", value=1.0))
    d = ModelSerialiser.to_dict(g, s)
    assert d["simulation_settings"]["start_date"] == "2020-01-01"


def test_from_dict_roundtrip_full_graph():
    g, c, ts, ex, ws, th = _full_graph()
    s = _default_settings()
    d = ModelSerialiser.to_dict(g, s)

    g2, s2, meta = ModelSerialiser.from_dict(d)

    assert g2.element_count == 5
    assert len(g2.connections) == 4
    assert s2.end_time == pytest.approx(365.0)

    # Check each element's key values survived
    c2  = g2.get_element_by_name("RunoffCoeff")
    ts2 = g2.get_element_by_name("Daily_Rainfall")
    ex2 = g2.get_element_by_name("RunoffRate")
    ws2 = g2.get_element_by_name("SoilMoisture")
    th2 = g2.get_element_by_name("Storage_Plot")

    assert c2.value                  == pytest.approx(0.3)
    assert ts2.data                  == ts.data
    assert ts2.interpolation         == InterpolationType.STEP
    assert ex2.formula               == "Daily_Rainfall * RunoffCoeff"
    assert ws2.initial_storage       == pytest.approx(80.0)
    assert ws2.upper_bound           == pytest.approx(150.0)
    assert th2.title                 == "Soil Moisture"
    assert th2.y_max                 == pytest.approx(150.0)


def test_from_dict_preserves_element_ids():
    g, c, *_ = _full_graph()
    d = ModelSerialiser.to_dict(g, _default_settings())
    g2, *_ = ModelSerialiser.from_dict(d)
    c2 = g2.get_element(c.id)
    assert c2.id == c.id


def test_from_dict_preserves_positions():
    g  = ModelGraph()
    c  = Constant(name="C", value=1.0, position=(120.5, 300.0))
    g.add_element(c)
    d  = ModelSerialiser.to_dict(g, _default_settings())
    g2, *_ = ModelSerialiser.from_dict(d)
    c2 = g2.get_element(c.id)
    assert c2.position[0] == pytest.approx(120.5)
    assert c2.position[1] == pytest.approx(300.0)


def test_from_dict_unbounded_waterstore():
    g  = ModelGraph()
    ws = WaterStore(name="WS", initial_storage=0, upper_bound=None)
    g.add_element(ws)
    d  = ModelSerialiser.to_dict(g, _default_settings())
    g2, *_ = ModelSerialiser.from_dict(d)
    ws2 = g2.get_element(ws.id)
    assert ws2.upper_bound is None


def test_from_dict_expression_ports_rebuilt():
    """Expression input ports are not persisted; they must be rebuilt from formula."""
    g  = ModelGraph()
    ex = Expression(name="Calc", formula="A * B")
    g.add_element(ex)
    d  = ModelSerialiser.to_dict(g, _default_settings())
    g2, *_ = ModelSerialiser.from_dict(d)
    ex2 = g2.get_element(ex.id)
    assert "A" in ex2.input_ports
    assert "B" in ex2.input_ports


# ── save / load (file I/O) ────────────────────────────────────────────────────

def test_save_creates_file(tmp_path):
    g, *_ = _full_graph()
    path = tmp_path / "test_model.hydrosim"
    ModelSerialiser.save(g, _default_settings(), path)
    assert path.exists()
    assert path.stat().st_size > 0


def test_save_produces_valid_json(tmp_path):
    g, *_ = _full_graph()
    path = tmp_path / "test_model.hydrosim"
    ModelSerialiser.save(g, _default_settings(), path)
    with open(path) as f:
        parsed = json.load(f)
    assert parsed["file_format_version"] == "1"


def test_save_load_roundtrip(tmp_path):
    g, c, ts, ex, ws, th = _full_graph()
    path = tmp_path / "roundtrip.hydrosim"
    ModelSerialiser.save(g, _default_settings(), path,
                         metadata={"name": "Test Model"})

    g2, s2, meta = ModelSerialiser.load(path)
    assert g2.element_count   == 5
    assert len(g2.connections) == 4
    assert meta["name"]        == "Test Model"

    c2 = g2.get_element_by_name("RunoffCoeff")
    assert c2.value == pytest.approx(0.3)


def test_save_load_roundtrip_calendar_settings(tmp_path):
    g  = ModelGraph()
    c  = Constant(name="C", value=1.0)
    g.add_element(c)
    s  = SimulationSettings(0.0, 366.0, 1.0, "calendar", date(2020, 1, 1))
    path = tmp_path / "cal.hydrosim"
    ModelSerialiser.save(g, s, path)
    g2, s2, _ = ModelSerialiser.load(path)
    assert s2.time_mode  == "calendar"
    assert s2.start_date == date(2020, 1, 1)


# ── Error handling ────────────────────────────────────────────────────────────

def test_load_file_not_found():
    with pytest.raises(FileNotFoundError):
        ModelSerialiser.load(Path("/nonexistent/path/model.hydrosim"))


def test_load_bad_json(tmp_path):
    path = tmp_path / "bad.hydrosim"
    path.write_text("not valid json {{{", encoding="utf-8")
    with pytest.raises(ModelFileError, match="corrupted"):
        ModelSerialiser.load(path)


def test_load_unknown_element_type(tmp_path):
    g  = ModelGraph()
    c  = Constant(name="C", value=1.0)
    g.add_element(c)
    d  = ModelSerialiser.to_dict(g, _default_settings())
    # Corrupt the element type
    d["elements"][0]["type"] = "StochasticBlackBox"
    path = tmp_path / "bad_type.hydrosim"
    with open(path, "w") as f:
        json.dump(d, f)
    with pytest.raises(ModelFileError, match="Unknown element type"):
        ModelSerialiser.load(path)


def test_load_future_version_raises(tmp_path):
    g  = ModelGraph()
    g.add_element(Constant(name="C", value=1.0))
    d  = ModelSerialiser.to_dict(g, _default_settings())
    d["file_format_version"] = "999"
    path = tmp_path / "future.hydrosim"
    with open(path, "w") as f:
        json.dump(d, f)
    with pytest.raises(VersionMismatchError):
        ModelSerialiser.load(path)


def test_load_missing_required_field(tmp_path):
    """A file missing 'simulation_settings' fails Pydantic validation."""
    d = {
        "hydrosim_version":    "1.0",
        "file_format_version": "1",
        "metadata":            {"name": "Test"},
        "elements":            [],
        "connections":         [],
        # simulation_settings deliberately omitted
    }
    path = tmp_path / "missing_field.hydrosim"
    with open(path, "w") as f:
        json.dump(d, f)
    with pytest.raises(ModelFileError):
        ModelSerialiser.load(path)
