# HydroSim — Implementation Plan
## Step-by-Step Build Guide for Claude Code

**Version:** 1.0  
**Approach:** Modular milestones — each phase produces something runnable before the next starts  
**Testing:** Implementation first, tests written after each module  
**Verification:** Automated self-checks Claude Code can run at the end of every step  
**Companion documents:** PRD v1.0 · App Flow v1.0 · Tech Stack v1.0 · Design System v1.0 · Backend Schema v1.0

---

## How to Use This Document

Each **Phase** is a self-contained milestone that ends with the application in a working, verifiable state. Do not start Phase N+1 until the verification command at the end of Phase N passes cleanly.

Each **Step** within a phase is a single focused task. Complete steps in order — they build on each other.

**Before starting any phase**, re-read the relevant sections of the companion documents listed at the top of that phase. Do not rely on memory — check the spec.

**If a verification check fails**, fix it before continuing. A broken foundation causes cascading failures in later phases.

---

## Phase Overview

```
Phase 0  ── Project scaffold & tooling            (~30 min)
Phase 1  ── Core data structures & base classes   (~45 min)
Phase 2  ── Element implementations               (~60 min)
Phase 3  ── Model graph & connections             (~45 min)
Phase 4  ── Model validator & serialiser          (~45 min)
Phase 5  ── Simulation engine                     (~60 min)
Phase 6  ── PyQt6 application shell               (~45 min)
Phase 7  ── Canvas — element cards & palette      (~60 min)
Phase 8  ── Canvas — connections & interactions   (~60 min)
Phase 9  ── Property dialogs                      (~60 min)
Phase 10 ── Result viewer & hydrograph            (~45 min)
Phase 11 ── Simulation integration & run flow     (~45 min)
Phase 12 ── Polish, example model & packaging     (~45 min)
```

Total estimated time: ~9 hours of focused Claude Code sessions.
Recommended session size: 2–3 phases per session.

---

## Phase 0 — Project Scaffold & Tooling

**Goal:** A correctly structured Python project that installs cleanly and can be imported.  
**Read first:** Tech Stack §20 (pyproject.toml template), PRD §6 (project structure)  
**Produces:** Installable package, passing import check

---

### Step 0.1 — Create directory structure

Create the complete directory tree exactly as specified in PRD §6:

```
hydrosim/
├── pyproject.toml
├── README.md
├── LICENSE
├── .pre-commit-config.yaml
├── .gitignore
├── hydrosim/
│   ├── __init__.py
│   ├── __main__.py
│   ├── app.py
│   ├── model/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── graph.py
│   │   ├── validator.py
│   │   ├── serialiser.py
│   │   └── elements/
│   │       ├── __init__.py
│   │       ├── constant.py
│   │       ├── timeseries.py
│   │       ├── waterstore.py
│   │       ├── expression.py
│   │       └── timehistory.py
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── runner.py
│   │   ├── solver.py
│   │   ├── parser.py
│   │   └── results.py
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── main_window.py
│   │   ├── canvas/
│   │   │   ├── __init__.py
│   │   │   ├── scene.py
│   │   │   ├── view.py
│   │   │   ├── element_item.py
│   │   │   ├── port_item.py
│   │   │   └── connection_item.py
│   │   ├── palette/
│   │   │   ├── __init__.py
│   │   │   └── palette_panel.py
│   │   ├── dialogs/
│   │   │   ├── __init__.py
│   │   │   ├── constant_dialog.py
│   │   │   ├── timeseries_dialog.py
│   │   │   ├── waterstore_dialog.py
│   │   │   ├── expression_dialog.py
│   │   │   └── timehistory_dialog.py
│   │   ├── results/
│   │   │   ├── __init__.py
│   │   │   └── hydrograph_widget.py
│   │   └── styles/
│   │       ├── __init__.py
│   │       ├── theme.py
│   │       └── stylesheet.qss
│   └── resources/
│       ├── icons/
│       │   ├── constant.svg
│       │   ├── timeseries.svg
│       │   ├── waterstore.svg
│       │   ├── expression.svg
│       │   └── timehistory.svg
│       ├── fonts/
│       │   └── .gitkeep
│       └── examples/
│           └── simple_water_balance.hydrosim
└── tests/
    ├── __init__.py
    ├── test_elements/
    │   ├── __init__.py
    │   ├── test_constant.py
    │   ├── test_timeseries.py
    │   ├── test_waterstore.py
    │   ├── test_expression.py
    │   └── test_timehistory.py
    ├── test_engine/
    │   ├── __init__.py
    │   ├── test_runner.py
    │   ├── test_solver.py
    │   └── test_parser.py
    └── test_model/
        ├── __init__.py
        ├── test_graph.py
        ├── test_validator.py
        └── test_serialiser.py
```

All `__init__.py` files start empty. All other `.py` files start with a module docstring and a `# TODO: implement` comment.

---

### Step 0.2 — Write pyproject.toml

Use the exact template from Tech Stack §20. Key fields:
- `name = "hydrosim"`
- `version = "0.1.0"`
- Entry point: `hydrosim = "hydrosim.__main__:main"`
- All production dependencies with version pins from Tech Stack §15

---

### Step 0.3 — Write __main__.py

```python
# hydrosim/__main__.py
"""Entry point: python -m hydrosim"""

def main():
    print("HydroSim v0.1.0 — starting...")
    # Phase 6 will replace this with the Qt application launch

if __name__ == "__main__":
    main()
```

---

### Step 0.4 — Write theme.py

Populate `hydrosim/gui/styles/theme.py` with ALL colour, typography, and dimension constants from Design System §2 and §4. This file must be complete before any GUI work begins. Every constant listed in the Design System must be present.

Key constants to include:
- All colour hex strings (`APP_BG`, `PANEL_BG`, `CAT_INPUT`, etc.)
- All category colour dicts (`CAT_COLOURS = {"input": CAT_INPUT, ...}`)
- All dimension integers (`CARD_WIDTH`, `PORT_DIAMETER`, etc.)
- All shadow strings (`SHADOW_SUBTLE`, `SHADOW_DIALOG`, etc.)
- Font family strings (`FONT_UI`, `FONT_MONO`)

---

### Step 0.5 — Write SVG icons

Create all 5 SVG files in `hydrosim/resources/icons/` using the exact SVG paths from Design System §14:
- `constant.svg` — two horizontal bars
- `timeseries.svg` — zigzag line with endpoint dots
- `waterstore.svg` — tank outline with fill
- `expression.svg` — integral-like curve with bar
- `timehistory.svg` — three ascending bars

Each SVG uses `width="20" height="20" viewBox="0 0 20 20"` and `fill="none"` at the root. The `{color}` placeholder in the Design System becomes `currentColor` in the SVG files (colour is applied at render time in PyQt6).

---

### Step 0.6 — Install and verify

```bash
pip install -e ".[dev]"
```

**Verification check — run this, it must pass:**
```bash
python -m hydrosim
# Expected output: "HydroSim v0.1.0 — starting..."

python -c "import hydrosim; import hydrosim.model; import hydrosim.engine; import hydrosim.gui; print('All imports OK')"
# Expected output: "All imports OK"
```

---

## Phase 1 — Core Data Structures & Base Classes

**Goal:** All enums, dataclasses, and the abstract `ElementBase` class fully implemented.  
**Read first:** Backend Schema §3 (core data structures), §4 (ElementBase)  
**Produces:** Importable base module, passing unit tests for data structures  
**No GUI code in this phase.**

---

### Step 1.1 — Implement enums and dataclasses in base.py

Implement in this order in `hydrosim/model/base.py`:

1. **Enums:** `PortType`, `ElementCategory`, `TimeSeriesType`, `InterpolationType`
2. **`Port` dataclass** — all fields including `_current_value` with `field(default=0.0, repr=False, compare=False)`
3. **`Connection` dataclass** — with `__post_init__` that auto-generates UUID if `id` is empty
4. **`SimulationSettings` dataclass** — with `n_steps` and `timesteps` properties
5. **`SimState` dataclass** — with `get()` and `set()` methods

All dataclasses use `@dataclass` decorator. All fields are type-annotated. Use `from __future__ import annotations` at the top of the file for forward references.

---

### Step 1.2 — Implement error types in base.py

Add all error classes and `ValidationError`/`ValidationWarning` dataclasses from Backend Schema §14:

```
HydroSimError (base Exception)
├── SimulationError
├── SimulationAborted
├── CircularDependencyError
├── ExpressionEvaluationError
├── ModelFileError
└── VersionMismatchError

ValidationError (dataclass, NOT an exception)
ValidationWarning (dataclass, NOT an exception)

Error code constants (strings):
ERR_NO_ELEMENTS, ERR_MISSING_REQUIRED_INPUT, etc.
WARN_UNITS_MISMATCH, etc.
```

---

### Step 1.3 — Implement ElementBase abstract class

Implement `ElementBase` in `hydrosim/model/base.py` exactly as specified in Backend Schema §4:

- `__init__` sets id, name, description, position; calls `_define_ports()`
- `_add_input_port()` and `_add_output_port()` helper methods
- `input_ports`, `output_ports`, `all_ports` properties returning copies
- `get_port()` method
- Abstract methods: `category` (property), `_define_ports`, `validate`, `compute`, `to_dict`, `from_dict`
- Concrete methods: `is_stock()` (returns False), `__repr__`

**Critical:** `_define_ports()` is called at the end of `__init__`. Subclasses call `super().__init__()` first, then their own `__init__` body. The ports dict is populated by `_define_ports()` which is called inside `super().__init__()` — this works because `_define_ports()` is overridden in the subclass and Python's method resolution calls the subclass version.

---

### Step 1.4 — Write tests for Phase 1

File: `tests/test_model/test_graph.py` (just the data structure parts for now)

```python
# Test SimulationSettings.n_steps calculation
def test_simulation_settings_n_steps():
    s = SimulationSettings(start_time=0, end_time=365, dt=1.0,
                           time_mode="elapsed", start_date=None)
    assert s.n_steps == 365
    assert len(s.timesteps) == 365

# Test Connection auto-generates UUID
def test_connection_auto_id():
    c = Connection(id="", from_element_id="a", from_port_name="value",
                   to_element_id="b", to_port_name="inflow")
    assert len(c.id) == 36   # UUID format

# Test SimState.get returns 0.0 for missing keys
def test_simstate_get_missing():
    state = SimState(t=0, dt=1, step=0, values={}, storage={})
    assert state.get("nonexistent_id", "value") == 0.0

# Test SimState.set and get round-trip
def test_simstate_set_get():
    state = SimState(t=0, dt=1, step=0, values={}, storage={})
    state.set("el_1", "storage", 42.5)
    assert state.get("el_1", "storage") == 42.5
```

---

### Step 1.5 — Verification check

```bash
pytest tests/test_model/test_graph.py -v
# Expected: all data structure tests pass

python -c "
from hydrosim.model.base import (
    ElementBase, Port, Connection, SimState,
    SimulationSettings, ValidationError, PortType,
    ElementCategory, HydroSimError
)
print('base.py imports OK')
"
```

---

## Phase 2 — Element Implementations

**Goal:** All 5 element types fully implemented with correct `compute()` logic.  
**Read first:** Backend Schema §5 (all element implementations), PRD §7  
**Produces:** All elements importable, water balance test passing  
**No GUI code. No graph code. Elements work standalone.**

---

### Step 2.1 — Implement Constant

File: `hydrosim/model/elements/constant.py`

- Constructor stores `value` (float) and `units` (str)
- `_define_ports()`: single output port `"value"` with `self.units`
- `validate()`: checks `math.isfinite(self.value)`
- `compute()`: `state.set(self.id, "value", self.value)` — one line
- `to_dict()` / `from_dict()`: include `type: "Constant"` in dict

Update `hydrosim/model/elements/__init__.py` to export `Constant`.

---

### Step 2.2 — Implement TimeSeries

File: `hydrosim/model/elements/timeseries.py`

- Constructor stores `units`, `data_type`, `interpolation`, `data` (list of [time, value] pairs)
- `_define_ports()`: single output port `"value"`
- `validate()`: checks data non-empty, times strictly increasing, no NaN/Inf
- `prepare()`: builds `scipy.interpolate.interp1d` with `kind='previous'` (STEP) or `'linear'`; sets `self._interpolator`; sets `self._prepared = True`
- `compute()`: calls `self._interpolator(state.t)` — raises `RuntimeError("prepare() not called")` if `self._prepared` is False
- `get_value_at(t)`: public method for GUI preview — calls `prepare()` internally if not prepared
- `to_dict()`: data stored as `[[t, v], ...]` list of lists (JSON-serialisable)
- `from_dict()`: reconstruct data from list of lists

---

### Step 2.3 — Implement WaterStore

File: `hydrosim/model/elements/waterstore.py`

This is the most critical element — implement carefully.

- Constructor stores `initial_storage`, `lower_bound`, `upper_bound` (None = unbounded), `units`
- `is_stock()` returns `True`
- `_define_ports()`: inputs `"inflow"` and `"outflow"` (both optional); outputs `"storage"`, `"overflow"`, `"deficit"`
- `validate()`: 3 checks as specified in Backend Schema §5.3
- `initialise(state)`: sets `state.storage[self.id] = self.initial_storage` and writes all three output ports to initial values (storage=initial, overflow=0, deficit=0)
- `compute(state, connections_in)`: exact forward Euler algorithm from Backend Schema §5.3 — read `state.storage[self.id]`, integrate, clamp to bounds, write back
- `get_water_balance_error()`: returns residual for diagnostic checks
- `to_dict()` / `from_dict()`: `upper_bound` serialised as `null` when None

**Critical invariant:** `compute()` reads `state.storage[self.id]` (previous step value set by `initialise()` or previous `compute()`) NOT `state.get(self.id, "storage")`.

---

### Step 2.4 — Implement Expression

File: `hydrosim/model/elements/expression.py`

- Constructor stores `formula` (str) and `output_units` (str)
- `_define_ports()`: single output port `"value"`; input ports are dynamic (start empty)
- `set_formula(formula)`: sets `self.formula`, calls `rebuild_input_ports()`
- `rebuild_input_ports()`: clears `_input_ports`, calls `ExpressionParser.extract_references(self.formula)`, adds one input port per reference
- `validate()`: calls `ExpressionParser.validate_syntax(self.formula)`, returns ValidationErrors for each error string
- `prepare(name_to_id)`: creates `self._parser = ExpressionParser(self.formula, name_to_id)`, sets `self._prepared = True`
- `compute(state, connections_in)`: calls `self._parser.evaluate(connections_in, state.t, state.dt)`, writes to `state.set(self.id, "value", result)`. On `ExpressionEvaluationError`, writes 0.0 and logs warning.
- `evaluate_test(input_values, t, dt)`: evaluates without state object (for GUI Test button)
- `to_dict()`: saves `formula` and `output_units` only — input ports are NOT saved (rebuilt from formula on load)
- `from_dict()`: reconstruct, then call `set_formula()` to rebuild ports

**Note:** `ExpressionParser` is imported from `hydrosim.engine.parser` — this is the one place engine is referenced from an element. This is acceptable because `Expression` needs the parser to define its dynamic ports. Keep the import inside the method (`prepare`, `validate`) to keep it lazy.

---

### Step 2.5 — Implement TimeHistoryResult

File: `hydrosim/model/elements/timehistory.py`

- Constructor stores `title`, `y_axis_label`, `y_axis_units`, `show_grid`, `y_min`, `y_max`
- `_define_ports()`: single input port `"series_1"` (required=True)
- `add_series_port()`: adds `series_2`, `series_3`, ... up to `MAX_SERIES = 8`
- `validate()`: check y_min < y_max if both set
- `compute()`: no-op (pass)
- `to_dict()` / `from_dict()`: includes all chart config parameters

---

### Step 2.6 — Write element tests

Files: `tests/test_elements/test_*.py`

Write these specific tests — they cover the critical logic:

**test_constant.py:**
```python
def test_constant_compute():
    el = Constant(name="C", value=3.14)
    state = SimState(t=0, dt=1, step=0, values={}, storage={})
    el.compute(state, {})
    assert state.get(el.id, "value") == pytest.approx(3.14)

def test_constant_validate_inf():
    el = Constant(name="C", value=float('inf'))
    errors = el.validate()
    assert len(errors) == 1
    assert errors[0].code == ERR_INVALID_PARAMETER

def test_constant_roundtrip():
    el = Constant(name="Manning_n", value=0.035, units="s/m^(1/3)")
    el2 = Constant.from_dict(el.to_dict())
    assert el2.name == el.name
    assert el2.value == el.value
    assert el2.units == el.units
```

**test_waterstore.py (most important):**
```python
def test_waterstore_integration_basic():
    """10 steps, constant inflow=5, outflow=2, dt=1 → storage grows by 3/step"""
    ws = WaterStore(name="S", initial_storage=100, lower_bound=0, upper_bound=200)
    state = SimState(t=0, dt=1.0, step=0, values={}, storage={})
    ws.initialise(state)
    for i in range(10):
        state.t = float(i)
        ws.compute(state, {"inflow": 5.0, "outflow": 2.0})
    assert state.get(ws.id, "storage") == pytest.approx(130.0, abs=1e-9)

def test_waterstore_overflow():
    ws = WaterStore(name="S", initial_storage=198, upper_bound=200)
    state = SimState(t=0, dt=1.0, step=0, values={}, storage={})
    ws.initialise(state)
    ws.compute(state, {"inflow": 5.0, "outflow": 0.0})
    assert state.get(ws.id, "storage") == pytest.approx(200.0)
    assert state.get(ws.id, "overflow") == pytest.approx(3.0)   # 3mm/day spilled

def test_waterstore_water_balance():
    """Mass conservation: ΔS == (inflow - outflow - overflow + deficit) * dt"""
    ws = WaterStore(name="S", initial_storage=50, lower_bound=0, upper_bound=100)
    state = SimState(t=0, dt=1.0, step=0, values={}, storage={})
    ws.initialise(state)
    import numpy as np
    inflows  = np.random.default_rng(42).uniform(0, 10, 100)
    outflows = np.random.default_rng(99).uniform(0, 8, 100)
    total_overflow = 0.0
    total_deficit  = 0.0
    for i in range(100):
        ws.compute(state, {"inflow": inflows[i], "outflow": outflows[i]})
        total_overflow += state.get(ws.id, "overflow")
        total_deficit  += state.get(ws.id, "deficit")
    delta_s = state.get(ws.id, "storage") - 50.0
    total_net = (inflows.sum() - outflows.sum() - total_overflow + total_deficit)
    assert delta_s == pytest.approx(total_net, rel=1e-6)

def test_waterstore_unbounded():
    ws = WaterStore(name="S", initial_storage=0, upper_bound=None)
    state = SimState(t=0, dt=1.0, step=0, values={}, storage={})
    ws.initialise(state)
    for _ in range(10):
        ws.compute(state, {"inflow": 100.0, "outflow": 0.0})
    assert state.get(ws.id, "overflow") == 0.0   # never overflows
    assert state.get(ws.id, "storage") == pytest.approx(1000.0)
```

**test_timeseries.py:**
```python
def test_timeseries_step_interpolation():
    ts = TimeSeries(name="R", data=[[0,0],[1,5],[2,0],[3,10]],
                    interpolation=InterpolationType.STEP)
    ts.prepare()
    state = SimState(t=1.5, dt=1, step=1, values={}, storage={})
    ts.compute(state, {})
    assert state.get(ts.id, "value") == pytest.approx(5.0)

def test_timeseries_linear_interpolation():
    ts = TimeSeries(name="R", data=[[0,0],[10,10]],
                    interpolation=InterpolationType.LINEAR)
    ts.prepare()
    state = SimState(t=5, dt=1, step=5, values={}, storage={})
    ts.compute(state, {})
    assert state.get(ts.id, "value") == pytest.approx(5.0)

def test_timeseries_flat_extrapolation():
    ts = TimeSeries(name="R", data=[[0,3],[1,5]])
    ts.prepare()
    state = SimState(t=999, dt=1, step=999, values={}, storage={})
    ts.compute(state, {})
    assert state.get(ts.id, "value") == pytest.approx(5.0)   # last value

def test_timeseries_validate_non_monotonic():
    ts = TimeSeries(name="R", data=[[0,1],[2,2],[1,3]])   # time goes backwards
    errors = ts.validate()
    assert any(e.code == ERR_INVALID_PARAMETER for e in errors)
```

---

### Step 2.7 — Verification check

```bash
pytest tests/test_elements/ -v
# Expected: all element tests pass

python -c "
from hydrosim.model.elements.constant import Constant
from hydrosim.model.elements.timeseries import TimeSeries
from hydrosim.model.elements.waterstore import WaterStore
from hydrosim.model.elements.expression import Expression
from hydrosim.model.elements.timehistory import TimeHistoryResult
print('All 5 elements import OK')

# Quick smoke test
c = Constant(name='Test', value=42.0)
assert c.name == 'Test'
assert 'value' in c.output_ports
print('Constant smoke test OK')
"
```

---

## Phase 3 — Model Graph & Connections

**Goal:** `ModelGraph` correctly manages elements and connections, with working topological sort.  
**Read first:** Backend Schema §6 (ModelGraph), §3 (Connection dataclass)  
**Produces:** Graph with add/remove operations and topological sort working correctly

---

### Step 3.1 — Implement ModelGraph

File: `hydrosim/model/graph.py`

Implement all methods from Backend Schema §6 in this order:

**Constructor:**
```python
def __init__(self):
    self._elements:    dict[str, ElementBase] = {}
    self._connections: dict[str, Connection]  = {}
    self._nx_graph:    nx.DiGraph             = nx.DiGraph()
```

**Element management (implement first):**
- `add_element(element)` — validates no duplicate ID, adds to dict and nx graph
- `remove_element(element_id)` — removes connections first, then element
- `get_element(element_id)` — raises KeyError
- `get_element_by_name(name)` — case-insensitive, returns None if missing
- `rename_element(element_id, new_name)` — updates name, updates Expression ports if needed
- `elements` property — returns `dict(self._elements)` (copy)
- `element_count` property

**Connection management (implement second):**
- `add_connection(connection)` — full validation then add; see Backend Schema §6 for the complete validation list; adds nx edge only if `_should_add_nx_edge()` is True
- `remove_connection(connection_id)` — remove from dict and nx graph
- `get_connection(connection_id)`
- `get_connections_from(element_id)`
- `get_connections_to(element_id)`
- `get_connections_to_port(element_id, port_name)`
- `connections` property — returns copy

**Graph analysis (implement third):**
- `get_execution_order()` — topological sort, raises `CircularDependencyError` if cycle
- `has_cycle()` — boolean
- `get_upstream_elements(element_id)`
- `build_name_to_id_map()` — lowercase keys

**Private helpers:**
- `_should_add_nx_edge(from_element)` — returns `not from_element.is_stock()`

**Connection validation in `add_connection()`** must check all of:
1. `from_element_id` exists in graph
2. `to_element_id` exists in graph
3. `from_port_name` is an output port on the source element
4. `to_port_name` is an input port on the destination element
5. The destination port is not already connected (check `get_connections_to_port`)
6. Would not create a cycle (check `has_cycle()` after temporarily adding to nx graph)

Raise `ValueError` with a descriptive message for each failed check.

---

### Step 3.2 — Write graph tests

File: `tests/test_model/test_graph.py`

```python
def test_add_and_get_element():
    g = ModelGraph()
    c = Constant(name="C", value=1.0)
    g.add_element(c)
    assert g.get_element(c.id) is c
    assert g.element_count == 1

def test_remove_element_removes_connections():
    g = ModelGraph()
    c  = Constant(name="C", value=1.0)
    ws = WaterStore(name="WS")
    g.add_element(c)
    g.add_element(ws)
    conn = Connection(id="", from_element_id=c.id, from_port_name="value",
                      to_element_id=ws.id, to_port_name="inflow")
    g.add_connection(conn)
    assert len(g.connections) == 1
    g.remove_element(c.id)
    assert len(g.connections) == 0

def test_execution_order_simple_chain():
    """Constant → Expression → WaterStore → TimeHistoryResult"""
    g = ModelGraph()
    c  = Constant(name="Rain", value=5.0)
    ex = Expression(name="Rate", formula="Rain * 0.3", output_units="mm/day")
    ws = WaterStore(name="Store")
    th = TimeHistoryResult(name="Plot")
    for el in [c, ex, ws, th]:
        g.add_element(el)
    g.add_connection(Connection("", c.id,  "value",   ex.id, "Rain"))
    g.add_connection(Connection("", ex.id, "value",   ws.id, "inflow"))
    g.add_connection(Connection("", ws.id, "storage", th.id, "series_1"))
    order = g.get_execution_order()
    names = [el.name for el in order]
    assert names.index("Rain") < names.index("Rate")
    assert names.index("Rate") < names.index("Store")

def test_stock_does_not_create_cycle():
    """WaterStore output → Expression input should NOT cause CircularDependencyError"""
    g = ModelGraph()
    ws = WaterStore(name="WS", initial_storage=100)
    ex = Expression(name="Evap", formula="WS.storage * 0.01", output_units="mm/day")
    ex.set_formula("WS.storage * 0.01")
    g.add_element(ws)
    g.add_element(ex)
    # This connection feeds stock output back into an expression
    # Should NOT raise CircularDependencyError because WS is a stock
    g.add_connection(Connection("", ws.id, "storage", ex.id, "WS.storage"))
    assert not g.has_cycle()

def test_circular_dependency_detected():
    """Two Expressions referencing each other should raise CircularDependencyError"""
    g = ModelGraph()
    e1 = Expression(name="A", formula="B * 2")
    e2 = Expression(name="B", formula="A * 2")
    g.add_element(e1)
    g.add_element(e2)
    g.add_connection(Connection("", e1.id, "value", e2.id, "A"))
    with pytest.raises((CircularDependencyError, ValueError)):
        g.add_connection(Connection("", e2.id, "value", e1.id, "B"))

def test_duplicate_connection_to_input_port_rejected():
    """Input ports accept only one connection"""
    g = ModelGraph()
    c1 = Constant(name="C1", value=1.0)
    c2 = Constant(name="C2", value=2.0)
    ws = WaterStore(name="WS")
    g.add_element(c1); g.add_element(c2); g.add_element(ws)
    g.add_connection(Connection("", c1.id, "value", ws.id, "inflow"))
    with pytest.raises(ValueError):
        g.add_connection(Connection("", c2.id, "value", ws.id, "inflow"))
```

---

### Step 3.3 — Verification check

```bash
pytest tests/test_model/test_graph.py -v
# Expected: all graph tests pass

python -c "
from hydrosim.model.graph import ModelGraph
from hydrosim.model.elements.constant import Constant
from hydrosim.model.elements.waterstore import WaterStore
from hydrosim.model.base import Connection

g = ModelGraph()
c = Constant(name='Rain', value=5.0)
ws = WaterStore(name='Store', initial_storage=100)
g.add_element(c)
g.add_element(ws)
conn = Connection('', c.id, 'value', ws.id, 'inflow')
g.add_connection(conn)
order = g.get_execution_order()
print(f'Execution order: {[el.name for el in order]}')
print('ModelGraph smoke test OK')
"
```

---

## Phase 4 — Model Validator & Serialiser

**Goal:** Models can be validated before running and saved/loaded as `.hydrosim` JSON files.  
**Read first:** Backend Schema §7 (Validator), §8 (Serialiser), PRD §9 (file format)  
**Produces:** Working save/load round-trip, validation errors correctly identified

---

### Step 4.1 — Implement ModelValidator

File: `hydrosim/model/validator.py`

Implement all methods from Backend Schema §7:

- `validate_all()` — runs all checks, collects all errors, returns combined list
- `validate_element(element_id)` — delegates to `element.validate()`
- `_check_model_not_empty()` — error if `graph.element_count == 0`
- `_check_element_parameters()` — calls `el.validate()` on each element
- `_check_required_ports_connected()` — for each input port where `required=True`, check `get_connections_to_port()` returns at least one connection
- `_check_no_circular_dependencies()` — calls `graph.has_cycle()`
- `_check_expression_references()` — parses each Expression formula, checks each reference name exists in graph (case-insensitive); uses `ExpressionParser.extract_references()`; if close match found via `suggest_correction()`, include in error message
- `get_warnings()` — runs all warning checks, returns list
- `_warn_units_mismatch()` — for each connection, compare source port units to destination port units; warn if different and neither is `"-"`
- `_warn_timeseries_too_short()` — optional in Phase 1 (return empty list if settings not available)
- `_warn_missing_descriptions()` — warn for elements where `description == ""`

---

### Step 4.2 — Implement ModelSerialiser

File: `hydrosim/model/serialiser.py`

Implement using Pydantic for load-side validation:

**Pydantic schemas** (define at top of file):
- `ConnectionSchema` — validates connection structure
- `SimSettingsSchema` — validates settings with field validators
- `HydroSimFileSchema` — top-level file schema

**`ELEMENT_REGISTRY` dict:**
```python
ELEMENT_REGISTRY = {
    "Constant":          Constant,
    "TimeSeries":        TimeSeries,
    "WaterStore":        WaterStore,
    "Expression":        Expression,
    "TimeHistoryResult": TimeHistoryResult,
}
```

**`save(graph, settings, filepath, metadata=None)`:**
1. Build top-level dict (see PRD §9.1 for exact structure)
2. `metadata` defaults to `{"name": "Untitled", "description": "", "author": "", "created": now_iso, "modified": now_iso}`
3. `json.dump(data, f, indent=2, ensure_ascii=False)`

**`load(filepath)`:**
1. `json.load(f)` — catch `json.JSONDecodeError` → raise `ModelFileError`
2. Check `file_format_version` — raise `VersionMismatchError` if too new
3. `HydroSimFileSchema.model_validate(raw)` — catch `ValidationError` → raise `ModelFileError`
4. Rebuild `ModelGraph`: deserialise each element, add to graph, then deserialise connections and add
5. Rebuild `SimulationSettings`
6. Return `(graph, settings, metadata_dict)`

**`_deserialise_element(data)`:** dispatch via `ELEMENT_REGISTRY`

**Canvas state** is saved/loaded separately from simulation state. Store element positions in each element's `position` field — already part of `to_dict()`.

---

### Step 4.3 — Write validator and serialiser tests

**test_validator.py:**
```python
def test_empty_model_error():
    g = ModelGraph()
    v = ModelValidator(g)
    errors = v.validate_all()
    assert any(e.code == ERR_NO_ELEMENTS for e in errors)

def test_missing_required_port_error():
    g = ModelGraph()
    th = TimeHistoryResult(name="Plot")
    g.add_element(th)
    v = ModelValidator(g)
    errors = v.validate_all()
    assert any(e.code == ERR_MISSING_REQUIRED_INPUT for e in errors)

def test_unknown_expression_reference():
    g = ModelGraph()
    ex = Expression(name="Calc", formula="Rainfal * 0.3")  # typo
    ex.set_formula("Rainfal * 0.3")
    g.add_element(ex)
    v = ModelValidator(g)
    errors = v.validate_all()
    assert any(e.code == ERR_UNKNOWN_REFERENCE for e in errors)
    assert any("Rainfal" in e.message for e in errors)

def test_valid_model_no_errors():
    g = ModelGraph()
    c  = Constant(name="Rain", value=5.0)
    ws = WaterStore(name="Store", initial_storage=80)
    th = TimeHistoryResult(name="Plot")
    g.add_element(c); g.add_element(ws); g.add_element(th)
    g.add_connection(Connection("", c.id, "value", ws.id, "inflow"))
    g.add_connection(Connection("", ws.id, "storage", th.id, "series_1"))
    v = ModelValidator(g)
    errors = v.validate_all()
    assert errors == []
```

**test_serialiser.py:**
```python
def test_save_load_roundtrip(tmp_path):
    """Build a model, save it, load it, verify it matches."""
    g = ModelGraph()
    c  = Constant(name="Rain", value=5.0, units="mm/day")
    ws = WaterStore(name="Store", initial_storage=80, upper_bound=150)
    th = TimeHistoryResult(name="Plot", title="Soil Moisture")
    for el in [c, ws, th]:
        g.add_element(el)
    g.add_connection(Connection("", c.id,  "value",   ws.id, "inflow"))
    g.add_connection(Connection("", ws.id, "storage", th.id, "series_1"))
    settings = SimulationSettings(0, 365, 1.0, "elapsed", None)

    path = tmp_path / "test.hydrosim"
    ModelSerialiser.save(g, settings, path)
    assert path.exists()

    g2, s2, meta = ModelSerialiser.load(path)
    assert g2.element_count == 3
    assert len(g2.connections) == 2
    assert s2.end_time == 365.0

    # Check Constant value preserved
    rain2 = g2.get_element_by_name("Rain")
    assert rain2.value == pytest.approx(5.0)

    # Check WaterStore bounds preserved
    store2 = g2.get_element_by_name("Store")
    assert store2.upper_bound == pytest.approx(150.0)

def test_load_bad_file(tmp_path):
    path = tmp_path / "bad.hydrosim"
    path.write_text("not valid json {{{")
    with pytest.raises(ModelFileError):
        ModelSerialiser.load(path)
```

---

### Step 4.4 — Verification check

```bash
pytest tests/test_model/ -v
# Expected: all model tests pass (graph + validator + serialiser)

python -c "
import tempfile, pathlib
from hydrosim.model.graph import ModelGraph
from hydrosim.model.elements.constant import Constant
from hydrosim.model.elements.waterstore import WaterStore
from hydrosim.model.elements.timehistory import TimeHistoryResult
from hydrosim.model.base import Connection, SimulationSettings
from hydrosim.model.serialiser import ModelSerialiser

g = ModelGraph()
c  = Constant(name='Rain', value=5.0)
ws = WaterStore(name='Store', initial_storage=80, upper_bound=150)
th = TimeHistoryResult(name='Plot')
for el in [c, ws, th]: g.add_element(el)
g.add_connection(Connection('', c.id,  'value',   ws.id, 'inflow'))
g.add_connection(Connection('', ws.id, 'storage', th.id, 'series_1'))
settings = SimulationSettings(0, 10, 1.0, 'elapsed', None)

with tempfile.NamedTemporaryFile(suffix='.hydrosim', delete=False) as f:
    path = pathlib.Path(f.name)

ModelSerialiser.save(g, settings, path)
g2, s2, _ = ModelSerialiser.load(path)
assert g2.element_count == 3
print('Save/load round-trip OK')
"
```

---

## Phase 5 — Simulation Engine

**Goal:** A complete simulation runs end-to-end producing correct numerical results.  
**Read first:** Backend Schema §9 (Runner), §10 (Solver), §11 (Parser), §12 (ResultsStore)  
**Produces:** Full simulation run passing water balance verification, all engine tests green

---

### Step 5.1 — Implement ExpressionParser

File: `hydrosim/engine/parser.py`

Implement from Backend Schema §11:

- `SAFE_AST_NODES` frozenset — all whitelisted node types
- `SAFE_FUNCTIONS` dict — all math functions
- `ExpressionParser.__init__(formula, name_to_id)` — stores formula, creates `SimpleEval`
- `ExpressionParser.evaluate(input_values, t, dt)` — injects names namespace, calls `self._evaluator.eval()`, handles exceptions
- `ExpressionParser.validate_syntax(formula)` — static method, parses AST, checks node whitelist, returns list of error strings
- `ExpressionParser.extract_references(formula)` — static method, walks AST, finds `Name` nodes and `Attribute` nodes (for dot-notation), excludes reserved names
- `ExpressionParser.suggest_correction(unknown, known_names)` — static method, uses `difflib.get_close_matches()` to find similar names

**Test that forbidden operations are rejected:**
```python
# These must all return errors from validate_syntax:
"__import__('os')"
"open('/etc/passwd')"
"eval('1+1')"
"[x for x in range(10)]"
```

---

### Step 5.2 — Implement ResultsStore

File: `hydrosim/engine/results.py`

Implement from Backend Schema §12:

- `__init__(timesteps, tracked, element_names)` — pre-allocate `np.zeros(n_steps, dtype=np.float64)` for each tracked pair
- `record(step, state)` — write each tracked value from state to its array at index `step`; update `completed_steps`
- `get_series(element_id, port_name)` — raises `KeyError` if not tracked
- `get_series_by_name(element_name, port_name)` — lookup by name
- `get_all_series()` — nested dict `{element_name: {port_name: ndarray}}`
- `get_completed_timesteps()` — returns `self.timesteps[:self.completed_steps]`
- `export_dataframe()` — builds Pandas DataFrame with `time_days` column + one column per series
- `is_complete` property

---

### Step 5.3 — Implement TimeStepSolver

File: `hydrosim/engine/solver.py`

Implement `TimeStepSolver.resolve_inputs(element, state)` from Backend Schema §10:

- Iterates over `element.input_ports`
- For each port, calls `graph.get_connections_to_port(element.id, port_name)`
- If no connections: omit from result dict (do not include in returned dict)
- If connections found: sum all source values from `state.get(source_id, source_port)`
- Returns `{port_name: float}` dict

---

### Step 5.4 — Implement SimulationRunner

File: `hydrosim/engine/runner.py`

Implement all methods from Backend Schema §9 in this exact order:

1. `__init__(graph, settings)` — store graph, settings; set `_stop_requested = False`
2. `stop()` — sets `_stop_requested = True` (thread-safe; no lock needed for bool)
3. `_validate()` — runs `ModelValidator(self.graph).validate_all()`; raises `SimulationError` if errors
4. `_build_execution_order()` — calls `self.graph.get_execution_order()`
5. `_initialise_state()` — creates fresh `SimState`
6. `_prepare_elements(state)` — calls `prepare()` on `TimeSeries` and `Expression` elements
7. `_initialise_stocks(state)` — calls `initialise(state)` on all stock elements
8. `_build_results_store(execution_order)` — finds tracked pairs, creates `ResultsStore`
9. `_timestep_loop(execution_order, state, results, progress_cb)` — main loop (see Backend Schema §9)
10. `_log_warnings(results)` — check water balance errors, log to Python `logging` module
11. `run(progress_callback=None)` — orchestrates steps 1–10 in sequence, returns `ResultsStore`

**Thread safety note:** `run()` is called from a background QThread in the GUI. It must not import or reference PyQt6. The `progress_callback` is a plain Python callable — the GUI passes a lambda that emits a Qt signal.

---

### Step 5.5 — Write engine tests

**test_parser.py:**
```python
def test_simple_arithmetic():
    p = ExpressionParser("Rain * 0.3", {"rain": "id_rain"})
    result = p.evaluate({"Rain": 10.0}, t=0, dt=1)
    assert result == pytest.approx(3.0)

def test_builtin_functions():
    p = ExpressionParser("sqrt(4) + abs(-1)", {})
    assert p.evaluate({}, 0, 1) == pytest.approx(3.0)

def test_special_variables_t_dt():
    p = ExpressionParser("t + dt", {})
    assert p.evaluate({}, t=5.0, dt=1.0) == pytest.approx(6.0)

def test_forbidden_import_rejected():
    errors = ExpressionParser.validate_syntax("__import__('os')")
    assert len(errors) > 0

def test_extract_references_simple():
    refs = ExpressionParser.extract_references("Daily_Rainfall * RunoffCoeff")
    assert "Daily_Rainfall" in refs
    assert "RunoffCoeff" in refs

def test_extract_references_dot_notation():
    refs = ExpressionParser.extract_references("SoilMoisture.storage * 0.01")
    assert "SoilMoisture.storage" in refs

def test_division_by_zero_returns_zero():
    p = ExpressionParser("1 / 0", {})
    result = p.evaluate({}, 0, 1)
    assert result == 0.0   # does not raise
```

**test_runner.py (integration test — most important):**
```python
def test_full_simulation_simple_water_balance():
    """
    Model: Constant(5 mm/day) → WaterStore(initial=100, upper=200)
    Run for 10 days, dt=1.
    Expected: storage increases by 5/day → final = 150 mm.
    """
    g = ModelGraph()
    c  = Constant(name="Rain", value=5.0, units="mm/day")
    ws = WaterStore(name="Store", initial_storage=100,
                    lower_bound=0, upper_bound=200, units="mm")
    th = TimeHistoryResult(name="Plot")
    for el in [c, ws, th]: g.add_element(el)
    g.add_connection(Connection("", c.id,  "value",   ws.id, "inflow"))
    g.add_connection(Connection("", ws.id, "storage", th.id, "series_1"))
    settings = SimulationSettings(0, 10, 1.0, "elapsed", None)

    runner = SimulationRunner(g, settings)
    results = runner.run()

    series = results.get_series_by_name("Store", "storage")
    assert results.is_complete
    assert series[-1] == pytest.approx(150.0, abs=1e-6)
    assert len(series) == 10

def test_simulation_with_expression():
    """
    Model: Constant(10) → Expression(Rain * 0.3) → WaterStore(initial=0)
    Expected after 5 days: storage = 5 * 3.0 = 15 mm.
    """
    g = ModelGraph()
    c  = Constant(name="Rain", value=10.0)
    ex = Expression(name="Runoff", formula="Rain * 0.3", output_units="mm/day")
    ex.set_formula("Rain * 0.3")
    ws = WaterStore(name="Store", initial_storage=0)
    th = TimeHistoryResult(name="Plot")
    for el in [c, ex, ws, th]: g.add_element(el)
    g.add_connection(Connection("", c.id,  "value", ex.id, "Rain"))
    g.add_connection(Connection("", ex.id, "value", ws.id, "inflow"))
    g.add_connection(Connection("", ws.id, "storage", th.id, "series_1"))
    settings = SimulationSettings(0, 5, 1.0, "elapsed", None)

    results = SimulationRunner(g, settings).run()
    series = results.get_series_by_name("Store", "storage")
    assert series[-1] == pytest.approx(15.0, abs=1e-6)

def test_simulation_stop():
    """Calling stop() during run aborts and returns partial results."""
    import threading
    g = ModelGraph()
    c  = Constant(name="R", value=1.0)
    ws = WaterStore(name="S", initial_storage=0, upper_bound=None)
    th = TimeHistoryResult(name="P")
    for el in [c, ws, th]: g.add_element(el)
    g.add_connection(Connection("", c.id,  "value",   ws.id, "inflow"))
    g.add_connection(Connection("", ws.id, "storage", th.id, "series_1"))
    settings = SimulationSettings(0, 1000, 1.0, "elapsed", None)

    runner = SimulationRunner(g, settings)

    def stop_after_delay():
        import time; time.sleep(0.1)
        runner.stop()

    t = threading.Thread(target=stop_after_delay)
    t.start()
    try:
        runner.run()
    except Exception as e:
        assert "aborted" in str(e).lower() or "stopped" in str(e).lower()
    t.join()
```

---

### Step 5.6 — Verification check

```bash
pytest tests/test_engine/ -v
# Expected: all engine tests pass

python -c "
from hydrosim.model.graph import ModelGraph
from hydrosim.model.elements.constant import Constant
from hydrosim.model.elements.waterstore import WaterStore
from hydrosim.model.elements.timehistory import TimeHistoryResult
from hydrosim.model.base import Connection, SimulationSettings
from hydrosim.engine.runner import SimulationRunner

g = ModelGraph()
c  = Constant(name='Rain', value=5.0)
ws = WaterStore(name='Store', initial_storage=100, upper_bound=200)
th = TimeHistoryResult(name='Plot')
for el in [c, ws, th]: g.add_element(el)
g.add_connection(Connection('', c.id, 'value', ws.id, 'inflow'))
g.add_connection(Connection('', ws.id, 'storage', th.id, 'series_1'))

settings = SimulationSettings(0, 10, 1.0, 'elapsed', None)
results = SimulationRunner(g, settings).run()
series = results.get_series_by_name('Store', 'storage')
print(f'Final storage after 10 days: {series[-1]:.1f} mm (expected 150.0)')
assert abs(series[-1] - 150.0) < 1e-6
print('Full simulation smoke test PASSED')
"
```

---

## Phase 6 — PyQt6 Application Shell

**Goal:** The application launches, shows a properly structured window with all zones visible.  
**Read first:** Design System §6 (layout), §7 (menu bar), §8 (toolbar), §15 (status bar), PRD §14  
**Produces:** `python -m hydrosim` opens the main window with correct layout and styling

---

### Step 6.1 — Load fonts and configure HiDPI

File: `hydrosim/__main__.py`

```python
import sys
import os
from pathlib import Path

def main():
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QFontDatabase
    from PyQt6.QtCore import Qt

    app = QApplication(sys.argv)
    app.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # Load bundled fonts
    fonts_dir = Path(__file__).parent / "resources" / "fonts"
    for font_file in fonts_dir.glob("*.ttf"):
        QFontDatabase.addApplicationFont(str(font_file))

    # Apply stylesheet
    qss_path = Path(__file__).parent / "gui" / "styles" / "stylesheet.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text())

    from hydrosim.gui.main_window import MainWindow
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
```

---

### Step 6.2 — Write stylesheet.qss

File: `hydrosim/gui/styles/stylesheet.qss`

Write the complete QSS stylesheet from Design System §24.1. Must include rules for:
- `QMainWindow` — background `#F5F6FA`
- `QDialog` — background `#FFFFFF`
- `QPushButton` — base style with radius 6px
- `QPushButton[primary="true"]` — blue primary
- `QLineEdit` — border, focus ring
- `QScrollBar` — custom scrollbar (10px wide, rounded thumb)
- `QMenuBar` — background `#FFFFFF`, border-bottom
- `QMenu` — rounded 8px, shadow

---

### Step 6.3 — Implement MainWindow skeleton

File: `hydrosim/gui/main_window.py`

Implement the main window with correct zone layout but placeholder content:

```python
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HydroSim — Untitled")
        self.setMinimumSize(1280, 768)

        # Central widget with vertical layout
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Add zones (placeholder labels for now)
        self._menu_bar  = self._build_menu_bar()      # returns QMenuBar
        self._toolbar   = self._build_toolbar()        # returns QWidget
        self._body      = self._build_body()           # returns QWidget (HBox)
        self._statusbar = self._build_status_bar()     # returns QWidget

        layout.addWidget(self._toolbar)
        layout.addWidget(self._body, stretch=1)
        layout.addWidget(self._statusbar)
        self.setMenuBar(self._menu_bar)
```

Each `_build_*` method returns the zone widget with correct height, background colour, and border — but with placeholder content (e.g., a QLabel "Canvas goes here").

Use exact heights from Design System §4.1:
- Menu bar: 32px (set via `QMenuBar`)
- Toolbar: 48px (set via `setFixedHeight(48)`)
- Status bar: 28px (set via `setFixedHeight(28)`)

---

### Step 6.4 — Implement MenuBar

Implement the menu bar using `QMenuBar` with the exact menu structure from App Flow §14.2:

```
File: New (Ctrl+N), Open (Ctrl+O), Save (Ctrl+S), Save As (Ctrl+Shift+S), ---,
      Recent Models (submenu), ---, Exit (Ctrl+Q)
Simulation: Simulation Settings (Ctrl+T), Run (F5), Stop (Esc), ---,
            Clear Results
View: Zoom In (Ctrl+=), Zoom Out (Ctrl+-), Zoom to Fit (Ctrl+Shift+F),
      Reset Zoom (Ctrl+0), ---, Show Simulation Log (toggle)
Help: Documentation, About HydroSim
```

Style the menu bar to match Design System §7:
- Brand logo + "HydroSim" text on the left
- Menu items with 5px 10px padding, 5px radius, hover `#EEF0F4`
- Dropdowns with 8px radius, shadow

Connect actions to placeholder slots (e.g., `self._on_new()`, `self._on_open()`) — leave slots as `pass` for now. They get connected in Phase 11.

---

### Step 6.5 — Implement Toolbar

Implement the toolbar widget matching Design System §8:

- New, Open, Save buttons (`.tbtn` style from Design System)
- Divider (1px `#E3E6EC`, 24px tall)
- Run button (green `#43A047`, 0 16px padding, play triangle icon)
- Stop button (red border, disabled styling)
- Spacer (`QWidget` with expanding size policy)
- Meta text: `Δt = 1 day · 365 steps` (Fira Code, 12px, grey)
- Run progress bar: 2px `#2E86C1` absolute at bottom of toolbar (hidden by default)

Run/Stop button states managed by `set_simulation_state(state: str)` method on toolbar:
- `"idle"`: Run enabled, Stop disabled
- `"running"`: Run disabled, Stop enabled; show progress bar
- `"complete"`: Run enabled, Stop disabled; hide progress bar

---

### Step 6.6 — Implement StatusBar

Implement the status bar widget matching Design System §15:

Left zone: logo SVG + model name (bold) + separator dot + element count  
Centre zone: status pill (absolute centred)  
Right zone: zoom control `[−] [100%] [+]`

Status pill states from Design System §15.2 — implement `set_sim_state(state, step=0, elapsed="")` method.

Zoom control emits `zoom_changed(float)` signal.

---

### Step 6.7 — Verification check

```bash
python -m hydrosim
# Expected: main window opens with correct layout
# Manual verify: all 4 zones visible, correct background colours,
#               menu bar has File/Simulation/View/Help menus,
#               Run button is green, Stop button is grey/disabled,
#               window title is "HydroSim — Untitled"
# Close the window — no errors in terminal

python -c "
import sys
from PyQt6.QtWidgets import QApplication
from hydrosim.gui.main_window import MainWindow
app = QApplication(sys.argv)
w = MainWindow()
w.show()
print('MainWindow created successfully')
app.quit()
"
```

---

## Phase 7 — Canvas: Element Cards & Palette

**Goal:** Elements can be dragged from the palette onto the canvas and displayed as correct cards.  
**Read first:** Design System §9 (palette), §10 (canvas), §11 (element cards), §12 (ports), §14 (icons)  
**Produces:** Drag-and-drop element placement, correctly styled cards for all 5 element types

---

### Step 7.1 — Implement HydroScene and HydroView

**HydroView** (`hydrosim/gui/canvas/view.py`):
- Subclass `QGraphicsView`
- Enable antialiasing: `setRenderHint(QPainter.RenderHint.Antialiasing)`
- Set drag mode: `QGraphicsView.DragMode.NoDrag` (we handle drag manually)
- Implement `wheelEvent()` for zoom toward cursor (see Design System §10.5)
- Implement space+drag for pan
- Accept drops: `setAcceptDrops(True)`, implement `dragEnterEvent`, `dropEvent`

**HydroScene** (`hydrosim/gui/canvas/scene.py`):
- Subclass `QGraphicsScene`
- Override `drawBackground()` for dot grid (see Design System §10.2)
- `add_element(element, position)` — creates `ElementItem`, adds to scene
- `remove_element(element_id)` — removes item and its connections
- `element_items: dict[str, ElementItem]` — tracks all items by element ID
- Signals: `element_added(str)`, `element_removed(str)`, `element_moved(str, float, float)`, `connection_requested(str, str, str, str)` (from_id, from_port, to_id, to_port)

---

### Step 7.2 — Implement ElementItem

File: `hydrosim/gui/canvas/element_item.py`

Subclass `QGraphicsItem`. This is the most complex single component.

**Constructor:**
```python
def __init__(self, element: ElementBase):
    super().__init__()
    self.element = element
    self._port_items: dict[str, PortItem] = {}

    self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
    self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
    self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
    self.setAcceptHoverEvents(True)
    self.setPos(element.position[0], element.position[1])
    self.setZValue(1)   # above connection lines

    self._create_port_items()
    self._setup_drop_shadow()
```

**`boundingRect()`:** `QRectF(0, 0, CARD_WIDTH, self._compute_height())`

`_compute_height()` = `CARD_TOP_BAR_H + head_height + divider_height + body_height`
- `head_height` ≈ 50px (icon + name + id)
- `body_height` = content_height + `PORT_ROW_HEIGHT * max(in_count, out_count)`

**`paint(painter, option, widget)`** — paint in this order:
1. `_paint_background(painter)` — white rounded rect with border (category colour if selected, else `#E5E7EB`)
2. `_paint_category_bar(painter)` — 4px solid rect at top in category colour
3. `_paint_head(painter)` — icon (22px) + name + ID
4. `_paint_divider(painter)` — 1px `#ECEEF2` horizontal line
5. `_paint_body_content(painter)` — type-specific content (value preview, formula preview, storage bar, sparkline)
6. Port items are separate `QGraphicsItem` children — they paint themselves

**Drop shadow** via `QGraphicsDropShadowEffect`:
```python
shadow = QGraphicsDropShadowEffect()
shadow.setBlurRadius(12)
shadow.setOffset(0, 4)
shadow.setColor(QColor(0, 0, 0, 26))   # rgba(0,0,0,0.10)
self.setGraphicsEffect(shadow)
```

**`_paint_body_content(painter)`** — switch on `self.element.__class__.__name__`:
- `Constant`: draw value in Fira Code, 13px (e.g., `"0.30"`)
- `TimeSeries`: draw `"mm/day"` + `"daily series"` labels
- `Expression`: draw formula tokens with syntax colouring (green for element refs, grey for operators)
- `WaterStore`: draw mini storage bar (see Design System §11.5)
- `TimeHistoryResult`: draw sparkline SVG path using QPainterPath

**State changes:**
- `set_selected(bool)` — triggers repaint with blue border
- `set_has_results(bool)` — shows/hides green dot in top-right
- `set_error(bool, message)` — shows/hides red border + warning triangle

**`itemChange()`:** emit scene's `element_moved` signal when position changes.

---

### Step 7.3 — Implement PortItem

File: `hydrosim/gui/canvas/port_item.py`

Subclass `QGraphicsEllipseItem`. Position as child of `ElementItem`.

```python
class PortItem(QGraphicsEllipseItem):
    def __init__(self, port: Port, element_item: ElementItem):
        # Positioned at element card edge, centred on port row
        size = PORT_DIAMETER
        super().__init__(-size/2, -size/2, size, size, parent=element_item)
        self.port = port
        self.element_item = element_item
        self._connected = False
        self.setAcceptHoverEvents(True)
        self._update_style()

    def _update_style(self):
        cat_color = QColor(CAT_COLOURS[...])
        if self.port.port_type == PortType.OUTPUT:
            self.setBrush(QBrush(cat_color))
            self.setPen(Qt.PenStyle.NoPen)
        else:  # INPUT
            if self._connected:
                self.setBrush(QBrush(cat_color))
            else:
                self.setBrush(QBrush(QColor("white")))
                self.setPen(QPen(cat_color, 1.5))

    def hoverEnterEvent(self, event):
        # Scale to PORT_HOVER_DIAMETER, show tooltip
        self.setRect(-PORT_HOVER_DIAMETER/2, -PORT_HOVER_DIAMETER/2,
                     PORT_HOVER_DIAMETER, PORT_HOVER_DIAMETER)

    def hoverLeaveEvent(self, event):
        self.setRect(-PORT_DIAMETER/2, -PORT_DIAMETER/2,
                     PORT_DIAMETER, PORT_DIAMETER)
```

Port positions (relative to parent ElementItem):
- Input ports: `x = -PORT_DIAMETER/2` (left edge), `y = card_y_for_port_row`
- Output ports: `x = CARD_WIDTH - PORT_DIAMETER/2` (right edge), same y calculation

---

### Step 7.4 — Implement PalettePanel

File: `hydrosim/gui/palette/palette_panel.py`

Match Design System §9 exactly:

- Search bar with magnifier icon at top
- Collapsible category sections (click header to toggle)
- Each category header: category colour text, 9px swatch square, chevron
- Each palette item: icon + name (bold 12.5px) + description (10.5px grey)
- Items are draggable: set `setDragEnabled` or implement `mouseMoveEvent` with `QDrag`
- Drag data: set MIME type `application/x-hydrosim-element-type` with element type name as string

Connect search input to filter method that shows/hides items matching query.

---

### Step 7.5 — Wire palette drag-drop to canvas

In `HydroView.dropEvent(event)`:
1. Read element type from MIME data
2. Convert drop position to scene coordinates: `self.mapToScene(event.position().toPoint())`
3. Create element with default parameters at that position
4. Call `scene.add_element(element, scene_pos)`
5. Open property dialog immediately after placement

In `MainWindow`, connect `scene.element_added` to update the status bar element count.

---

### Step 7.6 — Verification check

```bash
python -m hydrosim
# Manual verify:
# 1. Palette shows 4 categories: INPUT (green), STOCK (blue), EXPRESSION (teal), RESULT (orange)
# 2. Each category has correct elements listed
# 3. Search box filters elements as you type
# 4. Drag a Constant from palette → drop on canvas → card appears
# 5. Drag a WaterStore → card shows correct ports (inflow, outflow left; storage, overflow, deficit right)
# 6. Cards show correct category colour bar at top
# 7. Element name and ID shown in card head
# 8. Canvas has dot grid background
# 9. Scroll to zoom in/out
```

---

## Phase 8 — Canvas: Connections & Interactions

**Goal:** Users can draw connections between elements; connections render as bezier curves.  
**Read first:** Design System §13 (connection arrows), §10.4 (canvas interactions)  
**Produces:** Full drag-connect interaction, correct bezier rendering, element deletion

---

### Step 8.1 — Implement ConnectionItem

File: `hydrosim/gui/canvas/connection_item.py`

```python
class ConnectionItem(QGraphicsPathItem):
    def __init__(self, connection: Connection,
                 from_port_item: PortItem, to_port_item: PortItem):
        super().__init__()
        self.connection = connection
        self.from_port_item = from_port_item
        self.to_port_item   = to_port_item
        self.setZValue(-1)   # behind element cards
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        self._update_path()

    def _update_path(self):
        """Recalculate bezier path from current port positions."""
        start = self.from_port_item.scenePos()
        end   = self.to_port_item.scenePos()
        path  = self._build_bezier(start, end)
        self.setPath(path)
        self._update_style()

    def _build_bezier(self, start: QPointF, end: QPointF) -> QPainterPath:
        """Cubic bezier departing rightward from start, arriving leftward at end."""
        offset = CONN_CTRL_OFFSET
        path = QPainterPath()
        path.moveTo(start)
        path.cubicTo(
            QPointF(start.x() + offset, start.y()),
            QPointF(end.x()   - offset, end.y()),
            end
        )
        return path

    def _update_style(self):
        cat = CAT_OF_TYPE[self.connection_category]
        color = QColor(CAT_COLOURS[cat])
        color.setAlphaF(0.8)
        width = CONN_SELECTED_WIDTH if self.isSelected() else CONN_STROKE_WIDTH
        self.setPen(QPen(color, width))

    def update_positions(self):
        """Called when either connected element moves."""
        self._update_path()
```

Draw arrowhead as a `QPolygonF` child item at the destination end.

Call `connection_item.update_positions()` from `ElementItem.itemChange()` when position changes — all connections attached to that element must update.

---

### Step 8.2 — Implement connection drawing interaction

In `HydroScene`, implement the connection draw workflow:

**Mouse events on PortItem:**
1. `mousePressEvent` on an output port: begin connection drag
   - Create a temporary `QGraphicsPathItem` (the "rubber band" line)
   - Set `self._dragging_from_port = port_item`
2. `mouseMoveEvent` on scene: update rubber band line to cursor
   - Check if cursor is over a compatible input port → highlight green
   - Highlight incompatible ports red
3. `mouseReleaseEvent` on scene: 
   - If released over compatible input port → emit `connection_requested` signal
   - Else → cancel, remove rubber band

**Compatibility check:**
- Target must be an INPUT port
- Target must not already be connected
- Source and target cannot be on the same element
- Would not create a cycle (call `graph.has_cycle()` check)

**In `MainWindow`**, connect `scene.connection_requested(from_id, from_port, to_id, to_port)` to:
1. Create `Connection` object
2. Call `graph.add_connection(connection)`
3. Create `ConnectionItem` and add to scene

---

### Step 8.3 — Implement element selection and deletion

**Selection:**
- Click on element card: select it (deselect others)
- Click on empty canvas: deselect all
- Rubber-band drag on empty canvas: select multiple elements
- Shift+click: add to selection

**Deletion:**
- `keyPressEvent` in `HydroView`: if `Qt.Key.Key_Delete` and items selected:
  - Show confirmation dialog: "Delete N element(s) and their connections?"
  - If confirmed: call `graph.remove_element()` for each, remove `ElementItem` and connected `ConnectionItem` instances from scene

**Moving:**
- Elements are already movable via `ItemIsMovable` flag
- After move, emit `element_moved` signal → `graph` element position updated

---

### Step 8.4 — Verification check

```bash
python -m hydrosim
# Manual verify:
# 1. Place a Constant and a WaterStore on canvas
# 2. Hover over Constant output port → port grows, tooltip appears
# 3. Drag from Constant output port → rubber band line follows cursor
# 4. Hover over WaterStore inflow port → port glows green (compatible)
# 5. Release on inflow port → bezier connection arrow appears
# 6. Connection is category colour (green for Constant output)
# 7. Arrowhead visible at destination end
# 8. Move one element → connection updates dynamically
# 9. Click connection to select → turns blue
# 10. Select element → press Delete → confirmation dialog → element and connections removed
```

---

## Phase 9 — Property Dialogs

**Goal:** Double-clicking any element opens its correctly styled property dialog.  
**Read first:** Design System §16–18 (dialogs), PRD §12 (dialog specs)  
**Produces:** All 5 property dialogs working, changes applied to model on OK

---

### Step 9.1 — Implement base dialog structure

Create a `BaseElementDialog(QDialog)` in `hydrosim/gui/dialogs/__init__.py`:

```python
class BaseElementDialog(QDialog):
    def __init__(self, element: ElementBase, parent=None):
        super().__init__(parent)
        self.element = element
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_header())
        layout.addWidget(self._build_body(), stretch=1)
        layout.addWidget(self._build_footer())

    def _build_header(self) -> QWidget:
        """Icon + title + subtitle + close button. Matches Design System §16.3."""

    def _build_footer(self) -> QWidget:
        """Cancel + OK buttons. Matches Design System §16.5."""

    def _build_body(self) -> QWidget:
        """Override in subclasses."""
        raise NotImplementedError

    def apply_changes(self) -> None:
        """Override in subclasses — write dialog values back to element."""
        raise NotImplementedError
```

Dialog animation: use `QPropertyAnimation` on `windowOpacity` (0→1, 140ms) for fade-in on open.

---

### Step 9.2 — Implement ConstantDialog

File: `hydrosim/gui/dialogs/constant_dialog.py`

Fields: Name, Description, Value (QDoubleSpinBox with scientific notation), Units (with autocomplete from common units list).

On OK: validate name uniqueness in graph, validate value is finite, call `apply_changes()` which updates `element.name`, `element.value`, `element.units`. Rebuild element card display.

---

### Step 9.3 — Implement TimeSeriesDialog

File: `hydrosim/gui/dialogs/timeseries_dialog.py`

Fields: Name, Description, Units, Data Type (QComboBox), Interpolation (QComboBox).

Data table: `QTableWidget` with 2 columns (Time, Value). Buttons: Add Row, Delete Row, Import CSV, Clear All.

**Import CSV button:**
1. `QFileDialog.getOpenFileName()` with `*.csv` filter
2. Parse with `pandas.read_csv()`
3. Preview first 5 rows in a confirmation dialog
4. On confirm: populate table widget

Mini preview chart below table: embed small `pyqtgraph.PlotWidget` (80px tall) showing the data as a line. Updates live as data changes.

---

### Step 9.4 — Implement WaterStoreDialog

File: `hydrosim/gui/dialogs/waterstore_dialog.py`

Implement the storage indicator bar matching Design System §17.2:
- `QFrame` subclass with custom `paintEvent()`
- Blue gradient fill (`#4aa3da` → `#2E86C1`)
- Fill width = `(initial - lower) / (upper - lower) * total_width`
- Value label inside fill in white Fira Code 11px bold
- Scale labels below: `"0 mm"`, `"initial X of Y mm"`, `"150 mm"`

The storage indicator updates live as the user changes the value spinboxes.

---

### Step 9.5 — Implement ExpressionDialog

File: `hydrosim/gui/dialogs/expression_dialog.py`

The formula editor (Design System §18.2) — implement as `QWidget` with:
- Gutter bar at top (grey label `"ƒ(x) · expression"`)
- Line numbers column (grey `QLabel`)
- Code editor: `QTextEdit` with `setFont(QFont("Fira Code", 13))`

Syntax highlighting: subclass `QSyntaxHighlighter`. Apply colour rules:
- Element names (green `#4CAF82`)
- Operators `*+-/^` (grey `#8A93A0`)
- Numbers (purple `#7B68C8`)
- Function names `sqrt|abs|log|...` (teal `#00897B`)

Available elements chips: `QFlowLayout` (implement simple horizontal wrapping layout) with clickable chip widgets. Clicking a chip inserts its text at cursor in the formula editor.

Live validation: connect `textChanged` signal of formula editor → `ExpressionParser.validate_syntax()` → show/hide error label below editor.

Test button: calls `element.evaluate_test()` with dummy values (0.0 for each input), shows result pill.

---

### Step 9.6 — Implement TimeHistoryResultDialog

File: `hydrosim/gui/dialogs/timehistory_dialog.py`

Fields: Name, Description, Chart Title, Y-axis Label, Y-axis Units, Show Grid (QCheckBox), Y-axis Min/Max (with "Auto" checkbox for each).

Connected series list: read-only `QListWidget` showing `"ElementName.port_name"` for each connected input port. Informational only.

---

### Step 9.7 — Wire dialogs to canvas

In `MainWindow`, handle scene's `element_double_clicked(element)` signal:

```python
def _on_element_double_clicked(self, element: ElementBase):
    dialog_class = {
        "Constant":          ConstantDialog,
        "TimeSeries":        TimeSeriesDialog,
        "WaterStore":        WaterStoreDialog,
        "Expression":        ExpressionDialog,
        "TimeHistoryResult": TimeHistoryResultDialog,
    }.get(element.__class__.__name__)

    if dialog_class:
        dialog = dialog_class(element, self._graph, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            dialog.apply_changes()
            # Refresh canvas card
            self._scene.update_element_card(element.id)
            # Mark model as modified
            self._set_modified(True)
```

---

### Step 9.8 — Verification check

```bash
python -m hydrosim
# Manual verify for each element type:
# 1. Place element → dialog opens automatically (correct dialog, correct title)
# 2. Change name → card title updates on canvas
# 3. Cancel → no changes applied
# 4. WaterStore: change initial storage → storage bar updates live
# 5. Expression: type formula → syntax highlighting appears
# 6. Expression: type invalid formula → red error message appears below
# 7. Expression: click Test → result pill appears with computed value
# 8. TimeSeries: Import CSV → preview → data table populates
# 9. TimeSeries: mini chart updates when data changes
# 10. All dialogs: OK button disabled when validation errors present
```

---

## Phase 10 — Result Viewer & Hydrograph

**Goal:** The TimeHistoryResult viewer opens and displays a correctly styled hydrograph.  
**Read first:** Design System §19 (result viewer), §20 (hydrograph chart), PRD §13  
**Produces:** Draggable result window with interactive PyQtGraph hydrograph

---

### Step 10.1 — Implement HydrographWidget

File: `hydrosim/gui/results/hydrograph_widget.py`

```python
import pyqtgraph as pg

class HydrographWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._plot = pg.PlotWidget()
        self._curves: list[pg.PlotDataItem] = []
        self._setup_plot()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._plot)

    def _setup_plot(self):
        """Configure PyQtGraph plot to match Design System §20."""
        self._plot.setBackground('#FFFFFF')
        self._plot.showGrid(x=True, y=True, alpha=0.3)

        # Axis labels — Inter 11.5px bold
        label_style = {'color': TEXT_PRIMARY, 'font-size': '11pt',
                       'font-family': FONT_UI, 'font-weight': '600'}
        self._plot.setLabel('left',   '', **label_style)
        self._plot.setLabel('bottom', 'Time (days)', **label_style)

        # Tick font — Fira Code
        tick_font = QFont(FONT_MONO, 10)
        self._plot.getAxis('left').setTickFont(tick_font)
        self._plot.getAxis('bottom').setTickFont(tick_font)
        self._plot.getAxis('left').setTextPen(QColor(TEXT_SECONDARY))
        self._plot.getAxis('bottom').setTextPen(QColor(TEXT_SECONDARY))

        # Crosshair
        self._vline = pg.InfiniteLine(angle=90, movable=False,
                                      pen=pg.mkPen('#C2C7D0', width=1))
        self._hline = pg.InfiniteLine(angle=0,  movable=False,
                                      pen=pg.mkPen('#C2C7D0', width=1))
        self._plot.addItem(self._vline, ignoreBounds=True)
        self._plot.addItem(self._hline, ignoreBounds=True)
        self._plot.scene().sigMouseMoved.connect(self._on_mouse_moved)

    def plot_series(self, time: np.ndarray, values: np.ndarray,
                    label: str, color: str):
        """Add a time series to the chart."""
        pen = pg.mkPen(color=color, width=1.8)
        # Area fill
        fill_color = QColor(color)
        fill_color.setAlphaF(0.18)
        curve = self._plot.plot(x=time, y=values, pen=pen,
                                fillLevel=0, brush=pg.mkBrush(fill_color),
                                name=label)
        self._curves.append(curve)
        self._plot.addLegend()

    def clear(self):
        for curve in self._curves:
            self._plot.removeItem(curve)
        self._curves.clear()

    def _on_mouse_moved(self, pos):
        """Update crosshair position."""
        if self._plot.sceneBoundingRect().contains(pos):
            mouse_point = self._plot.getViewBox().mapSceneToView(pos)
            self._vline.setPos(mouse_point.x())
            self._hline.setPos(mouse_point.y())
```

---

### Step 10.2 — Implement ResultViewerWindow

Draggable floating window matching Design System §19:

```python
class ResultViewerWindow(QWidget):
    def __init__(self, element: TimeHistoryResult,
                 results: ResultsStore, parent=None):
        super().__init__(parent,
            Qt.WindowType.Window |
            Qt.WindowType.FramelessWindowHint)
        self.element = element
        self.results = results
        self.resize(800, 500)
        self._setup_ui()
        self._populate_chart()
        self._drag_offset = None

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_title_bar())
        layout.addWidget(self._build_legend_bar())
        layout.addWidget(self._hydrograph := HydrographWidget(), stretch=1)
        layout.addWidget(self._build_chart_toolbar())
        self._apply_styling()

    def _build_title_bar(self):
        """Coral dot + title + [Export CSV] + [×]. Draggable."""

    def _build_chart_toolbar(self):
        """Home + Pan + Zoom + separator + Save PNG buttons. Matching Design System §19.4."""

    def _populate_chart(self):
        """Read results and plot each connected series."""
        colours = [CAT_STOCK, CAT_RESULT, CAT_INPUT, CAT_EXPR,
                   "#7B68C8", "#E8A020", "#E53935", "#795548"]
        for i, (port_name, _) in enumerate(self.element.input_ports.items()):
            conns = self.results.get_connections_to_port(...)
            # ... resolve and plot each series

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event):
        if self._drag_offset:
            new_pos = event.globalPosition().toPoint() - self._drag_offset
            self.move(max(0, new_pos.x()), max(0, new_pos.y()))

    def mouseReleaseEvent(self, event):
        self._drag_offset = None
```

---

### Step 10.3 — Wire result viewer to canvas

In `MainWindow._on_element_double_clicked()`:
- If element is `TimeHistoryResult` AND results are available:
  - Create `ResultViewerWindow(element, self._results)`, show it
- If no results available:
  - Show brief status bar message: `"Run simulation first to view results"`

Track open viewer windows so they can be updated when simulation re-runs.

---

### Step 10.4 — Verification check

```bash
python -m hydrosim
# Manual verify:
# 1. Load example model (File → Open → simple_water_balance.hydrosim)
# 2. Double-click Storage_Plot element
# 3. Message "Run simulation first" appears in status bar
# 4. Run the simulation
# 5. Double-click Storage_Plot → result viewer window opens
# 6. Hydrograph shows soil moisture curve (sinusoidal-ish seasonal pattern)
# 7. Crosshair follows mouse, correct time/value in tooltip
# 8. Drag title bar → window moves
# 9. Export CSV → file picker → CSV saved
# 10. Close window → no errors
```

---

## Phase 11 — Simulation Integration & Run Flow

**Goal:** The full Run → Progress → Results → View cycle works end-to-end from the GUI.  
**Read first:** App Flow §8 (running simulation), Backend Schema §13 (data flow)  
**Produces:** Complete working simulation triggered from GUI toolbar

---

### Step 11.1 — Implement SimulationThread

File: `hydrosim/engine/runner.py` (add class at bottom)

```python
from PyQt6.QtCore import QThread, pyqtSignal

class SimulationThread(QThread):
    """Runs SimulationRunner in a background thread."""
    progress   = pyqtSignal(float)      # 0.0–1.0
    finished   = pyqtSignal(object)     # emits ResultsStore
    error      = pyqtSignal(str)        # emits error message

    def __init__(self, graph: ModelGraph, settings: SimulationSettings):
        super().__init__()
        self._runner = SimulationRunner(graph, settings)

    def run(self):
        try:
            results = self._runner.run(
                progress_callback=lambda p: self.progress.emit(p)
            )
            self.finished.emit(results)
        except SimulationAborted:
            # Not an error — user stopped it
            pass
        except Exception as e:
            self.error.emit(str(e))

    def stop(self):
        self._runner.stop()
```

---

### Step 11.2 — Wire Run button to simulation thread

In `MainWindow`, implement `_on_run()`:

```python
def _on_run(self):
    # 1. Validate model — show dialog if errors
    validator = ModelValidator(self._graph)
    errors = validator.validate_all()
    if errors:
        self._show_validation_dialog(errors)
        return

    # 2. Pre-run: save autosave, set UI state
    self._autosave()
    self._set_simulation_state("running")
    self._results = None

    # 3. Clear existing result viewers
    for viewer in self._result_viewers.values():
        viewer.close()
    self._result_viewers.clear()

    # 4. Start thread
    self._sim_thread = SimulationThread(self._graph, self._settings)
    self._sim_thread.progress.connect(self._on_sim_progress)
    self._sim_thread.finished.connect(self._on_sim_finished)
    self._sim_thread.error.connect(self._on_sim_error)
    self._sim_thread.start()

def _on_sim_progress(self, progress: float):
    self._toolbar.set_progress(progress)
    step = int(progress * self._settings.n_steps)
    self._statusbar.set_sim_state("running", step=step)

def _on_sim_finished(self, results: ResultsStore):
    self._results = results
    self._set_simulation_state("complete")
    elapsed = f"{results.run_duration_s:.2f}s"
    self._statusbar.set_sim_state("complete", elapsed=elapsed)
    # Mark all TimeHistoryResult cards as having results
    for el in self._graph.elements.values():
        if isinstance(el, TimeHistoryResult):
            self._scene.set_element_has_results(el.id, True)

def _on_sim_error(self, message: str):
    self._set_simulation_state("idle")
    QMessageBox.critical(self, "Simulation Error", message)

def _on_stop(self):
    if self._sim_thread:
        self._sim_thread.stop()
        self._set_simulation_state("idle")
```

---

### Step 11.3 — Implement validation error dialog

```python
def _show_validation_dialog(self, errors: list[ValidationError]):
    dialog = QDialog(self)
    dialog.setWindowTitle("Model Errors")
    # ... list errors with "Go to element" buttons
    # Clicking "Go to element" closes dialog, centres canvas on element,
    # opens property dialog
```

---

### Step 11.4 — Implement file operations

Wire all File menu actions:

**New:** `_on_new()` — check unsaved changes → create fresh `ModelGraph` → clear scene → reset title

**Open:** `_on_open()` — `QFileDialog.getOpenFileName(filter="HydroSim Files (*.hydrosim)")` → `ModelSerialiser.load()` → rebuild scene from graph

**Save:** `_on_save()` — if no current file path, call `_on_save_as()`, else `ModelSerialiser.save()`

**Save As:** `_on_save_as()` — `QFileDialog.getSaveFileName()` → `ModelSerialiser.save()`

**Modified tracking:** set window title `"HydroSim — {model_name}*"` (asterisk) when model changes. Connect all `ModelGraph` mutation signals to `_set_modified(True)`.

---

### Step 11.5 — Implement simulation settings dialog

`QDialog` with fields for start time, end time, dt, time mode. Updates `self._settings` on OK. Shows computed `n_steps` and estimated runtime.

---

### Step 11.6 — Create example model file

Create `hydrosim/resources/examples/simple_water_balance.hydrosim` using the exact JSON structure from PRD §9. The model must match the example described in App Flow §12 (5 elements, 3 connections, 365-day simulation with dt=1 day).

Generate the file by building the model in Python and calling `ModelSerialiser.save()`:

```python
# scripts/generate_example.py
# Run this once to generate the example file
import numpy as np
# ... build the 5-element model with synthetic rainfall data (np.random.seed(42))
# ... save to hydrosim/resources/examples/simple_water_balance.hydrosim
```

---

### Step 11.7 — Verification check (complete end-to-end)

```bash
python -m hydrosim
# Complete manual verification:
# 1. Launch → welcome dialog appears
# 2. Click "Open Example Model" → canvas populates with 5 elements
# 3. Model name in title bar: "Simple Water Balance"
# 4. Click Run → progress bar fills across toolbar bottom
# 5. Status bar shows "Running… step N / 365" with animated dot
# 6. Simulation completes in < 1 second
# 7. Status bar shows "Simulation complete — 365 steps in 0.Xs"
# 8. Storage_Plot card shows green dot + sparkline preview
# 9. Double-click Storage_Plot → result viewer opens
# 10. Hydrograph shows realistic soil moisture curve
# 11. File → Save As → save to a new location
# 12. File → New → unsaved changes dialog appears
# 13. Open the saved file → model restored correctly
# 14. Re-run simulation → same results

pytest tests/ -v
# Expected: all tests pass
```

---

## Phase 12 — Polish, Example Model & Packaging

**Goal:** App is production-ready for Phase 1 release. All acceptance criteria from PRD §18 pass.  
**Read first:** PRD §18 (acceptance criteria), PRD §19 (out of scope confirmation)  
**Produces:** Installable package passing all 14 acceptance criteria

---

### Step 12.1 — Add autosave

Implement autosave via `QTimer` in `MainWindow`:
- Timer fires every 5 minutes (`300_000` ms)
- If `self._modified` is True: save to `~/.hydrosim/autosave/{model_name}_autosave.hydrosim`
- Create `~/.hydrosim/` directory if it doesn't exist
- On launch: check for autosave files and offer to restore (see App Flow §11.3)

---

### Step 12.2 — Add keyboard shortcuts

Ensure all shortcuts from App Flow §14 are wired in `MainWindow`:

```python
# In _build_menu_bar() — QAction shortcut method:
new_action.setShortcut(QKeySequence("Ctrl+N"))
open_action.setShortcut(QKeySequence("Ctrl+O"))
save_action.setShortcut(QKeySequence("Ctrl+S"))
run_action.setShortcut(QKeySequence("F5"))

# In HydroView.keyPressEvent():
if event.key() == Qt.Key.Key_Delete: self._delete_selected()
if event.key() == Qt.Key.Key_Escape: self._cancel_connection_drag()
if (event.modifiers() == Qt.KeyboardModifier.ControlModifier
        and event.key() == Qt.Key.Key_A):
    self._scene.selectAll()
```

---

### Step 12.3 — Add zoom to fit

Implement `_zoom_to_fit()` in `MainWindow`:
```python
def _zoom_to_fit(self):
    items_rect = self._scene.itemsBoundingRect()
    self._view.fitInView(items_rect.adjusted(-40, -40, 40, 40),
                         Qt.AspectRatioMode.KeepAspectRatio)
```

---

### Step 12.4 — Add model modified indicator

- Window title shows asterisk `*` when unsaved changes exist
- Implement `_set_modified(True/False)` in `MainWindow`
- Connect to: element add/remove, connection add/remove, property dialog OK, element move (on mouseRelease, not every pixel)

---

### Step 12.5 — Add simulation log panel

Implement `QDockWidget` with `QPlainTextEdit` (read-only, Fira Code 11px):
- Dockable at the bottom of the window
- Auto-shows when simulation starts
- Receives log messages via Python `logging` module
- Format: `[HH:MM:SS] message`
- Log: simulation start, settings summary, execution order, completion time, water balance warnings

---

### Step 12.6 — Write final integration tests

`tests/test_engine/test_runner.py` — add the complete integration test from PRD §17.2:

```python
def test_full_example_model_runs(tmp_path):
    """AC-12: The example model loads and runs correctly."""
    from pathlib import Path
    example_path = (Path(__file__).parent.parent.parent /
                    "hydrosim" / "resources" / "examples" /
                    "simple_water_balance.hydrosim")
    assert example_path.exists(), "Example model file not found"

    graph, settings, _ = ModelSerialiser.load(example_path)
    assert graph.element_count == 5
    assert len(graph.connections) == 3

    runner = SimulationRunner(graph, settings)
    results = runner.run()

    assert results.is_complete
    assert results.completed_steps == settings.n_steps

    storage = results.get_series_by_name("SoilMoisture", "storage")
    assert len(storage) == settings.n_steps
    assert np.all(storage >= 0)
    assert np.all(storage <= 150)
    print(f"Example model: storage range [{storage.min():.1f}, {storage.max():.1f}] mm")
```

---

### Step 12.7 — Run PRD acceptance criteria checklist

Run each check below. All must pass before Phase 12 is complete.

```bash
# AC-13: All unit tests pass
pytest tests/ -v --tb=short
# Expected: 0 failures

# AC-07: Water balance error < 1e-6
python -c "
from hydrosim.model.graph import ModelGraph
from hydrosim.model.elements.waterstore import WaterStore
from hydrosim.model.elements.constant import Constant
from hydrosim.model.elements.timehistory import TimeHistoryResult
from hydrosim.model.base import Connection, SimulationSettings
from hydrosim.engine.runner import SimulationRunner
import numpy as np

g = ModelGraph()
c  = Constant(name='R', value=3.7)
ws = WaterStore(name='S', initial_storage=80, lower_bound=0, upper_bound=150)
th = TimeHistoryResult(name='P')
for el in [c, ws, th]: g.add_element(el)
g.add_connection(Connection('', c.id, 'value', ws.id, 'inflow'))
g.add_connection(Connection('', ws.id, 'storage', th.id, 'series_1'))
settings = SimulationSettings(0, 365, 1.0, 'elapsed', None)
results = SimulationRunner(g, settings).run()
storage = results.get_series_by_name('S', 'storage')
# Water balance: ΔS = inflow * n_steps * dt
delta_s = storage[-1] - 80.0
expected = min(3.7 * 365, 150 - 80)   # capped at upper bound
print(f'Water balance check: delta_S = {delta_s:.8f}')
print('AC-07 PASS' if abs(delta_s - expected) < 1e-6 else 'AC-07 FAIL')
"

# AC-05: Save/load round-trip (run serialiser tests)
pytest tests/test_model/test_serialiser.py -v

# AC-12: Example model runs
pytest tests/test_engine/test_runner.py::test_full_example_model_runs -v
```

---

### Step 12.8 — Final launch verification

```bash
# Clean install test
pip install -e .
python -m hydrosim

# Verify all AC items manually:
# AC-01: Launches without errors ✓
# AC-02: All 5 elements placeable from palette ✓
# AC-03: Elements connectable by port drag ✓
# AC-04: All 5 dialogs open, validate, reject invalid input ✓
# AC-05: Save → load → identical model ✓
# AC-06: Simulation runs, hydrograph appears ✓
# AC-07: Water balance < 1e-6 ✓ (automated above)
# AC-08: Expression formula evaluates correctly ✓
# AC-09: TimeSeries STEP interpolation correct ✓
# AC-10: Circular dependency detected before run ✓
# AC-11: Export CSV produces valid file ✓
# AC-12: Example model loads and runs ✓
# AC-13: All tests pass ✓ (automated above)
# AC-14: No uncaught exceptions during normal operation ✓
```

---

## Appendix A — Quick Reference: File Ownership

| File | Phase implemented | Key class |
|---|---|---|
| `model/base.py` | 1 | `ElementBase`, `Port`, `Connection`, `SimState` |
| `model/elements/constant.py` | 2 | `Constant` |
| `model/elements/timeseries.py` | 2 | `TimeSeries` |
| `model/elements/waterstore.py` | 2 | `WaterStore` |
| `model/elements/expression.py` | 2 | `Expression` |
| `model/elements/timehistory.py` | 2 | `TimeHistoryResult` |
| `model/graph.py` | 3 | `ModelGraph` |
| `model/validator.py` | 4 | `ModelValidator` |
| `model/serialiser.py` | 4 | `ModelSerialiser` |
| `engine/parser.py` | 5 | `ExpressionParser` |
| `engine/results.py` | 5 | `ResultsStore` |
| `engine/solver.py` | 5 | `TimeStepSolver` |
| `engine/runner.py` | 5 + 11 | `SimulationRunner`, `SimulationThread` |
| `gui/styles/theme.py` | 0 | All design constants |
| `gui/styles/stylesheet.qss` | 6 | Global QSS |
| `gui/main_window.py` | 6 + 11 | `MainWindow` |
| `gui/canvas/scene.py` | 7 | `HydroScene` |
| `gui/canvas/view.py` | 7 | `HydroView` |
| `gui/canvas/element_item.py` | 7 | `ElementItem` |
| `gui/canvas/port_item.py` | 7 | `PortItem` |
| `gui/canvas/connection_item.py` | 8 | `ConnectionItem` |
| `gui/palette/palette_panel.py` | 7 | `PalettePanel` |
| `gui/dialogs/*.py` | 9 | All dialog classes |
| `gui/results/hydrograph_widget.py` | 10 | `HydrographWidget`, `ResultViewerWindow` |

---

## Appendix B — Critical Invariants Reminder

These are the 10 invariants from Backend Schema §16. Claude Code must not violate them:

1. **Stock elements break cycles** — `WaterStore.is_stock()` returns True; no nx edge added for stock outputs
2. **State read-before-write** — `WaterStore.compute()` reads `state.storage[id]` before writing new value
3. **prepare() before compute()** — runner calls `prepare()` on all elements before the loop starts
4. **All output ports written every timestep** — `compute()` calls `state.set()` for every output port
5. **Results arrays pre-allocated** — `ResultsStore` uses `np.zeros(n_steps)` not list append
6. **Model layer never imports engine** — `hydrosim/model/*.py` never imports from `hydrosim/engine/`
7. **IDs are UUIDs, names are user-visible** — formulas use names; state dicts use IDs
8. **connections_in uses port names** — dict passed to `compute()` is `{port_name: value}`
9. **Water balance must close** — `|ΔS - net_flux * dt| < 1e-9` after every WaterStore timestep
10. **JSON round-trip is lossless** — `from_dict(to_dict(element))` reproduces the element exactly

---

*End of HydroSim Implementation Plan v1.0*
