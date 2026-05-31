"""Tests for SimulationRunner — includes the critical integration tests."""
import threading
import pytest
import numpy as np

from hydrosim.model.graph    import ModelGraph
from hydrosim.model.base     import Connection, SimulationSettings, SimulationError, SimulationAborted
from hydrosim.engine.runner  import SimulationRunner
from hydrosim.model.elements import Constant, TimeSeries, WaterStore, Expression, TimeHistoryResult
from hydrosim.model.base import InterpolationType, TimeSeriesType


def _conn(a, ap, b, bp):
    return Connection("", a.id, ap, b.id, bp)


def _settings(end=10, dt=1.0):
    return SimulationSettings(0.0, float(end), dt, "elapsed", None)


def _simple_graph(inflow=5.0, initial=100.0, upper=200.0):
    """Constant(inflow) → WaterStore → TimeHistoryResult"""
    g  = ModelGraph()
    c  = Constant(name="Rain", value=inflow, description="inflow")
    ws = WaterStore(name="Store", initial_storage=initial,
                    lower_bound=0, upper_bound=upper,
                    units="mm", description="storage")
    th = TimeHistoryResult(name="Plot", description="result")
    for el in [c, ws, th]: g.add_element(el)
    g.add_connection(_conn(c,  "value",   ws, "inflow"))
    g.add_connection(_conn(ws, "storage", th, "series_1"))
    return g, c, ws, th


# ── Basic simulation ──────────────────────────────────────────────────────────

def test_simple_run_final_storage():
    """inflow=5/day, initial=100, 10 steps → final=150"""
    g, c, ws, th = _simple_graph(inflow=5.0, initial=100.0)
    results = SimulationRunner(g, _settings(end=10)).run()

    series = results.get_series_by_name("Store", "storage")
    assert results.is_complete
    assert series[-1] == pytest.approx(150.0, abs=1e-9)
    assert len(series) == 10


def test_storage_grows_monotonically():
    g, *_ = _simple_graph(inflow=3.0, initial=50.0)
    results = SimulationRunner(g, _settings(end=5)).run()
    series  = results.get_series_by_name("Store", "storage")
    for i in range(1, len(series)):
        assert series[i] >= series[i - 1]


def test_zero_inflow_storage_unchanged():
    g, c, ws, th = _simple_graph(inflow=0.0, initial=80.0)
    results = SimulationRunner(g, _settings(end=10)).run()
    series  = results.get_series_by_name("Store", "storage")
    assert np.allclose(series, 80.0)


def test_results_shape():
    g, *_ = _simple_graph()
    results = SimulationRunner(g, _settings(end=365)).run()
    series  = results.get_series_by_name("Store", "storage")
    assert len(series) == 365
    assert len(results.timesteps) == 365


# ── Expression element in chain ───────────────────────────────────────────────

def test_simulation_with_expression():
    """Constant(10) → Expression(Rain * 0.3) → WaterStore(0) → 5 days → 15"""
    g  = ModelGraph()
    c  = Constant(name="Rain",   value=10.0, description="rain")
    ex = Expression(name="Runoff", formula="Rain * 0.3",
                    output_units="mm/day", description="runoff")
    ws = WaterStore(name="Store", initial_storage=0,
                    lower_bound=0, description="store")
    th = TimeHistoryResult(name="Plot", description="plot")
    for el in [c, ex, ws, th]: g.add_element(el)
    g.add_connection(_conn(c,  "value", ex, "Rain"))
    g.add_connection(_conn(ex, "value", ws, "inflow"))
    g.add_connection(_conn(ws, "storage", th, "series_1"))

    results = SimulationRunner(g, _settings(end=5)).run()
    series  = results.get_series_by_name("Store", "storage")
    assert series[-1] == pytest.approx(15.0, abs=1e-6)


def test_expression_with_t_variable():
    """Expression uses t; output should change each step."""
    g  = ModelGraph()
    ex = Expression(name="TimeVal", formula="t * 2.0",
                    output_units="-", description="time×2")
    th = TimeHistoryResult(name="Plot", description="plot")
    g.add_element(ex); g.add_element(th)
    g.add_connection(_conn(ex, "value", th, "series_1"))

    results = SimulationRunner(g, _settings(end=5)).run()
    series  = results.get_series_by_name("TimeVal", "value")
    # t=0,1,2,3,4 → values 0,2,4,6,8
    expected = [0.0, 2.0, 4.0, 6.0, 8.0]
    assert np.allclose(series, expected)


# ── TimeSeries element ────────────────────────────────────────────────────────

def test_simulation_with_timeseries():
    """TimeSeries → WaterStore: storage should match cumulative rainfall."""
    data = [[float(i), float(i)] for i in range(10)]  # value = day number
    g  = ModelGraph()
    ts = TimeSeries(name="Rain", data=data,
                    interpolation=InterpolationType.STEP,
                    description="rain")
    ws = WaterStore(name="Store", initial_storage=0,
                    lower_bound=0, description="store")
    th = TimeHistoryResult(name="Plot", description="plot")
    for el in [ts, ws, th]: g.add_element(el)
    g.add_connection(_conn(ts, "value",   ws, "inflow"))
    g.add_connection(_conn(ws, "storage", th, "series_1"))

    results = SimulationRunner(g, _settings(end=5)).run()
    series  = results.get_series_by_name("Store", "storage")
    # Steps 0..4: inflow = 0,1,2,3,4 → storage = 0,1,3,6,10
    assert series[-1] == pytest.approx(10.0, abs=1e-6)


# ── WaterStore overflow / water balance ───────────────────────────────────────

def test_overflow_tracked_in_results():
    g  = ModelGraph()
    c  = Constant(name="Rain", value=10.0, description="rain")
    ws = WaterStore(name="Store", initial_storage=195,
                    lower_bound=0, upper_bound=200, description="store")
    th = TimeHistoryResult(name="Plot", description="plot")
    for el in [c, ws, th]: g.add_element(el)
    g.add_connection(_conn(c,  "value",   ws, "inflow"))
    g.add_connection(_conn(ws, "storage", th, "series_1"))
    # Also track overflow
    g.add_connection(_conn(ws, "overflow", th, "series_2"))

    results = SimulationRunner(g, _settings(end=5)).run()
    overflow = results.get_series_by_name("Store", "overflow")
    assert overflow.sum() > 0


def test_water_balance_closes_over_365_days():
    """
    Strict water balance test: ΔS == (inflow - outflow - overflow + deficit) * dt
    over 365 daily steps. Error must be < 1e-6 of total inflow.
    """
    rng  = np.random.default_rng(42)
    data = [[float(i), max(0.0, rng.normal(3.0, 2.0))] for i in range(366)]

    g  = ModelGraph()
    ts = TimeSeries(name="Rain", data=data,
                    interpolation=InterpolationType.STEP, description="rain")
    ws = WaterStore(name="Store", initial_storage=80,
                    lower_bound=0, upper_bound=150, units="mm", description="store")
    th = TimeHistoryResult(name="Plot", description="plot")
    for el in [ts, ws, th]: g.add_element(el)
    g.add_connection(_conn(ts, "value",   ws, "inflow"))
    g.add_connection(_conn(ws, "storage", th, "series_1"))
    # Track overflow and deficit too
    g.add_connection(_conn(ws, "overflow", th, "series_2"))
    g.add_connection(_conn(ws, "deficit",  th, "series_3"))

    results = SimulationRunner(g, _settings(end=365)).run()
    storage  = results.get_series_by_name("Store",   "storage")
    overflow = results.get_series_by_name("Store",   "overflow")
    deficit  = results.get_series_by_name("Store",   "deficit")
    rain     = [row[1] for row in data[:365]]

    delta_s   = storage[-1] - 80.0
    total_in  = sum(rain)
    net_flux  = sum(rain) - overflow.sum() + deficit.sum()
    balance_err = abs(delta_s - net_flux)
    assert balance_err < 1e-6 * max(total_in, 1.0), \
        f"Water balance error {balance_err:.2e} exceeds threshold"


# ── Multiple series in TimeHistoryResult ─────────────────────────────────────

def test_multiple_series_tracked():
    g, c, ws, th = _simple_graph()
    g.add_connection(_conn(ws, "overflow", th, "series_2"))

    results = SimulationRunner(g, _settings(end=5)).run()
    storage  = results.get_series_by_name("Store", "storage")
    overflow = results.get_series_by_name("Store", "overflow")
    assert len(storage)  == 5
    assert len(overflow) == 5


# ── Progress callback ─────────────────────────────────────────────────────────

def test_progress_callback_called():
    g, *_ = _simple_graph()
    progress_values = []
    SimulationRunner(g, _settings(end=10)).run(
        progress_callback=lambda p: progress_values.append(p)
    )
    assert len(progress_values) == 10
    assert progress_values[-1] == pytest.approx(1.0)
    assert progress_values[0]  == pytest.approx(0.1)


# ── Stop signal ───────────────────────────────────────────────────────────────

def test_stop_aborts_run():
    """
    stop() via progress_callback aborts simulation deterministically.
    We call stop() inside the callback once progress > 10%.
    """
    g  = ModelGraph()
    c  = Constant(name="Rain", value=1.0, description="rain")
    ws = WaterStore(name="Store", initial_storage=0,
                    upper_bound=None, description="store")
    th = TimeHistoryResult(name="Plot", description="plot")
    for el in [c, ws, th]: g.add_element(el)
    g.add_connection(_conn(c,  "value",   ws, "inflow"))
    g.add_connection(_conn(ws, "storage", th, "series_1"))

    runner = SimulationRunner(g, _settings(end=1000))

    def _stop_at_10pct(progress: float) -> None:
        if progress >= 0.10:
            runner.stop()

    with pytest.raises(SimulationAborted) as exc_info:
        runner.run(progress_callback=_stop_at_10pct)

    # Should have stopped well before 100%
    assert exc_info.value.step < 1000


# ── Validation failures ───────────────────────────────────────────────────────

def test_invalid_model_raises_simulation_error():
    """Empty model → SimulationError before any timestep runs."""
    g = ModelGraph()
    with pytest.raises(SimulationError):
        SimulationRunner(g, _settings()).run()


def test_missing_required_port_raises():
    """A non-isolated Expression with an unconnected required port → SimulationError."""
    g  = ModelGraph()
    c  = Constant(name="A", value=1.0, description="d")
    ex = Expression(name="Calc", formula="A + B", description="d")  # B never connected
    th = TimeHistoryResult(name="Plot", description="plot")
    for el in [c, ex, th]: g.add_element(el)
    # Connect A and ex→th (non-isolated) but leave B disconnected
    g.add_connection(Connection("", c.id, "value", ex.id, "A"))
    g.add_connection(Connection("", ex.id, "value", th.id, "series_1"))
    with pytest.raises(SimulationError):
        SimulationRunner(g, _settings()).run()


# ── ResultsStore interface ────────────────────────────────────────────────────

def test_results_export_dataframe():
    g, *_ = _simple_graph()
    results = SimulationRunner(g, _settings(end=5)).run()
    df = results.export_dataframe()
    assert "time_days" in df.columns
    assert len(df) == 5
    # Should have a column for Store.storage
    storage_col = [c for c in df.columns if "storage" in c]
    assert len(storage_col) == 1


def test_results_get_all_series():
    g, *_ = _simple_graph()
    results = SimulationRunner(g, _settings(end=5)).run()
    all_s   = results.get_all_series()
    assert "Store" in all_s
    assert "storage" in all_s["Store"]


def test_get_series_not_tracked_raises():
    g, c, ws, th = _simple_graph()
    results = SimulationRunner(g, _settings(end=5)).run()
    with pytest.raises(KeyError):
        results.get_series(c.id, "value")   # Constant is not tracked (not in TH)


# ── Sub-daily timestep ────────────────────────────────────────────────────────

def test_hourly_timestep():
    """dt=1/24 (hourly), run 1 day → 24 steps."""
    g, c, ws, th = _simple_graph(inflow=24.0, initial=0.0, upper=10000.0)
    s = SimulationSettings(0.0, 1.0, 1.0/24, "elapsed", None)
    results = SimulationRunner(g, s).run()
    series  = results.get_series_by_name("Store", "storage")
    assert len(series) == 24
    # 24 steps × 24 mm/day × (1/24) day/step = 24 mm total
    assert series[-1] == pytest.approx(24.0, abs=1e-6)
