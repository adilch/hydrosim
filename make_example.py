"""
Generate "Hawkesbury Catchment Daily Water Balance (2020).hydrosim"

A realistic 365-day dual-store water balance for a humid temperate catchment:

  Daily_Rainfall  ──►  RunoffRate  (25% runoff)
        │
        ├──►  NetSoilInflow  (rainfall - runoff - ET)
        │              │
        └──►  ActualET  │
                        ▼
                   SoilMoisture  (0–200 mm)
                        │ overflow ──►  ShallowGW  (0–400 mm)
                        │                   │ drainage (slow)
                        │                   ▼ outflow
                        ▼
                   SoilMoisture_Plot   (series: storage + overflow)
                   Groundwater_Plot    (series: GW storage + rainfall)

Seasonal pattern: wet summer/autumn (Jan-Apr, Oct-Dec), dry winter (Jun-Aug).
"""
import json, math, random
from pathlib import Path
from datetime import datetime, timezone
import uuid

random.seed(42)

# ── Synthetic daily rainfall — 700 mm/year with seasonal wet/dry cycle ───────
def rainfall_day(doy: int) -> float:
    # Wet season Jan-Apr (doy 1-120) and Oct-Dec (doy 274-365)
    # Dry season May-Sep (doy 121-273)
    wet_factor = max(0, math.cos(2 * math.pi * (doy - 15) / 365))
    prob = 0.10 + 0.25 * wet_factor
    if random.random() > prob:
        return 0.0
    r = random.random()
    if r < 0.55: return round(random.uniform(1,   12), 1)  # light
    if r < 0.82: return round(random.uniform(12,  30), 1)  # moderate
    if r < 0.95: return round(random.uniform(30,  65), 1)  # heavy
    return round(random.uniform(65, 110), 1)                # rare extreme

rainfall = [[float(d), rainfall_day(d + 1)] for d in range(365)]

# ── Potential ET — sinusoidal seasonal, higher in summer ─────────────────────
def pet_day(doy: int) -> float:
    return round(3.2 + 2.0 * math.cos(2 * math.pi * (doy - 15) / 365), 2)

pet_data = [[float(d), pet_day(d + 1)] for d in range(365)]

# ── Groundwater drainage series: slow base-flow (0.8 mm/day) ─────────────────
# Represented as a Constant so it can connect to ShallowGW outflow
# (In a real model you'd use an Expression referencing GW.storage)

def uid(): return str(uuid.uuid4())

# Element IDs
rain_id    = uid()
pet_id     = uid()
rc_id      = uid()
drain_id   = uid()   # Constant: base-flow drainage from GW
runoff_id  = uid()
et_id      = uid()
net_id     = uid()
soil_id    = uid()
gw_id      = uid()
plot1_id   = uid()
plot2_id   = uid()

def conn(fid, fp, tid, tp):
    return {"id": uid(), "from_element_id": fid, "from_port_name": fp,
            "to_element_id": tid, "to_port_name": tp}

connections = [
    # Rainfall + RunoffCoeff → RunoffRate
    conn(rain_id,   "value",   runoff_id, "Daily_Rainfall"),
    conn(rc_id,     "value",   runoff_id, "RunoffCoeff"),

    # Rainfall + PET → ActualET
    conn(rain_id,   "value",   et_id,     "Daily_Rainfall"),
    conn(pet_id,    "value",   et_id,     "PET"),

    # All → NetSoilInflow
    conn(rain_id,   "value",   net_id,    "Daily_Rainfall"),
    conn(runoff_id, "value",   net_id,    "RunoffRate"),
    conn(et_id,     "value",   net_id,    "ActualET"),

    # NetSoilInflow → SoilMoisture
    conn(net_id,    "value",   soil_id,   "inflow"),

    # SoilMoisture overflow → ShallowGW inflow
    conn(soil_id,   "overflow", gw_id,   "inflow"),

    # Constant drainage → ShallowGW outflow (slow base-flow)
    conn(drain_id,  "value",   gw_id,    "outflow"),

    # Plot 1: SoilMoisture storage + overflow
    conn(soil_id,   "storage",  plot1_id, "series_1"),
    conn(soil_id,   "overflow", plot1_id, "series_2"),

    # Plot 2: GW storage + daily rainfall
    conn(gw_id,     "storage",  plot2_id, "series_1"),
    conn(rain_id,   "value",    plot2_id, "series_2"),
]

elements = [
    # ── Input elements (green) ────────────────────────────────────────────
    {
        "id": rain_id, "type": "TimeSeries", "name": "Daily_Rainfall",
        "description": "Synthetic daily rainfall, Hawkesbury region 2020 (mm/day). "
                       "Wet season Jan-Apr + Oct-Dec; dry May-Sep.",
        "position": [60, 200],
        "parameters": {
            "units": "mm/day", "data_type": "period_total",
            "interpolation": "step", "data": rainfall
        }
    },
    {
        "id": pet_id, "type": "TimeSeries", "name": "PET",
        "description": "Potential evapotranspiration — sinusoidal seasonal pattern, "
                       "peak 5.2 mm/day in Jan, trough 1.2 mm/day in Jul.",
        "position": [60, 440],
        "parameters": {
            "units": "mm/day", "data_type": "period_average",
            "interpolation": "linear", "data": pet_data
        }
    },
    {
        "id": rc_id, "type": "Constant", "name": "RunoffCoeff",
        "description": "Fraction of rainfall converted to direct runoff (0.25 = 25%). "
                       "Represents impervious areas and saturated soil response.",
        "position": [60, 320],
        "parameters": {"value": 0.25, "units": "-"}
    },
    {
        "id": drain_id, "type": "Constant", "name": "GW_Baseflow",
        "description": "Constant groundwater drainage rate (base-flow) = 1.2 mm/day. "
                       "Represents slow seepage to streams and deep percolation.",
        "position": [60, 560],
        "parameters": {"value": 1.2, "units": "mm/day"}
    },

    # ── Expression elements (teal) ────────────────────────────────────────
    {
        "id": runoff_id, "type": "Expression", "name": "RunoffRate",
        "description": "Direct runoff = rainfall × runoff coefficient. "
                       "This water bypasses the soil store entirely.",
        "position": [380, 260],
        "parameters": {
            "formula": "Daily_Rainfall * RunoffCoeff",
            "output_units": "mm/day"
        }
    },
    {
        "id": et_id, "type": "Expression", "name": "ActualET",
        "description": "Actual ET = min(PET, 70% of rainfall). ET is limited by water availability "
                       "on dry days. Uses Budyko-style supply limitation.",
        "position": [380, 460],
        "parameters": {
            "formula": "min(PET, Daily_Rainfall * 0.7)",
            "output_units": "mm/day"
        }
    },
    {
        "id": net_id, "type": "Expression", "name": "NetSoilInflow",
        "description": "Net water entering the soil store = Rainfall - Runoff - ET. "
                       "Can be negative on dry days (ET draws down soil moisture).",
        "position": [620, 340],
        "parameters": {
            "formula": "Daily_Rainfall - RunoffRate - ActualET",
            "output_units": "mm/day"
        }
    },

    # ── Stock elements (blue) ─────────────────────────────────────────────
    {
        "id": soil_id, "type": "WaterStore", "name": "SoilMoisture",
        "description": "Root-zone soil moisture store. Field capacity = 200 mm "
                       "(upper bound). Wilting point = 0 mm (lower bound). "
                       "Starts at 110 mm (55% full — typical winter condition).",
        "position": [880, 280],
        "parameters": {
            "initial_storage": 110.0, "lower_bound": 0.0,
            "upper_bound": 200.0, "units": "mm"
        }
    },
    {
        "id": gw_id, "type": "WaterStore", "name": "ShallowGroundwater",
        "description": "Shallow aquifer recharged by soil overflow. "
                       "Drained by constant baseflow of 1.2 mm/day to streams. "
                       "Capacity = 400 mm; starts at 45 mm.",
        "position": [880, 480],
        "parameters": {
            "initial_storage": 45.0, "lower_bound": 0.0,
            "upper_bound": 400.0, "units": "mm"
        }
    },

    # ── Result elements (orange) ──────────────────────────────────────────
    {
        "id": plot1_id, "type": "TimeHistoryResult", "name": "SoilMoisture_Plot",
        "description": "Root-zone soil moisture storage and overflow to groundwater. "
                       "Blue = storage (mm), orange = overflow rate (mm/day).",
        "position": [1140, 200],
        "parameters": {
            "title": "Root-Zone Soil Moisture — Hawkesbury 2020",
            "y_axis_label": "Storage / Overflow",
            "y_axis_units": "mm / mm·d⁻¹",
            "show_grid": True,
            "y_min": 0.0, "y_max": 210.0
        }
    },
    {
        "id": plot2_id, "type": "TimeHistoryResult", "name": "Groundwater_Plot",
        "description": "Shallow groundwater storage (recharge minus baseflow) "
                       "and daily rainfall input. GW should pulse after wet events.",
        "position": [1140, 460],
        "parameters": {
            "title": "Shallow Groundwater & Daily Rainfall — Hawkesbury 2020",
            "y_axis_label": "GW Storage (mm) / Rainfall (mm/day)",
            "y_axis_units": "-",
            "show_grid": True,
            "y_min": None, "y_max": None
        }
    },
]

now = datetime.now(timezone.utc).isoformat()
model = {
    "hydrosim_version":    "1.0",
    "file_format_version": "1",
    "metadata": {
        "name":        "Hawkesbury Catchment Water Balance (2020)",
        "description": (
            "Daily dual-store water balance for a humid temperate Australian catchment. "
            "Features: seasonal rainfall, ET, direct runoff, soil moisture dynamics, "
            "and shallow groundwater with base-flow drainage. "
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
    "canvas_state": {"zoom": 0.65, "pan_x": -40.0, "pan_y": 0.0},
}

out_path = Path("Hawkesbury_Water_Balance_2020.hydrosim")
out_path.write_text(json.dumps(model, indent=2), encoding="utf-8")
print(f"Saved: {out_path}  ({out_path.stat().st_size // 1024} KB)")

# Quick self-test
from hydrosim.model.serialiser import ModelSerialiser
from hydrosim.model.validator  import ModelValidator
from hydrosim.engine.runner    import SimulationRunner
g, s, m = ModelSerialiser.load(out_path)
assert not ModelValidator(g).validate_all(), "Validation errors!"
r = SimulationRunner(g, s).run()
assert r.is_complete
soil = r.get_series_by_name("SoilMoisture",       "storage")
gw   = r.get_series_by_name("ShallowGroundwater", "storage")
over = r.get_series_by_name("SoilMoisture",       "overflow")
rain_total = sum(row[1] for row in model["elements"][0]["parameters"]["data"])

print()
print(f"  Annual rainfall  : {rain_total:.0f} mm")
print(f"  Soil moisture    : {soil.min():.0f}..{soil.max():.0f} mm  (cap 200)")
print(f"  Overflow to GW   : {over.sum():.0f} mm/year")
print(f"  Groundwater      : {gw.min():.0f}..{gw.max():.0f} mm  (cap 400)")
print(f"  Run time         : {r.run_duration_s*1000:.0f} ms")
print()
print("Model structure:")
for el in elements:
    print(f"  [{el['type'][:2]}] {el['name']}")
print(f"\n  {len(connections)} connections")
print()
print("Ready! Open in HydroSim:")
print("  File > Open > Hawkesbury_Water_Balance_2020.hydrosim")
print("  Press F5 (or Run button)")
print("  Double-click SoilMoisture_Plot or Groundwater_Plot to see charts")
