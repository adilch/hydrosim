# HydroSim

**Open-source probabilistic hydrological simulation platform** — purpose-built for hydrologists.

Build water balance models visually by dragging and connecting elements on a canvas, run time-stepping simulations, and view interactive hydrograph results.

> Phase 1 MVP — all 14 acceptance criteria passing, 213 unit tests green.

---

## Features

- **Drag-and-drop canvas** — place and connect elements visually; bezier arrows show data flow
- **5 element types** — Constant, TimeSeries, WaterStore, Expression, TimeHistoryResult
- **Simulation engine** — forward-Euler integration with topological sort execution order
- **Interactive results viewer** — PyQtGraph hydrograph with zoom/pan/crosshair and CSV export
- **Save/load** — `.hydrosim` JSON files with full model state
- **Debug mode** — per-step element values, validation warnings, water balance diagnostics in the log panel
- **Isolated element handling** — unused elements on canvas are silently skipped with a log notice

---

## Installation

**Requirements:** Python 3.11+

```bash
# Clone and install in editable mode with dev dependencies
git clone https://github.com/adilch/hydrosim.git
cd hydrosim
pip install -e ".[dev]"
```

**Optional — download bundled fonts (Inter + Fira Code):**
```bash
python download_fonts.py
```

---

## Usage

```bash
# Launch the application
python -m hydrosim

# Or via the installed entry point
hydrosim
```

On first launch, HydroSim will offer to open the bundled example model (`simple_water_balance.hydrosim`).

A more detailed example is also included:
```
Hawkesbury_Water_Balance_2020.hydrosim   — dual-store daily water balance, 365 days
```
Open it via **File → Open**, then press **F5** to run.

---

## Quick Start

1. **File → New** (or open the example model)
2. Drag elements from the left palette onto the canvas
3. Draw connections by dragging from an output port (right edge) to an input port (left edge)
4. Press **F5** (or the green **Run** button) to simulate
5. Double-click a **Time History Result** element to open the hydrograph viewer

---

## Architecture

Three strictly separated layers — the model and engine have **zero PyQt6 dependencies**:

```
GUI (PyQt6)          — canvas, dialogs, palette, result viewer
   │
Model (pure Python)  — elements, graph, validator, serialiser
   │
Engine (pure Python) — runner, solver, expression parser, results store
```

---

## Element Types

| Element | Category | Description |
|---------|----------|-------------|
| **Constant** | Input | Fixed scalar value (parameter) |
| **TimeSeries** | Input | Time-varying input from a data table (CSV import) |
| **WaterStore** | Stock | Bounded storage with forward-Euler integration; tracks overflow and deficit |
| **Expression** | Expression | User-defined formula referencing other elements; safe AST evaluation |
| **TimeHistoryResult** | Result | Collects and displays time series as an interactive hydrograph |

---

## Development

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=hydrosim --cov-report=term-missing

# Format and lint
black hydrosim/ tests/
ruff check hydrosim/
```

**Test suite:** 213 tests across elements, engine, model graph, validator, and serialiser.

---

## Project Structure

```
hydrosim/
├── hydrosim/
│   ├── model/          # Pure Python — elements, graph, validator, serialiser
│   ├── engine/         # Pure Python — runner, solver, parser, results
│   ├── gui/            # PyQt6 — canvas, palette, dialogs, result viewer
│   └── resources/      # SVG icons, fonts, example models
├── tests/              # pytest test suite
├── pyproject.toml
└── Hawkesbury_Water_Balance_2020.hydrosim   # example model
```

---

## License

MIT — see [LICENSE](LICENSE)
