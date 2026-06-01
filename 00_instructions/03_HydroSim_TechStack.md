# HydroSim — Technology Stack Document
## Reference for Claude Code Development

**Version:** 1.0  
**Status:** Approved for Development  
**Prepared for:** Claude Code (AI-assisted development)  
**Companion documents:** PRD v1.0, Application Flow v1.0  
**Date:** May 2026

---

## Table of Contents

1. [Philosophy & Guiding Principles](#1-philosophy--guiding-principles)
2. [Stack Overview](#2-stack-overview)
3. [Core Runtime](#3-core-runtime)
4. [GUI Framework](#4-gui-framework)
5. [Plotting & Visualisation](#5-plotting--visualisation)
6. [Numerical & Scientific Computing](#6-numerical--scientific-computing)
7. [Data Handling](#7-data-handling)
8. [Model & Graph Infrastructure](#8-model--graph-infrastructure)
9. [Expression Parsing & Evaluation](#9-expression-parsing--evaluation)
10. [File I/O & Serialisation](#10-file-io--serialisation)
11. [Performance Acceleration](#11-performance-acceleration)
12. [Testing & Quality](#12-testing--quality)
13. [Packaging & Distribution](#13-packaging--distribution)
14. [Developer Tooling](#14-developer-tooling)
15. [Dependency Matrix](#15-dependency-matrix)
16. [Version Pinning Strategy](#16-version-pinning-strategy)
17. [Platform Support](#17-platform-support)
18. [Future Stack Considerations (Phase 2+)](#18-future-stack-considerations-phase-2)
19. [What NOT to Use](#19-what-not-to-use)
20. [pyproject.toml Template](#20-pyprojecttoml-template)

---

## 1. Philosophy & Guiding Principles

Every library chosen for HydroSim must satisfy at least three of these four criteria:

**1. Claude Code familiarity**
The library must be well within Claude Code's training data — widely documented, actively maintained, and used across thousands of open-source projects. Obscure or highly specialised libraries slow down AI-assisted development because code suggestions become unreliable.

**2. Scientific Python ecosystem alignment**
Libraries must integrate cleanly with the NumPy/SciPy/Pandas ecosystem — HydroSim's numerical backbone. Libraries that pass data as native Python lists, custom objects, or non-standard array types create unnecessary conversion overhead.

**3. No unnecessary complexity**
If a standard library or a simpler library can do the job adequately, use it. Complexity has a cost: more dependencies, longer install times, more things that can break, and more surface area for Claude Code to make mistakes.

**4. Longevity and maintenance**
Libraries must have active maintainers, regular releases, and a meaningful user community. A library that hasn't been updated in 2 years is a liability.

**Explicit priority order when trade-offs arise:**
```
Correctness > Reliability > Claude familiarity > Performance > Features
```

---

## 2. Stack Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        HydroSim Stack                            │
├──────────────┬───────────────────────────────────────────────────┤
│ LAYER        │ LIBRARIES                                         │
├──────────────┼───────────────────────────────────────────────────┤
│ GUI          │ PyQt6  +  PyQtGraph                               │
├──────────────┼───────────────────────────────────────────────────┤
│ Canvas       │ PyQt6 QGraphicsScene / QGraphicsView (native)     │
├──────────────┼───────────────────────────────────────────────────┤
│ Plotting     │ PyQtGraph (primary)  +  Matplotlib (export/print) │
├──────────────┼───────────────────────────────────────────────────┤
│ Numerical    │ NumPy  +  SciPy                                   │
├──────────────┼───────────────────────────────────────────────────┤
│ Data         │ Pandas                                            │
├──────────────┼───────────────────────────────────────────────────┤
│ Graph/Model  │ NetworkX  (dependency resolution)                 │
├──────────────┼───────────────────────────────────────────────────┤
│ Expr Parser  │ Python ast (stdlib)  +  simpleeval               │
├──────────────┼───────────────────────────────────────────────────┤
│ Serialiser   │ json (stdlib)  +  pydantic                        │
├──────────────┼───────────────────────────────────────────────────┤
│ Performance  │ Numba (optional JIT, Phase 2)                     │
├──────────────┼───────────────────────────────────────────────────┤
│ Testing      │ pytest  +  pytest-qt  +  pytest-cov               │
├──────────────┼───────────────────────────────────────────────────┤
│ Packaging    │ Poetry  +  PyInstaller                            │
├──────────────┼───────────────────────────────────────────────────┤
│ Dev Tools    │ Black  +  Ruff  +  mypy  +  pre-commit            │
└──────────────┴───────────────────────────────────────────────────┘
```

---

## 3. Core Runtime

### Python 3.11+

**Why 3.11 specifically:**
- 10–60% speed improvement over Python 3.9 for numerical workloads (faster CPython interpreter)
- `tomllib` in stdlib (useful for config files)
- Improved error messages — critically important for a hydrologist debugging models
- `typing.Self` and improved type hints — cleaner code for Claude Code to generate
- `ExceptionGroup` — useful for collecting multiple validation errors in one pass
- Well within Claude Code's training data — the most widely documented modern Python version

**Minimum version:** 3.11  
**Tested against:** 3.11, 3.12  
**Not supported:** < 3.10 (no match statements, worse typing support)

**Key stdlib modules used directly (no installation needed):**

| Module | Use in HydroSim |
|---|---|
| `ast` | Expression parser — safely parse formula strings |
| `json` | Model file save/load |
| `dataclasses` | Port, Connection, SimState, ValidationError data structures |
| `typing` | Type annotations throughout (Protocol, TypedDict, Literal) |
| `enum` | ElementCategory, PortType, TimeSeriesType enums |
| `uuid` | Auto-generate element IDs |
| `datetime` | Calendar-mode timestamps |
| `pathlib` | File path handling (never use `os.path` directly) |
| `logging` | Simulation log, debug output |
| `copy` | Deep copying model state during simulation |
| `abc` | `ElementBase` abstract base class |
| `math` | Math functions in expression evaluator namespace |
| `threading` | Background simulation thread |
| `queue` | Progress updates from simulation thread to GUI |

---

## 4. GUI Framework

### PyQt6 6.6+

**Package:** `PyQt6`  
**Install:** `pip install PyQt6`  
**Licence:** GPL v3 (open source use) / Commercial (for closed-source distribution)  
**Docs:** https://www.riverbankcomputing.com/static/Docs/PyQt6/

**Why PyQt6 over alternatives:**

| Option | Decision | Reason |
|---|---|---|
| **PyQt6** | ✅ **CHOSEN** | Most Claude Code training data, most tutorials, best community support |
| PySide6 | Viable | LGPL licence advantage, but less Claude familiarity; switch later if licensing required |
| PyQt5 | ❌ | Qt5 is aging; no Python 3.12+ wheels guaranteed |
| Tkinter | ❌ | Cannot build a production QGraphicsScene node editor |
| Electron | ❌ | Massively overkill, wrong ecosystem, kills Python integration |
| Dear PyGui | ❌ | No QGraphicsScene equivalent; immature for this use case |

**Core Qt modules used in HydroSim:**

| Qt Module | Purpose |
|---|---|
| `PyQt6.QtWidgets` | QMainWindow, QDialog, QGraphicsView, QGraphicsScene, all widgets |
| `PyQt6.QtGui` | QPainter, QPen, QBrush, QColor, QFont, QIcon, QPainterPath |
| `PyQt6.QtCore` | QThread, QTimer, pyqtSignal, Qt namespace, QPointF, QRectF |
| `PyQt6.QtSvg` | Loading SVG element icons |
| `PyQt6.QtSvgWidgets` | Displaying SVG icons in widgets |

**Key Qt patterns Claude Code must follow:**

```python
# CORRECT — PyQt6 enum access (Qt6 style, fully qualified)
alignment = Qt.AlignmentFlag.AlignLeft
pen_style = Qt.PenStyle.SolidLine
key = Qt.Key.Key_Delete

# WRONG — PyQt5 style (will fail in PyQt6)
alignment = Qt.AlignLeft          # AttributeError
pen_style = Qt.SolidLine          # AttributeError

# CORRECT — Signal definition
class MyWidget(QWidget):
    element_added = pyqtSignal(str)        # emits element id
    simulation_progress = pyqtSignal(float)  # emits 0.0-1.0

# CORRECT — Thread-safe GUI updates from QThread
# Never update GUI directly from a non-GUI thread
# Use signals to communicate from QThread → main thread
class SimulationThread(QThread):
    progress = pyqtSignal(float)
    finished = pyqtSignal(object)  # emits ResultsStore
    error = pyqtSignal(str)

    def run(self):
        try:
            for step in engine.steps():
                self.progress.emit(step / total)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))
```

**QGraphicsScene/View patterns for the canvas:**

```python
# Element items inherit from QGraphicsItem (not QGraphicsWidget)
# Use QGraphicsItem for performance — QGraphicsWidget is heavier
class ElementItem(QGraphicsItem):
    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, CARD_WIDTH, self.card_height)

    def paint(self, painter: QPainter, option, widget=None):
        # All drawing via QPainter — no QWidget children inside
        ...

# Connection arrows inherit from QGraphicsPathItem
class ConnectionItem(QGraphicsPathItem):
    def update_path(self):
        path = QPainterPath()
        # Cubic bezier: P0 → P1 (ctrl) → P2 (ctrl) → P3
        path.moveTo(self.start)
        path.cubicTo(ctrl1, ctrl2, self.end)
        self.setPath(path)
```

---

## 5. Plotting & Visualisation

### PyQtGraph 0.13+ (Primary)

**Package:** `pyqtgraph`  
**Install:** `pip install pyqtgraph`  
**Licence:** MIT  
**Docs:** https://pyqtgraph.readthedocs.io

**Why PyQtGraph over Matplotlib for in-app plotting:**

PyQtGraph is built on top of Qt's native `QGraphicsScene`, which means it integrates seamlessly into a PyQt6 application without any embedding hacks. Performance comparisons show PyQtGraph renders 75–150× faster than Matplotlib's `FigureCanvasQTAgg` for the same dataset — important when showing a 365-step hydrograph that updates after every model edit.

| Criterion | PyQtGraph | Matplotlib |
|---|---|---|
| Speed | ✅ Very fast (Qt native) | ❌ Slow (~75-150× slower for live data) |
| Qt integration | ✅ Native (IS a Qt widget) | ⚠️ Embedded (wrapper widget, some lag) |
| Interactivity | ✅ Native pan/zoom/crosshair | ⚠️ Requires toolbar, less smooth |
| Publication quality | ⚠️ Good but not LaTeX-quality | ✅ Excellent |
| NumPy integration | ✅ Directly accepts np.ndarray | ✅ Directly accepts np.ndarray |
| Claude familiarity | ✅ High | ✅ Very high |
| Hydrograph display | ✅ Perfect | ✅ Perfect |

**PyQtGraph used for:**
- `TimeHistoryResult` viewer — interactive hydrograph with crosshair, pan, zoom
- Mini sparkline previews inside element cards on canvas
- Real-time progress chart during simulation (future feature)

**Key PyQtGraph patterns:**

```python
import pyqtgraph as pg

# Set PyQtGraph to use PyQt6 BEFORE any imports
pg.mkQApp()  # or set QT_API env var

# Standard hydrograph plot
plot_widget = pg.PlotWidget()
plot_widget.setBackground('w')  # white background
plot_widget.showGrid(x=True, y=True, alpha=0.3)
plot_widget.setLabel('left', 'Storage', units='mm')
plot_widget.setLabel('bottom', 'Time', units='days')

# Add a time series
curve = plot_widget.plot(
    x=time_array,       # np.ndarray
    y=storage_array,    # np.ndarray
    pen=pg.mkPen(color='#2E86C1', width=2),
    name='SoilMoisture.storage'
)

# Crosshair (standard hydrologist tool)
vLine = pg.InfiniteLine(angle=90, movable=False)
hLine = pg.InfiniteLine(angle=0, movable=False)
plot_widget.addItem(vLine, ignoreBounds=True)
plot_widget.addItem(hLine, ignoreBounds=True)
```

---

### Matplotlib 3.8+ (Secondary — Export Only)

**Package:** `matplotlib`  
**Install:** `pip install matplotlib`  
**Licence:** PSF-based (permissive)  
**Docs:** https://matplotlib.org/stable/

**Why keep Matplotlib at all:**
Matplotlib is used exclusively for **export-quality chart rendering** — when the user clicks "Save as PNG" or "Print". PyQtGraph's export quality, while good, does not match Matplotlib for 300 DPI publication figures. Matplotlib also has a much richer set of plot styles and annotations useful for export.

**Matplotlib used for:**
- High-resolution PNG/SVG/PDF export of hydrographs
- Future: Flow duration curve export, flood frequency plot export
- NOT used for any in-app interactive display

```python
# Export-quality figure generation (runs in background thread)
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def export_hydrograph(results: ResultsStore, filepath: Path, dpi: int = 150):
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(results.timesteps, results.values['SoilMoisture']['storage'],
            color='#2E86C1', linewidth=1.5, label='SoilMoisture.storage')
    ax.set_xlabel('Time (days)')
    ax.set_ylabel('Storage (mm)')
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(filepath, dpi=dpi)
    plt.close(fig)  # ALWAYS close figures to prevent memory leaks
```

---

## 6. Numerical & Scientific Computing

### NumPy 1.26+

**Package:** `numpy`  
**Install:** `pip install numpy`  
**Licence:** BSD  
**Docs:** https://numpy.org/doc/stable/

NumPy is the foundational numerical library. In HydroSim, almost all simulation state is stored and computed as NumPy arrays.

**Where NumPy is used:**

| Use case | NumPy feature |
|---|---|
| Time array | `np.linspace(start, end, n_steps)` |
| Results storage | `np.zeros(n_steps)` arrays per output port |
| TimeSeries interpolation | `np.interp()` for linear interpolation |
| Forward Euler integration | Vectorised addition: `storage += net_flux * dt` |
| Water balance check | `np.sum()`, `np.abs()`, `np.max()` |
| Statistics | `np.mean()`, `np.std()`, `np.percentile()` |
| Flow duration curve | `np.sort()`, `np.arange()` |

**Critical patterns Claude Code must follow:**

```python
import numpy as np

# ALWAYS pre-allocate result arrays before the simulation loop
# NEVER append to lists inside the loop and convert at the end
n_steps = int((end_time - start_time) / dt)
storage_array = np.zeros(n_steps, dtype=np.float64)
overflow_array = np.zeros(n_steps, dtype=np.float64)

# Use float64 consistently — float32 causes precision errors in hydrology
# (cumulative rounding errors over 365+ timesteps are significant)
DTYPE = np.float64  # define this as a module-level constant

# Vectorised operations where possible (avoid Python for-loops on arrays)
# BAD:
for i in range(len(arr)):
    result[i] = arr[i] * 2

# GOOD:
result = arr * 2  # vectorised, ~100x faster

# NaN handling — use np.nan for missing values, not 0.0
# Check for NaN propagation in results
if np.any(np.isnan(storage_array)):
    raise SimulationError("NaN detected in storage — check model inputs")
```

---

### SciPy 1.11+

**Package:** `scipy`  
**Install:** `pip install scipy`  
**Licence:** BSD  
**Docs:** https://docs.scipy.org/doc/scipy/

SciPy provides the advanced scientific functions that NumPy alone doesn't cover.

**Where SciPy is used in HydroSim:**

| SciPy module | HydroSim use |
|---|---|
| `scipy.interpolate.interp1d` | Advanced TimeSeries interpolation (cubic, nearest) |
| `scipy.interpolate.PchipInterpolator` | Monotone cubic interpolation for LookupTable (Phase 2) |
| `scipy.stats` | Statistical distribution fitting for FloodFrequencyResult (Phase 2) |
| `scipy.stats.genextreme` | GEV distribution for flood frequency analysis (Phase 2) |
| `scipy.stats.gumbel_r` | Gumbel distribution for flood frequency (Phase 2) |
| `scipy.optimize` | Parameter calibration / curve fitting (Phase 3) |

**Phase 1 SciPy usage (minimal — primarily interpolation):**

```python
from scipy.interpolate import interp1d
import numpy as np

class TimeSeries:
    def _build_interpolator(self):
        """Build interpolation function once, reuse during simulation."""
        self._interpolator = interp1d(
            self.times,   # x: time values (np.ndarray)
            self.values,  # y: data values (np.ndarray)
            kind='linear',       # or 'previous' for step interpolation
            bounds_error=False,  # don't raise on extrapolation
            fill_value=(self.values[0], self.values[-1])  # flat extrapolation
        )

    def get_value_at(self, t: float) -> float:
        return float(self._interpolator(t))
```

---

## 7. Data Handling

### Pandas 2.1+

**Package:** `pandas`  
**Install:** `pip install pandas`  
**Licence:** BSD  
**Docs:** https://pandas.pydata.org/docs/

Pandas is used for:
- Parsing and validating CSV imports in `TimeSeries` dialogs
- Storing and exporting results as DataFrames
- Date/time handling in Calendar mode (leveraging `DatetimeIndex`)
- The `ExportResult` CSV writer

**Where Pandas is used:**

```python
import pandas as pd
from pathlib import Path

# CSV import in TimeSeries dialog
def parse_timeseries_csv(filepath: Path) -> pd.DataFrame:
    df = pd.read_csv(filepath, parse_dates=[0])  # auto-detect date column
    if df.shape[1] < 2:
        raise ValueError(f"Expected 2 columns, got {df.shape[1]}")
    df.columns = ['time', 'value']
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    if df['value'].isna().any():
        bad_rows = df[df['value'].isna()].index.tolist()
        raise ValueError(f"Non-numeric values in rows: {bad_rows}")
    return df.dropna().sort_values('time').reset_index(drop=True)

# Results export
def export_results_csv(results: ResultsStore, filepath: Path):
    data = {'time_days': results.timesteps}
    if results.start_date:
        data['date'] = pd.date_range(
            start=results.start_date,
            periods=len(results.timesteps),
            freq=f"{results.dt}D"
        )
    for element_id, ports in results.values.items():
        for port_name, array in ports.items():
            col_name = f"{results.element_names[element_id]}.{port_name}"
            data[col_name] = array
    pd.DataFrame(data).to_csv(filepath, index=False, float_format='%.6f')
```

**Important Pandas guidance:**

```python
# Use copy() when slicing DataFrames to avoid SettingWithCopyWarning
subset = df[df['value'] > 0].copy()

# Use .iloc for positional indexing, .loc for label indexing
# Never mix them — it confuses Claude Code

# For time-based operations, use pd.Timestamp for calendar dates
start = pd.Timestamp('2020-01-01')
end = pd.Timestamp('2020-12-31')
date_range = pd.date_range(start=start, end=end, freq='D')
```

---

## 8. Model & Graph Infrastructure

### NetworkX 3.2+

**Package:** `networkx`  
**Install:** `pip install networkx`  
**Licence:** BSD  
**Docs:** https://networkx.org/documentation/stable/

NetworkX handles the **dependency graph** of the model — determining which elements to compute in which order, and detecting circular dependencies.

**Why NetworkX:**
- Claude Code has extensive training data on NetworkX
- Topological sort is a one-liner: `list(nx.topological_sort(G))`
- Cycle detection is built in: `nx.is_directed_acyclic_graph(G)`
- Trivially correct — no need to implement graph algorithms from scratch

**Where NetworkX is used:**

```python
import networkx as nx

class ModelGraph:
    def __init__(self):
        self._graph = nx.DiGraph()
        self._elements: dict[str, ElementBase] = {}

    def add_element(self, element: ElementBase):
        self._elements[element.id] = element
        self._graph.add_node(element.id, element=element)

    def add_connection(self, connection: Connection):
        # Skip edges FROM stock elements — they don't create dependency cycles
        # because stocks use their previous timestep value
        from_elem = self._elements[connection.from_element_id]
        if not isinstance(from_elem, StockElement):
            self._graph.add_edge(
                connection.from_element_id,
                connection.to_element_id,
                connection=connection
            )

    def get_execution_order(self) -> list[ElementBase]:
        """Returns elements in topologically sorted execution order."""
        if not nx.is_directed_acyclic_graph(self._graph):
            cycles = list(nx.simple_cycles(self._graph))
            raise CircularDependencyError(cycles)
        sorted_ids = list(nx.topological_sort(self._graph))
        return [self._elements[eid] for eid in sorted_ids
                if eid in self._elements]

    def get_dependencies(self, element_id: str) -> list[str]:
        """Returns element IDs that must be computed before this one."""
        return list(self._graph.predecessors(element_id))
```

**NetworkX is NOT used for:**
- Canvas layout (positions are managed by PyQt6 QGraphicsScene)
- Rendering connections (handled by `ConnectionItem` in Qt)
- Storing element data (elements stored in the `ModelGraph` dict, not the nx graph)

---

### Pydantic 2.5+

**Package:** `pydantic`  
**Install:** `pip install pydantic`  
**Licence:** MIT  
**Docs:** https://docs.pydantic.dev/latest/

Pydantic is used for **model file validation and serialisation**. It provides automatic type checking, clear error messages, and JSON schema generation — all critical for reliable `.hydrosim` file parsing.

**Why Pydantic:**
- Validates model files on load — catches corrupt or malformed files with clear error messages
- Auto-generates JSON schema for `.hydrosim` format documentation
- Claude Code generates Pydantic models fluently and correctly
- V2 (Rust-based core) is significantly faster than V1

**Pydantic models for serialisation:**

```python
from pydantic import BaseModel, field_validator, model_validator
from typing import Literal
from datetime import date

class ConstantSchema(BaseModel):
    id: str
    type: Literal["Constant"]
    name: str
    description: str = ""
    position: tuple[float, float]
    parameters: ConstantParameters

class ConstantParameters(BaseModel):
    value: float
    units: str = "-"

    @field_validator('value')
    @classmethod
    def must_be_finite(cls, v):
        import math
        if not math.isfinite(v):
            raise ValueError('value must be finite (not NaN or Inf)')
        return v

class WaterStoreSchema(BaseModel):
    id: str
    type: Literal["WaterStore"]
    name: str
    description: str = ""
    position: tuple[float, float]
    parameters: WaterStoreParameters

class WaterStoreParameters(BaseModel):
    initial_storage: float
    lower_bound: float = 0.0
    upper_bound: float | None = None
    units: str = "m3"

    @model_validator(mode='after')
    def bounds_must_be_valid(self):
        if self.upper_bound is not None:
            if self.lower_bound >= self.upper_bound:
                raise ValueError('lower_bound must be less than upper_bound')
            if not (self.lower_bound <= self.initial_storage <= self.upper_bound):
                raise ValueError('initial_storage must be within bounds')
        return self

# Discriminated union for loading any element type
ElementSchema = Annotated[
    ConstantSchema | TimeSeriesSchema | WaterStoreSchema |
    ExpressionSchema | TimeHistorySchema,
    Field(discriminator='type')
]
```

---

## 9. Expression Parsing & Evaluation

### Python `ast` (stdlib) + `simpleeval` 0.9+

**Package:** `simpleeval`  
**Install:** `pip install simpleeval`  
**Licence:** MIT  
**Docs:** https://github.com/danthedeckie/simpleeval

The expression evaluator needs to be **safe** (no arbitrary code execution), **fast** (called once per element per timestep), and **extensible** (custom functions, element references).

**Two-layer approach:**

**Layer 1 — Validation (at model build time): `ast` module**
When the user types a formula, use Python's `ast.parse()` to check syntax and walk the AST to verify only whitelisted node types are present. This happens in the GUI at edit time.

**Layer 2 — Evaluation (at simulation time): `simpleeval`**
`simpleeval` provides a sandboxed `eval`-like interface that accepts a names dict and a functions dict. It's faster than a custom AST walker and has been battle-tested for safe expression evaluation.

```python
from simpleeval import SimpleEval, NameNotDefined, FunctionNotDefined
import math

# Define the safe evaluation context
SAFE_FUNCTIONS = {
    'abs': abs,
    'sqrt': math.sqrt,
    'exp': math.exp,
    'log': math.log,
    'log10': math.log10,
    'sin': math.sin,
    'cos': math.cos,
    'tan': math.tan,
    'min': min,
    'max': max,
    'round': round,
    'floor': math.floor,
    'ceil': math.ceil,
    'if_': lambda cond, a, b: a if cond else b,  # if() is reserved; use if_
}

class ExpressionEvaluator:
    def __init__(self, formula: str):
        self.formula = formula
        self._evaluator = SimpleEval(functions=SAFE_FUNCTIONS)

    def evaluate(self, names: dict[str, float]) -> float:
        """Evaluate formula with current element values."""
        self._evaluator.names = names  # inject current element outputs
        try:
            result = self._evaluator.eval(self.formula)
            return float(result)
        except NameNotDefined as e:
            raise ExpressionEvaluationError(f"Unknown variable: {e}")
        except ZeroDivisionError:
            return 0.0  # return 0, log warning
        except Exception as e:
            raise ExpressionEvaluationError(str(e))
```

**Why `simpleeval` over raw `ast.literal_eval` or `eval()`:**
- `eval()` is a security risk — can execute arbitrary Python code
- `ast.literal_eval()` only handles literals, not expressions
- A custom AST walker is correct but ~200 lines of boilerplate
- `simpleeval` provides exactly the right abstraction: safe, configurable, maintained

---

## 10. File I/O & Serialisation

### `json` (stdlib) + Pydantic

The `.hydrosim` file format is plain JSON. No custom binary format, no YAML, no TOML.

**Rationale for JSON:**
- Human-readable — a hydrologist can open a `.hydrosim` file in a text editor and understand it
- Trivially versionable in git
- Claude Code handles JSON flawlessly
- No parsing library needed (stdlib `json` module)
- Pydantic adds schema validation on top

**File operations pattern:**

```python
import json
from pathlib import Path
from pydantic import ValidationError

def save_model(model: ModelGraph, filepath: Path) -> None:
    """Save model to .hydrosim JSON file."""
    data = ModelSerializer.to_dict(model)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_model(filepath: Path) -> ModelGraph:
    """Load model from .hydrosim JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        raw = json.load(f)

    # Version check
    file_version = raw.get('file_format_version', '0')
    if int(file_version) > CURRENT_FORMAT_VERSION:
        raise VersionMismatchError(file_version, CURRENT_FORMAT_VERSION)

    # Pydantic validation
    try:
        schema = HydroSimFileSchema.model_validate(raw)
    except ValidationError as e:
        raise ModelFileError(f"Invalid model file: {e}")

    return ModelSerializer.from_schema(schema)
```

---

## 11. Performance Acceleration

### Phase 1: Pure NumPy (No JIT)

For Phase 1, the simulation engine uses **pure NumPy vectorised operations**. This is sufficient for the Phase 1 scope:

- 365 daily timesteps × 5 elements = 1,825 operations
- Each operation is a simple float arithmetic expression
- Expected runtime: < 0.5 seconds on any modern hardware
- No JIT compilation needed or beneficial at this scale

**The simulation inner loop must be kept NumPy-vectorisable:**

```python
# GOOD — vectorisable design
# Pre-compute the full inflow array BEFORE the timestep loop when possible
# Then use NumPy slicing inside the loop
for i, t in enumerate(timesteps):
    inflow = inflow_array[i]   # np.ndarray lookup, not a function call
    storage = prev_storage + (inflow - outflow) * dt
    storage = np.clip(storage, lower_bound, upper_bound)
    storage_array[i] = storage

# BETTER — for simple elements with no inter-timestep dependencies
# Vectorise the entire simulation (no Python loop at all)
net_flux = inflow_array - outflow_array  # vectorised
storage_array = np.cumsum(net_flux * dt) + initial_storage
storage_array = np.clip(storage_array, lower_bound, upper_bound)
# Note: cumsum version doesn't handle bounds correctly — use loop for WaterStore
```

---

### Phase 2: Numba JIT (Optional Acceleration)

**Package:** `numba`  
**Install:** `pip install numba`  
**Licence:** BSD  
**Docs:** https://numba.readthedocs.io

Numba is listed as an **optional Phase 2 dependency** for when models grow to thousands of elements or Monte Carlo simulations require hundreds of realisations.

**When Numba becomes beneficial:**
- Monte Carlo: 1,000 realisations × 365 timesteps × 50 elements = 18,250,000 operations
- At this scale, Python loop overhead becomes significant
- Numba's `@jit(nopython=True)` eliminates Python overhead from numerical loops

```python
from numba import jit
import numpy as np

@jit(nopython=True, cache=True)
def run_waterstore_numba(
    inflow: np.ndarray,
    outflow: np.ndarray,
    initial_storage: float,
    lower_bound: float,
    upper_bound: float,
    dt: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """JIT-compiled WaterStore integration — ~10-50x faster than pure Python."""
    n = len(inflow)
    storage = np.zeros(n)
    overflow = np.zeros(n)
    deficit = np.zeros(n)
    s = initial_storage

    for i in range(n):
        s = s + (inflow[i] - outflow[i]) * dt
        if upper_bound > 0 and s > upper_bound:
            overflow[i] = (s - upper_bound) / dt
            s = upper_bound
        if s < lower_bound:
            deficit[i] = (lower_bound - s) / dt
            s = lower_bound
        storage[i] = s
    return storage, overflow, deficit
```

**Numba integration strategy:**
- Numba functions are defined but only called if `numba` is installed (`try: import numba`)
- Fall back to pure NumPy implementation if Numba is not available
- This makes Numba an optional performance enhancement, not a hard dependency
- First call to a Numba function is slow (JIT compilation) — warm up during app launch

---

## 12. Testing & Quality

### pytest 7.4+

**Package:** `pytest`  
**Install:** `pip install pytest`  
**Licence:** MIT  
**Docs:** https://docs.pytest.org

Primary test runner. All tests in `tests/` directory. Run with `pytest` or `pytest -v` for verbose.

```python
# tests/test_elements/test_waterstore.py

import pytest
import numpy as np
from hydrosim.model.elements.waterstore import WaterStore
from hydrosim.engine.runner import SimulationRunner

def test_waterstore_basic_integration():
    """Forward Euler integration over 10 steps."""
    store = WaterStore(
        name="test_store",
        initial_storage=100.0,
        lower_bound=0.0,
        upper_bound=200.0,
        units="mm"
    )
    # Constant inflow=5, outflow=2, dt=1 → storage increases 3/step
    inflow = np.full(10, 5.0)
    outflow = np.full(10, 2.0)
    storage, overflow, deficit = store.integrate(inflow, outflow, dt=1.0)
    assert storage[-1] == pytest.approx(130.0, abs=1e-9)
    assert np.all(overflow == 0)
    assert np.all(deficit == 0)

def test_waterstore_overflow():
    store = WaterStore(initial_storage=190.0, upper_bound=200.0)
    inflow = np.full(5, 5.0)
    outflow = np.zeros(5)
    storage, overflow, deficit = store.integrate(inflow, outflow, dt=1.0)
    assert storage[-1] == pytest.approx(200.0)
    assert np.sum(overflow) > 0

def test_waterstore_water_balance():
    """Mass must be conserved: ΔS = inflow - outflow - overflow + deficit."""
    store = WaterStore(initial_storage=50.0, upper_bound=100.0)
    inflow = np.random.uniform(0, 10, 100)
    outflow = np.random.uniform(0, 8, 100)
    storage, overflow, deficit = store.integrate(inflow, outflow, dt=1.0)
    delta_s = storage[-1] - 50.0
    total_in = np.sum(inflow) - np.sum(outflow) - np.sum(overflow) + np.sum(deficit)
    assert delta_s == pytest.approx(total_in, rel=1e-6)
```

---

### pytest-qt 4.2+

**Package:** `pytest-qt`  
**Install:** `pip install pytest-qt`  
**Licence:** MIT

Required for testing PyQt6 GUI components without launching a full display. Provides the `qtbot` fixture for simulating user interactions.

```python
# tests/test_gui/test_canvas.py

def test_element_placement(qtbot):
    from hydrosim.gui.canvas.scene import HydroScene
    scene = HydroScene()
    qtbot.addWidget(scene)

    # Simulate dropping an element
    from hydrosim.model.elements.constant import Constant
    element = Constant(name="TestConst", value=1.0, units="m")
    scene.add_element(element, position=(100, 200))

    assert len(scene.element_items) == 1
    item = scene.element_items[element.id]
    assert item.pos().x() == pytest.approx(100)
```

---

### pytest-cov 4.1+

**Package:** `pytest-cov`  
**Install:** `pip install pytest-cov`  
**Licence:** MIT

Coverage reporting. Run with:
```bash
pytest --cov=hydrosim --cov-report=html --cov-report=term-missing
```

**Coverage targets:**
- `hydrosim/model/` → ≥ 90% coverage
- `hydrosim/engine/` → ≥ 90% coverage
- `hydrosim/gui/` → ≥ 60% coverage (GUI code is harder to unit test)

---

## 13. Packaging & Distribution

### Poetry 1.7+

**Package:** `poetry`  
**Install:** `pip install poetry` (or via official installer)  
**Docs:** https://python-poetry.org/docs/

Poetry manages dependencies, virtual environments, and builds. All dependency versions are declared in `pyproject.toml`.

**Key Poetry commands:**
```bash
poetry install                  # install all dependencies
poetry install --with dev       # include dev dependencies
poetry run hydrosim             # run the app
poetry run pytest               # run tests
poetry build                    # build distribution packages
poetry add <package>            # add new dependency
poetry add --group dev <pkg>    # add dev-only dependency
```

---

### PyInstaller 6.3+ (Distribution)

**Package:** `pyinstaller`  
**Install:** `pip install pyinstaller`  
**Docs:** https://pyinstaller.org/en/stable/

Used to bundle HydroSim into a standalone executable for distribution to hydrologists who don't have Python installed.

```bash
# Build standalone executable
pyinstaller hydrosim.spec

# Output: dist/HydroSim/HydroSim.exe (Windows)
#         dist/HydroSim/HydroSim.app (macOS)
#         dist/HydroSim/HydroSim     (Linux)
```

**PyInstaller spec file considerations:**
- Include Qt plugins: `--collect-all PyQt6`
- Include resources: `--add-data "hydrosim/resources:resources"`
- Hidden imports: `--hidden-import pyqtgraph`

---

## 14. Developer Tooling

### Black 24+ (Code Formatter)

```bash
black hydrosim/ tests/     # format all Python files
black --check hydrosim/    # check without modifying (for CI)
```

Configuration in `pyproject.toml`:
```toml
[tool.black]
line-length = 100
target-version = ["py311"]
```

---

### Ruff 0.3+ (Linter)

**Faster than flake8, isort, and many other linters combined. Single tool.**

```bash
ruff check hydrosim/        # lint
ruff check --fix hydrosim/  # auto-fix safe issues
```

```toml
[tool.ruff]
line-length = 100
target-version = "py311"
select = ["E", "F", "W", "I", "UP", "B", "SIM"]
ignore = ["E501"]  # line length handled by Black
```

---

### mypy 1.8+ (Type Checker)

```bash
mypy hydrosim/
```

```toml
[tool.mypy]
python_version = "3.11"
strict = false          # start relaxed, tighten over time
warn_return_any = true
warn_unused_imports = true
ignore_missing_imports = true  # for PyQt6 stubs
```

**Type stubs for PyQt6:**
```bash
pip install PyQt6-stubs  # provides type information for mypy
```

---

### pre-commit 3.6+

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.1.0
    hooks:
      - id: black
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        args: [--fix]
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-json
      - id: check-yaml
```

---

## 15. Dependency Matrix

### Production Dependencies

| Package | Min Version | Purpose | Phase |
|---|---|---|---|
| `PyQt6` | 6.6.0 | GUI framework | 1 |
| `pyqtgraph` | 0.13.3 | Interactive plotting | 1 |
| `matplotlib` | 3.8.0 | Export-quality charts | 1 |
| `numpy` | 1.26.0 | Numerical arrays | 1 |
| `scipy` | 1.11.0 | Interpolation, statistics | 1 |
| `pandas` | 2.1.0 | CSV import/export, dates | 1 |
| `networkx` | 3.2.0 | Dependency graph, topo sort | 1 |
| `pydantic` | 2.5.0 | Model file validation | 1 |
| `simpleeval` | 0.9.13 | Safe expression evaluation | 1 |
| `numba` | 0.59.0 | JIT acceleration | 2 (optional) |
| `pint` | 0.23 | Units system | 2 |

### Development Dependencies

| Package | Min Version | Purpose |
|---|---|---|
| `pytest` | 7.4.0 | Test runner |
| `pytest-qt` | 4.2.0 | GUI testing |
| `pytest-cov` | 4.1.0 | Coverage reporting |
| `black` | 24.0.0 | Code formatter |
| `ruff` | 0.3.0 | Linter |
| `mypy` | 1.8.0 | Type checker |
| `PyQt6-stubs` | 6.6.0 | mypy type stubs for PyQt6 |
| `pre-commit` | 3.6.0 | Git hooks |
| `pyinstaller` | 6.3.0 | Distribution packaging |

---

## 16. Version Pinning Strategy

**Production dependencies:** Pin to minor version (`~=`):
```toml
numpy = "~=1.26"          # allows 1.26.x, not 1.27
scipy = "~=1.11"
pandas = "~=2.1"
PyQt6 = "~=6.6"
```

**Dev dependencies:** Pin to compatible release (`>=`):
```toml
pytest = ">=7.4"
black = ">=24.0"
```

**Why this strategy:**
- Minor version pins prevent unexpected breaking changes from patch releases
- Major version changes (e.g., NumPy 2.0) require explicit upgrade decision
- Dev tools are less version-sensitive — allow minor upgrades freely

**Lockfile:** `poetry.lock` is committed to the repository. This guarantees reproducible builds for all developers.

---

## 17. Platform Support

| Platform | Support level | Notes |
|---|---|---|
| Windows 10/11 (x64) | ✅ Primary | Most hydrologists use Windows |
| macOS 13+ (Apple Silicon + Intel) | ✅ Primary | PyQt6 has native ARM wheels |
| Ubuntu 22.04+ | ✅ Primary | For Linux users and CI |
| Other Linux (Fedora, Arch) | ⚠️ Best effort | Should work, not CI-tested |
| Windows ARM | ❌ Not supported | PyQt6 no ARM Windows wheels |
| Python 3.10 | ⚠️ Best effort | Missing some typing features |
| Python < 3.10 | ❌ Not supported | |

**CI matrix (GitHub Actions):**
```yaml
strategy:
  matrix:
    os: [windows-latest, macos-latest, ubuntu-latest]
    python-version: ["3.11", "3.12"]
```

---

## 18. Future Stack Considerations (Phase 2+)

These libraries are NOT used in Phase 1 but should be considered in the architecture so Phase 1 code doesn't block their adoption:

| Library | Purpose | Phase |
|---|---|---|
| `pint` | Physical units system — enforce unit compatibility between ports | 2 |
| `numba` | JIT acceleration for Monte Carlo simulation | 2 |
| `xarray` | N-dimensional labelled arrays for gridded hydrology data | 3 |
| `pyproj` | Coordinate reference system transformations | 3 |
| `shapely` | Geometric operations for catchment delineation | 3 |
| `geopandas` | Spatial dataframes for GIS integration | 3 |
| `dataretrieval` | USGS water data API client | 3 |
| `lmfit` | Parameter estimation and calibration | 3 |
| `SALib` | Sensitivity analysis (Sobol, Morris methods) | 3 |
| `HydroErr` | Hydrological model performance metrics (NSE, KGE) | 2 |

**Architecture decisions in Phase 1 that enable Phase 2:**
1. `Port` objects have a `units` field — ready for Pint integration
2. `ElementBase.get_output_value()` is designed per-timestep — Numba JIT can wrap it
3. `ResultsStore` uses `np.ndarray` — directly compatible with xarray
4. Model file format has `file_format_version` — enables migration scripts

---

## 19. What NOT to Use

These libraries are explicitly excluded. Claude Code must not introduce them:

| Library | Reason excluded |
|---|---|
| `eval()` built-in | Security risk — arbitrary code execution |
| `exec()` built-in | Security risk |
| `pickle` | Security risk for model files; use JSON |
| `PyQt5` / `PySide2` | Qt5 legacy — use PyQt6 |
| `tkinter` | Cannot build the required canvas |
| `wxPython` | Wrong ecosystem |
| `Kivy` | Wrong ecosystem |
| `Flask` / `FastAPI` | No web server needed in Phase 1 |
| `SQLite` / `SQLAlchemy` | Overkill — JSON files are sufficient |
| `Celery` | Overkill — QThread is sufficient |
| `Docker` | Overkill for a desktop app |
| `NodeGraphQt` | Deprecated (archived Oct 2025); build canvas natively |
| `pyqode` | Unmaintained — use QTextEdit with custom highlighter |
| `PyQwt` | Unmaintained — use PyQtGraph |
| `sympy` | Overkill for expression evaluation — use simpleeval |
| `asteval` | Less maintained than simpleeval |
| `numexpr` | Adds complexity without benefit at Phase 1 scale |

---

## 20. pyproject.toml Template

This is the complete `pyproject.toml` Claude Code should use as the starting point:

```toml
[tool.poetry]
name = "hydrosim"
version = "0.1.0"
description = "Open-source probabilistic hydrological simulation platform"
authors = ["HydroSim Contributors"]
license = "MIT"
readme = "README.md"
homepage = "https://github.com/hydrosim/hydrosim"
repository = "https://github.com/hydrosim/hydrosim"
keywords = ["hydrology", "simulation", "water resources", "rainfall-runoff"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Science/Research",
    "Topic :: Scientific/Engineering :: Hydrology",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
packages = [{include = "hydrosim"}]

[tool.poetry.scripts]
hydrosim = "hydrosim.__main__:main"

[tool.poetry.dependencies]
python = ">=3.11,<3.13"
PyQt6 = "~=6.6"
pyqtgraph = "~=0.13"
matplotlib = "~=3.8"
numpy = "~=1.26"
scipy = "~=1.11"
pandas = "~=2.1"
networkx = "~=3.2"
pydantic = "~=2.5"
simpleeval = "~=0.9"

[tool.poetry.group.dev.dependencies]
pytest = ">=7.4"
pytest-qt = ">=4.2"
pytest-cov = ">=4.1"
black = ">=24.0"
ruff = ">=0.3"
mypy = ">=1.8"
PyQt6-stubs = ">=6.6"
pre-commit = ">=3.6"
pyinstaller = ">=6.3"

[tool.poetry.group.optional.dependencies]
numba = "~=0.59"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.black]
line-length = 100
target-version = ["py311"]

[tool.ruff]
line-length = 100
target-version = "py311"
select = ["E", "F", "W", "I", "UP", "B", "SIM"]
ignore = ["E501", "B008"]

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_imports = true
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = "-v --tb=short"

[tool.coverage.run]
source = ["hydrosim"]
omit = ["hydrosim/gui/*", "tests/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
]
```

---

*End of HydroSim Technology Stack Document v1.0*
