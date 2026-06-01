# HydroSim — Application Flow Document
## How a Hydrologist Moves Through the Application

**Version:** 1.0  
**Audience:** Developers, UI designers, Claude Code  
**Purpose:** Describes end-to-end user journeys, screen transitions, interaction patterns, and workflow logic for HydroSim Phase 1.

---

## Table of Contents

1. [Application Launch & First Run](#1-application-launch--first-run)
2. [Main Window Orientation](#2-main-window-orientation)
3. [Starting a New Model](#3-starting-a-new-model)
4. [Placing Elements on the Canvas](#4-placing-elements-on-the-canvas)
5. [Configuring Elements](#5-configuring-elements)
6. [Connecting Elements](#6-connecting-elements)
7. [Validating the Model](#7-validating-the-model)
8. [Running a Simulation](#8-running-a-simulation)
9. [Viewing Results](#9-viewing-results)
10. [Iterating on the Model](#10-iterating-on-the-model)
11. [Saving and Loading Models](#11-saving-and-loading-models)
12. [Complete Worked Example — Soil Moisture Water Balance](#12-complete-worked-example--soil-moisture-water-balance)
13. [Error Recovery Flows](#13-error-recovery-flows)
14. [Keyboard Shortcuts Reference](#14-keyboard-shortcuts-reference)
15. [State Transition Diagram](#15-state-transition-diagram)

---

## 1. Application Launch & First Run

### 1.1 Launching the Application

The user launches HydroSim either:
- By running `hydrosim` from the terminal
- By double-clicking the desktop shortcut (if installed)
- By running `python -m hydrosim`

**What happens on launch:**
1. The splash screen appears for ~1.5 seconds showing the HydroSim logo and version number
2. Application checks for a `~/.hydrosim/preferences.json` file
3. Main window opens

### 1.2 First Run Experience

On first launch (no preferences file exists):

**The application opens with:**
- A welcome dialog in the centre of the screen:

```
┌──────────────────────────────────────────────┐
│                                              │
│         Welcome to HydroSim v1.0            │
│                                              │
│  An open-source hydrological simulation      │
│  platform for water resources engineers.     │
│                                              │
│  ┌──────────────────┐  ┌──────────────────┐  │
│  │  Open Example    │  │   New Model      │  │
│  │  Model           │  │                  │  │
│  └──────────────────┘  └──────────────────┘  │
│                                              │
│         [ ] Don't show this again           │
└──────────────────────────────────────────────┘
```

**If user clicks "Open Example Model":**
- Loads `simple_water_balance.hydrosim` from resources
- Canvas populates with the pre-built example
- User can immediately explore a working model, run it, and view results
- This is the recommended first-run path

**If user clicks "New Model":**
- Welcome dialog closes
- User is presented with the empty canvas
- Proceed to Section 3 (Starting a New Model)

### 1.3 Returning User Experience

On subsequent launches (preferences file exists):

- Welcome dialog is skipped (unless "Don't show this again" was unchecked)
- If the user had a model open when they last closed the app, a prompt appears:

```
┌──────────────────────────────────────────────┐
│  Reopen last model?                          │
│                                              │
│  "Catchment_Analysis.hydrosim"              │
│  Last modified: 28 May 2026, 3:42 PM        │
│                                              │
│         [Start Fresh]    [Reopen]           │
└──────────────────────────────────────────────┘
```

---

## 2. Main Window Orientation

When the main window is open, the user sees four distinct zones. Understanding these zones is the foundation of using HydroSim effectively.

### 2.1 Zone Map

```
┌─────────────────────────────────────────────────────────────┐
│  ZONE 1: Menu Bar & Toolbar                                 │
│  File | Simulation | View | Help    [New][Open][Save][Run]  │
├──────────────┬──────────────────────────────────────────────┤
│              │                                              │
│  ZONE 2:     │           ZONE 3: Canvas                    │
│  Element     │                                              │
│  Palette     │   ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·   │
│              │                                              │
│  [INPUT ▼]   │        [Elements float here]                │
│  Constant    │                                              │
│  TimeSeries  │                                              │
│              │                                              │
│  [STOCK ▼]   │                                              │
│  WaterStore  │                                              │
│              │                                              │
│  [EXPR ▼]    │                                              │
│  Expression  │                                              │
│              │                                              │
│  [RESULT ▼]  │                                              │
│  TimeHistory │                                              │
│              │                                              │
├──────────────┴──────────────────────────────────────────────┤
│  ZONE 4: Status Bar    Model Name  |  Status  |  Zoom 100% │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Zone Purposes

**Zone 1 — Menu Bar & Toolbar**
The user comes here for file operations (New, Open, Save) and simulation control (Run, Stop). The toolbar puts the most frequent actions one click away. The menu bar provides access to all settings and less-frequent operations.

**Zone 2 — Element Palette**
The user comes here when they want to add a new element to the model. Think of this as the parts bin — all available element types live here. Elements are grouped by category with colour-coded headers. The user drags from here onto the canvas.

**Zone 3 — Canvas**
This is where the model lives. The user spends most of their time here — placing, connecting, moving, and inspecting elements. The canvas is infinite and zoomable. All model-building happens on the canvas.

**Zone 4 — Status Bar**
Passive information zone. The user glances here to check the model name, simulation status, and current zoom level. Not interactive except for the zoom display (which can be clicked to reset to 100%).

### 2.3 Mental Model the User Should Have

A HydroSim model is a **network of connected elements**. Data flows from left to right:

```
Sources → Transformations → Storages → Results
(Input)   (Expression)     (Stock)    (Result)
```

- **Input elements** (green) are the sources of data — rainfall, parameters, constants
- **Expression elements** (teal) transform and combine values — calculating runoff, ET, net flux
- **Stock elements** (blue) store and accumulate water over time — soil moisture, reservoirs
- **Result elements** (orange) collect and display outputs — hydrographs, statistics

This left-to-right data flow convention is not enforced but should be encouraged. The palette is ordered to match this mental model.

---

## 3. Starting a New Model

### 3.1 Creating a New Model

**Via toolbar:** Click [New] button  
**Via menu:** File → New Model (Ctrl+N)  
**Via welcome dialog:** Click "New Model"

**If there are unsaved changes in the current model:**
```
┌────────────────────────────────────────────────┐
│  You have unsaved changes to                   │
│  "Catchment_Analysis"                          │
│                                                │
│  Do you want to save before starting a        │
│  new model?                                    │
│                                                │
│     [Cancel]   [Don't Save]   [Save]          │
└────────────────────────────────────────────────┘
```

After confirming, the canvas clears and a blank model is created.

### 3.2 Naming the Model

The user should name their model early. The title bar shows `HydroSim — Untitled*` until saved.

**Best practice prompt (shown as a subtle banner below the toolbar on first new model):**
```
💡 Tip: Save your model early with a meaningful name — File → Save (Ctrl+S)
                                                              [×] Dismiss
```

### 3.3 Setting Simulation Parameters Before Building

**Recommended first step:** Before placing any elements, set the simulation time period.

**Via menu:** Simulation → Simulation Settings (Ctrl+T)

The Simulation Settings dialog opens:

```
┌──────────────────────────────────────────────┐
│  Simulation Settings                         │
├──────────────────────────────────────────────┤
│  Time Mode:  ○ Elapsed Days  ● Calendar      │
│                                              │
│  Start Date:  [ 01 / 01 / 2020 ]            │
│  End Date:    [ 31 / 12 / 2020 ]            │
│  Timestep:    [ 1.0 ] days                  │
│                                              │
│  ─────────────────────────────────────────  │
│  Computed: 366 timesteps                     │
│  Estimated run time: < 1 second             │
│                                              │
│                    [Cancel]  [Apply]         │
└──────────────────────────────────────────────┘
```

**Why this matters:** TimeSeries elements need to know what time range they cover. Setting this upfront helps the user think about their data requirements before placing elements.

---

## 4. Placing Elements on the Canvas

This is the primary model-building action. There are two ways to place elements.

### 4.1 Method 1: Drag from Palette (Recommended)

1. User identifies the element type they need in the left palette
2. User clicks and holds on the palette item
3. A semi-transparent ghost of the element card follows the cursor onto the canvas
4. User releases the mouse button at the desired canvas location
5. Element appears at the drop position with a default name (`Constant_1`, `TimeSeries_1`, etc.)
6. The property dialog opens automatically so the user can configure the element immediately

**Visual during drag:**
- Ghost card is 50% opacity, follows cursor
- Canvas highlights drop zones with a subtle blue tint when cursor is over canvas
- Palette item shows a drag cursor `⠿`

### 4.2 Method 2: Double-Click in Palette

1. User double-clicks a palette item
2. Element appears at the centre of the current canvas viewport
3. Property dialog opens automatically

This method is faster when the user doesn't care about precise positioning — they can move elements later.

### 4.3 Immediately After Placement — Property Dialog Opens

The property dialog opens **automatically** after every new element placement. This is intentional — it encourages the user to name and configure the element before moving on. An unnamed, unconfigured element floating on the canvas creates confusion.

**The user should:**
1. Give the element a meaningful name (e.g., `Daily_Rainfall_Penrith` not `TimeSeries_1`)
2. Fill in the required parameters
3. Click OK

If the user clicks Cancel, the element is created with default parameters and the generic name. The user can reconfigure it later by double-clicking.

### 4.4 Positioning Elements on the Canvas

**Moving elements:**
- Click to select (blue border appears)
- Drag to new position
- Selected elements can also be moved with arrow keys (1px per press, 10px with Shift)

**Selecting multiple elements:**
- Click and drag on empty canvas to rubber-band select
- Shift+click to add/remove individual elements from selection
- Ctrl+A to select all elements

**Moving multiple elements:**
- Drag any selected element — all selected elements move together, preserving relative positions
- Connection arrows automatically reroute as elements move

**Alignment guidance:**
- No snap-to-grid in Phase 1 (deferred to Phase 2)
- Convention: arrange elements left to right in data flow order
- Leave enough horizontal space for connection arrows to arc gracefully (~100px between cards)

### 4.5 Recommended Canvas Layout Pattern

```
Column 1        Column 2         Column 3        Column 4
(x ≈ 100)      (x ≈ 350)        (x ≈ 600)       (x ≈ 850)

[TimeSeries]                    [WaterStore]    [TimeHistory
                [Expression]         ↑           Result]
[Constant]          ↑          connects here
     ↑         connects here
 connects
   here
```

---

## 5. Configuring Elements

### 5.1 Opening the Property Dialog

**To open:** Double-click any element card on the canvas

The dialog opens as a modal window centred on the application. The canvas is not interactive while a dialog is open.

### 5.2 Configuring a Constant Element

The simplest element. The user fills in:

1. **Name** — e.g., `RunoffCoeff`
   - Must be unique in the model
   - No spaces (use underscores)
   - Case-insensitive in formulas but stored as typed
   - Live validation: red border + error message if duplicate or invalid characters

2. **Description** — e.g., `"Fraction of rainfall that becomes runoff"`
   - Optional but strongly encouraged for model documentation

3. **Value** — e.g., `0.30`
   - Numeric spinner with manual entry
   - Supports scientific notation (e.g., `1.5e-3`)

4. **Units** — e.g., `-` (dimensionless)
   - Free text with autocomplete from common units: `m3`, `mm`, `m3/s`, `mm/day`, `km2`, `m`, `-`

Click **OK** → dialog closes → element card updates to show the new name and value preview.

### 5.3 Configuring a TimeSeries Element

The most data-intensive element. The user must provide a time series of values.

**Step 1 — Basic settings:**
- Name, Description, Units, Data Type, Interpolation (as described in PRD)

**Step 2 — Entering data:**

The user has three options:

**Option A: Manual entry in table**
- Click [Add Row] to add rows to the data table
- Type time value (days from start, or calendar date in Calendar mode) and data value
- Suitable for small datasets (< 20 rows)

**Option B: Import from CSV (most common)**
- Click [Import CSV...]
- File picker opens — user navigates to their data file
- CSV format expected: two columns, first row optional header
  ```
  date,rainfall_mm
  2020-01-01,0.0
  2020-01-02,12.3
  2020-01-03,0.0
  ```
- Preview of parsed data shown before confirming import
- Common errors handled gracefully:
  - Non-numeric values → highlighted in red with row numbers
  - Non-monotonic time → warning with option to auto-sort
  - Wrong number of columns → clear error message

**Option C: Paste from clipboard**
- User copies two columns from Excel
- Clicks [Paste from Clipboard]
- Same parsing logic as CSV import

**Step 3 — Verify data:**
- A mini preview chart is shown at the bottom of the dialog
- Shows the time series as a line chart
- User can visually verify the data looks correct before clicking OK

### 5.4 Configuring an Expression Element

This is the most complex dialog. The user writes a formula that references other elements.

**Step 1 — Name and units**
- Name: e.g., `RunoffRate`
- Output Units: e.g., `mm/day`

**Step 2 — Writing the formula**

The formula editor is the centrepiece of this dialog:

```
┌──────────────────────────────────────────────────────┐
│  Formula                                             │
├──────────────────────────────────────────────────────┤
│  Daily_Rainfall * RunoffCoeff                        │
│  ▲               ▲                                   │
│  green           green                               │
│  (element ref)   (element ref)                       │
└──────────────────────────────────────────────────────┘
│  ✓ Valid  →  Result at t=0: 3.69 mm/day  [Test]     │
└──────────────────────────────────────────────────────┘
```

**How the user writes a formula:**
- They type directly, or
- They click element names in the "Available Elements" panel below the editor — this inserts the name at the cursor position

**Available Elements panel:**
```
Available Elements & Ports — click to insert
┌────────────────────────────────────────────┐
│  [Daily_Rainfall · value]  [RunoffCoeff · value]  │
│  [SoilMoisture · storage]  [SoilMoisture · overflow] │
└────────────────────────────────────────────┘
```

**Live feedback:**
- Syntax errors underlined in red as the user types
- Error message shown below editor: e.g., `Unknown element "Rainfal" — did you mean "Rainfall"?`
- Green tick + computed result shown when formula is valid

**Test button:**
- Evaluates the formula at t=0 using current input element values
- Shows result in a green pill: `= 3.69 mm/day`
- If formula errors at runtime (e.g., division by zero at t=0): shows orange warning

### 5.5 Configuring a WaterStore Element

```
┌──────────────────────────────────────────┐
│  🔵 WaterStore — SoilMoisture            │
├──────────────────────────────────────────┤
│  Name:            SoilMoisture           │
│  Description:     Root zone moisture     │
│  Units:           mm                     │
├──────────────────────────────────────────┤
│  Initial Storage:  [ 80.0 ]              │
│  Lower Bound:      [ 0.0  ]              │
│  Upper Bound:      [ 150.0 ]  □ Unbounded│
├──────────────────────────────────────────┤
│  Storage indicator:                      │
│  0 ────────[■■■■■■──────────]──── 150   │
│              ↑ 80mm (53%)                │
└──────────────────────────────────────────┘
```

The storage indicator bar is interactive — the user can drag the initial storage marker to set the value visually, or type in the field directly.

**Validation rules shown live:**
- If initial storage < lower bound → red field, error: `"Initial storage cannot be below lower bound"`
- If initial storage > upper bound → red field, error: `"Initial storage cannot exceed upper bound"`
- If lower bound ≥ upper bound → red field: `"Lower bound must be less than upper bound"`

### 5.6 Configuring a TimeHistoryResult Element

The simplest result element to configure:
- Name (used as chart title by default)
- Chart Title, Y-axis Label, Y-axis Units
- Grid on/off
- Y-axis min/max (or Auto)

The user does not connect series here — series are connected by drawing connection arrows from other element outputs to this element's input ports on the canvas.

---

## 6. Connecting Elements

Connections are what make HydroSim a simulation tool rather than a collection of isolated calculators. Getting connections right is the most important modelling step.

### 6.1 Drawing a Connection

1. User hovers over an **output port** (right side of a card)
   - Port dot grows from 10px to 14px
   - Tooltip appears: `"value (mm/day) — TimeSeries output"`
   - Cursor changes to crosshair

2. User clicks and drags from the output port
   - A bezier curve follows the cursor from the port
   - The curve is drawn in the source element's category colour

3. As the user drags toward another element:
   - **Compatible input ports** glow green with a pulsing ring
   - **Incompatible ports** (already connected, or same element) glow red
   - **No visual change** on output ports (can't connect output to output)

4. User releases the mouse over a compatible input port
   - Connection arrow snaps into place
   - Arrow is rendered as a smooth bezier curve

5. If user releases on empty canvas (not over a port):
   - Connection is cancelled
   - No arrow is drawn

### 6.2 What Can Connect to What

**Rules:**
- Output ports can have **multiple** outgoing connections (fan-out allowed)
- Input ports accept **exactly one** incoming connection (fan-in not allowed)
- An element cannot connect to itself (no self-loops)
- Connections that would create a **circular dependency** (among non-stock elements) are blocked with a visual warning

**Phase 1 port compatibility (simple rule):**
- All ports carry scalar float values
- Any output port can connect to any input port
- Unit compatibility is **not enforced** in Phase 1 — the user is responsible for ensuring units are consistent (a warning is shown in the simulation log if connected port units appear mismatched)

### 6.3 Inspecting a Connection

**Hover over a connection arrow:**
- Arrow highlights (stroke thickens to 3px)
- Tooltip shows: `"Daily_Rainfall.value → RunoffRate.input_1 (mm/day)"`

**Click on a connection arrow:**
- Arrow selected (turns blue)
- Status bar shows connection details

**Delete a connection:**
- Select the connection arrow
- Press Delete key
- Or right-click → Delete Connection

### 6.4 Reconnecting a Port

If a user wants to change what an input port is connected to:
1. Delete the existing connection (click arrow → Delete)
2. Draw a new connection from a different output port

Or drag the arrowhead end of an existing connection to a new input port (Phase 2 feature — not in Phase 1).

### 6.5 Common Connection Patterns

**Pattern 1 — Simple chain (most common):**
```
[TimeSeries] ──value──► [Expression] ──value──► [WaterStore.inflow]
                                                        │
                                              [WaterStore.storage]
                                                        │
                                                        ▼
                                               [TimeHistoryResult]
```

**Pattern 2 — Fan-out (one source feeds multiple elements):**
```
[TimeSeries: Rainfall]
    │ value
    ├──────────────────► [Expression: RunoffCalc]
    │
    └──────────────────► [Expression: ETCalc]
```

**Pattern 3 — Multiple inputs to WaterStore:**
```
[Expression: RunoffRate] ──value──► [WaterStore.inflow]
[Expression: ETRate]     ──value──► [WaterStore.outflow]
                                          │
                                    [WaterStore.storage]
```

---

## 7. Validating the Model

### 7.1 When Validation Runs

Validation runs automatically in two situations:
1. **When the user clicks Run** — full validation before simulation starts
2. **Continuously in the background** — the canvas shows element-level error indicators in real time

### 7.2 Real-Time Canvas Validation (Passive)

As the user builds the model, the canvas shows live feedback:

**Unconnected required port:**
- The port dot turns red
- A small red warning triangle appears in the element card's top-right corner
- Hovering the triangle shows: `"Required input 'inflow' is not connected"`

**Invalid formula in Expression:**
- Expression card shows red border
- Warning triangle with message: `"Formula error — unknown element 'Rainfal'"`

**Invalid parameter:**
- The element card shows a yellow border (warning, not blocking)
- e.g., WaterStore with initial storage > upper bound

This real-time feedback means by the time the user clicks Run, most errors are already visible and fixable.

### 7.3 Pre-Run Validation Dialog

When the user clicks Run and errors exist, a validation summary dialog appears:

```
┌────────────────────────────────────────────────────┐
│  ⚠ Model has 2 errors — cannot run                │
├────────────────────────────────────────────────────┤
│                                                    │
│  ✗ RunoffRate — formula references unknown         │
│    element "Rainfal". Did you mean "Rainfall"?     │
│    [Go to element]                                 │
│                                                    │
│  ✗ WaterStore.inflow — required input port         │
│    is not connected.                               │
│    [Go to element]                                 │
│                                                    │
├────────────────────────────────────────────────────┤
│                                      [Close]       │
└────────────────────────────────────────────────────┘
```

**[Go to element] buttons:**
- Close the dialog
- Pan and zoom the canvas to centre on the offending element
- Select the element (blue border)
- Open its property dialog if the error is in a parameter

This makes error navigation fast — the user doesn't have to hunt for the problem element on a large canvas.

### 7.4 Validation Warnings (Non-Blocking)

Some issues are warnings, not errors — simulation proceeds but the user is informed:

- **Units mismatch** — connected ports have different units (`mm/day` feeding `m3/s`)
- **Large timestep** — timestep may be too coarse for accurate integration
- **Empty description fields** — model documentation is incomplete
- **TimeSeries shorter than simulation period** — extrapolation will be used

Warnings appear in the simulation log after the run completes.

---

## 8. Running a Simulation

### 8.1 Initiating a Run

**Via toolbar:** Click the green [▶ Run] button  
**Via menu:** Simulation → Run Simulation  
**Via keyboard:** F5

### 8.2 Pre-Run Checklist (Internal)

Before the simulation engine starts, the application automatically:
1. Saves the model to a temporary backup file
2. Runs full model validation
3. If errors: shows validation dialog (Section 7.3), stops
4. If only warnings: shows warning count in status bar, proceeds
5. Resolves execution order (topological sort)
6. Initialises the ResultsStore

### 8.3 During the Run

**UI state during simulation:**
- [▶ Run] button becomes greyed out and disabled
- [■ Stop] button becomes active (red)
- A progress bar appears in the status bar:
  ```
  ⏳ Running...  [████████████░░░░░░░░░░░░]  65%  (237/365 days)
  ```
- The canvas remains **visible but not editable** (elements cannot be moved or edited while running)
- The Simulation Log panel opens automatically at the bottom (if it was hidden)

**Simulation Log during run (updates in real time):**
```
[10:32:15] Starting simulation: Simple Water Balance
[10:32:15] Settings: 2020-01-01 to 2020-12-31, dt=1.0 day (366 steps)
[10:32:15] Execution order resolved:
           1. Daily_Rainfall  2. RunoffCoeff  3. RunoffRate
           4. SoilMoisture    5. Storage_Plot
[10:32:15] Running timesteps...
[10:32:15] ✓ Complete — 366 timesteps in 0.18s
```

### 8.4 Stopping a Run

If the user clicks [■ Stop] during a simulation:
- Simulation stops after the current timestep completes
- Partial results up to that point are preserved
- Status bar shows: `● Stopped at day 187 of 366`
- Partial results are viewable in TimeHistoryResult elements

### 8.5 After the Run

**Successful completion:**
- Status bar updates: `● Simulation complete — 366 steps in 0.18s` (green)
- [▶ Run] button re-enables
- TimeHistoryResult element cards now show a small green dot (results available indicator)
- A subtle animation on TimeHistoryResult cards: a tiny sparkline hydrograph appears inside the card

**User's next step:** Double-click a TimeHistoryResult element to view the full results (Section 9).

---

## 9. Viewing Results

### 9.1 Opening the Result Viewer

Double-click any **TimeHistoryResult** element that has a green results dot.

A floating results window opens (not a modal — the user can keep it open while editing the model):

```
┌──────────────────────────────────────────────────────────┐
│  Storage_Plot — Results                      [Export CSV]│
├──────────────────────────────────────────────────────────┤
│                                                          │
│  150 ┤                                                   │
│      │    ╭──╮                                           │
│  100 ┤   ╭╯  ╰╮                          ╭──╮           │
│      │  ╭╯    ╰──╮                    ╭──╯  ╰╮          │
│   50 ┤ ╭╯        ╰────────────╮      ╭╯      ╰──        │
│      │╭╯                      ╰──────╯                   │
│    0 ┤┴──────────────────────────────────────────────    │
│      Jan  Feb  Mar  Apr  May  Jun  Jul  Aug  Sep  Oct    │
│                                                          │
│      — SoilMoisture.storage (mm)                        │
│                                                          │
├──────────────────────────────────────────────────────────┤
│  [🔍+] [🔍-] [↔] [⌂] [💾 PNG]                          │
└──────────────────────────────────────────────────────────┘
```

### 9.2 Interacting with the Chart

**Hover:** Moving the cursor over the chart shows a crosshair and a tooltip:
```
Day 45 (14 Feb 2020)
SoilMoisture.storage: 112.4 mm
```

**Zoom:** Click the zoom tool in the toolbar, then drag a rectangle on the chart to zoom in. Scroll wheel also zooms.

**Pan:** Click the pan tool, then drag to move the view.

**Reset view:** Click the home icon to return to full extent.

**Save as PNG:** Click the save icon → file picker → saves the chart as a PNG image at 150 DPI.

### 9.3 Multiple Series on One Chart

A TimeHistoryResult can show multiple series if multiple output ports are connected to it. Each series gets a different colour from the palette:

```
— SoilMoisture.storage (mm)      [blue]
— RunoffRate.value (mm/day)      [orange]
```

The user connects additional series by drawing more connections from element output ports to additional `series_2`, `series_3` ports on the TimeHistoryResult card. New ports appear automatically when all existing ports are connected.

### 9.4 Exporting Results

**[Export CSV] button:**
Saves a CSV file with:
```
time_days,date,SoilMoisture.storage,RunoffRate.value
0.0,2020-01-01,80.0,0.0
1.0,2020-01-02,83.7,3.7
2.0,2020-01-03,82.1,1.2
...
```

File picker opens to choose save location and filename.

### 9.5 Multiple Result Windows

Multiple TimeHistoryResult windows can be open simultaneously. The user can:
- Compare outputs side by side
- Drag windows to different monitors
- Minimise individual result windows

Results windows are not closed when the user edits the model — only when the user re-runs the simulation (which clears and regenerates all results).

---

## 10. Iterating on the Model

Most of the user's time in HydroSim is spent in an iterative loop:

```
Build/Edit → Run → View Results → Identify Issue → Edit → Run → ...
```

### 10.1 Editing After a Run

After viewing results, the user may want to:

**Change a parameter value:**
1. Double-click the element
2. Change the value in the dialog
3. Click OK — element card updates immediately
4. Re-run the simulation

**The canvas shows a warning after editing:** A yellow banner appears below the toolbar:
```
⚠ Model has changed since last run — results may be out of date.  [Run Now]
```
This prevents the user from forgetting that the displayed results are stale.

**Add a new element:**
1. Drag from palette
2. Configure in dialog
3. Connect to existing elements
4. Re-run

**Delete an element:**
1. Click to select
2. Press Delete
3. Confirm: `"Delete 'RunoffRate' and its connections? [Cancel] [Delete]"`
4. Element and all its connections are removed
5. Re-run if needed

**Modify a connection:**
1. Click the connection arrow to select it
2. Press Delete to remove it
3. Draw a new connection

### 10.2 Sensitivity Analysis Workflow

A common hydrologist workflow — testing how sensitive outputs are to parameter values:

1. Build the model and get baseline results
2. Double-click a Constant element (e.g., `RunoffCoeff = 0.30`)
3. Change to a new value (e.g., `0.40`)
4. Click OK
5. Re-run simulation
6. Open the TimeHistoryResult — compare new curve against the mental model of the baseline
7. Repeat for different values

**In Phase 1, the user must manually remember baseline results.** Phase 2 will add the ability to overlay multiple run results on the same chart.

### 10.3 Model Documentation Workflow

Good modelling practice encourages documenting the model. HydroSim supports this through description fields on every element.

**Recommended workflow:**
- After building a working model, go back through each element
- Fill in the Description field with:
  - What the element represents physically
  - Where parameter values came from (literature, calibration, assumption)
  - Any caveats or limitations

This documentation is preserved in the `.hydrosim` file and makes the model understandable to collaborators or to the user's future self.

---

## 11. Saving and Loading Models

### 11.1 Saving a Model

**First save (Ctrl+S):**
- File picker opens to choose location and filename
- File is saved as `ModelName.hydrosim`
- Window title updates: `HydroSim — ModelName` (asterisk removed)

**Subsequent saves (Ctrl+S):**
- Saves to the same file silently
- Status bar briefly shows: `✓ Saved` for 2 seconds

**Save As (Ctrl+Shift+S):**
- File picker opens regardless
- Useful for creating a new version of the model

**What is saved in the file:**
- All element configurations (parameters, names, descriptions)
- All connections
- Canvas layout (element positions, zoom level, pan offset)
- Simulation settings
- Model metadata (name, author, creation date, modification date)

**What is NOT saved:**
- Simulation results (results are regenerated on each run)
- Window size and position

### 11.2 Loading a Model

**Via toolbar:** Click [Open] button  
**Via menu:** File → Open Model (Ctrl+O)  
**Via Recent Models:** File → Recent Models → click filename  
**Via file system:** Double-click a `.hydrosim` file (if OS file association is set up)

**Loading process:**
1. File picker opens (if not opening via recent/file association)
2. File is parsed and validated
3. Canvas clears and new model is drawn
4. All elements appear in their saved positions
5. Connections are redrawn
6. Simulation settings are restored
7. Status bar shows: `● Ready — model loaded`

**If file format is invalid or corrupted:**
```
┌────────────────────────────────────────────┐
│  Could not open file                       │
│                                            │
│  "Catchment_v3.hydrosim" could not be     │
│  opened. The file may be corrupted or      │
│  created by an incompatible version.       │
│                                            │
│  Error detail: Unexpected key "stochastic" │
│  in element at index 3.                   │
│                                            │
│                              [OK]         │
└────────────────────────────────────────────┘
```

### 11.3 Auto-Save

HydroSim saves a backup copy automatically:
- Every 5 minutes if the model has unsaved changes
- Backup saved to `~/.hydrosim/autosave/ModelName_autosave.hydrosim`
- If the application crashes, on next launch:

```
┌────────────────────────────────────────────┐
│  Auto-save found                           │
│                                            │
│  HydroSim found an auto-saved version of  │
│  "Catchment_Analysis" from 10 minutes ago. │
│                                            │
│  [Use Auto-save]    [Open Original]        │
└────────────────────────────────────────────┘
```

---

## 12. Complete Worked Example — Soil Moisture Water Balance

This section walks through the complete workflow a hydrologist would follow to build and run a simple daily soil moisture model from scratch. This is the canonical Phase 1 use case.

### 12.1 Problem Statement

A hydrologist wants to simulate daily soil moisture storage in a 50 km² catchment for the year 2020. They have:
- Daily observed rainfall data (CSV file, 366 rows)
- An assumed runoff coefficient of 0.30 (30% of rainfall becomes runoff)
- Initial soil moisture of 80 mm (field-measured)
- Field capacity (upper bound) of 150 mm
- Wilting point (lower bound) of 0 mm

They want to see how soil moisture varies through the year.

---

### 12.2 Step-by-Step Build

**Step 1: Launch and set up**
1. Launch HydroSim → click "New Model" in welcome dialog
2. Simulation → Simulation Settings:
   - Time Mode: Calendar
   - Start Date: 01/01/2020
   - End Date: 31/12/2020
   - Timestep: 1.0 day
   - Click Apply
3. File → Save As → `Soil_Moisture_2020.hydrosim`

**Step 2: Place the TimeSeries element (rainfall input)**
1. Drag `TimeSeries` from palette → drop on canvas at position (100, 200)
2. Property dialog opens automatically:
   - Name: `Daily_Rainfall`
   - Description: `Observed daily rainfall at Penrith gauge (mm/day)`
   - Units: `mm/day`
   - Data Type: `Period Total`
   - Interpolation: `Step`
   - Click [Import CSV...] → navigate to `rainfall_2020.csv` → select → preview shows 366 rows → click Import
   - Mini chart shows the rainfall data — user confirms it looks correct
   - Click OK
3. Canvas now shows a green TimeSeries card labelled `Daily_Rainfall`

**Step 3: Place the Constant element (runoff coefficient)**
1. Drag `Constant` from palette → drop at position (100, 350)
2. Property dialog:
   - Name: `RunoffCoeff`
   - Description: `Fraction of rainfall converting to runoff (assumed)`
   - Value: `0.30`
   - Units: `-` (dimensionless)
   - Click OK
3. Canvas shows green Constant card labelled `RunoffCoeff` showing value `0.30`

**Step 4: Place the Expression element (runoff rate calculation)**
1. Drag `Expression` from palette → drop at position (350, 270)
2. Property dialog:
   - Name: `RunoffRate`
   - Description: `Daily runoff rate as fraction of rainfall`
   - Output Units: `mm/day`
   - Formula field: click `[Daily_Rainfall · value]` in Available Elements panel → inserts `Daily_Rainfall`
   - Type ` * ` 
   - Click `[RunoffCoeff · value]` → inserts `RunoffCoeff`
   - Formula now reads: `Daily_Rainfall * RunoffCoeff`
   - Live validation shows: `✓ Valid → Result at t=0: 0.0 mm/day` (zero because day 1 has no rainfall)
   - Click [Test] → shows `= 0.0 mm/day` (correct for Jan 1)
   - Click OK

**Step 5: Place the WaterStore element (soil moisture)**
1. Drag `WaterStore` from palette → drop at position (600, 270)
2. Property dialog:
   - Name: `SoilMoisture`
   - Description: `Root zone soil moisture, field capacity = 150mm`
   - Units: `mm`
   - Initial Storage: `80.0`
   - Lower Bound: `0.0`
   - Upper Bound: `150.0`
   - Storage indicator bar shows initial at 53% of capacity
   - Click OK
3. Canvas shows blue WaterStore card with ports: `inflow`, `outflow` (inputs); `storage`, `overflow`, `deficit` (outputs)

**Step 6: Place the TimeHistoryResult element**
1. Drag `TimeHistoryResult` from palette → drop at position (850, 270)
2. Property dialog:
   - Name: `Storage_Plot`
   - Chart Title: `Daily Soil Moisture Storage — 2020`
   - Y-axis Label: `Storage`
   - Y-axis Units: `mm`
   - Y-axis Min: `0` (manual)
   - Y-axis Max: `150` (manual — matches field capacity)
   - Click OK

**Step 7: Connect the elements**

Connection 1 — Rainfall feeds runoff calculation:
1. Hover over `Daily_Rainfall` output port `value` (right side of card)
2. Drag → release on `RunoffRate` input port (Expression elements auto-create input ports as needed)
3. Green bezier arrow appears

Connection 2 — Runoff feeds soil moisture store:
1. Hover over `RunoffRate` output port `value`
2. Drag → release on `SoilMoisture` input port `inflow`
3. Blue-ish bezier arrow appears

Connection 3 — Soil moisture storage goes to result:
1. Hover over `SoilMoisture` output port `storage`
2. Drag → release on `Storage_Plot` input port `series_1`
3. Orange bezier arrow appears

**Canvas now looks like:**
```
[Daily_Rainfall] ──► [RunoffRate] ──► [SoilMoisture] ──► [Storage_Plot]
[RunoffCoeff]   ──►       ↑               storage ──►
```

**Step 8: Validate and run**
1. Glance at canvas — no red borders or warning triangles visible
2. Click [▶ Run] button
3. Progress bar fills over ~0.2 seconds
4. Status bar: `● Simulation complete — 366 steps in 0.21s`
5. `Storage_Plot` card shows green dot + tiny sparkline

**Step 9: View results**
1. Double-click `Storage_Plot` card
2. Results window opens showing a time series of soil moisture
3. User sees seasonal pattern — moisture rising in wet months, depleting in dry months
4. Hover over the summer minimum → tooltip: `Day 198 (16 Jul 2020): 12.3 mm`
5. Click [Export CSV] → save to `results_2020.csv`

**Step 10: Iterate — test a different runoff coefficient**
1. Double-click `RunoffCoeff`
2. Change value from `0.30` to `0.45`
3. Click OK
4. Yellow banner appears: `⚠ Model changed since last run — results may be out of date`
5. Click [▶ Run] again
6. Results update — storage depletes faster under higher runoff
7. User compares result mentally against the previous run

**Step 11: Save**
1. Ctrl+S → saves silently
2. Title bar: `HydroSim — Soil_Moisture_2020` (no asterisk)

---

## 13. Error Recovery Flows

### 13.1 Formula Error in Expression

**Scenario:** User types `Daily_Rainfal * RunoffCoeff` (typo — missing 'l')

**What happens:**
- As user types, live validation triggers
- `Daily_Rainfal` is underlined in red
- Error message below formula field: `Unknown element "Daily_Rainfal". Did you mean "Daily_Rainfall"?`
- OK button is disabled

**Recovery:**
- User corrects the typo
- Error clears immediately
- OK button re-enables

### 13.2 TimeSeries CSV Import Failure

**Scenario:** User imports a CSV with three columns instead of two

**What happens:**
```
┌──────────────────────────────────────────────┐
│  Import Warning                              │
│                                              │
│  The CSV file has 3 columns. HydroSim       │
│  expects exactly 2 (time, value).            │
│                                              │
│  Which columns should be used?              │
│                                              │
│  Time column:   [Column 1 ▾]               │
│  Value column:  [Column 2 ▾]               │
│                                              │
│               [Cancel]   [Import]           │
└──────────────────────────────────────────────┘
```

User selects correct columns and imports successfully.

### 13.3 Circular Dependency

**Scenario:** User accidentally creates a loop — Expression A references Expression B which references Expression A

**What happens:**
- Canvas shows both Expression cards with red borders
- Warning on both cards: `"Circular dependency detected"`
- If user tries to run, validation dialog shows:
  ```
  ✗ Circular dependency: ExprA → ExprB → ExprA
    [Go to ExprA]
  ```

**Recovery:**
- User deletes one of the connections creating the loop
- Error clears

### 13.4 WaterStore Bounds Violation at Runtime

**Scenario:** WaterStore upper bound is 100 mm but inflows are very large, causing constant overflow

**What happens:**
- Simulation completes successfully (overflow is a valid output, not an error)
- Simulation log shows: `⚠ SoilMoisture: overflow occurred at 87 of 366 timesteps (24%). Consider increasing upper bound.`
- `overflow` output port is available to connect to a TimeHistoryResult to visualise

**Recovery:**
- User adds a TimeHistoryResult, connects `SoilMoisture.overflow`, re-runs
- Sees the overflow hydrograph — decides whether to adjust upper bound or accept the result

### 13.5 File Load — Version Mismatch

**Scenario:** User tries to open a file created by a future version of HydroSim

**What happens:**
```
┌──────────────────────────────────────────────┐
│  Version Mismatch                            │
│                                              │
│  "Advanced_Model.hydrosim" was created       │
│  with HydroSim v2.0. You are running v1.0.  │
│                                              │
│  Some features may not load correctly.      │
│  Unrecognised elements will be skipped.     │
│                                              │
│  [Cancel]          [Open Anyway]            │
└──────────────────────────────────────────────┘
```

---

## 14. Keyboard Shortcuts Reference

| Action | Shortcut |
|---|---|
| **File** | |
| New Model | Ctrl+N |
| Open Model | Ctrl+O |
| Save | Ctrl+S |
| Save As | Ctrl+Shift+S |
| Exit | Ctrl+Q |
| **Simulation** | |
| Simulation Settings | Ctrl+T |
| Run | F5 |
| Stop | Escape (during run) |
| **Canvas** | |
| Select All | Ctrl+A |
| Delete Selected | Delete |
| Zoom In | Ctrl+= |
| Zoom Out | Ctrl+- |
| Zoom to Fit | Ctrl+Shift+F |
| Reset Zoom (100%) | Ctrl+0 |
| Pan Canvas | Space + drag |
| **Element** | |
| Open Properties | Double-click or Enter (when selected) |
| Duplicate Element | Ctrl+D |
| Move (fine) | Arrow keys (1px) |
| Move (coarse) | Shift+Arrow keys (10px) |
| **View** | |
| Toggle Simulation Log | Ctrl+L |

---

## 15. State Transition Diagram

This diagram shows the high-level states the application moves through and what triggers each transition.

```
                    ┌─────────────┐
                    │   LAUNCH    │
                    └──────┬──────┘
                           │ app starts
                    ┌──────▼──────┐
                    │  WELCOME    │◄── first run only
                    └──────┬──────┘
              ┌────────────┼────────────┐
         open example   new model   open file
              │            │            │
    ┌─────────▼──┐  ┌──────▼──┐  ┌────▼────────┐
    │  EXAMPLE   │  │  EMPTY  │  │  LOADED     │
    │  LOADED    │  │  MODEL  │  │  MODEL      │
    └─────────┬──┘  └──────┬──┘  └────┬────────┘
              └────────────┼──────────┘
                           │
                    ┌──────▼──────┐
                    │   EDITING   │◄────────────────┐
                    │   MODEL     │                 │
                    └──────┬──────┘                 │
                           │ click Run              │
                    ┌──────▼──────┐                 │
                    │ VALIDATING  │                 │
                    └──────┬──────┘                 │
              ┌────────────┼──────────┐             │
         errors        no errors    warnings        │
              │            │            │           │
    ┌─────────▼──┐  ┌──────▼──────────▼──┐         │
    │ VALIDATION │  │     RUNNING         │         │
    │  DIALOG    │  └──────┬─────────┬───┘         │
    └─────────┬──┘         │         │              │
              │        complete    stopped           │
              │    ┌───────▼──┐  ┌──▼──────────┐   │
              │    │ RESULTS  │  │  PARTIAL    │   │
          edit     │ READY    │  │  RESULTS    │   │
              │    └───────┬──┘  └──┬──────────┘   │
              │            │        │               │
              └────────────┴────────┴───────────────┘
                           │ edit model
                    (back to EDITING)
```

**Key states:**
- **EDITING** — normal canvas interaction, property dialogs, connecting elements
- **VALIDATING** — brief internal state when Run is clicked, not visible unless errors found
- **RUNNING** — simulation executing, canvas locked, progress bar visible
- **RESULTS READY** — simulation complete, result viewers available, canvas editable again
- **PARTIAL RESULTS** — simulation stopped early, partial results viewable

---

*End of HydroSim Application Flow Document v1.0*
