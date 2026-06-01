# HydroSim — Product Requirements Document
## Phase 1 MVP

**Version:** 1.0  
**Status:** Draft for Development  
**Prepared for:** Claude Code (AI-assisted development)  
**Date:** May 2026  

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Goals & Non-Goals](#2-goals--non-goals)
3. [Users & Use Cases](#3-users--use-cases)
4. [System Architecture](#4-system-architecture)
5. [Technology Stack](#5-technology-stack)
6. [Project Structure](#6-project-structure)
7. [Element Specifications](#7-element-specifications)
8. [Simulation Engine](#8-simulation-engine)
9. [Model File Format](#9-model-file-format)
10. [Visual Canvas](#10-visual-canvas)
11. [Element Palette](#11-element-palette)
12. [Property Dialogs](#12-property-dialogs)
13. [Results Viewer](#13-results-viewer)
14. [Main Window & Menus](#14-main-window--menus)
15. [Visual Design System](#15-visual-design-system)
16. [Error Handling](#16-error-handling)
17. [Testing Requirements](#17-testing-requirements)
18. [MVP Acceptance Criteria](#18-mvp-acceptance-criteria)
19. [Out of Scope for Phase 1](#19-out-of-scope-for-phase-1)
20. [Appendix A — Example Model](#20-appendix-a--example-model)
21. [Appendix B — Glossary](#21-appendix-b--glossary)

---

## 1. Project Overview

### 1.1 What is HydroSim?

HydroSim is an open-source, probabilistic dynamic simulation platform for water resources and hydrology applications. It is inspired by GoldSim (a commercial general-purpose Monte Carlo simulation tool) but purpose-built for hydrologists, with domain-specific elements, hydrological equations, and hydrology-first result visualisations.

Users build models visually on a drag-and-drop canvas by placing and connecting **elements** — self-contained computational nodes representing inputs, storages, calculations, and results. The simulation engine executes these connected elements forward through time, producing time series of outputs at every timestep.

### 1.2 Phase 1 Scope

Phase 1 delivers a working MVP with:
- A functional **PyQt6 desktop application** with drag-and-drop canvas
- **5 core element types** fully implemented (Constant, TimeSeries, WaterStore, Expression, TimeHistoryResult)
- A **simulation engine** that executes models and produces results
- **Save/load** of model files in JSON format
- A simple but polished **visual design** following the HydroSim design system

Phase 1 is complete when a user can build a simple rainfall-storage model, run it, and view a hydrograph result — entirely within the GUI.

### 1.3 Design Philosophy

- **Domain-first:** Every design decision prioritises the hydrologist's mental model, not generic software conventions
- **Transparency:** Models should be self-documenting — element names, units, and connections should be readable at a glance
- **Correctness over features:** A small set of elements that work perfectly is better than many that are unreliable
- **AI-assisted development:** Code should be clean, well-commented, and modular so Claude Code can extend it incrementally

---

## 2. Goals & Non-Goals

### 2.1 Goals (Phase 1)

- [ ] Build a working PyQt6 desktop application that launches, saves, and loads models
- [ ] Implement 5 fully functional element types
- [ ] Implement a time-stepping simulation engine with correct numerical integration
- [ ] Build a drag-and-drop canvas with bezier connection arrows
- [ ] Implement a TimeHistoryResult viewer showing simulated hydrographs
- [ ] Validate mass conservation in WaterStore elements
- [ ] Support model save/load via JSON files
- [ ] Provide clear error messages for invalid models

### 2.2 Non-Goals (Phase 1)

- Monte Carlo / probabilistic simulation (Phase 2)
- StochasticConstant, LookupTable, StochasticTimeSeries elements (Phase 2)
- MuskingumDelay, TravelTimeDelay routing elements (Phase 2)
- Event elements (ScheduledEvent, ThresholdEvent etc.) (Phase 2)
- FlowDurationResult, FloodFrequencyResult, WaterBalanceResult (Phase 2)
- GIS integration or spatial data (Phase 3)
- Python Script element (Phase 2)
- Undo/redo (Phase 2)
- Mini-map (Phase 2)
- Auto-layout (Phase 2)
- Export to Excel/NetCDF (Phase 2)

---

## 3. Users & Use Cases

### 3.1 Primary User

**Hydrologist with light coding skills.** They understand rainfall-runoff processes, can read Python but do not write it fluently. They are comfortable with Excel and have used simulation tools before (HEC-HMS, SWMM, or GoldSim). They want a tool that lets them build and run water balance models without writing code.

### 3.2 Phase 1 Use Cases

**UC-01: Build a simple water balance model**
A user places a TimeSeries element (daily rainfall), connects it to a WaterStore element (soil moisture store), adds a Constant for initial storage, and views the storage time series in a TimeHistoryResult. They run the simulation and see storage varying over time.

**UC-02: Compute a derived quantity**
A user adds an Expression element to compute runoff as a fraction of rainfall (`runoff = rainfall * 0.3`). They connect the Expression output to a WaterStore inflow and view the resulting hydrograph.

**UC-03: Save and reload a model**
A user saves their model to a `.hydrosim` JSON file, closes the application, reopens it, loads the file, and sees their model exactly as they left it — elements in the same positions with the same parameters.

**UC-04: Identify a model error**
A user connects a TimeSeries output to a WaterStore inflow but forgets to specify the WaterStore's lower bound. The application shows a validation warning before running and explains what is missing.

---

## 4. System Architecture

HydroSim is structured as three loosely coupled layers:

```
┌─────────────────────────────────────────────────────┐
│                  GUI Layer (PyQt6)                   │
│  MainWindow / Canvas / Palette / Dialogs / Results  │
└───────────────────┬─────────────────────────────────┘
                    │  reads/writes
┌───────────────────▼─────────────────────────────────┐
│               Model Layer (Pure Python)              │
│   ModelGraph / ElementBase / ConnectionGraph /       │
│   ModelValidator / ModelSerializer (JSON)            │
└───────────────────┬─────────────────────────────────┘
                    │  executes
┌───────────────────▼─────────────────────────────────┐
│            Simulation Engine (Pure Python)           │
│   SimulationRunner / TimeStepSolver /                │
│   ResultsStore / WaterBalanceChecker                 │
└─────────────────────────────────────────────────────┘
```

**Key principle:** The Model Layer and Simulation Engine must have **zero dependency on PyQt6**. They are pure Python modules that can be tested independently, run from the command line, or called from scripts. The GUI layer depends on the Model Layer; the Model Layer does not depend on the GUI.

---

## 5. Technology Stack

| Component | Technology | Version | Notes |
|---|---|---|---|
| Language | Python | 3.11+ | Type hints throughout |
| GUI framework | PyQt6 | 6.6+ | QGraphicsScene for canvas |
| Plotting | Matplotlib | 3.8+ | Embedded in PyQt6 via FigureCanvasQTAgg |
| Numerical | NumPy | 1.26+ | Array operations in engine |
| Data | Pandas | 2.1+ | TimeSeries data handling |
| File format | JSON | stdlib | Model save/load |
| Packaging | Poetry | 1.7+ | Dependency management |
| Testing | pytest | 7.4+ | Unit + integration tests |
| Code style | Black + Ruff | latest | Auto-formatting |

### 5.1 Installation

The application must be installable via:
```bash
pip install hydrosim
```
And launchable via:
```bash
hydrosim
```
Or directly:
```bash
python -m hydrosim
```

---

## 6. Project Structure

```
hydrosim/
├── pyproject.toml              # Poetry config, dependencies, entry points
├── README.md
├── LICENSE                     # MIT
│
├── hydrosim/                   # Main package
│   ├── __init__.py
│   ├── __main__.py             # Entry point: python -m hydrosim
│   ├── app.py                  # QApplication setup, MainWindow launch
│   │
│   ├── model/                  # Model Layer (no PyQt6 imports)
│   │   ├── __init__.py
│   │   ├── base.py             # ElementBase abstract class
│   │   ├── graph.py            # ModelGraph: elements + connections
│   │   ├── connection.py       # Connection dataclass
│   │   ├── validator.py        # ModelValidator
│   │   ├── serializer.py       # JSON save/load
│   │   └── elements/
│   │       ├── __init__.py
│   │       ├── constant.py     # Constant element
│   │       ├── timeseries.py   # TimeSeries element
│   │       ├── waterstore.py   # WaterStore element
│   │       ├── expression.py   # Expression element
│   │       └── timehistory.py  # TimeHistoryResult element
│   │
│   ├── engine/                 # Simulation Engine (no PyQt6 imports)
│   │   ├── __init__.py
│   │   ├── runner.py           # SimulationRunner: orchestrates execution
│   │   ├── solver.py           # TimeStepSolver: per-timestep computation
│   │   ├── results.py          # ResultsStore: stores output arrays
│   │   └── parser.py           # Expression parser / evaluator
│   │
│   ├── gui/                    # GUI Layer (PyQt6)
│   │   ├── __init__.py
│   │   ├── main_window.py      # MainWindow (QMainWindow)
│   │   ├── canvas/
│   │   │   ├── __init__.py
│   │   │   ├── scene.py        # HydroScene (QGraphicsScene)
│   │   │   ├── view.py         # HydroView (QGraphicsView)
│   │   │   ├── element_item.py # ElementItem (QGraphicsItem)
│   │   │   ├── port_item.py    # PortItem (QGraphicsEllipseItem)
│   │   │   └── connection_item.py # ConnectionItem (QGraphicsPathItem)
│   │   ├── palette/
│   │   │   ├── __init__.py
│   │   │   └── palette_panel.py  # Left sidebar element palette
│   │   ├── dialogs/
│   │   │   ├── __init__.py
│   │   │   ├── constant_dialog.py
│   │   │   ├── timeseries_dialog.py
│   │   │   ├── waterstore_dialog.py
│   │   │   ├── expression_dialog.py
│   │   │   └── timehistory_dialog.py
│   │   ├── results/
│   │   │   ├── __init__.py
│   │   │   └── hydrograph_widget.py  # Matplotlib hydrograph viewer
│   │   └── styles/
│   │       ├── __init__.py
│   │       ├── theme.py        # Colours, fonts, dimensions constants
│   │       └── stylesheet.qss  # Qt stylesheet
│   │
│   └── resources/
│       ├── icons/              # SVG element icons (24x24)
│       │   ├── constant.svg
│       │   ├── timeseries.svg
│       │   ├── waterstore.svg
│       │   ├── expression.svg
│       │   └── timehistory.svg
│       └── examples/
│           └── simple_water_balance.hydrosim  # Example model file
│
└── tests/
    ├── __init__.py
    ├── test_elements/
    │   ├── test_constant.py
    │   ├── test_timeseries.py
    │   ├── test_waterstore.py
    │   ├── test_expression.py
    │   └── test_timehistory.py
    ├── test_engine/
    │   ├── test_runner.py
    │   ├── test_solver.py
    │   └── test_parser.py
    └── test_model/
        ├── test_graph.py
        ├── test_validator.py
        └── test_serializer.py
```

---

## 7. Element Specifications

All elements inherit from `ElementBase`. This section defines the full specification for each Phase 1 element.

### 7.1 ElementBase (Abstract)

**File:** `hydrosim/model/base.py`

**Attributes (all elements):**

| Attribute | Type | Description |
|---|---|---|
| `id` | `str` | Unique identifier, auto-generated UUID on creation |
| `name` | `str` | User-defined display name (e.g., `"Rainfall_Bankstown"`) |
| `description` | `str` | Optional documentation string |
| `category` | `ElementCategory` | Enum: INPUT, STOCK, EXPRESSION, RESULT |
| `position` | `tuple[float, float]` | Canvas position (x, y) in scene coordinates |
| `input_ports` | `list[Port]` | Named input ports |
| `output_ports` | `list[Port]` | Named output ports |

**Port dataclass:**

```python
@dataclass
class Port:
    name: str          # e.g. "inflow", "outflow", "value"
    units: str         # e.g. "m3/s", "mm/day", "-" (dimensionless)
    description: str   # tooltip text
    required: bool     # True = must be connected before running
    port_type: PortType  # Enum: INPUT or OUTPUT
```

**Abstract methods all elements must implement:**

```python
def validate(self) -> list[ValidationError]:
    """Return list of errors. Empty list = valid."""

def get_output_value(self, port_name: str, t: float, state: SimState) -> float:
    """Return the value of a named output port at time t."""

def to_dict(self) -> dict:
    """Serialise element to JSON-compatible dict."""

@classmethod
def from_dict(cls, data: dict) -> "ElementBase":
    """Deserialise element from dict."""
```

---

### 7.2 Constant Element

**File:** `hydrosim/model/elements/constant.py`  
**Category:** INPUT  
**Colour:** `#4CAF82` (Leaf Green)  
**Icon:** `constant.svg` — letter C in a circle

**Description:** Represents a single fixed scalar value that does not change during the simulation. Used for parameters such as Manning's roughness coefficient, catchment area, or initial storage.

**Parameters:**

| Parameter | Type | Default | Constraints |
|---|---|---|---|
| `value` | `float` | `0.0` | Any finite number |
| `units` | `str` | `"-"` | Free text, e.g. `"m3"`, `"mm/day"`, `"m2"` |

**Ports:**

| Port | Direction | Name | Units |
|---|---|---|---|
| Output | OUT | `value` | As specified by user |

**Behaviour:**
- `get_output_value("value", t, state)` always returns `self.value` regardless of `t`
- Has no input ports — it is a source element
- Validation: value must be a finite float (not NaN or Inf)

**Example use:** Defining Manning's n = 0.035, catchment area = 45.2 km², initial soil moisture = 80 mm

---

### 7.3 TimeSeries Element

**File:** `hydrosim/model/elements/timeseries.py`  
**Category:** INPUT  
**Colour:** `#4CAF82` (Leaf Green)  
**Icon:** `timeseries.svg` — zigzag line on axes

**Description:** Provides a time-varying input to the model from a table of time/value pairs. The most commonly used input for observed or design rainfall, evapotranspiration, or observed streamflow.

**Parameters:**

| Parameter | Type | Default | Constraints |
|---|---|---|---|
| `units` | `str` | `"-"` | Free text |
| `data_type` | `TimeSeriesType` | `PERIOD_TOTAL` | Enum (see below) |
| `interpolation` | `InterpolationType` | `LINEAR` | Enum: LINEAR, STEP |
| `data` | `list[tuple[float, float]]` | `[]` | List of (time_days, value) pairs, sorted by time |

**TimeSeriesType Enum:**

| Value | Description | Hydrology use |
|---|---|---|
| `INSTANTANEOUS` | Value at the exact recorded time | Stage gauge readings, temperature |
| `PERIOD_TOTAL` | Total accumulated over the interval ending at this time | Daily rainfall depth (mm) |
| `PERIOD_AVERAGE` | Mean rate over the interval ending at this time | Mean daily flow (m³/s) |

**Ports:**

| Port | Direction | Name | Units |
|---|---|---|---|
| Output | OUT | `value` | As specified by user |

**Behaviour:**
- At time `t`, returns the interpolated value from the data table using the specified interpolation method
- For STEP interpolation: returns the value of the most recent data point at or before `t`
- For LINEAR interpolation: linearly interpolates between adjacent data points
- Before the first data point: returns the first value (flat extrapolation)
- After the last data point: returns the last value (flat extrapolation)
- Returns 0.0 if data table is empty

**Validation:**
- Data table must have at least 1 row
- Time values must be strictly monotonically increasing
- No NaN or Inf values

**Data entry in GUI:**
- Table widget with two columns: Time (days from simulation start, or calendar date) and Value
- Import from CSV button: two-column CSV (time, value)
- Time can be entered as elapsed days (float) or as calendar dates (auto-converted to elapsed days)

---

### 7.4 WaterStore Element

**File:** `hydrosim/model/elements/waterstore.py`  
**Category:** STOCK  
**Colour:** `#2E86C1` (Ocean Blue)  
**Icon:** `waterstore.svg` — cylinder/tank outline

**Description:** A bounded water storage volume that accumulates inflows and loses outflows over time. The core stock element for Phase 1. Represents any bounded water storage: a soil moisture zone, a detention pond, a simple reservoir, or a river reach storage.

This is a **state variable** — its value at each timestep depends on its value at the previous timestep. The simulation engine integrates the net flux (inflows minus outflows) using a forward Euler scheme.

**Parameters:**

| Parameter | Type | Default | Constraints |
|---|---|---|---|
| `initial_storage` | `float` | `0.0` | Must be within [lower_bound, upper_bound] |
| `lower_bound` | `float` | `0.0` | Must be < upper_bound; typically 0 |
| `upper_bound` | `float \| None` | `None` | If None, no upper bound (infinite capacity) |
| `units` | `str` | `"m3"` | Volume units, e.g. `"m3"`, `"mm"`, `"ML"` |

**Ports:**

| Port | Direction | Name | Units | Required |
|---|---|---|---|---|
| Input | IN | `inflow` | volume/time | No (defaults to 0) |
| Input | IN | `outflow` | volume/time | No (defaults to 0) |
| Output | OUT | `storage` | volume | — |
| Output | OUT | `overflow` | volume/time | — |
| Output | OUT | `deficit` | volume/time | — |

**Governing equation (forward Euler integration):**

```
storage[t+dt] = storage[t] + (inflow[t] - outflow[t]) * dt

if storage[t+dt] > upper_bound:
    overflow[t] = (storage[t+dt] - upper_bound) / dt
    storage[t+dt] = upper_bound
else:
    overflow[t] = 0.0

if storage[t+dt] < lower_bound:
    deficit[t] = (lower_bound - storage[t+dt]) / dt
    storage[t+dt] = lower_bound
else:
    deficit[t] = 0.0
```

**Output descriptions:**

| Output | Description |
|---|---|
| `storage` | Current volume in the store (in specified units) |
| `overflow` | Rate at which water spills when upper bound is exceeded (volume/time) |
| `deficit` | Rate of unmet outflow demand when lower bound would be violated (volume/time) |

**Validation:**
- `initial_storage` must be within [lower_bound, upper_bound]
- `lower_bound` must be a finite number
- If `upper_bound` is specified, it must be > `lower_bound`
- Units must be non-empty string
- Inflow and outflow ports must carry compatible units (volume/time)

**Water balance tracking:**
At every timestep, the engine records:
```
balance_error[t] = storage[t] - storage[t-1] - (inflow[t] - outflow[t] - overflow[t] + deficit[t]) * dt
```
If cumulative balance error exceeds 1e-6 of total inflow, a warning is written to the simulation log.

---

### 7.5 Expression Element

**File:** `hydrosim/model/elements/expression.py`  
**Category:** EXPRESSION  
**Colour:** `#00897B` (Teal)  
**Icon:** `expression.svg` — f(x) text

**Description:** Computes a single scalar output from a user-defined mathematical formula. References other element outputs by name. The formula is evaluated at every timestep during simulation. Equivalent to a formula cell in a spreadsheet.

**Parameters:**

| Parameter | Type | Default | Constraints |
|---|---|---|---|
| `formula` | `str` | `""` | Valid mathematical expression string |
| `output_units` | `str` | `"-"` | Units of the computed output |

**Ports:**
- Input ports are **dynamic** — automatically created based on element names referenced in the formula
- One fixed output port: `value` (units as specified by `output_units`)

**Formula syntax:**

Operators:
```
+   -   *   /   **  (power)
(   )   (grouping)
>   <   >=  <=  ==  !=  (comparison, returns 0.0 or 1.0)
```

Built-in functions:
```
abs(x)       sqrt(x)      exp(x)       log(x)       log10(x)
sin(x)       cos(x)       tan(x)       
min(a, b)    max(a, b)    
round(x)     floor(x)     ceil(x)      
if(cond, val_true, val_false)
```

Special variables (automatically available in all expressions):
```
t          — current simulation time in days (float)
dt         — current timestep in days (float)
```

Referencing other elements:
- Single-output elements: reference by element name, e.g. `Rainfall_mm`
- Multi-output elements: use dot notation, e.g. `SoilMoisture.storage`, `SoilMoisture.overflow`
- Element names are case-insensitive in expressions but displayed in their defined case

**Example formulas:**
```
# Runoff as fraction of rainfall
Rainfall_mm * RunoffCoeff

# Manning's equation (Q in m3/s)
(1.0 / Manning_n) * CrossSection_A * HydRadius ** (2.0/3.0) * sqrt(ChannelSlope)

# Conditional: ET only when temperature > 0
if(Temperature > 0, Kc * ET_reference, 0.0)

# Net flux for WaterStore
Inflow_rate - Outflow_rate - Evaporation_rate
```

**Expression evaluation:**
- Implemented using Python's `ast` module (Abstract Syntax Tree parser)
- Safe evaluation — no `eval()` calls; only whitelisted operations are permitted
- Element output values are injected into the evaluation namespace at each timestep
- If formula references an element name that does not exist in the model, validation fails with a clear error

**Validation:**
- Formula must be non-empty
- Formula must parse without syntax errors
- All referenced element names must exist in the model graph
- All referenced port names (after dot) must exist on the referenced element
- Formula must not contain circular references (checked by validator)

**GUI Expression Editor:**
- Multi-line text field with monospace font (Fira Code or Consolas)
- Syntax highlighting: numbers (grey), element references (green), functions (blue), operators (black), errors (red underline)
- Autocomplete dropdown: shows available element names and port names as user types
- Live validation: shows error message below field if formula is invalid
- "Test" button: evaluates formula at t=0 with current input values and shows result

---

### 7.6 TimeHistoryResult Element

**File:** `hydrosim/model/elements/timehistory.py`  
**Category:** RESULT  
**Colour:** `#E8633A` (Coral Orange)  
**Icon:** `timehistory.svg` — hydrograph line chart

**Description:** Collects and displays the time history of one or more connected element outputs as a line chart (hydrograph). This is the primary way users view simulation results in Phase 1.

**Parameters:**

| Parameter | Type | Default | Constraints |
|---|---|---|---|
| `title` | `str` | `"Time History"` | Chart title |
| `y_axis_label` | `str` | `""` | Y-axis label |
| `y_axis_units` | `str` | `"-"` | Units displayed on Y-axis |
| `show_grid` | `bool` | `True` | Show gridlines |
| `y_min` | `float \| None` | `None` | Manual Y-axis minimum (None = auto) |
| `y_max` | `float \| None` | `None` | Manual Y-axis maximum (None = auto) |

**Ports:**

| Port | Direction | Name | Required |
|---|---|---|---|
| Input (dynamic, up to 8) | IN | `series_1` ... `series_8` | At least 1 required |

Each input port collects the full time history of the connected output.

**Behaviour:**
- During simulation, at each timestep, records the current value of each connected input port
- After simulation, displays all collected series as a multi-line chart
- Each series displayed in a different colour (auto-assigned from a 8-colour palette)
- Legend shows element name + port name for each series
- Double-clicking the element on the canvas opens the result viewer window

**Result viewer features:**
- Matplotlib figure embedded in a Qt widget
- X-axis: simulation time (days, or calendar dates if simulation uses calendar time)
- Y-axis: values in specified units
- Hover tooltip: shows time and value at cursor position
- Toolbar: zoom, pan, save figure as PNG
- Export button: saves data as CSV (time column + one column per series)

---

## 8. Simulation Engine

**Files:** `hydrosim/engine/`

### 8.1 Simulation Settings

Before running, the user specifies simulation settings via a dialog:

| Setting | Type | Default | Description |
|---|---|---|---|
| `start_time` | `float` | `0.0` | Start time in days |
| `end_time` | `float` | `365.0` | End time in days |
| `timestep` | `float` | `1.0` | Timestep in days (e.g. 1.0 = daily, 0.0417 ≈ hourly) |
| `time_mode` | `TimeMode` | `ELAPSED` | Enum: ELAPSED (days from 0) or CALENDAR |
| `start_date` | `date \| None` | `None` | Calendar start date (if CALENDAR mode) |

### 8.2 Execution Order

The simulation engine resolves the correct order to evaluate elements at each timestep using **topological sorting** of the model graph.

**Algorithm:**
1. Build directed acyclic graph (DAG) of element dependencies from connections
2. Apply Kahn's algorithm to produce a topologically sorted execution order
3. Stock elements (WaterStore) are treated as state variables — their output at timestep `t` is their stored value from timestep `t-1`, so they do not create dependency cycles
4. If a circular dependency exists among non-stock elements, raise `CircularDependencyError`

**Execution order example:**
```
Constant (area) ──►
                    Expression (runoff_rate) ──► WaterStore ──► TimeHistoryResult
TimeSeries (rain) ──►
```
Sorted order: `[Constant, TimeSeries, Expression, WaterStore, TimeHistoryResult]`

### 8.3 Per-Timestep Execution Loop

```python
for t in timesteps:
    for element in sorted_elements:
        element.compute(t, dt, state)
    results_store.record(t, state)
```

Each element's `compute(t, dt, state)` method:
1. Reads its input port values from `state` (values computed by upstream elements this timestep)
2. Computes its output values
3. Writes its output values to `state`
4. For WaterStore: updates its internal storage value using forward Euler integration

### 8.4 SimState Object

```python
@dataclass
class SimState:
    t: float                                    # Current time (days)
    dt: float                                   # Current timestep (days)
    values: dict[str, dict[str, float]]         # values[element_id][port_name] = value
    storage: dict[str, float]                   # storage[element_id] = current stock value
```

### 8.5 ResultsStore

Stores the complete time history of all saved outputs:

```python
@dataclass
class ResultsStore:
    timesteps: np.ndarray                       # Shape: (n_timesteps,)
    values: dict[str, dict[str, np.ndarray]]    # values[element_id][port_name] = array shape (n_timesteps,)
```

Only outputs that are connected to a `TimeHistoryResult` element are stored (to minimise memory).

### 8.6 Expression Parser

**File:** `hydrosim/engine/parser.py`

The expression parser safely evaluates formula strings at runtime.

**Implementation approach:**
- Parse formula string using Python's `ast.parse()`
- Walk the AST and reject any node types not in the whitelist
- Whitelisted node types: `Expression`, `BinOp`, `UnaryOp`, `Call`, `Num`, `Name`, `Constant`, `IfExp`, `Compare`, `BoolOp`
- Forbidden: `Import`, `Exec`, `Attribute` (except whitelisted dot-notation for port access), `Subscript`, `Lambda`, `ListComp`, `GeneratorExp`
- Inject values namespace: `{"element_name": value, "element_name.port": value, "t": t, "dt": dt, **math_functions}`
- Evaluate using `eval()` on the validated AST (safe because AST is fully controlled)

**Math functions namespace:**
```python
MATH_FUNCTIONS = {
    "abs": abs, "sqrt": math.sqrt, "exp": math.exp,
    "log": math.log, "log10": math.log10,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "min": min, "max": max,
    "round": round, "floor": math.floor, "ceil": math.ceil,
    "if": lambda cond, a, b: a if cond else b,
}
```

### 8.7 Simulation Runner

**File:** `hydrosim/engine/runner.py`

```
SimulationRunner
├── validate_model(graph) → list[ValidationError]
├── build_execution_order(graph) → list[ElementBase]
├── run(graph, settings) → ResultsStore
│   ├── initialise state
│   ├── for each timestep:
│   │   ├── evaluate each element in order
│   │   └── record results
│   └── return ResultsStore
└── run_async(graph, settings, progress_callback) → Future[ResultsStore]
```

`run_async` runs the simulation in a background thread (QThread) and emits progress signals to update a progress bar in the GUI without freezing the UI.

### 8.8 Progress and Logging

During simulation:
- A progress bar in the status bar shows `t / end_time` percentage
- A simulation log (plain text, shown in a dockable panel) records:
  - Simulation start time
  - Settings summary
  - Any warnings (e.g. water balance errors > threshold)
  - Completion time and total timesteps computed

---

## 9. Model File Format

**Extension:** `.hydrosim`  
**Format:** JSON (UTF-8 encoded)  
**Version field:** included for future backwards compatibility

### 9.1 Top-level Structure

```json
{
  "hydrosim_version": "1.0",
  "file_format_version": "1",
  "metadata": {
    "name": "Simple Water Balance",
    "description": "Basic rainfall-storage model",
    "author": "",
    "created": "2026-05-28T10:00:00",
    "modified": "2026-05-28T10:00:00"
  },
  "simulation_settings": {
    "start_time": 0.0,
    "end_time": 365.0,
    "timestep": 1.0,
    "time_mode": "ELAPSED",
    "start_date": null
  },
  "elements": [ ... ],
  "connections": [ ... ]
}
```

### 9.2 Element Serialisation

Each element in the `elements` array:

```json
{
  "id": "a1b2c3d4-...",
  "type": "Constant",
  "name": "Manning_n",
  "description": "Manning roughness for main channel",
  "position": [120.0, 240.0],
  "parameters": {
    "value": 0.035,
    "units": "-"
  }
}
```

```json
{
  "id": "e5f6g7h8-...",
  "type": "TimeSeries",
  "name": "Daily_Rainfall",
  "description": "Observed daily rainfall at Bankstown gauge",
  "position": [120.0, 380.0],
  "parameters": {
    "units": "mm/day",
    "data_type": "PERIOD_TOTAL",
    "interpolation": "STEP",
    "data": [
      [0.0, 0.0],
      [1.0, 12.3],
      [2.0, 0.0],
      [3.0, 45.2]
    ]
  }
}
```

```json
{
  "id": "i9j0k1l2-...",
  "type": "WaterStore",
  "name": "SoilMoisture",
  "description": "Root zone soil moisture storage",
  "position": [400.0, 310.0],
  "parameters": {
    "initial_storage": 80.0,
    "lower_bound": 0.0,
    "upper_bound": 150.0,
    "units": "mm"
  }
}
```

```json
{
  "id": "m3n4o5p6-...",
  "type": "Expression",
  "name": "RunoffRate",
  "description": "Simple proportional runoff",
  "position": [280.0, 380.0],
  "parameters": {
    "formula": "Daily_Rainfall * 0.3",
    "output_units": "mm/day"
  }
}
```

```json
{
  "id": "q7r8s9t0-...",
  "type": "TimeHistoryResult",
  "name": "Storage_Plot",
  "description": "",
  "position": [600.0, 310.0],
  "parameters": {
    "title": "Soil Moisture Storage",
    "y_axis_label": "Storage",
    "y_axis_units": "mm",
    "show_grid": true,
    "y_min": null,
    "y_max": null
  }
}
```

### 9.3 Connection Serialisation

Each connection in the `connections` array:

```json
{
  "id": "conn-u1v2w3x4-...",
  "from_element_id": "e5f6g7h8-...",
  "from_port": "value",
  "to_element_id": "m3n4o5p6-...",
  "to_port": "series_1"
}
```

### 9.4 Canvas Layout

Canvas view state is stored in a separate optional section (not required for simulation):

```json
{
  "canvas_state": {
    "zoom": 1.0,
    "pan_x": 0.0,
    "pan_y": 0.0
  }
}
```

---

## 10. Visual Canvas

**Files:** `hydrosim/gui/canvas/`

### 10.1 HydroView (QGraphicsView)

The main canvas viewport. Wraps `HydroScene`.

**Interactions:**

| Action | Input |
|---|---|
| Pan canvas | Middle mouse button drag OR Space + left mouse drag |
| Zoom in/out | Mouse scroll wheel |
| Zoom to fit | Ctrl+Shift+F |
| Select element | Left click on element |
| Select multiple | Left click drag (rubber-band selection) |
| Deselect all | Click on empty canvas |
| Move element(s) | Drag selected element(s) |
| Open properties | Double-click on element |
| Delete selected | Delete key |
| Start connection | Drag from output port dot |
| Cancel connection | Escape key during drag |

**Zoom limits:** 10% minimum, 400% maximum

**Zoom behaviour:** Zooms toward cursor position (not canvas centre)

### 10.2 HydroScene (QGraphicsScene)

Manages all canvas items.

**Responsibilities:**
- Owns all `ElementItem` and `ConnectionItem` instances
- Handles drop events from palette (creates new elements at drop position)
- Emits signals when model changes: `element_added`, `element_removed`, `connection_added`, `connection_removed`, `element_moved`
- Keeps `ModelGraph` in sync with visual state — every canvas change updates the model immediately

**Background:** Light grey grid (`#F5F6FA`) with subtle dot grid pattern (every 20px, dot colour `#DEE2E8`)

### 10.3 ElementItem (QGraphicsItem)

Represents one element as a rounded rectangle card on the canvas.

**Visual structure:**

```
┌─────────────────────────────────────┐
│ ████████ (4px category colour bar)  │
├─────────────────────────────────────┤
│  [icon 20px]  Element Name (bold)   │
│               element_id (small)    │
├─────────────────────────────────────┤
│ ●─── inflow                         │  ← input ports (left)
│ ●─── outflow                        │
│                       value  ───●   │  ← output ports (right)
│                     storage  ───●   │
│                    overflow  ───●   │
└─────────────────────────────────────┘
```

**Dimensions:**
- Width: 180px (fixed)
- Height: auto (minimum 80px, grows 20px per additional port beyond 2)
- Corner radius: 10px
- Category colour bar height: 4px

**Visual states:**

| State | Appearance |
|---|---|
| Default | White fill, category colour border (1.5px), light drop shadow |
| Selected | White fill, `#2E86C1` blue border (2.5px), stronger shadow |
| Hover | Slight shadow increase |
| Has results | Small filled green circle (8px) in top-right corner |
| Error | `#E53935` red border (2px), warning triangle icon in top-right |

**Typography:**
- Element name: 12px, weight 600, colour `#1A1A2E`
- Element ID: 10px, weight 400, colour `#6B7280`, monospace font
- Port labels: 10px, weight 400, colour `#374151`

### 10.4 PortItem (QGraphicsEllipseItem)

Small circular connector dots on element card edges.

**Dimensions:** 10px diameter

**Visual states:**

| State | Appearance |
|---|---|
| Input port, unconnected | Hollow circle, category colour border (1.5px), white fill |
| Input port, connected | Filled circle, category colour |
| Output port, unconnected | Filled circle, category colour, 70% opacity |
| Output port, connected | Filled circle, category colour, 100% opacity |
| Hover | Circle scales to 14px, tooltip appears |
| Drag target (compatible) | Green glow ring |
| Drag target (incompatible) | Red glow ring |

**Tooltip on hover:** Shows `"port_name (units) — description"`

### 10.5 ConnectionItem (QGraphicsPathItem)

Bezier curve connecting an output port to an input port.

**Path:** Cubic bezier curve. Control points:
- P0: output port centre
- P1: P0 + (80px, 0) — horizontal right departure
- P2: P3 + (-80px, 0) — horizontal left arrival
- P3: input port centre

**Visual:**
- Stroke: 2px, source element's category colour, 80% opacity
- Arrowhead: 8px filled triangle at P3 (destination end)
- Selected: stroke 3px, `#2E86C1` blue
- Hover: stroke 2.5px, full opacity

**Connection validation:**
- A connection is only allowed if the target port is not already connected (input ports accept one connection only)
- Output ports can have multiple connections
- Visual feedback during drag: green port glow if compatible, red if not

---

## 11. Element Palette

**File:** `hydrosim/gui/palette/palette_panel.py`

The left sidebar panel listing all available elements.

**Structure:**
```
┌─────────────────────┐
│  🔍 Search...       │  ← Filter input
├─────────────────────┤
│ ▼ INPUT             │  ← Collapsible category header (green)
│   [C] Constant      │
│   [~] TimeSeries    │
├─────────────────────┤
│ ▼ STOCK             │  ← Category header (blue)
│   [🪣] WaterStore   │
├─────────────────────┤
│ ▼ EXPRESSION        │  ← Category header (teal)
│   [f] Expression    │
├─────────────────────┤
│ ▼ RESULT            │  ← Category header (orange)
│   [📈] TimeHistory  │
└─────────────────────┘
```

**Interactions:**
- **Drag to canvas:** Drag any palette item onto the canvas to create a new element at the drop position
- **Double-click:** Creates element at the centre of the current canvas viewport
- **Search:** Filters visible items across all categories (case-insensitive, matches name or description)
- **Collapse/expand:** Click category header to toggle visibility

**Palette item:**
- Shows icon (20px) + element type name + one-line description
- Hover: light background highlight
- Drag ghost: semi-transparent copy of item follows cursor

**Panel width:** 200px fixed, not resizable in Phase 1

---

## 12. Property Dialogs

Each element type has a dedicated property dialog that opens on double-click. All dialogs share the following conventions:

**Common structure:**
```
┌──────────────────────────────────────┐
│ [Icon] Element Type Name             │  ← Header
├──────────────────────────────────────┤
│ Name:        [________________]      │
│ Description: [________________]      │
├──────────────────────────────────────┤
│ [Element-specific parameters]        │
├──────────────────────────────────────┤
│           [Cancel]  [OK]            │
└──────────────────────────────────────┘
```

- Name field: validated as unique within model (no spaces, alphanumeric + underscore)
- OK button applies changes; Cancel discards
- Live validation: errors shown inline, OK button disabled if any validation errors

### 12.1 Constant Dialog

Fields:
- Name (text, required, unique)
- Description (text, optional)
- Value (float input with spin box, supports scientific notation)
- Units (text input with autocomplete from common units list)

### 12.2 TimeSeries Dialog

Fields:
- Name, Description
- Units (text)
- Data Type (dropdown: Instantaneous / Period Total / Period Average)
- Interpolation (dropdown: Linear / Step)
- Data table (editable QTableWidget, 2 columns: Time [days] / Value)
  - Add row button
  - Delete row button
  - Import CSV button (opens file picker, parses 2-column CSV)
  - Clear all button

### 12.3 WaterStore Dialog

Fields:
- Name, Description
- Units (text, e.g. `m3`, `mm`, `ML`)
- Initial Storage (float)
- Lower Bound (float, default 0.0)
- Upper Bound (float or "None" checkbox for unbounded)
- Live preview: shows initial storage on a simple min/max bar indicator

### 12.4 Expression Dialog

Fields:
- Name, Description
- Output Units (text)
- Formula (multi-line text editor with syntax highlighting)
  - Available elements panel: shows all element names and their output ports in a scrollable list (click to insert into formula)
  - Error message area below formula field
  - Test button: evaluates at t=0, shows result or error

### 12.5 TimeHistoryResult Dialog

Fields:
- Name, Description
- Chart Title (text)
- Y-axis Label (text)
- Y-axis Units (text)
- Show Grid (checkbox)
- Y-axis Minimum (float or "Auto" checkbox)
- Y-axis Maximum (float or "Auto" checkbox)
- Connected Series: list showing which ports are connected (read-only, informational)

---

## 13. Results Viewer

**File:** `hydrosim/gui/results/hydrograph_widget.py`

The TimeHistoryResult viewer opens as a separate floating window (not a dialog) when the user double-clicks a TimeHistoryResult element after simulation.

### 13.1 Hydrograph Window

**Layout:**
```
┌─────────────────────────────────────────────┐
│ "Soil Moisture Storage"       [Export CSV]  │
├─────────────────────────────────────────────┤
│                                             │
│   [Matplotlib figure — fills window]        │
│                                             │
│   X: Time (days)  Y: Storage (mm)          │
│   Legend: series names                     │
├─────────────────────────────────────────────┤
│ [Matplotlib toolbar: zoom, pan, save PNG]   │
└─────────────────────────────────────────────┘
```

**Chart style:**
- Background: white
- Grid: light grey (`#E5E7EB`), major gridlines only
- Line colours: cycle through `["#2E86C1", "#E8633A", "#4CAF82", "#7B68C8", "#E8A020", "#00897B", "#E53935", "#795548"]`
- Line width: 1.5px
- Font: matches Qt application font
- Legend: upper right, inside plot, semi-transparent background

**Multiple series:**
- Up to 8 series shown on same axes
- Each series labelled as `"ElementName.port_name"`
- Legend entry shows element name and port

**Export CSV:**
- Saves a CSV with columns: `time_days`, then one column per series named by element and port
- File picker to choose save location

### 13.2 Results Window Management

- Multiple result windows can be open simultaneously
- Each window is independent and can be resized
- Windows remain open after being closed (data preserved) — reopening the element re-shows the window
- Results are cleared when simulation is re-run

---

## 14. Main Window & Menus

**File:** `hydrosim/gui/main_window.py`

### 14.1 Window Layout

```
┌──────────────────────────────────────────────────────┐
│ Menu bar: File | Simulation | View | Help            │
├─────────────────────────────────────────────────────-┤
│ Toolbar: [New] [Open] [Save] | [Run] [Stop]          │
├────────────┬─────────────────────────────────────────┤
│            │                                         │
│  Element   │           Canvas                        │
│  Palette   │                                         │
│  (200px)   │                                         │
│            │                                         │
│            │                                         │
├────────────┴─────────────────────────────────────────┤
│ Status bar: [Model name] [●Ready / ⏳Running]  [zoom] │
└──────────────────────────────────────────────────────┘
```

**Window title:** `HydroSim — [model name][*]` (asterisk when unsaved changes)

**Minimum window size:** 1024 × 768px

### 14.2 Menus

**File menu:**
- New Model (Ctrl+N)
- Open Model... (Ctrl+O)
- Save Model (Ctrl+S)
- Save Model As... (Ctrl+Shift+S)
- Recent Models (submenu, last 5 files)
- ─────
- Exit (Ctrl+Q)

**Simulation menu:**
- Simulation Settings... (Ctrl+T) — opens settings dialog
- Run Simulation (F5 or Ctrl+R)
- Stop Simulation (Escape, only active while running)
- ─────
- Clear Results

**View menu:**
- Zoom In (Ctrl+=)
- Zoom Out (Ctrl+-)
- Zoom to Fit (Ctrl+Shift+F)
- Reset Zoom (Ctrl+0)
- ─────
- Show Simulation Log (toggle dockable panel)

**Help menu:**
- Documentation (opens README or docs URL)
- About HydroSim

### 14.3 Toolbar

Icons with tooltips:
- New, Open, Save (file operations)
- Separator
- Run (green play button, disabled while running)
- Stop (red stop button, enabled only while running)

### 14.4 Simulation Settings Dialog

Opens from Simulation menu. Fields:
- Start Time (days, float, default 0.0)
- End Time (days, float, default 365.0)
- Timestep (days, float, default 1.0)
- Time Mode (radio: Elapsed Days / Calendar)
- Start Date (date picker, only enabled in Calendar mode)

Live validation: shows computed number of timesteps `((end - start) / dt)` and warns if > 100,000 timesteps (performance warning).

### 14.5 Simulation Log Panel

Dockable panel at the bottom of the window (hidden by default, shown automatically when simulation runs).

Content (plain text, monospace font):
```
[10:32:15] HydroSim v1.0
[10:32:15] Starting simulation: Simple Water Balance
[10:32:15] Settings: t=0..365 days, dt=1.0 day (365 timesteps)
[10:32:15] Execution order: [Daily_Rainfall, Runoff_Coefficient, RunoffRate, SoilMoisture, Storage_Plot]
[10:32:15] Running...
[10:32:15] Simulation complete. 365 timesteps in 0.23s
[10:32:15] Water balance check: OK (max error = 1.2e-10 mm)
```

---

## 15. Visual Design System

**File:** `hydrosim/gui/styles/theme.py`

### 15.1 Colour Palette

```python
# Category colours
COLOUR_INPUT      = "#4CAF82"   # Leaf Green
COLOUR_STOCK      = "#2E86C1"   # Ocean Blue
COLOUR_EVENT      = "#E8A020"   # Amber
COLOUR_DELAY      = "#7B68C8"   # Slate Purple
COLOUR_EXPRESSION = "#00897B"   # Teal
COLOUR_RESULT     = "#E8633A"   # Coral Orange

# UI neutrals
COLOUR_BG_APP       = "#F5F6FA"  # App background
COLOUR_BG_CANVAS    = "#F5F6FA"  # Canvas background
COLOUR_BG_CARD      = "#FFFFFF"  # Element card fill
COLOUR_BG_PANEL     = "#FFFFFF"  # Sidebar/panel background
COLOUR_BORDER_CARD  = "#E5E7EB"  # Default card border
COLOUR_TEXT_PRIMARY = "#1A1A2E"  # Primary text
COLOUR_TEXT_SECONDARY = "#6B7280"  # Secondary/label text
COLOUR_GRID_DOT     = "#DEE2E8"  # Canvas grid dots
COLOUR_SELECTION    = "#2E86C1"  # Selection ring

# Semantic colours
COLOUR_ERROR   = "#E53935"  # Error state
COLOUR_WARNING = "#FB8C00"  # Warning state
COLOUR_SUCCESS = "#43A047"  # Success/complete state
```

### 15.2 Typography

```python
FONT_FAMILY     = "Inter"         # Primary (fallback: Segoe UI, SF Pro, sans-serif)
FONT_MONO       = "Fira Code"     # Monospace (fallback: Consolas, Courier New)

FONT_SIZE_XS    = 9               # Tiny labels
FONT_SIZE_SM    = 10              # Port labels, secondary text
FONT_SIZE_MD    = 12              # Element names, body text
FONT_SIZE_LG    = 14              # Dialog headings
FONT_SIZE_XL    = 18              # Window titles

FONT_WEIGHT_NORMAL  = 400
FONT_WEIGHT_MEDIUM  = 500
FONT_WEIGHT_SEMIBOLD = 600
FONT_WEIGHT_BOLD    = 700
```

### 15.3 Spacing & Dimensions

```python
CARD_WIDTH          = 180    # Element card width (px)
CARD_CORNER_RADIUS  = 10     # Card corner radius (px)
CARD_HEADER_HEIGHT  = 4      # Category colour bar height (px)
CARD_PADDING        = 10     # Inner padding (px)
CARD_MIN_HEIGHT     = 80     # Minimum card height (px)
CARD_PORT_HEIGHT    = 20     # Height per port row (px)

PORT_DIAMETER       = 10     # Port dot size (px)
PORT_HOVER_DIAMETER = 14     # Port dot size on hover (px)

PALETTE_WIDTH       = 200    # Left panel width (px)
CONNECTION_CTRL_OFFSET = 80  # Bezier control point offset (px)
```

### 15.4 QSS Stylesheet

The file `hydrosim/gui/styles/stylesheet.qss` applies global Qt widget styling for a clean, modern look. Key rules:
- QMainWindow, QDialog backgrounds: `#F5F6FA`
- QPushButton: rounded corners (6px), category-appropriate hover states
- QLineEdit, QTextEdit: subtle border, focus ring in `#2E86C1`
- QTableWidget: alternating row colours, no grid lines
- QDockWidget: clean header, no ugly title bars

---

## 16. Error Handling

### 16.1 Model Validation Errors

Run before simulation. Shown in a validation dialog with a list of errors. Simulation does not proceed until all errors are resolved.

| Error | Condition | Message |
|---|---|---|
| `MISSING_REQUIRED_INPUT` | Required port not connected | `"{element}" has unconnected required input "{port}"` |
| `CIRCULAR_DEPENDENCY` | Cycle exists among non-stock elements | `"Circular dependency detected: {element_chain}"` |
| `INVALID_FORMULA` | Expression formula fails to parse | `"{element}": formula error — {parser_message}` |
| `UNKNOWN_REFERENCE` | Formula references non-existent element | `"{element}": formula references unknown element "{name}"` |
| `INVALID_PARAMETER` | Parameter fails validation | `"{element}": {parameter} — {reason}"` |
| `EMPTY_TIMESERIES` | TimeSeries has no data | `"{element}": time series has no data rows` |
| `BOUNDS_VIOLATION` | WaterStore initial storage outside bounds | `"{element}": initial storage {val} outside bounds [{lo}, {hi}]` |
| `NO_ELEMENTS` | Model has no elements | `"Model is empty — add elements before running"` |

### 16.2 Runtime Errors

Errors occurring during simulation (caught per-timestep):

| Error | Handling |
|---|---|
| Division by zero in Expression | Log warning, output = 0.0, continue |
| sqrt of negative number | Log warning, output = 0.0, continue |
| NaN propagation | Log error, stop simulation, show message |
| Timestep too large for TimeSeries | Log warning, use flat extrapolation |

### 16.3 File I/O Errors

| Error | Handling |
|---|---|
| File not found | Show dialog: "File not found: {path}" |
| Invalid JSON | Show dialog: "Could not open file — file may be corrupted" |
| Unsupported version | Show dialog: "File was created by a newer version of HydroSim" |
| Permission denied | Show dialog: "Could not save — permission denied" |

### 16.4 Unsaved Changes

When closing or creating a new model with unsaved changes:
> "You have unsaved changes. Do you want to save before closing?"
> [Save] [Don't Save] [Cancel]

---

## 17. Testing Requirements

### 17.1 Unit Tests

All tests in `tests/` using `pytest`. Target: **>80% code coverage** on model and engine modules.

**Element tests** (`tests/test_elements/`):
- Each element: test construction, validation (valid + invalid cases), `get_output_value()`, `to_dict()` + `from_dict()` round-trip
- WaterStore: test forward Euler integration, overflow, deficit, water balance error
- Expression: test formula evaluation, function calls, element reference resolution, forbidden operations rejected
- TimeSeries: test interpolation (linear, step), extrapolation, period_total vs instantaneous

**Engine tests** (`tests/test_engine/`):
- `test_runner.py`: test topological sort, full simulation run (end-to-end), results shape
- `test_solver.py`: test per-timestep execution, state passing between elements
- `test_parser.py`: test safe evaluation, math functions, forbidden AST nodes rejected, dot notation

**Model tests** (`tests/test_model/`):
- `test_graph.py`: add/remove elements, add/remove connections, port compatibility
- `test_validator.py`: test each validation error condition
- `test_serializer.py`: round-trip save/load for each element type, full model

### 17.2 Integration Tests

A complete model integration test in `tests/test_engine/test_runner.py`:

```python
def test_simple_water_balance():
    """
    Build: Constant(0.3) → Expression(rain * coeff) → WaterStore
                TimeSeries(daily_rain) ↗
    Run for 10 days, verify:
    - WaterStore storage changes correctly
    - Water balance closes
    - Results store has correct shape
    """
```

### 17.3 Manual Test Checklist

Before release, manually verify:
- [ ] App launches on clean Python 3.11 environment
- [ ] New model → place all 5 element types from palette
- [ ] Connect elements, open all property dialogs, edit and save parameters
- [ ] Run simulation → results appear in TimeHistoryResult
- [ ] Save model → close app → reopen → load file → model appears correctly
- [ ] Run simulation after reload → same results
- [ ] Delete element → connected connections removed automatically
- [ ] Error dialog appears for invalid model (missing connection)
- [ ] Zoom and pan work correctly
- [ ] Export CSV from result viewer

---

## 18. MVP Acceptance Criteria

The Phase 1 MVP is considered complete when **all** of the following pass:

| # | Criterion |
|---|---|
| AC-01 | App launches without errors on Windows 10+, macOS 13+, Ubuntu 22.04+ |
| AC-02 | All 5 element types can be placed from palette onto canvas |
| AC-03 | Elements can be connected by dragging from output port to input port |
| AC-04 | All 5 property dialogs open, accept valid input, and reject invalid input with clear messages |
| AC-05 | A model containing all 5 element types can be saved and reloaded identically |
| AC-06 | Simulation runs end-to-end and produces a hydrograph in TimeHistoryResult |
| AC-07 | WaterStore water balance error is < 1e-6 over a 365-day daily timestep simulation |
| AC-08 | Expression element correctly evaluates formulas referencing other elements |
| AC-09 | TimeSeries PERIOD_TOTAL with STEP interpolation returns correct values |
| AC-10 | Circular dependency in expressions is detected and reported before simulation |
| AC-11 | CSV export from TimeHistoryResult produces a valid CSV file |
| AC-12 | The example model (`simple_water_balance.hydrosim`) loads and runs correctly |
| AC-13 | All unit tests pass (`pytest tests/`) |
| AC-14 | No uncaught exceptions during normal operation (all errors gracefully handled) |

---

## 19. Out of Scope for Phase 1

The following are explicitly deferred to future phases:

**Phase 2 — Routing & Uncertainty:**
- Monte Carlo simulation (StochasticConstant, multiple realizations)
- MuskingumDelay, TravelTimeDelay, LinearReservoirDelay elements
- Event elements (ScheduledEvent, ThresholdEvent, StormEvent)
- LookupTable element (stage-storage curves)
- FlowDurationResult, FloodFrequencyResult, WaterBalanceResult
- Selector element, PythonScript element
- Undo/redo stack
- Mini-map

**Phase 3 — Advanced:**
- Reservoir element (multi-inflow/outflow with stage-storage)
- GIS / spatial integration (shapefile import, catchment delineation)
- USGS / BOM data API integration for TimeSeries
- NetCDF export
- Auto-layout algorithm

---

## 20. Appendix A — Example Model

The file `hydrosim/resources/examples/simple_water_balance.hydrosim` is bundled with the application. It demonstrates a simple daily water balance model:

**Model structure:**
```
[TimeSeries: Daily_Rainfall (mm/day)]
        │ value
        ▼
[Expression: RunoffRate]  ←── [Constant: RunoffCoeff = 0.3]
   formula: "Daily_Rainfall * RunoffCoeff"
        │ value (mm/day)
        ▼
[WaterStore: SoilMoisture]  ←── (inflow)
   initial=80mm, lower=0, upper=150mm
        │ storage
        ▼
[TimeHistoryResult: Storage_Plot]
   title: "Daily Soil Moisture Storage"
   y_axis: "Storage (mm)"
```

**TimeSeries data:** 365 days of synthetic daily rainfall (random seed 42, mean 3 mm/day, monthly seasonal variation).

---

## 21. Appendix B — Glossary

| Term | Definition |
|---|---|
| **Element** | A self-contained computational node on the canvas with input and output ports |
| **Port** | A named input or output connector on an element |
| **Connection** | A directed link from an output port to an input port |
| **Stock** | An element whose output depends on its historical values (has memory) |
| **State variable** | The stored value of a Stock element at the current timestep |
| **Forward Euler** | Numerical integration method: `x[t+dt] = x[t] + dx/dt * dt` |
| **Topological sort** | Algorithm to order elements so each is computed after its dependencies |
| **Timestep (dt)** | The time interval between simulation updates (days) |
| **Realization** | One complete simulation run (Phase 2: one sample in a Monte Carlo ensemble) |
| **Water balance** | The accounting equation: ΔStorage = Inflows − Outflows |
| **Model graph** | The complete set of elements and connections defining a model |
| **Canvas** | The infinite zoomable/pannable workspace where the model is built visually |
| **Palette** | The sidebar panel listing available element types for drag-and-drop |
| **HydroSim file** | A `.hydrosim` JSON file containing the model definition and canvas layout |
