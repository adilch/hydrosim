# HydroSim — Backend Schema
## Architecture, Class Hierarchy & Data Flow Reference for Claude Code

**Version:** 1.0  
**Detail level:** Medium — classes, method signatures, data flow  
**Companion documents:** PRD v1.0, App Flow v1.0, Tech Stack v1.0, Design System v1.0  
**Scope:** Everything in `hydrosim/model/` and `hydrosim/engine/` — the pure Python backend with zero PyQt6 dependencies.

---

## Table of Contents

1. [Backend Overview](#1-backend-overview)
2. [Module Map](#2-module-map)
3. [Core Data Structures](#3-core-data-structures)
4. [Element Base Class](#4-element-base-class)
5. [Element Implementations](#5-element-implementations)
6. [Model Graph](#6-model-graph)
7. [Model Validator](#7-model-validator)
8. [Model Serialiser](#8-model-serialiser)
9. [Simulation Engine — Runner](#9-simulation-engine--runner)
10. [Simulation Engine — Solver](#10-simulation-engine--solver)
11. [Simulation Engine — Expression Parser](#11-simulation-engine--expression-parser)
12. [Results Store](#12-results-store)
13. [Complete Data Flow](#13-complete-data-flow)
14. [Error Types](#14-error-types)
15. [Inter-Module Contracts](#15-inter-module-contracts)
16. [Key Invariants Claude Code Must Preserve](#16-key-invariants-claude-code-must-preserve)

---

## 1. Backend Overview

The backend is structured as two sub-packages that are deliberately kept independent of each other and completely free of PyQt6 imports:

```
hydrosim/
├── model/          ← WHAT the model IS (data, structure, configuration)
│   ├── base.py         ElementBase abstract class + Port + Connection
│   ├── graph.py        ModelGraph — owns all elements + connections
│   ├── validator.py    ModelValidator — checks graph before running
│   ├── serialiser.py   JSON save/load
│   └── elements/       One file per element type
│       ├── constant.py
│       ├── timeseries.py
│       ├── waterstore.py
│       ├── expression.py
│       └── timehistory.py
│
└── engine/         ← WHAT the model DOES (simulation, computation)
    ├── runner.py       SimulationRunner — orchestrates the full run
    ├── solver.py       TimeStepSolver — per-timestep computation
    ├── parser.py       ExpressionParser — safe formula evaluation
    └── results.py      ResultsStore — holds all output arrays
```

**Golden rule:** `model/` never imports from `engine/`. `engine/` imports from `model/` (reads elements and graph) but never writes back to it. The GUI imports from both. This one-way dependency keeps testing trivial and the architecture clean.

---

## 2. Module Map

```
┌─────────────────────────────────────────────────────────────────┐
│                          GUI Layer                              │
│  (imports from model + engine; never imported by them)          │
└─────────┬───────────────────────────┬───────────────────────────┘
          │ reads/writes               │ runs
          ▼                           ▼
┌──────────────────┐        ┌──────────────────────────┐
│   model/         │        │   engine/                │
│                  │        │                          │
│  ModelGraph ─────┼────────► SimulationRunner         │
│    │             │        │    │                     │
│    ├─ elements[] │        │    ├─ ModelValidator      │
│    └─ conns[]    │        │    ├─ TimeStepSolver      │
│                  │        │    │    └─ ExpressionParser│
│  ModelValidator  │        │    └─ ResultsStore        │
│  ModelSerialiser │        │                          │
└──────────────────┘        └──────────────────────────┘
          │                           │
          └──────────┬────────────────┘
                     ▼
              JSON (.hydrosim files)
```

---

## 3. Core Data Structures

These dataclasses are defined in `hydrosim/model/base.py` and used everywhere.

### 3.1 PortType Enum

```python
# hydrosim/model/base.py
from enum import Enum, auto

class PortType(Enum):
    INPUT  = auto()
    OUTPUT = auto()

class ElementCategory(Enum):
    INPUT      = "input"
    STOCK      = "stock"
    EXPRESSION = "expression"
    RESULT     = "result"

class TimeSeriesType(Enum):
    INSTANTANEOUS  = "instantaneous"
    PERIOD_TOTAL   = "period_total"
    PERIOD_AVERAGE = "period_average"

class InterpolationType(Enum):
    LINEAR = "linear"
    STEP   = "step"       # returns value at most recent data point ≤ t
```

### 3.2 Port

```python
@dataclass
class Port:
    name:        str         # e.g. "inflow", "storage", "value"
    port_type:   PortType    # INPUT or OUTPUT
    units:       str         # e.g. "m3/s", "mm/day", "-"
    description: str         # tooltip / documentation
    required:    bool        # True = must be connected before simulation

    # Runtime — set during simulation, not persisted
    _current_value: float = field(default=0.0, repr=False, compare=False)
```

### 3.3 Connection

```python
@dataclass
class Connection:
    id:               str    # UUID string, auto-generated
    from_element_id:  str    # UUID of source element
    from_port_name:   str    # name of source output port
    to_element_id:    str    # UUID of destination element
    to_port_name:     str    # name of destination input port

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
```

### 3.4 SimulationSettings

```python
@dataclass
class SimulationSettings:
    start_time:  float       # days from epoch (0.0 for elapsed mode)
    end_time:    float       # days (must be > start_time)
    dt:          float       # timestep in days (e.g. 1.0 = daily)
    time_mode:   str         # "elapsed" | "calendar"
    start_date:  date | None # only used when time_mode == "calendar"

    @property
    def n_steps(self) -> int:
        return int(round((self.end_time - self.start_time) / self.dt))

    @property
    def timesteps(self) -> np.ndarray:
        """Array of time values at each step."""
        return np.linspace(self.start_time, self.end_time, self.n_steps,
                           endpoint=False)
```

### 3.5 SimState

The live state object passed between elements during each timestep:

```python
@dataclass
class SimState:
    t:        float                          # current time in days
    dt:       float                          # current timestep in days
    step:     int                            # current step index (0-based)
    values:   dict[str, dict[str, float]]    # values[element_id][port_name]
    storage:  dict[str, float]               # storage[element_id] for stocks

    def get(self, element_id: str, port_name: str) -> float:
        """Safe accessor — returns 0.0 if not yet computed."""
        return self.values.get(element_id, {}).get(port_name, 0.0)

    def set(self, element_id: str, port_name: str, value: float) -> None:
        if element_id not in self.values:
            self.values[element_id] = {}
        self.values[element_id][port_name] = value
```

---

## 4. Element Base Class

**File:** `hydrosim/model/base.py`

`ElementBase` is the abstract parent of every element type. Claude Code must subclass it for each element — never instantiate it directly.

```python
from abc import ABC, abstractmethod

class ElementBase(ABC):
    """Abstract base class for all HydroSim elements."""

    def __init__(
        self,
        name:        str,
        description: str = "",
        element_id:  str | None = None,
        position:    tuple[float, float] = (0.0, 0.0),
    ):
        self.id:          str   = element_id or str(uuid.uuid4())
        self.name:        str   = name
        self.description: str   = description
        self.position:    tuple[float, float] = position

        # Ports are defined by each subclass via _define_ports()
        self._input_ports:  dict[str, Port] = {}
        self._output_ports: dict[str, Port] = {}
        self._define_ports()

    # ── Port definition (called in __init__) ──────────────────────────

    @abstractmethod
    def _define_ports(self) -> None:
        """
        Subclass defines its ports here by calling self._add_input_port()
        and self._add_output_port(). Called once at construction.
        """

    def _add_input_port(self, name: str, units: str, description: str,
                        required: bool = False) -> None:
        self._input_ports[name] = Port(name, PortType.INPUT, units,
                                       description, required)

    def _add_output_port(self, name: str, units: str,
                         description: str) -> None:
        self._output_ports[name] = Port(name, PortType.OUTPUT, units,
                                        description, required=False)

    # ── Port accessors ────────────────────────────────────────────────

    @property
    def input_ports(self) -> dict[str, Port]:
        return self._input_ports

    @property
    def output_ports(self) -> dict[str, Port]:
        return self._output_ports

    @property
    def all_ports(self) -> dict[str, Port]:
        return {**self._input_ports, **self._output_ports}

    def get_port(self, name: str) -> Port | None:
        return self.all_ports.get(name)

    # ── Abstract interface ────────────────────────────────────────────

    @property
    @abstractmethod
    def category(self) -> ElementCategory:
        """Return the ElementCategory enum value for this element."""

    @abstractmethod
    def validate(self) -> list["ValidationError"]:
        """
        Validate element's own parameters (independent of connections).
        Returns list of ValidationError. Empty list = valid.
        """

    @abstractmethod
    def compute(self, state: SimState, connections_in: dict[str, float]) -> None:
        """
        Compute this element's outputs for the current timestep.

        Args:
            state:           Current simulation state. Read from it for
                             previous stock values; write output values to it.
            connections_in:  {port_name: value} for each connected input port.
                             Values already resolved by the solver from upstream
                             elements' outputs. Unconnected optional ports not present.

        Side effects:
            Must call state.set(self.id, port_name, value) for each output port.
            Stock elements must also update state.storage[self.id].
        """

    @abstractmethod
    def to_dict(self) -> dict:
        """
        Serialise element to a JSON-compatible dict.
        Must include: id, type (class name string), name, description, position,
        and a 'parameters' sub-dict with all element-specific config.
        """

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict) -> "ElementBase":
        """
        Deserialise element from dict produced by to_dict().
        Must reconstruct complete element state.
        """

    # ── Concrete helpers (not abstract) ──────────────────────────────

    def is_stock(self) -> bool:
        """True for elements that maintain internal state across timesteps."""
        return False   # overridden by WaterStore and future stock elements

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id!r}, name={self.name!r})"
```

---

## 5. Element Implementations

### 5.1 Constant

**File:** `hydrosim/model/elements/constant.py`

```python
class Constant(ElementBase):
    """A fixed scalar value that does not change during simulation."""

    def __init__(
        self,
        name:        str,
        value:       float = 0.0,
        units:       str   = "-",
        description: str   = "",
        element_id:  str | None = None,
        position:    tuple[float, float] = (0.0, 0.0),
    ): ...

    @property
    def category(self) -> ElementCategory:
        return ElementCategory.INPUT

    def _define_ports(self) -> None:
        self._add_output_port("value", self.units, "The constant scalar value")

    def validate(self) -> list[ValidationError]:
        # Check: value is finite (not NaN or Inf)

    def compute(self, state: SimState, connections_in: dict[str, float]) -> None:
        # state.set(self.id, "value", self.value)
        # No inputs, no timestep dependency — always returns self.value

    def to_dict(self) -> dict:
        # returns: {id, type: "Constant", name, description, position,
        #           parameters: {value, units}}

    @classmethod
    def from_dict(cls, data: dict) -> "Constant": ...
```

**Key behaviour:** `compute()` is the simplest possible — always sets `"value"` to `self.value`. No inputs. No state.

---

### 5.2 TimeSeries

**File:** `hydrosim/model/elements/timeseries.py`

```python
class TimeSeries(ElementBase):
    """Time-varying input from a table of (time, value) pairs."""

    def __init__(
        self,
        name:          str,
        units:         str                = "-",
        data_type:     TimeSeriesType     = TimeSeriesType.PERIOD_TOTAL,
        interpolation: InterpolationType  = InterpolationType.STEP,
        data:          list[tuple[float, float]] = None,   # [(time_days, value), ...]
        description:   str               = "",
        element_id:    str | None        = None,
        position:      tuple[float, float] = (0.0, 0.0),
    ): ...

    @property
    def category(self) -> ElementCategory:
        return ElementCategory.INPUT

    def _define_ports(self) -> None:
        self._add_output_port("value", self.units,
                              "Interpolated value at current timestep")

    def validate(self) -> list[ValidationError]:
        # Check: data is not empty
        # Check: time values are strictly increasing
        # Check: no NaN or Inf values

    def prepare(self) -> None:
        """
        Called once before simulation starts.
        Builds the SciPy interpolator from self.data.
        Must be called after data is set and before compute() is called.
        """
        times  = np.array([row[0] for row in self.data], dtype=np.float64)
        values = np.array([row[1] for row in self.data], dtype=np.float64)

        kind = 'previous' if self.interpolation == InterpolationType.STEP \
               else 'linear'

        from scipy.interpolate import interp1d
        self._interpolator = interp1d(
            times, values,
            kind=kind,
            bounds_error=False,
            fill_value=(values[0], values[-1])   # flat extrapolation at edges
        )

    def compute(self, state: SimState, connections_in: dict[str, float]) -> None:
        # value = float(self._interpolator(state.t))
        # state.set(self.id, "value", value)
        # Raises RuntimeError if prepare() was not called first

    def get_value_at(self, t: float) -> float:
        """Direct query — used by expression editor Test button."""

    def to_dict(self) -> dict:
        # parameters: {units, data_type, interpolation, data: [[t,v], ...]}

    @classmethod
    def from_dict(cls, data: dict) -> "TimeSeries": ...
```

**Key behaviour:** `prepare()` must be called by the runner before the timestep loop. `compute()` calls the pre-built interpolator — never rebuilds it each timestep.

---

### 5.3 WaterStore

**File:** `hydrosim/model/elements/waterstore.py`

```python
class WaterStore(ElementBase):
    """
    Bounded water storage that integrates inflow - outflow over time.
    This is a STATE VARIABLE — its output at timestep t depends on
    its value at timestep t-1.
    """

    def __init__(
        self,
        name:            str,
        initial_storage: float       = 0.0,
        lower_bound:     float       = 0.0,
        upper_bound:     float | None = None,   # None = unbounded
        units:           str         = "m3",
        description:     str         = "",
        element_id:      str | None  = None,
        position:        tuple[float, float] = (0.0, 0.0),
    ): ...

    @property
    def category(self) -> ElementCategory:
        return ElementCategory.STOCK

    def is_stock(self) -> bool:
        return True   # ← critical: tells graph to treat as state variable

    def _define_ports(self) -> None:
        self._add_input_port("inflow",  self.units + "/day",
                             "Volume inflow rate per timestep", required=False)
        self._add_input_port("outflow", self.units + "/day",
                             "Volume outflow rate per timestep", required=False)
        self._add_output_port("storage",  self.units,
                              "Current storage volume")
        self._add_output_port("overflow", self.units + "/day",
                              "Overflow rate when upper bound exceeded")
        self._add_output_port("deficit",  self.units + "/day",
                              "Unmet outflow rate when lower bound hit")

    def validate(self) -> list[ValidationError]:
        # Check: lower_bound is finite
        # Check: if upper_bound is set, upper_bound > lower_bound
        # Check: initial_storage is within [lower_bound, upper_bound]

    def initialise(self, state: SimState) -> None:
        """
        Called once before the timestep loop by the runner.
        Sets initial storage in state.storage and sets initial output values.
        """
        state.storage[self.id] = self.initial_storage
        state.set(self.id, "storage",  self.initial_storage)
        state.set(self.id, "overflow", 0.0)
        state.set(self.id, "deficit",  0.0)

    def compute(self, state: SimState, connections_in: dict[str, float]) -> None:
        """
        Forward Euler integration.

        Algorithm:
            s_prev   = state.storage[self.id]    ← from previous timestep
            inflow   = connections_in.get("inflow",  0.0)
            outflow  = connections_in.get("outflow", 0.0)
            s_new    = s_prev + (inflow - outflow) * state.dt

            if upper_bound and s_new > upper_bound:
                overflow = (s_new - upper_bound) / state.dt
                s_new    = upper_bound
            else:
                overflow = 0.0

            if s_new < lower_bound:
                deficit = (lower_bound - s_new) / state.dt
                s_new   = lower_bound
            else:
                deficit = 0.0

            state.storage[self.id] = s_new
            state.set(self.id, "storage",  s_new)
            state.set(self.id, "overflow", overflow)
            state.set(self.id, "deficit",  deficit)
        """

    def get_water_balance_error(self, state: SimState,
                                connections_in: dict[str, float],
                                s_prev: float) -> float:
        """
        Returns the residual error in the water balance equation:
            error = ΔS - (inflow - outflow - overflow + deficit) * dt
        Should be ~0 if integration is correct. Used by runner for diagnostics.
        """

    def to_dict(self) -> dict:
        # parameters: {initial_storage, lower_bound, upper_bound, units}

    @classmethod
    def from_dict(cls, data: dict) -> "WaterStore": ...
```

**Key behaviour:**
- `is_stock()` returns `True` — the graph treats this element's OUTPUT as available from the PREVIOUS timestep, breaking what would otherwise be a circular dependency
- `initialise()` must be called before the loop
- `compute()` reads `state.storage[self.id]` for the previous value, not `state.get(self.id, "storage")` which would be the value just written this step

---

### 5.4 Expression

**File:** `hydrosim/model/elements/expression.py`

```python
class Expression(ElementBase):
    """
    Evaluates a user-defined formula at each timestep.
    Input ports are dynamically created based on element names referenced
    in the formula.
    """

    def __init__(
        self,
        name:         str,
        formula:      str   = "",
        output_units: str   = "-",
        description:  str   = "",
        element_id:   str | None = None,
        position:     tuple[float, float] = (0.0, 0.0),
    ): ...

    @property
    def category(self) -> ElementCategory:
        return ElementCategory.EXPRESSION

    def _define_ports(self) -> None:
        # Output port is always fixed
        self._add_output_port("value", self.output_units, "Formula result")
        # Input ports are dynamic — rebuilt when formula changes
        # Do NOT add input ports here; call rebuild_input_ports() instead

    def set_formula(self, formula: str) -> None:
        """
        Update the formula and rebuild dynamic input ports.
        Called when user edits the formula in the dialog.
        """
        self.formula = formula
        self.rebuild_input_ports()

    def rebuild_input_ports(self) -> None:
        """
        Parse the formula to find referenced element names.
        Create one input port per unique element name referenced.
        Port name = element name (e.g., "Daily_Rainfall").
        Port name for dot-notation = full reference (e.g., "SoilMoisture.storage").

        This method is idempotent — safe to call multiple times.
        """
        self._input_ports.clear()
        if not self.formula:
            return
        refs = ExpressionParser.extract_references(self.formula)
        for ref in refs:
            self._add_input_port(
                name=ref,
                units="-",      # units not known until connected
                description=f"Input from {ref}",
                required=True
            )

    def validate(self) -> list[ValidationError]:
        # Check: formula is non-empty
        # Check: formula parses without syntax error
        # Check: formula contains no forbidden AST nodes
        # References to element names are NOT checked here (graph-level check)

    def prepare(self, name_to_id: dict[str, str]) -> None:
        """
        Called once before simulation by the runner.
        Builds the evaluator with the correct element ID mappings.

        Args:
            name_to_id: maps element name → element ID
                        e.g. {"Daily_Rainfall": "a1b2c3...", ...}
        """
        from hydrosim.engine.parser import ExpressionParser
        self._parser = ExpressionParser(self.formula, name_to_id)

    def compute(self, state: SimState, connections_in: dict[str, float]) -> None:
        """
        Evaluate formula with current input values.
        connections_in keys are element names (matching port names).
        """
        # result = self._parser.evaluate(connections_in, state.t, state.dt)
        # state.set(self.id, "value", result)

    def evaluate_test(self, input_values: dict[str, float], t: float = 0.0,
                      dt: float = 1.0) -> float:
        """
        Evaluate the formula with provided values.
        Used by the Test button in the Expression dialog.
        Raises ExpressionEvaluationError on failure.
        """

    def to_dict(self) -> dict:
        # parameters: {formula, output_units}
        # Note: input ports are NOT persisted — they are rebuilt from formula

    @classmethod
    def from_dict(cls, data: dict) -> "Expression": ...
```

**Key behaviour:**
- Input ports are **dynamic** — they don't exist until `rebuild_input_ports()` is called after setting a formula
- The solver resolves input port values by matching port names to element names in the graph
- `prepare()` is called by the runner after graph validation, passing the name→ID mapping

---

### 5.5 TimeHistoryResult

**File:** `hydrosim/model/elements/timehistory.py`

```python
class TimeHistoryResult(ElementBase):
    """
    Collects time histories of connected outputs.
    Has no outputs itself — it is a terminal/sink element.
    """

    MAX_SERIES = 8   # maximum number of connected series

    def __init__(
        self,
        name:         str,
        title:        str        = "",
        y_axis_label: str        = "",
        y_axis_units: str        = "-",
        show_grid:    bool       = True,
        y_min:        float | None = None,
        y_max:        float | None = None,
        description:  str        = "",
        element_id:   str | None = None,
        position:     tuple[float, float] = (0.0, 0.0),
    ): ...

    @property
    def category(self) -> ElementCategory:
        return ElementCategory.RESULT

    def _define_ports(self) -> None:
        # Starts with one input port; more added when series_1 is connected
        self._add_input_port("series_1", "-",
                             "First time series to display", required=True)

    def add_series_port(self) -> str:
        """
        Add the next series input port (series_2, series_3, ...).
        Called by ModelGraph when series_N is connected and N < MAX_SERIES.
        Returns the name of the new port.
        """
        n = len(self._input_ports) + 1
        if n > self.MAX_SERIES:
            raise ValueError(f"Maximum {self.MAX_SERIES} series per result element")
        port_name = f"series_{n}"
        self._add_input_port(port_name, "-",
                             f"Series {n} to display", required=False)
        return port_name

    def validate(self) -> list[ValidationError]:
        # Check: at least series_1 exists (always true)
        # Check: if y_min and y_max both set, y_min < y_max

    def compute(self, state: SimState, connections_in: dict[str, float]) -> None:
        """
        Does not compute anything — data collection is handled by ResultsStore.
        This method is a no-op; it exists to satisfy the abstract interface.
        """

    def to_dict(self) -> dict:
        # parameters: {title, y_axis_label, y_axis_units,
        #              show_grid, y_min, y_max}

    @classmethod
    def from_dict(cls, data: dict) -> "TimeHistoryResult": ...
```

**Key behaviour:** `compute()` is a no-op. Data recording is done by `ResultsStore` which reads the values already written to `SimState` by upstream elements.

---

## 6. Model Graph

**File:** `hydrosim/model/graph.py`

The `ModelGraph` is the single source of truth for the model's structure. It owns all elements and connections. The GUI canvas is a visual representation of this object.

```python
import networkx as nx

class ModelGraph:
    """
    Owns all elements and connections.
    Maintains a NetworkX DiGraph for dependency analysis.
    All mutations go through this class — never modify elements or connections directly.
    """

    def __init__(self):
        self._elements:    dict[str, ElementBase] = {}
        self._connections: dict[str, Connection]  = {}
        self._nx_graph:    nx.DiGraph             = nx.DiGraph()

    # ── Element management ────────────────────────────────────────────

    def add_element(self, element: ElementBase) -> None:
        """
        Add an element to the graph.
        Raises ValueError if element.id already exists.
        """
        if element.id in self._elements:
            raise ValueError(f"Element {element.id!r} already in graph")
        self._elements[element.id] = element
        self._nx_graph.add_node(element.id, element=element)

    def remove_element(self, element_id: str) -> None:
        """
        Remove element and all its connections from the graph.
        Raises KeyError if not found.
        """
        # Remove all connections involving this element first
        conn_ids = [c.id for c in self._connections.values()
                    if c.from_element_id == element_id
                    or c.to_element_id == element_id]
        for cid in conn_ids:
            self.remove_connection(cid)
        del self._elements[element_id]
        self._nx_graph.remove_node(element_id)

    def get_element(self, element_id: str) -> ElementBase:
        """Raises KeyError if not found."""
        return self._elements[element_id]

    def get_element_by_name(self, name: str) -> ElementBase | None:
        """Case-insensitive search by element name. Returns None if not found."""
        name_lower = name.lower()
        for el in self._elements.values():
            if el.name.lower() == name_lower:
                return el
        return None

    def rename_element(self, element_id: str, new_name: str) -> None:
        """
        Rename an element. Updates any Expression elements whose formulas
        reference the old name — rebuilds their input ports.
        Raises ValueError if new_name already taken by another element.
        """

    @property
    def elements(self) -> dict[str, ElementBase]:
        return dict(self._elements)   # return copy — never expose internal dict

    @property
    def element_count(self) -> int:
        return len(self._elements)

    # ── Connection management ─────────────────────────────────────────

    def add_connection(self, connection: Connection) -> None:
        """
        Add a connection between elements.

        Validates before adding:
          - Both element IDs exist
          - from_port_name is an output port on the source element
          - to_port_name is an input port on the destination element
          - to_port is not already connected (input ports: one connection only)
          - Connection does not create a cycle among non-stock elements

        After adding:
          - Updates the NetworkX graph (edge added unless from-element is a stock)
          - If destination is TimeHistoryResult and new series port needed, adds it
        """

    def remove_connection(self, connection_id: str) -> None:
        """Remove connection. Raises KeyError if not found."""
        conn = self._connections[connection_id]
        del self._connections[connection_id]
        # Remove nx edge (if it exists — stock outputs don't have edges)
        if self._nx_graph.has_edge(conn.from_element_id, conn.to_element_id):
            self._nx_graph.remove_edge(conn.from_element_id, conn.to_element_id)

    def get_connection(self, connection_id: str) -> Connection:
        return self._connections[connection_id]

    def get_connections_from(self, element_id: str) -> list[Connection]:
        """All connections where this element is the source."""
        return [c for c in self._connections.values()
                if c.from_element_id == element_id]

    def get_connections_to(self, element_id: str) -> list[Connection]:
        """All connections where this element is the destination."""
        return [c for c in self._connections.values()
                if c.to_element_id == element_id]

    def get_connections_to_port(self, element_id: str,
                                port_name: str) -> list[Connection]:
        """All connections feeding a specific input port."""
        return [c for c in self._connections.values()
                if c.to_element_id == element_id
                and c.to_port_name == port_name]

    @property
    def connections(self) -> dict[str, Connection]:
        return dict(self._connections)

    # ── Graph analysis ────────────────────────────────────────────────

    def get_execution_order(self) -> list[ElementBase]:
        """
        Returns elements sorted in topological order for simulation.

        Algorithm:
          1. Build DAG with stock element outputs excluded from edges
             (stocks break cycles by providing their previous-step value)
          2. Apply nx.topological_sort()
          3. Return ElementBase objects in sorted order

        Raises CircularDependencyError if a cycle exists among non-stock elements.
        """
        if not nx.is_directed_acyclic_graph(self._nx_graph):
            cycles = list(nx.simple_cycles(self._nx_graph))
            raise CircularDependencyError(cycles)
        sorted_ids = list(nx.topological_sort(self._nx_graph))
        return [self._elements[eid] for eid in sorted_ids
                if eid in self._elements]

    def has_cycle(self) -> bool:
        """True if a circular dependency exists among non-stock elements."""
        return not nx.is_directed_acyclic_graph(self._nx_graph)

    def get_upstream_elements(self, element_id: str) -> list[ElementBase]:
        """All elements that must be computed before this one."""
        return [self._elements[eid]
                for eid in nx.ancestors(self._nx_graph, element_id)
                if eid in self._elements]

    def build_name_to_id_map(self) -> dict[str, str]:
        """
        Returns {element_name: element_id} for all elements.
        Used by Expression.prepare() to resolve formula references.
        Case-insensitive: keys are lowercase.
        """
        return {el.name.lower(): el.id
                for el in self._elements.values()}

    # ── NetworkX edge rule ────────────────────────────────────────────

    def _should_add_nx_edge(self, from_element: ElementBase) -> bool:
        """
        Stock elements provide their PREVIOUS timestep value, so their output
        connections do NOT create a topological dependency. All other elements
        (Input, Expression, Result) DO create dependency edges.
        """
        return not from_element.is_stock()
```

**Key design:** The NetworkX graph only includes edges from non-stock elements. This means `WaterStore.storage → TimeHistoryResult` does NOT create an nx edge, allowing the graph to remain acyclic even when storage feeds back into calculations.

---

## 7. Model Validator

**File:** `hydrosim/model/validator.py`

Validation runs at two points: continuously in the GUI (per-element) and fully before simulation starts.

```python
class ModelValidator:
    """
    Validates a ModelGraph before simulation.
    All checks are read-only — the validator never modifies the graph.
    """

    def __init__(self, graph: ModelGraph):
        self.graph = graph

    def validate_all(self) -> list[ValidationError]:
        """
        Run full validation. Returns all errors found.
        Simulation must not proceed if this returns a non-empty list.
        """
        errors: list[ValidationError] = []
        errors.extend(self._check_model_not_empty())
        errors.extend(self._check_element_parameters())
        errors.extend(self._check_required_ports_connected())
        errors.extend(self._check_no_circular_dependencies())
        errors.extend(self._check_expression_references())
        return errors

    def validate_element(self, element_id: str) -> list[ValidationError]:
        """
        Validate a single element's parameters.
        Used by GUI for real-time feedback. Does NOT check connections.
        """
        el = self.graph.get_element(element_id)
        return el.validate()

    # ── Individual checks ─────────────────────────────────────────────

    def _check_model_not_empty(self) -> list[ValidationError]:
        """Error if model has no elements."""

    def _check_element_parameters(self) -> list[ValidationError]:
        """
        Call el.validate() on every element.
        Collect all returned ValidationErrors.
        """

    def _check_required_ports_connected(self) -> list[ValidationError]:
        """
        For every element, for every input port where required=True:
        check that at least one connection feeds that port.
        Error: MISSING_REQUIRED_INPUT
        """

    def _check_no_circular_dependencies(self) -> list[ValidationError]:
        """
        Check the ModelGraph's NetworkX DAG.
        Error: CIRCULAR_DEPENDENCY — includes the cycle path in the message.
        """

    def _check_expression_references(self) -> list[ValidationError]:
        """
        For every Expression element:
        - Parse the formula
        - Extract referenced element names
        - Check each name exists in the graph (case-insensitive)
        Error: UNKNOWN_REFERENCE — with "did you mean X?" suggestion if close match found
        """

    def get_warnings(self) -> list[ValidationWarning]:
        """
        Non-blocking issues. Simulation proceeds but warnings are logged.
        """
        warnings = []
        warnings.extend(self._warn_units_mismatch())
        warnings.extend(self._warn_timeseries_too_short())
        warnings.extend(self._warn_missing_descriptions())
        return warnings

    def _warn_units_mismatch(self) -> list[ValidationWarning]:
        """
        For each connection, check if source port units ≠ destination port units.
        Warn (do not error) if they differ and neither is "-" (dimensionless).
        """

    def _warn_timeseries_too_short(self) -> list[ValidationWarning]:
        """
        For each TimeSeries element, check if its data range covers the
        full simulation period. Warn if flat extrapolation will be used.
        Requires SimulationSettings — pass as optional arg or skip this check
        if settings not yet available.
        """

    def _warn_missing_descriptions(self) -> list[ValidationWarning]:
        """Warn for elements with empty description fields."""
```

---

## 8. Model Serialiser

**File:** `hydrosim/model/serialiser.py`

```python
class ModelSerialiser:
    """
    Converts between ModelGraph objects and the .hydrosim JSON format.
    Uses Pydantic for validation on load.
    """

    CURRENT_FORMAT_VERSION = "1"

    # ── Save ──────────────────────────────────────────────────────────

    @staticmethod
    def save(graph: ModelGraph, settings: SimulationSettings,
             filepath: Path, metadata: dict | None = None) -> None:
        """
        Serialise graph + settings to a .hydrosim JSON file.

        File structure:
            {
              "hydrosim_version": "1.0",
              "file_format_version": "1",
              "metadata": { name, description, author, created, modified },
              "simulation_settings": { start_time, end_time, dt, ... },
              "elements": [ {element dict}, ... ],
              "connections": [ {connection dict}, ... ],
              "canvas_state": { zoom, pan_x, pan_y }
            }

        Raises:
            IOError if file cannot be written.
        """

    @staticmethod
    def to_dict(graph: ModelGraph, settings: SimulationSettings,
                metadata: dict | None = None) -> dict:
        """
        Serialise to a plain dict without writing to disk.
        Useful for autosave and undo snapshots.
        """

    # ── Load ──────────────────────────────────────────────────────────

    @staticmethod
    def load(filepath: Path) -> tuple[ModelGraph, SimulationSettings, dict]:
        """
        Load a .hydrosim file.
        Returns: (graph, settings, metadata)

        Raises:
            FileNotFoundError
            ModelFileError (invalid JSON or Pydantic validation failure)
            VersionMismatchError (file_format_version > CURRENT_FORMAT_VERSION)
        """

    @staticmethod
    def from_dict(data: dict) -> tuple[ModelGraph, SimulationSettings, dict]:
        """
        Deserialise from a dict (inverse of to_dict).
        Validates with Pydantic schema before deserialising.
        """

    # ── Element dispatch ──────────────────────────────────────────────

    ELEMENT_REGISTRY: dict[str, type[ElementBase]] = {
        "Constant":          Constant,
        "TimeSeries":        TimeSeries,
        "WaterStore":        WaterStore,
        "Expression":        Expression,
        "TimeHistoryResult": TimeHistoryResult,
    }

    @classmethod
    def _deserialise_element(cls, data: dict) -> ElementBase:
        """
        Dispatch to the correct element class based on data["type"].
        Raises ModelFileError if type is unrecognised.
        """
        element_type = data.get("type")
        klass = cls.ELEMENT_REGISTRY.get(element_type)
        if klass is None:
            raise ModelFileError(
                f"Unknown element type {element_type!r}. "
                f"Known types: {list(cls.ELEMENT_REGISTRY)}"
            )
        return klass.from_dict(data)
```

**Pydantic schema** (abbreviated — full schemas defined inline in serialiser.py):

```python
from pydantic import BaseModel, field_validator
from typing import Annotated, Literal

class ConnectionSchema(BaseModel):
    id:               str
    from_element_id:  str
    from_port_name:   str
    to_element_id:    str
    to_port_name:     str

class SimSettingsSchema(BaseModel):
    start_time:  float
    end_time:    float
    dt:          float
    time_mode:   Literal["elapsed", "calendar"]
    start_date:  str | None = None   # ISO date string

    @field_validator("dt")
    def dt_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("dt must be positive")
        return v

class HydroSimFileSchema(BaseModel):
    hydrosim_version:    str
    file_format_version: str
    metadata:            dict
    simulation_settings: SimSettingsSchema
    elements:            list[dict]   # validated individually by element class
    connections:         list[ConnectionSchema]
    canvas_state:        dict | None = None
```

---

## 9. Simulation Engine — Runner

**File:** `hydrosim/engine/runner.py`

The `SimulationRunner` is the top-level orchestrator. The GUI calls `run_async()` which spawns a `QThread`.

```python
class SimulationRunner:
    """
    Orchestrates a complete simulation run.
    Reads from ModelGraph + SimulationSettings.
    Writes to ResultsStore.
    Pure Python — no PyQt6 imports.
    """

    def __init__(
        self,
        graph:    ModelGraph,
        settings: SimulationSettings,
    ):
        self.graph    = graph
        self.settings = settings
        self._stop_requested = False

    # ── Public API ────────────────────────────────────────────────────

    def run(
        self,
        progress_callback: Callable[[float], None] | None = None,
    ) -> ResultsStore:
        """
        Execute the full simulation synchronously.

        Sequence:
          1. validate()              → raise SimulationError if invalid
          2. build_execution_order() → list[ElementBase]
          3. initialise_state()      → SimState
          4. prepare_elements()      → call prepare() on TimeSeries, Expression
          5. initialise_stocks()     → call initialise() on WaterStore
          6. initialise_results()    → ResultsStore with pre-allocated arrays
          7. timestep_loop()         → call solver for each timestep
          8. return ResultsStore

        Args:
            progress_callback: called with float 0.0–1.0 at each timestep.
                               Used by GUI thread to update progress bar.

        Raises:
            SimulationError:       model is invalid
            SimulationAborted:     stop() was called during run
        """

    def stop(self) -> None:
        """
        Signal the runner to stop after the current timestep.
        Thread-safe — can be called from any thread.
        """
        self._stop_requested = True

    # ── Internal sequence steps ───────────────────────────────────────

    def _validate(self) -> None:
        """
        Run ModelValidator.validate_all().
        Raise SimulationError(errors) if any errors found.
        """
        validator = ModelValidator(self.graph)
        errors = validator.validate_all()
        if errors:
            raise SimulationError(errors)

    def _build_execution_order(self) -> list[ElementBase]:
        """
        Get topologically sorted element list from graph.
        Raises CircularDependencyError (propagated from ModelGraph).
        """
        return self.graph.get_execution_order()

    def _initialise_state(self) -> SimState:
        """
        Create a fresh SimState with empty values dicts.
        """
        return SimState(
            t=self.settings.start_time,
            dt=self.settings.dt,
            step=0,
            values={},
            storage={},
        )

    def _prepare_elements(self, state: SimState) -> None:
        """
        Call prepare() on elements that need pre-simulation setup:
          - TimeSeries.prepare()    → builds interpolator
          - Expression.prepare()    → builds parser with name→ID map
        """
        name_to_id = self.graph.build_name_to_id_map()
        for el in self.graph.elements.values():
            if isinstance(el, TimeSeries):
                el.prepare()
            elif isinstance(el, Expression):
                el.prepare(name_to_id)

    def _initialise_stocks(self, state: SimState) -> None:
        """
        Call initialise() on all stock elements to set initial storage.
        Must be called AFTER _initialise_state() and BEFORE the timestep loop.
        """
        for el in self.graph.elements.values():
            if el.is_stock():
                el.initialise(state)

    def _build_results_store(self,
                             execution_order: list[ElementBase]) -> ResultsStore:
        """
        Create ResultsStore and pre-allocate output arrays.
        Only allocates arrays for ports that feed into a TimeHistoryResult.
        """
        # Find which (element_id, port_name) pairs are connected to results
        tracked: list[tuple[str, str]] = []
        for el in self.graph.elements.values():
            if isinstance(el, TimeHistoryResult):
                for conn in self.graph.get_connections_to(el.id):
                    tracked.append((conn.from_element_id, conn.from_port_name))

        return ResultsStore(
            timesteps=self.settings.timesteps,
            tracked=tracked,
            element_names={el.id: el.name
                           for el in self.graph.elements.values()},
        )

    def _timestep_loop(
        self,
        execution_order: list[ElementBase],
        state:           SimState,
        results:         ResultsStore,
        progress_cb:     Callable[[float], None] | None,
    ) -> None:
        """
        Main simulation loop.

        For each timestep:
          1. Update state.t, state.step
          2. For each element in execution_order:
             a. Resolve input values from state (via connections)
             b. Call element.compute(state, connections_in)
          3. Record tracked outputs into results arrays
          4. Check for stop signal
          5. Call progress_callback
        """
        solver = TimeStepSolver(self.graph)
        n = self.settings.n_steps

        for i, t in enumerate(self.settings.timesteps):
            if self._stop_requested:
                raise SimulationAborted(step=i, t=t)

            state.t    = t
            state.step = i

            for element in execution_order:
                connections_in = solver.resolve_inputs(element, state)
                element.compute(state, connections_in)

            results.record(i, state)

            if progress_cb:
                progress_cb((i + 1) / n)

    def _log_warnings(self, results: ResultsStore) -> None:
        """
        After the loop, check water balance errors and log warnings.
        """
```

---

## 10. Simulation Engine — Solver

**File:** `hydrosim/engine/solver.py`

The `TimeStepSolver` handles the per-element input resolution at each timestep.

```python
class TimeStepSolver:
    """
    Resolves input values for each element at the current timestep.
    Reads from SimState; does not write to it.
    """

    def __init__(self, graph: ModelGraph):
        self.graph = graph

    def resolve_inputs(
        self,
        element: ElementBase,
        state:   SimState,
    ) -> dict[str, float]:
        """
        Build the connections_in dict for element.compute().

        For each input port of the element:
          - Find the connection(s) feeding that port
          - Read the source element's output value from state
          - If port has multiple connections, SUM the values
          - If port has no connection and is not required, return 0.0
          - If port has no connection and is required, raise MissingInputError

        Returns:
            {port_name: float_value} for each input port that has a connection.
            Ports with no connection are omitted (element.compute uses .get() with default 0.0).

        Special case — Expression elements:
            Port names ARE the element names (e.g., "Daily_Rainfall").
            The source value is looked up by:
              state.get(source_element_id, source_port_name)
        """
        result: dict[str, float] = {}

        for port_name, port in element.input_ports.items():
            connections = self.graph.get_connections_to_port(element.id, port_name)

            if not connections:
                # Optional unconnected port — omit from dict
                # Required unconnected port — caught by validator, not here
                continue

            # Sum all values feeding this port (fan-in)
            total = 0.0
            for conn in connections:
                source_value = state.get(conn.from_element_id, conn.from_port_name)
                total += source_value

            result[port_name] = total

        return result
```

---

## 11. Simulation Engine — Expression Parser

**File:** `hydrosim/engine/parser.py`

```python
from simpleeval import SimpleEval, NameNotDefined
import ast
import math

# Whitelist of safe AST node types
SAFE_AST_NODES = frozenset({
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Call,
    ast.Constant, ast.Name, ast.IfExp, ast.Compare,
    ast.BoolOp, ast.Attribute,   # for dot-notation: SoilMoisture.storage
    # Operators
    ast.Add, ast.Sub, ast.Mul, ast.Div, ast.Pow, ast.USub, ast.UAdd,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.And, ast.Or, ast.Not,
})

SAFE_FUNCTIONS = {
    "abs":   abs,     "sqrt":  math.sqrt,  "exp":   math.exp,
    "log":   math.log, "log10": math.log10, "sin":   math.sin,
    "cos":   math.cos, "tan":   math.tan,
    "min":   min,     "max":   max,
    "round": round,   "floor": math.floor, "ceil":  math.ceil,
    "if_":   lambda cond, a, b: a if cond else b,
}

class ExpressionParser:
    """
    Safe formula evaluator using simpleeval.
    Constructed once per Expression element during prepare().
    """

    def __init__(self, formula: str, name_to_id: dict[str, str]):
        """
        Args:
            formula:     The formula string e.g. "Daily_Rainfall * RunoffCoeff"
            name_to_id:  {"daily_rainfall": "uuid-...", "runoffcoeff": "uuid-..."}
                         Keys must be lowercase element names.
        """
        self.formula    = formula
        self.name_to_id = name_to_id   # lowercase name → element UUID
        self._evaluator = SimpleEval(functions=SAFE_FUNCTIONS)

    def evaluate(
        self,
        input_values: dict[str, float],   # {port_name: value} from solver
        t:  float,
        dt: float,
    ) -> float:
        """
        Evaluate formula with current input values.

        input_values keys are element names as written in the formula.
        Special variables t and dt are always available.

        Returns float result.
        Raises ExpressionEvaluationError on any failure.
        """
        names = dict(input_values)   # element_name → value
        names["t"]  = t
        names["dt"] = dt

        self._evaluator.names = names
        try:
            result = self._evaluator.eval(self.formula)
            if not math.isfinite(result):
                raise ExpressionEvaluationError(
                    f"Formula produced non-finite result: {result}"
                )
            return float(result)
        except NameNotDefined as e:
            raise ExpressionEvaluationError(f"Unknown variable: {e}")
        except ZeroDivisionError:
            return 0.0   # log warning but continue simulation
        except Exception as e:
            raise ExpressionEvaluationError(str(e))

    # ── Static utilities (used by GUI for live validation) ────────────

    @staticmethod
    def validate_syntax(formula: str) -> list[str]:
        """
        Check formula syntax without evaluating.
        Returns list of error messages (empty = valid syntax).
        Does NOT check if referenced element names exist.
        """
        if not formula.strip():
            return ["Formula is empty"]
        try:
            tree = ast.parse(formula, mode='eval')
        except SyntaxError as e:
            return [f"Syntax error: {e.msg} at position {e.offset}"]

        # Walk AST and check for forbidden nodes
        errors = []
        for node in ast.walk(tree):
            if type(node) not in SAFE_AST_NODES:
                errors.append(
                    f"Forbidden operation: {type(node).__name__}"
                )
        return errors

    @staticmethod
    def extract_references(formula: str) -> list[str]:
        """
        Parse the formula and return all Name nodes that are not
        built-in function names or special variables (t, dt).
        These are the element names the formula depends on.

        e.g. "Daily_Rainfall * RunoffCoeff"
             → ["Daily_Rainfall", "RunoffCoeff"]

        e.g. "SoilMoisture.storage * 0.01"
             → ["SoilMoisture.storage"]    ← dot-notation as single ref

        Returns deduplicated list preserving first-occurrence order.
        """
        RESERVED = set(SAFE_FUNCTIONS.keys()) | {"t", "dt", "True", "False"}
        refs = []
        seen = set()
        try:
            tree = ast.parse(formula, mode='eval')
        except SyntaxError:
            return []

        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id not in RESERVED:
                if node.id not in seen:
                    refs.append(node.id)
                    seen.add(node.id)
            elif isinstance(node, ast.Attribute):
                # Reconstruct "element.port" from AST
                if isinstance(node.value, ast.Name):
                    ref = f"{node.value.id}.{node.attr}"
                    if ref not in seen:
                        refs.append(ref)
                        seen.add(ref)
        return refs

    @staticmethod
    def suggest_correction(unknown_name: str,
                           known_names: list[str]) -> str | None:
        """
        If unknown_name is close to a known element name (edit distance ≤ 2),
        return the closest match as a suggestion. Used in error messages.
        Returns None if no close match found.
        """
```

---

## 12. Results Store

**File:** `hydrosim/engine/results.py`

```python
class ResultsStore:
    """
    Holds the complete time history of tracked output ports.
    Pre-allocated at the start of simulation for performance.
    Populated by the runner's timestep loop.
    Read by the GUI's result viewer.
    """

    def __init__(
        self,
        timesteps:     np.ndarray,              # shape (n_steps,)
        tracked:       list[tuple[str, str]],   # [(element_id, port_name), ...]
        element_names: dict[str, str],           # {element_id: element_name}
    ):
        self.timesteps     = timesteps
        self.element_names = element_names
        self._n            = len(timesteps)

        # Pre-allocate output arrays
        # shape: (n_steps,) per tracked (element_id, port_name) pair
        self._arrays: dict[tuple[str, str], np.ndarray] = {
            key: np.zeros(self._n, dtype=np.float64)
            for key in tracked
        }

        # Runtime metadata
        self.completed_steps: int   = 0
        self.was_stopped:     bool  = False
        self.run_duration_s:  float = 0.0   # wall-clock seconds

    def record(self, step: int, state: SimState) -> None:
        """
        Record all tracked port values from state at the given step index.
        Called once per timestep by the runner.
        """
        for (element_id, port_name), array in self._arrays.items():
            array[step] = state.get(element_id, port_name)
        self.completed_steps = step + 1

    def get_series(self, element_id: str, port_name: str) -> np.ndarray:
        """
        Return the recorded time series for a specific port.
        Raises KeyError if not tracked.
        """
        return self._arrays[(element_id, port_name)]

    def get_series_by_name(self, element_name: str,
                           port_name: str) -> np.ndarray:
        """
        Lookup by element name instead of ID.
        Useful for GUI — user thinks in names not UUIDs.
        """
        element_id = next(
            (eid for eid, name in self.element_names.items()
             if name == element_name),
            None
        )
        if element_id is None:
            raise KeyError(f"No element named {element_name!r}")
        return self.get_series(element_id, port_name)

    def get_all_series(self) -> dict[str, dict[str, np.ndarray]]:
        """
        Return all tracked series as nested dict:
        {element_name: {port_name: np.ndarray}}
        """
        result: dict[str, dict[str, np.ndarray]] = {}
        for (element_id, port_name), array in self._arrays.items():
            name = self.element_names.get(element_id, element_id)
            if name not in result:
                result[name] = {}
            result[name][port_name] = array
        return result

    def get_completed_timesteps(self) -> np.ndarray:
        """
        Return only the portion of the timesteps array that was completed.
        Useful when simulation was stopped early.
        """
        return self.timesteps[:self.completed_steps]

    def export_dataframe(self) -> "pd.DataFrame":
        """
        Export all tracked series as a Pandas DataFrame.
        Columns: "time_days", then "ElementName.port_name" per series.
        """
        import pandas as pd
        data = {"time_days": self.get_completed_timesteps()}
        for (eid, port), array in self._arrays.items():
            name = self.element_names.get(eid, eid)
            col  = f"{name}.{port}"
            data[col] = array[:self.completed_steps]
        return pd.DataFrame(data)

    @property
    def is_complete(self) -> bool:
        return self.completed_steps >= self._n and not self.was_stopped
```

---

## 13. Complete Data Flow

This diagram traces data from user configuration to displayed results.

```
USER BUILDS MODEL IN GUI
         │
         ▼
  ModelGraph.add_element()         ← elements placed on canvas
  ModelGraph.add_connection()       ← connections drawn
         │
         ▼
  ModelValidator.validate_all()     ← triggered by Run button
         │
    ┌────┴────┐
  errors    no errors
    │            │
  show UI       ▼
  dialog   SimulationRunner.__init__(graph, settings)
                │
                ▼
           runner._validate()           ← re-validate (safety check)
                │
                ▼
           runner._build_execution_order()
           → graph.get_execution_order()
           → nx.topological_sort()
           → [Constant, TimeSeries, Expression, WaterStore, TimeHistoryResult]
                │
                ▼
           runner._initialise_state()   → SimState(t=0, dt=1, values={}, storage={})
                │
                ▼
           runner._prepare_elements()
           → TimeSeries.prepare()       → builds scipy interpolator
           → Expression.prepare()       → builds ExpressionParser
                │
                ▼
           runner._initialise_stocks()
           → WaterStore.initialise()    → state.storage["ws_id"] = 80.0
                │
                ▼
           runner._build_results_store()
           → ResultsStore(n_steps=365, tracked=[("ws_id","storage")])
                │
                ▼
         ┌──────────────────────────────────────────────────────┐
         │           TIMESTEP LOOP  t = 0, 1, 2 ... 364        │
         │                                                      │
         │  For each element in [Const, TS, Expr, WS, THR]:    │
         │                                                      │
         │  1. solver.resolve_inputs(element, state)            │
         │     → reads state.values for upstream elements       │
         │     → returns {port_name: float}                     │
         │                                                      │
         │  2. element.compute(state, connections_in)           │
         │     Constant:    state.set(id, "value", 0.3)         │
         │     TimeSeries:  state.set(id, "value", interp(t))   │
         │     Expression:  state.set(id, "value", 3.69)        │
         │     WaterStore:  s += (3.69 - 0) * 1.0              │
         │                  state.set(id, "storage", 83.69)     │
         │                  state.storage[id] = 83.69           │
         │     TimeHist:    (no-op)                             │
         │                                                      │
         │  3. results.record(step, state)                      │
         │     → arrays["ws_id","storage"][step] = 83.69        │
         │                                                      │
         │  4. progress_callback(step / 365)                    │
         └──────────────────────────────────────────────────────┘
                │
                ▼
         ResultsStore (complete)
                │
                ▼
         GUI reads results.get_all_series()
                │
                ▼
         PyQtGraph renders hydrograph
```

---

## 14. Error Types

**File:** `hydrosim/model/base.py` and `hydrosim/engine/runner.py`

```python
# ── Validation errors (model layer) ──────────────────────────

class HydroSimError(Exception):
    """Base for all HydroSim errors."""

@dataclass
class ValidationError:
    """A single model validation error (not an exception — it's data)."""
    code:       str        # e.g. "MISSING_REQUIRED_INPUT"
    element_id: str | None # which element caused it (None = model-level)
    message:    str        # human-readable, shown in validation dialog
    suggestion: str = ""   # optional "did you mean X?" hint

# Error codes (constants):
ERR_NO_ELEMENTS          = "NO_ELEMENTS"
ERR_MISSING_REQUIRED_INPUT = "MISSING_REQUIRED_INPUT"
ERR_CIRCULAR_DEPENDENCY  = "CIRCULAR_DEPENDENCY"
ERR_INVALID_FORMULA      = "INVALID_FORMULA"
ERR_UNKNOWN_REFERENCE    = "UNKNOWN_REFERENCE"
ERR_INVALID_PARAMETER    = "INVALID_PARAMETER"
ERR_EMPTY_TIMESERIES     = "EMPTY_TIMESERIES"
ERR_BOUNDS_VIOLATION     = "BOUNDS_VIOLATION"

@dataclass
class ValidationWarning:
    """A non-blocking issue logged to the simulation log."""
    code:       str
    element_id: str | None
    message:    str

WARN_UNITS_MISMATCH      = "UNITS_MISMATCH"
WARN_TIMESERIES_SHORT    = "TIMESERIES_SHORT"
WARN_MISSING_DESCRIPTION = "MISSING_DESCRIPTION"
WARN_WATER_BALANCE_ERROR = "WATER_BALANCE_ERROR"

# ── Runtime exceptions (engine layer) ────────────────────────

class SimulationError(HydroSimError):
    """Raised when model validation fails before simulation starts."""
    def __init__(self, errors: list[ValidationError]):
        self.errors = errors
        super().__init__(f"{len(errors)} validation error(s)")

class SimulationAborted(HydroSimError):
    """Raised when stop() is called during a run."""
    def __init__(self, step: int, t: float):
        self.step = step
        self.t    = t
        super().__init__(f"Simulation aborted at step {step} (t={t:.2f})")

class CircularDependencyError(HydroSimError):
    """Raised by ModelGraph when a cycle is detected."""
    def __init__(self, cycles: list[list[str]]):
        self.cycles = cycles
        super().__init__(f"Circular dependency: {cycles}")

class ExpressionEvaluationError(HydroSimError):
    """Raised by ExpressionParser when formula evaluation fails."""

class ModelFileError(HydroSimError):
    """Raised by ModelSerialiser when a file cannot be parsed."""

class VersionMismatchError(HydroSimError):
    """Raised when file_format_version > CURRENT_FORMAT_VERSION."""
    def __init__(self, file_version: str, current_version: str):
        self.file_version    = file_version
        self.current_version = current_version
        super().__init__(
            f"File requires HydroSim format v{file_version}; "
            f"this version supports up to v{current_version}"
        )
```

---

## 15. Inter-Module Contracts

These are the precise boundaries between modules. Claude Code must never cross them.

### 15.1 What `model/` provides to `engine/`

| Provided by | Consumed by | What |
|---|---|---|
| `ModelGraph` | `SimulationRunner` | Elements, connections, execution order |
| `ElementBase.compute()` | `TimeStepSolver` | Per-timestep computation |
| `ElementBase.is_stock()` | `SimulationRunner` | Identifies state variables |
| `TimeSeries.prepare()` | `SimulationRunner` | Interpolator setup |
| `Expression.prepare()` | `SimulationRunner` | Parser setup |
| `WaterStore.initialise()` | `SimulationRunner` | Initial state |
| `ModelValidator` | `SimulationRunner` | Pre-run validation |
| `SimulationSettings` | `SimulationRunner` | Time parameters |

### 15.2 What `engine/` provides to GUI

| Provided by | Consumed by | What |
|---|---|---|
| `SimulationRunner.run()` | GUI toolbar Run button | Synchronous run (for testing) |
| `SimulationRunner.stop()` | GUI toolbar Stop button | Abort signal |
| `ResultsStore.get_all_series()` | Result viewer | Time series data for plotting |
| `ResultsStore.export_dataframe()` | Export CSV button | Pandas DataFrame |
| `ExpressionParser.validate_syntax()` | Expression dialog | Live formula validation |
| `ExpressionParser.extract_references()` | Expression dialog | Available elements chips |

### 15.3 What `model/` provides to GUI

| Provided by | Consumed by | What |
|---|---|---|
| `ModelGraph.add_element()` | Canvas drop handler | Element placement |
| `ModelGraph.add_connection()` | Canvas connection draw | Link elements |
| `ModelGraph.remove_element()` | Canvas delete handler | Element removal |
| `ModelGraph.elements` | Canvas render | Element positions and names |
| `ModelGraph.connections` | Canvas render | Connection arrows |
| `ModelSerialiser.save()` | File → Save | Write .hydrosim file |
| `ModelSerialiser.load()` | File → Open | Read .hydrosim file |
| `ElementBase.validate()` | Property dialogs | Real-time field validation |

---

## 16. Key Invariants Claude Code Must Preserve

These invariants must hold at all times. Tests should verify them.

**1. Stock elements break dependency cycles**
`WaterStore.is_stock()` returns `True`. The graph builder must NOT add a NetworkX edge for connections originating from a stock element. This is what allows a WaterStore output to feed back into an Expression without creating a cycle.

**2. State is read-before-write for stocks**
In `WaterStore.compute()`, the previous storage is read from `state.storage[self.id]` BEFORE computing the new value. Never read `state.get(self.id, "storage")` inside compute — that would read the value just written in the same timestep.

**3. prepare() before compute()**
`TimeSeries` and `Expression` have a `prepare()` method that must be called before the timestep loop. `compute()` raises `RuntimeError` if called without `prepare()`. The runner guarantees this ordering.

**4. All output ports written every timestep**
Every element's `compute()` must call `state.set()` for EVERY output port, even if the value is 0.0 or unchanged. Partial writes cause downstream elements to read stale values.

**5. Results arrays are pre-allocated**
`ResultsStore` allocates `np.zeros(n_steps)` arrays before the loop starts. `record()` writes by index `array[step] = value`. Never append to lists and convert — this guarantees O(1) write and no memory reallocation during the loop.

**6. Model layer never imports engine**
`hydrosim/model/*.py` files must never import from `hydrosim/engine/`. Verify with: `grep -r "from hydrosim.engine" hydrosim/model/` (should return nothing).

**7. Element IDs are UUIDs, element names are user-visible**
IDs (`str(uuid.uuid4())`) are internal — never shown in the UI except as small monospace text on cards. Names are user-defined, used in formulas, and must be unique within a model. All formula parsing uses names; all state lookups use IDs.

**8. Connections_in uses port names, not element IDs**
The dict passed to `element.compute()` is `{port_name: float}` — keyed by the destination element's port names. For Expression elements, port names equal the referenced element names (by design). The solver handles the mapping from element ID to value using state.

**9. Water balance must close**
After every WaterStore timestep: `|ΔS - (inflow - outflow - overflow + deficit) * dt| < 1e-9`. The runner checks this and logs `WARN_WATER_BALANCE_ERROR` if violated. A failing water balance indicates a bug in WaterStore.compute().

**10. JSON round-trip is lossless**
For every element type: `element == ElementClass.from_dict(element.to_dict())` (with appropriate `__eq__` defined). The serialiser tests verify this for all five element types.

---

*End of HydroSim Backend Schema v1.0*
