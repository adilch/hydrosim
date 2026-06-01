"""
Generate "Blue Mountains Reservoir — Annual Water Balance (2020).hydrosim"

A realistic daily water balance for a 50 GL reservoir in southeastern Australia.

Model structure:
                        Catchment_Area (Constant)
  Daily_Rainfall ──────►  RunoffInflow (Expression) ──► BlueReservoir ──► volume ──► Volume_Plot
  (TimeSeries)   │         (rain × area × coeff / 1000)      │              overflow ─┘
                 │                                             │ area
  Monthly_PanEvap──► EvapLoss (Expression)                    ▼             level ──► Level_Plot
  (TimeSeries)   │   (panEvap × area × factor / 1000)  EvapLoss.outflow
  Pan_Factor ────┘

Key outputs:
  BlueReservoir.volume   — stored volume (m³)
  BlueReservoir.level    — water surface elevation via E-V curve (m)
  BlueReservoir.overflow — spill over the dam wall (m³/day)
  BlueReservoir.area     — surface area (m²) — fed back into evaporation

Run with:  python make_reservoir_example.py
Open in HydroSim -> File > Open -> press F5 to run.
Double-click Volume_Plot or Level_Plot to view results.
"""
import json, math, random
from pathlib import Path
from datetime import datetime, timezone
import uuid

random.seed(2020)

# ── Synthetic daily rainfall — 800 mm/year, subtropical seasonal ─────────────
def rainfall_day(doy: int) -> float:
    """
    Wet months: April-June (frontal systems) and January-February (summer storms).
    Dry months: August-October.
    """
    # Dual-peak seasonal probability
    p1 = max(0, math.cos(2 * math.pi * (doy - 135) / 365))  # peak mid-May
    p2 = max(0, math.cos(2 * math.pi * (doy - 30)  / 365))  # peak late-Jan
    prob = 0.12 + 0.20 * max(p1, p2)
    if random.random() > prob:
        return 0.0
    r = random.random()
    if r < 0.60: return round(random.uniform(1, 15), 1)
    if r < 0.85: return round(random.uniform(15, 40), 1)
    if r < 0.95: return round(random.uniform(40, 80), 1)
    return round(random.uniform(80, 140), 1)   # rare extreme events

rainfall = [[float(d), rainfall_day(d + 1)] for d in range(365)]

# Diagnostic: total annual rainfall
total_rain = sum(r[1] for r in rainfall)
print(f"  Annual rainfall     : {total_rain:.0f} mm")

# ── Monthly pan evaporation (mm/day) — sinusoidal, peak Jan, min Jul ─────────
def pet_day(doy: int) -> float:
    """Pan evaporation: 8 mm/day peak (summer), 2 mm/day min (winter)."""
    return round(5.0 + 3.0 * math.cos(2 * math.pi * (doy - 15) / 365), 2)

pan_evap = [[float(d), pet_day(d + 1)] for d in range(365)]

# ── Reservoir bathymetry — Blue Mountains 50 GL reservoir ────────────────────
# [Elevation (m AHD), Volume (m³), Surface Area (m²)]
# Physically consistent: as elevation rises, volume and area increase
bathymetry = [
    [195.0,          0,         0],
    [198.0,    500_000,   180_000],
    [201.0,  2_500_000,   650_000],
    [204.0,  7_000_000, 1_400_000],
    [207.0, 16_000_000, 2_600_000],
    [210.0, 30_000_000, 3_800_000],
    [213.0, 43_000_000, 4_600_000],
    [215.0, 50_000_000, 5_200_000],   # full supply level
]

# ── Element IDs ───────────────────────────────────────────────────────────────
def uid(): return str(uuid.uuid4())

rain_id      = uid()
pan_evap_id  = uid()
catchment_id = uid()
coeff_id     = uid()
pan_fac_id   = uid()
runoff_id    = uid()
evap_id      = uid()
res_id       = uid()
vol_plot_id  = uid()
lvl_plot_id  = uid()

def conn(fid, fp, tid, tp):
    return {"id": uid(), "from_element_id": fid, "from_port_name": fp,
            "to_element_id": tid, "to_port_name": tp}

# RunoffInflow = Daily_Rainfall (mm/day) × Catchment_Area (m²) × Runoff_Coeff / 1000
# Units: mm/day × m² / 1000 = m/day × m² × 10⁻³ = 10⁻³ m³/day per mm per m²
# = m³/day (correct — divide by 1000 to convert mm -> m)
# EvapLoss = Monthly_PanEvap (mm/day) × BlueReservoir.area (m²) × Pan_Factor / 1000

connections = [
    # RunoffInflow inputs
    conn(rain_id,      "value",   runoff_id, "Daily_Rainfall"),
    conn(catchment_id, "value",   runoff_id, "Catchment_Area"),
    conn(coeff_id,     "value",   runoff_id, "Runoff_Coeff"),

    # EvapLoss inputs
    conn(pan_evap_id, "value",   evap_id, "Monthly_PanEvap"),
    conn(res_id,      "area",    evap_id, "BlueReservoir.area"),   # feedback from stock
    conn(pan_fac_id,  "value",   evap_id, "Pan_Factor"),

    # Reservoir inflow / outflow
    conn(runoff_id, "value",    res_id, "inflow"),
    conn(evap_id,   "value",    res_id, "outflow"),

    # Volume plot: stored volume + overflow
    conn(res_id, "volume",   vol_plot_id, "series_1"),
    conn(res_id, "overflow", vol_plot_id, "series_2"),

    # Level plot: water surface elevation + daily rainfall (secondary axis)
    conn(res_id,   "level", lvl_plot_id, "series_1"),
    conn(rain_id, "value",  lvl_plot_id, "series_2"),
]

elements = [
    # ── Input elements ────────────────────────────────────────────────────
    {
        "id": rain_id, "type": "TimeSeries", "name": "Daily_Rainfall",
        "description": "Synthetic daily rainfall for Blue Mountains catchment (mm/day). "
                       "Dual-peak seasonal pattern: summer storms + winter fronts.",
        "position": [60, 80],
        "parameters": {
            "units": "mm/day", "data_type": "period_total",
            "interpolation": "step", "data": rainfall
        }
    },
    {
        "id": pan_evap_id, "type": "TimeSeries", "name": "Monthly_PanEvap",
        "description": "Daily pan evaporation rate (mm/day). "
                       "Sinusoidal seasonal: 8 mm/day peak Jan, 2 mm/day min Jul.",
        "position": [60, 340],
        "parameters": {
            "units": "mm/day", "data_type": "period_average",
            "interpolation": "linear", "data": pan_evap
        }
    },
    {
        "id": catchment_id, "type": "Constant", "name": "Catchment_Area",
        "description": "Ungauged catchment draining to Blue Mountains Reservoir (m²). "
                       "800 km² — derived from topographic analysis.",
        "position": [60, 200],
        "parameters": {"value": 800_000_000.0, "units": "m2"}
    },
    {
        "id": coeff_id, "type": "Constant", "name": "Runoff_Coeff",
        "description": "Catchment runoff coefficient (dimensionless). "
                       "0.08 — low because dry eucalypt forest with deep soils.",
        "position": [60, 440],
        "parameters": {"value": 0.08, "units": "-"}
    },
    {
        "id": pan_fac_id, "type": "Constant", "name": "Pan_Factor",
        "description": "Pan-to-lake evaporation conversion factor (dimensionless). "
                       "0.75 — standard Australian value (FAO 56).",
        "position": [60, 540],
        "parameters": {"value": 0.75, "units": "-"}
    },

    # ── Expression elements ───────────────────────────────────────────────
    {
        "id": runoff_id, "type": "Expression", "name": "RunoffInflow",
        "description": "Daily runoff volume reaching the reservoir (m³/day). "
                       "Formula: rainfall (mm/day) × catchment area (m²) × runoff coefficient / 1000",
        "position": [380, 160],
        "parameters": {
            "formula": "Daily_Rainfall * Catchment_Area * Runoff_Coeff / 1000",
            "output_units": "m3/day"
        }
    },
    {
        "id": evap_id, "type": "Expression", "name": "EvapLoss",
        "description": "Daily evaporation loss from reservoir surface (m³/day). "
                       "Uses reservoir area output from previous timestep (stock feedback). "
                       "Formula: pan evap (mm/day) × surface area (m²) × pan factor / 1000",
        "position": [380, 460],
        "parameters": {
            "formula": "Monthly_PanEvap * BlueReservoir.area * Pan_Factor / 1000",
            "output_units": "m3/day"
        }
    },

    # ── Reservoir stock ───────────────────────────────────────────────────
    {
        "id": res_id, "type": "Reservoir", "name": "BlueReservoir",
        "description": "Blue Mountains Reservoir — 50 GL full supply capacity (FSL = 215 m AHD). "
                       "Bathymetry from storage survey. "
                       "Inflow from catchment runoff; outflow from open-water evaporation.",
        "position": [680, 300],
        "parameters": {
            "initial_volume": 25_000_000.0,    # start at 50% capacity
            "min_volume":     0.0,
            "max_volume":     50_000_000.0,    # 50 GL full supply
            "volume_units":   "m3",
            "flow_units":     "m3/day",
            "bathymetry":     bathymetry
        }
    },

    # ── Result elements ───────────────────────────────────────────────────
    {
        "id": vol_plot_id, "type": "TimeHistoryResult", "name": "Volume_Plot",
        "description": "Reservoir storage volume and daily overflow to downstream (m³/day).",
        "position": [980, 180],
        "parameters": {
            "title":        "Blue Mountains Reservoir — Storage Volume (2020)",
            "y_axis_label": "Volume / Overflow",
            "y_axis_units": "m3",
            "show_grid":    True,
            "y_min": 0.0, "y_max": 55_000_000.0
        }
    },
    {
        "id": lvl_plot_id, "type": "TimeHistoryResult", "name": "Level_Plot",
        "description": "Water surface elevation (m AHD) from E-V curve, "
                       "with daily rainfall on secondary axis for context.",
        "position": [980, 460],
        "parameters": {
            "title":        "Blue Mountains Reservoir — Water Level & Rainfall (2020)",
            "y_axis_label": "Elevation (m AHD) / Rainfall (mm/day)",
            "y_axis_units": "-",
            "show_grid":    True,
            "y_min": None, "y_max": None
        }
    },
]

# ── Top-level file ─────────────────────────────────────────────────────────
now = datetime.now(timezone.utc).isoformat()
model = {
    "hydrosim_version":    "1.0",
    "file_format_version": "1",
    "metadata": {
        "name": "Blue Mountains Reservoir — Annual Water Balance (2020)",
        "description": (
            "Daily water balance for a 50 GL reservoir in southeastern Australia. "
            "Demonstrates the Reservoir element with elevation-volume-area bathymetry. "
            "Inflow from catchment runoff; outflow from area-dependent evaporation. "
            "Open in HydroSim and press F5 to run."
        ),
        "author":   "HydroSim example model",
        "created":  now,
        "modified": now,
    },
    "simulation_settings": {
        "start_time": 0.0,
        "end_time":   365.0,
        "dt":         1.0,
        "time_mode":  "calendar",
        "start_date": "2020-01-01",
    },
    "elements":    elements,
    "connections": connections,
    "canvas_state": {"zoom": 0.65, "pan_x": -30.0, "pan_y": 0.0},
}

out_path = Path("BlueMountains_Reservoir_2020.hydrosim")
out_path.write_text(json.dumps(model, indent=2), encoding="utf-8")
print(f"  Saved: {out_path}  ({out_path.stat().st_size // 1024} KB)")

# ── Self-test ─────────────────────────────────────────────────────────────────
print("\nRunning self-test ...")
from hydrosim.model.serialiser import ModelSerialiser
from hydrosim.model.validator  import ModelValidator
from hydrosim.engine.runner    import SimulationRunner

g, s, m = ModelSerialiser.load(out_path)
print(f"  Loaded: {g.element_count} elements, {len(g.connections)} connections")

errors = ModelValidator(g).validate_all()
assert not errors, f"Validation errors: {errors}"
print("  Validation: OK")

results = SimulationRunner(g, s).run()
assert results.is_complete
print(f"  Simulation: {results.completed_steps} steps in {results.run_duration_s*1000:.0f} ms")

volume   = results.get_series_by_name("BlueReservoir", "volume")
level    = results.get_series_by_name("BlueReservoir", "level")
overflow = results.get_series_by_name("BlueReservoir", "overflow")

print(f"\n  BlueReservoir results:")
print(f"    Volume   : {volume.min()/1e6:.1f} – {volume.max()/1e6:.1f} GL  "
      f"(initial 25 GL, capacity 50 GL)")
print(f"    Level    : {level.min():.1f} – {level.max():.1f} m AHD  "
      f"(FSL = 215 m)")
print(f"    Overflow : {overflow.sum()/1e6:.1f} GL total spill")

# Report all tracked series
all_s = results.get_all_series()
print(f"\n  Tracked series ({sum(len(v) for v in all_s.values())}):")
for el_name, ports in all_s.items():
    for port_name, arr in ports.items():
        print(f"    {el_name}.{port_name}:  min={arr.min():.3g}  max={arr.max():.3g}")

# Level always within bathymetry bounds [195, 215] m
assert level.min() >= 195.0 - 0.1, f"Level below bathymetry minimum: {level.min()}"
assert level.max() <= 215.0 + 0.1, f"Level above FSL: {level.max()}"
print(f"    Level within bathymetry bounds [195, 215] m OK")

# Volume always within reservoir bounds
assert volume.min() >= 0.0,           "Volume went below zero"
assert volume.max() <= 50_000_000.1,  "Volume exceeded maximum"
print(f"    Volume within bounds [0, 50 GL] OK")

df = results.export_dataframe()
print(f"\n  DataFrame: {df.shape[0]} rows × {df.shape[1]} columns")
print(f"  Columns  : {list(df.columns)}")

print(f"""
Model ready — open in HydroSim:
  File > Open > {out_path}
  Press F5 to run
  Double-click Volume_Plot  -> reservoir volume + overflow
  Double-click Level_Plot   -> water level (m AHD) + daily rainfall
  In Level_Plot, set series_2 (Daily_Rainfall) to Right axis for dual-axis view
""")
