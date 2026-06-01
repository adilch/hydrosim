"""Tests for Reservoir element."""
import pytest
import numpy as np

from hydrosim.model.elements.reservoir import Reservoir
from hydrosim.model.base import SimState, ERR_INVALID_PARAMETER, ERR_BOUNDS_VIOLATION


# ── Sample bathymetry ─────────────────────────────────────────────────────────

_BATHY = [
    [100.0,       0.0,     0.0],
    [102.0,  100_000.0, 25_000.0],
    [105.0,  500_000.0, 60_000.0],
    [108.0, 1_500_000.0, 95_000.0],
    [110.0, 2_000_000.0, 110_000.0],
]


def _state(dt: float = 1.0) -> SimState:
    return SimState(t=0.0, dt=dt, step=0, values={}, storage={})


def _run(res: Reservoir, inflow: float, outflow: float,
         dt: float = 1.0, steps: int = 1) -> SimState:
    state = _state(dt)
    res.prepare()
    res.initialise(state)
    for i in range(steps):
        state.t    = float(i) * dt
        state.step = i
        res.compute(state, {"inflow": inflow, "outflow": outflow})
    return state


# ── Dynamic ports ─────────────────────────────────────────────────────────────

def test_no_bathymetry_no_level_port():
    r = Reservoir(name="R")
    assert "level" not in r.output_ports
    assert "area"  not in r.output_ports


def test_ev_data_adds_level_port():
    r = Reservoir(name="R", bathymetry=_BATHY)
    assert "level" in r.output_ports


def test_ea_data_adds_area_port():
    r = Reservoir(name="R", bathymetry=_BATHY)
    assert "area" in r.output_ports


def test_no_area_column_no_area_port():
    bathy_no_area = [[r[0], r[1]] for r in _BATHY]
    r = Reservoir(name="R", bathymetry=bathy_no_area)
    assert "level" in r.output_ports
    assert "area"  not in r.output_ports


def test_rebuild_output_ports_adds_level():
    r = Reservoir(name="R")
    assert "level" not in r.output_ports
    r.bathymetry = _BATHY
    r.rebuild_output_ports()
    assert "level" in r.output_ports
    assert "area"  in r.output_ports


# ── Basic integration ─────────────────────────────────────────────────────────

def test_integration_grows():
    r     = Reservoir(name="R", initial_volume=0, max_volume=2e6)
    state = _run(r, inflow=50_000, outflow=0, steps=10)
    assert state.get(r.id, "volume") == pytest.approx(500_000.0, abs=1e-6)


def test_zero_flux_unchanged():
    r     = Reservoir(name="R", initial_volume=500_000, max_volume=2e6)
    state = _run(r, inflow=0.0, outflow=0.0, steps=5)
    assert state.get(r.id, "volume") == pytest.approx(500_000.0)


def test_overflow_capped():
    r = Reservoir(name="R", initial_volume=1_900_000, max_volume=2_000_000)
    state = _run(r, inflow=200_000, outflow=0)
    assert state.get(r.id, "volume")   == pytest.approx(2_000_000.0)
    assert state.get(r.id, "overflow") == pytest.approx(100_000.0)


def test_deficit_capped():
    r = Reservoir(name="R", initial_volume=50_000, min_volume=0)
    state = _run(r, inflow=0, outflow=100_000)
    assert state.get(r.id, "volume")  == pytest.approx(0.0)
    assert state.get(r.id, "deficit") == pytest.approx(50_000.0)


def test_unbounded_no_overflow():
    r     = Reservoir(name="R", initial_volume=0, max_volume=None)
    state = _run(r, inflow=1e9, outflow=0, steps=10)
    assert state.get(r.id, "overflow") == pytest.approx(0.0)


# ── E-V interpolation ─────────────────────────────────────────────────────────

def test_level_at_known_volume():
    r = Reservoir(name="R", initial_volume=500_000, max_volume=2e6,
                  bathymetry=_BATHY)
    r.prepare()
    level = r.get_level_at(500_000.0)
    assert level == pytest.approx(105.0, abs=1e-6)


def test_level_interpolated_midpoint():
    r = Reservoir(name="R", bathymetry=_BATHY)
    r.prepare()
    # midpoint between 100_000 (102m) and 500_000 (105m) → 300_000
    # fraction = (300_000 - 100_000) / (500_000 - 100_000) = 0.5
    # elevation = 102 + 0.5 * (105 - 102) = 103.5
    level = r.get_level_at(300_000.0)
    assert level == pytest.approx(103.5, abs=1e-6)


def test_level_extrapolation_below():
    r = Reservoir(name="R", bathymetry=_BATHY)
    r.prepare()
    level = r.get_level_at(0.0)
    assert level == pytest.approx(100.0)  # flat extrapolation at min


def test_level_extrapolation_above():
    r = Reservoir(name="R", bathymetry=_BATHY)
    r.prepare()
    level = r.get_level_at(5_000_000.0)
    assert level == pytest.approx(110.0)  # flat extrapolation at max


def test_level_computed_in_state():
    r     = Reservoir(name="R", initial_volume=500_000, max_volume=2e6,
                      bathymetry=_BATHY)
    state = _run(r, inflow=0, outflow=0, steps=1)
    level = state.get(r.id, "level")
    assert level == pytest.approx(105.0, abs=1e-6)


# ── E-A interpolation ─────────────────────────────────────────────────────────

def test_area_at_known_volume():
    r = Reservoir(name="R", initial_volume=500_000, bathymetry=_BATHY)
    r.prepare()
    area = r.get_area_at(500_000.0)
    # At V=500_000 → elev=105 → area=60_000
    assert area == pytest.approx(60_000.0, abs=1.0)


def test_area_in_state():
    r     = Reservoir(name="R", initial_volume=500_000, max_volume=2e6,
                      bathymetry=_BATHY)
    state = _run(r, inflow=0, outflow=0, steps=1)
    area  = state.get(r.id, "area")
    assert area == pytest.approx(60_000.0, abs=1.0)


# ── Water balance ─────────────────────────────────────────────────────────────

def test_water_balance_closes():
    rng = np.random.default_rng(42)
    r   = Reservoir(name="R", initial_volume=500_000, min_volume=0,
                    max_volume=2_000_000, bathymetry=_BATHY)
    state = _state()
    r.prepare()
    r.initialise(state)

    inflows  = rng.uniform(0, 150_000, 100)
    outflows = rng.uniform(0, 100_000, 100)
    total_ov = total_df = 0.0

    for i in range(100):
        state.t = float(i)
        r.compute(state, {"inflow": inflows[i], "outflow": outflows[i]})
        total_ov += state.get(r.id, "overflow")
        total_df += state.get(r.id, "deficit")

    delta_v  = state.get(r.id, "volume") - 500_000.0
    net_flux = inflows.sum() - outflows.sum() - total_ov + total_df
    assert abs(delta_v - net_flux) < 1e-6 * max(inflows.sum(), 1.0)


# ── Validation ────────────────────────────────────────────────────────────────

def test_validate_ok():
    r = Reservoir(name="R", initial_volume=500_000, min_volume=0,
                  max_volume=2_000_000, bathymetry=_BATHY)
    assert r.validate() == []


def test_validate_max_below_min():
    r = Reservoir(name="R", initial_volume=0, min_volume=500_000,
                  max_volume=100_000)
    errors = r.validate()
    assert any(e.code == ERR_INVALID_PARAMETER for e in errors)


def test_validate_initial_outside_bounds():
    r = Reservoir(name="R", initial_volume=3_000_000, min_volume=0,
                  max_volume=2_000_000)
    errors = r.validate()
    assert any(e.code == ERR_BOUNDS_VIOLATION for e in errors)


def test_validate_non_monotonic_elevations():
    bad_bathy = [[100.0, 0], [98.0, 100_000], [110.0, 500_000]]  # elev goes down
    r = Reservoir(name="R", bathymetry=bad_bathy)
    errors = r.validate()
    assert any(e.code == ERR_INVALID_PARAMETER for e in errors)


def test_validate_non_monotonic_volumes():
    bad_bathy = [[100.0, 500_000], [105.0, 100_000]]  # volume goes down
    r = Reservoir(name="R", bathymetry=bad_bathy)
    errors = r.validate()
    assert any(e.code == ERR_INVALID_PARAMETER for e in errors)


# ── Serialisation ─────────────────────────────────────────────────────────────

def test_to_dict_structure():
    r = Reservoir(name="Warragamba", initial_volume=2_050_000,
                  min_volume=0, max_volume=2_027_000_000,
                  volume_units="m3", flow_units="m3/day",
                  bathymetry=_BATHY[:2])
    d = r.to_dict()
    assert d["type"] == "Reservoir"
    assert d["parameters"]["initial_volume"] == pytest.approx(2_050_000.0)
    assert d["parameters"]["volume_units"]   == "m3"
    assert len(d["parameters"]["bathymetry"]) == 2


def test_from_dict_roundtrip():
    r  = Reservoir(name="Warragamba", initial_volume=500_000,
                   min_volume=0, max_volume=2_000_000,
                   volume_units="ML", flow_units="ML/day",
                   bathymetry=_BATHY, description="test reservoir",
                   position=(300.0, 200.0))
    r2 = Reservoir.from_dict(r.to_dict())
    assert r2.name           == r.name
    assert r2.initial_volume == pytest.approx(r.initial_volume)
    assert r2.max_volume     == pytest.approx(r.max_volume)
    assert r2.volume_units   == r.volume_units
    assert r2.bathymetry     == r.bathymetry
    assert r2.id             == r.id
    # Dynamic ports rebuilt from bathymetry
    assert "level" in r2.output_ports
    assert "area"  in r2.output_ports


def test_unbounded_roundtrip():
    r  = Reservoir(name="R", max_volume=None)
    r2 = Reservoir.from_dict(r.to_dict())
    assert r2.max_volume is None
