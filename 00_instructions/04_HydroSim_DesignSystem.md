# HydroSim — Design System
## Visual & Interaction Reference for Claude Code

**Version:** 1.0  
**Source:** Extracted from Claude Design prototype (HydroSim.html + styles.css + JSX components)  
**Companion documents:** PRD v1.0, App Flow v1.0, Tech Stack v1.0  
**Purpose:** This document gives Claude Code the exact design tokens, component specifications, interaction patterns, and visual rules needed to implement HydroSim's PyQt6 UI pixel-accurately. Every value here is derived from the working HTML/CSS/JSX prototype — treat it as the design authority.

---

## Table of Contents

1. [Design Philosophy](#1-design-philosophy)
2. [Colour System](#2-colour-system)
3. [Typography](#3-typography)
4. [Spacing & Sizing](#4-spacing--sizing)
5. [Elevation & Shadows](#5-elevation--shadows)
6. [Layout Architecture](#6-layout-architecture)
7. [Menu Bar](#7-menu-bar)
8. [Toolbar](#8-toolbar)
9. [Element Palette](#9-element-palette)
10. [Canvas](#10-canvas)
11. [Element Cards (Nodes)](#11-element-cards-nodes)
12. [Port Dots](#12-port-dots)
13. [Connection Arrows](#13-connection-arrows)
14. [Element Icons (SVG Paths)](#14-element-icons-svg-paths)
15. [Status Bar](#15-status-bar)
16. [Property Dialogs](#16-property-dialogs)
17. [WaterStore Dialog](#17-waterstore-dialog)
18. [Expression Dialog](#18-expression-dialog)
19. [Result Viewer Window](#19-result-viewer-window)
20. [Hydrograph Chart](#20-hydrograph-chart)
21. [Buttons](#21-buttons)
22. [Form Fields](#22-form-fields)
23. [Animations & Transitions](#23-animations--transitions)
24. [PyQt6 Implementation Notes](#24-pyqt6-implementation-notes)
25. [CSS Variable → PyQt6 Mapping](#25-css-variable--pyqt6-mapping)

---

## 1. Design Philosophy

**Modern engineering software aesthetic.** Clean and functional, not flashy. Think Notion meets lab instrument software — every element earns its place. Light theme only. No dark mode in Phase 1.

**Four rules that govern all visual decisions:**

1. **Colour codes category, not decoration** — element category colours (green, blue, teal, orange) are the primary visual system. They appear on category headers, card top bars, port dots, connection arrows, and icons. They are never used decoratively.

2. **White panels float on grey** — the app background is `#F5F6FA` (light grey). All panels, cards, and dialogs are `#FFFFFF` (white). This one-step contrast creates depth without shadows on every surface.

3. **Monospace for data, proportional for UI** — any value that is a number, formula, identifier, code, or unit uses Fira Code. All labels, headings, and descriptions use Inter. This distinction is rigidly enforced.

4. **Subtle motion, never decorative** — transitions are 120ms maximum. Animations serve functional purposes only (progress indicator, dialog entrance, status pulse). No hover animations on the canvas.

---

## 2. Colour System

### 2.1 CSS Custom Properties → PyQt6 Constants

All colours below must be defined as Python constants in `hydrosim/gui/styles/theme.py`. Reference them everywhere — never hardcode hex values in widget code.

```python
# hydrosim/gui/styles/theme.py

# ── App surfaces ───────────────────────────────────────────
APP_BG          = "#F5F6FA"   # Application background, canvas background
PANEL_BG        = "#FFFFFF"   # All panels: palette, toolbar, dialogs, cards
BORDER_SUBTLE   = "#E7E9EE"   # Panel borders, toolbar bottom, dialog separators
BORDER_FIELD    = "#E5E7EB"   # Form field borders (default state)
BORDER_INNER    = "#ECEEF2"   # Inner borders: menu dividers, node body dividers
SURFACE_RAISED  = "#F4F6F9"   # Hover state for toolbar buttons, search bg
SURFACE_DEEPENED = "#F5F6FA"  # Formula editor body bg, chart toolbar bg

# ── Text ───────────────────────────────────────────────────
TEXT_PRIMARY    = "#1A1A2E"   # All headings, body text, element names
TEXT_SECONDARY  = "#6B7280"   # Labels, metadata, port names, placeholder text
TEXT_TERTIARY   = "#9CA3AF"   # Placeholder text in search
TEXT_FAINT      = "#C2C7D0"   # Line numbers in formula editor, separators

# ── Element category colours ───────────────────────────────
CAT_INPUT       = "#4CAF82"   # Input elements: Constant, TimeSeries
CAT_STOCK       = "#2E86C1"   # Stock elements: WaterStore
CAT_EXPR        = "#00897B"   # Expression elements: Expression
CAT_RESULT      = "#E8633A"   # Result elements: TimeHistoryResult

# ── Semantic colours ───────────────────────────────────────
SEL_BLUE        = "#2E86C1"   # Selection rings, focus rings, primary buttons
ERR_RED         = "#E53935"   # Error states, Stop button colour
OK_GREEN        = "#43A047"   # Run button, success states, OK pill
WARN_AMBER      = "#FB8C00"   # Warnings (not used in Phase 1 UI but reserve)

# ── Syntax highlighting (formula editor) ──────────────────
SYNTAX_ELEM     = "#4CAF82"   # Element name references (same as CAT_INPUT)
SYNTAX_OP       = "#8A93A0"   # Operators: *, +, -, /
SYNTAX_NUM      = "#7B68C8"   # Numeric literals
SYNTAX_FN       = "#00897B"   # Function names (same as CAT_EXPR)

# ── Canvas ────────────────────────────────────────────────
GRID_DOT        = "#DEE2E8"   # Dot grid points on canvas
GRID_DOT_SIZE   = 1.6         # Dot radius in pixels (default)
GRID_SPACING    = 20          # Grid interval in pixels (default)

# ── Overlay ───────────────────────────────────────────────
OVERLAY_BG      = "rgba(20, 22, 34, 0.34)"  # Dialog backdrop
```

### 2.2 Category Colour Usage Rules

| Context | Rule |
|---|---|
| Card top bar | Solid fill, full category colour, 4px height |
| Card border (default) | `BORDER_FIELD` (`#E5E7EB`) — NOT the category colour |
| Card border (selected) | `SEL_BLUE` (`#2E86C1`) — NOT the category colour |
| Port dot (output) | Solid fill, category colour |
| Port dot (input, unconnected) | Hollow: category colour border, white fill |
| Port dot (input, connected) | Solid fill, category colour |
| Connection arrow | Category colour of the SOURCE element, 80% opacity |
| Palette category header text | Category colour |
| Palette category swatch | 9×9px rounded square, category colour |
| Icon inside card | Category colour |
| Dialog header icon background | 10% tint of category colour |

### 2.3 Tints for Dialog Icon Backgrounds

These are the `background` values for the circular icon container in dialog headers:

```python
DIALOG_ICON_BG = {
    "input":  "#E8F5EE",   # ~10% tint of CAT_INPUT
    "stock":  "#E3F0FA",   # ~10% tint of CAT_STOCK
    "expr":   "#E0F2F1",   # ~10% tint of CAT_EXPR
    "result": "#FBE9E4",   # ~10% tint of CAT_RESULT
}
```

---

## 3. Typography

### 3.1 Font Families

```python
FONT_UI   = "Inter"         # All UI text — labels, buttons, names, descriptions
FONT_MONO = "Fira Code"     # All data text — values, IDs, formulas, units, shortcuts

# PyQt6 fallback chain:
FONT_UI_FAMILY   = "Inter, Segoe UI, system-ui, sans-serif"
FONT_MONO_FAMILY = "Fira Code, ui-monospace, SF Mono, Menlo, Consolas, monospace"
```

### 3.2 Type Scale

All sizes in pixels (screen pixels, not points):

| Token | Size | Weight | Use |
|---|---|---|---|
| `TEXT_XS` | 10px | 400 | Port labels, node IDs, line numbers, scale labels |
| `TEXT_SM` | 11px | 400/600 | Status bar, palette descriptions, dialog subtitles, shortcuts |
| `TEXT_SM_PLUS` | 11.5px | 400/600 | Field labels (600), status pills (600), chart legend |
| `TEXT_MD` | 12px | 400/500/600 | Palette item names (600), menu items (400), chips (600) |
| `TEXT_MD_PLUS` | 12.5px | 400/600 | Search input, dialog field inputs, palette item names |
| `TEXT_BASE` | 13px | 400/500/600 | Toolbar buttons (500), menu bar items (400), dialog inputs (400), formula code |
| `TEXT_BASE_PLUS` | 13.5px | 400 | Formula code text |
| `TEXT_LG` | 15px | 700 | Dialog header titles |
| `TEXT_XL` | 13px | 700 | Menu bar brand name (same size as menu items, heavier) |

### 3.3 Typography Application Rules

**Always monospace (`FONT_MONO`):**
- Element IDs on cards (e.g., `ts_rain`)
- Numeric values inside cards (e.g., `0.30`)
- Units display inside cards (e.g., `mm/day`)
- Formula editor content
- Storage indicator values
- Keyboard shortcut hints in menus
- Zoom percentage in status bar
- Simulation step count
- Any `mm`, `m³/s`, `mm/day` unit text anywhere
- `Δt = 1 day · 365 steps` in toolbar meta

**Always proportional (`FONT_UI`):**
- Everything else — labels, names, descriptions, buttons, headings

---

## 4. Spacing & Sizing

### 4.1 Core Dimensions

```python
# Application frame
APP_MIN_WIDTH   = 1280   # px — minimum window width

# Zones
MENUBAR_HEIGHT  = 32     # px
TOOLBAR_HEIGHT  = 48     # px
PALETTE_WIDTH   = 200    # px
STATUSBAR_HEIGHT = 28    # px

# Element cards
CARD_WIDTH      = 180    # px (fixed, not resizable in Phase 1)
CARD_CORNER_R   = 10     # px — border radius (default, user-tweakable 0–18)
CARD_TOP_BAR_H  = 4      # px — category colour bar at top of card
CARD_PADDING_H  = 12     # px — horizontal inner padding
CARD_PADDING_V  = 10     # px — vertical inner padding (head area)
CARD_DIVIDER_H  = 1      # px — height of separator between head and body

# Ports
PORT_DIAMETER   = 10     # px — default port dot size
PORT_HOVER_D    = 14     # px — port dot size on hover
PORT_ROW_HEIGHT = 20     # px — height of each port row in card body
PORT_OFFSET_X   = 6      # px — port dot extends outside card edge by this amount

# Connections
CONN_STROKE_W   = 2.0    # px
CONN_CTRL_OFFSET = 80    # px — bezier control point horizontal offset
ARROW_SIZE      = 7      # px — arrowhead polygon size

# Canvas
CANVAS_LOGICAL_W = 4000  # px — logical canvas width
CANVAS_LOGICAL_H = 3000  # px — logical canvas height
ZOOM_MIN        = 0.4    # 40%
ZOOM_MAX        = 2.0    # 200%
ZOOM_STEP       = 0.1    # per scroll tick or zoom button click

# Palette
PAL_ITEM_MARGIN = 8      # px — horizontal margin around palette items
PAL_ITEM_PADDING_H = 9   # px — horizontal inner padding
PAL_ITEM_PADDING_V = 8   # px — vertical inner padding
PAL_ITEM_RADIUS = 8      # px — palette item border radius
PAL_ICON_SIZE   = 20     # px — palette icon size
CAT_HEADER_H    = 40     # px — approx category header height (padding-based)
CAT_SWATCH_SIZE = 9      # px — category colour swatch square size
CAT_SWATCH_R    = 3      # px — swatch corner radius

# Dialogs
DIALOG_RADIUS   = 14     # px
DIALOG_HEAD_PAD = 18     # px — vertical / 20px horizontal
DIALOG_BODY_PAD = 20     # px
DIALOG_FOOT_PAD_V = 14   # px
DIALOG_ICON_SIZE = 34    # px — square containing the element icon
DIALOG_ICON_R   = 9      # px — icon container corner radius

# Buttons
BTN_RADIUS      = 6      # px
BTN_PAD_V       = 8      # px
BTN_PAD_H       = 16     # px
BTN_FONT_SIZE   = 13     # px
BTN_FONT_WEIGHT = 600

# Form fields
FIELD_RADIUS    = 6      # px
FIELD_PAD_V     = 9      # px
FIELD_PAD_H     = 11     # px
FIELD_FONT_SIZE = 13     # px
FIELD_LABEL_SIZE = 11.5  # px, weight 600

# Toolbar buttons
TBTN_HEIGHT     = 32     # px
TBTN_RADIUS     = 7      # px
TBTN_PAD_H      = 12     # px
TBTN_FONT_SIZE  = 13     # px
TBTN_FONT_W     = 500

# Chips (Available Elements in Expression dialog)
CHIP_RADIUS     = 20     # px (pill shape)
CHIP_PAD_V      = 6      # px
CHIP_PAD_H      = 11     # px
CHIP_DOT_SIZE   = 8      # px
```

### 4.2 Grid System for Dialogs

Dialogs use a 2-column grid for related fields:

```python
FIELD_GRID_COLS = 2
FIELD_GRID_GAP  = 14     # px
FIELD_ROW_GAP   = 16     # px — margin-bottom on each field
```

---

## 5. Elevation & Shadows

Three shadow levels, user-tweakable via the Tweaks panel:

```python
SHADOW_FLAT     = "0 1px 2px rgba(0, 0, 0, 0.07)"
SHADOW_SUBTLE   = "0 4px 12px rgba(0, 0, 0, 0.10)"   # DEFAULT for element cards
SHADOW_FLOATING = "0 10px 26px rgba(0, 0, 0, 0.16)"

# Dialogs and floating windows always use:
SHADOW_DIALOG   = "0 24px 64px rgba(0, 0, 0, 0.30)"

# Dropdown menus:
SHADOW_DROPDOWN = "0 8px 28px rgba(0, 0, 0, 0.14)"

# Run button:
SHADOW_RUN_BTN  = "0 1px 2px rgba(67, 160, 71, 0.35)"
```

**In PyQt6**, shadows are applied via `QGraphicsDropShadowEffect` on `QGraphicsItem` subclasses, or via QSS `box-shadow` equivalent where possible.

---

## 6. Layout Architecture

The main window is a vertical flex stack with a horizontal split in the centre:

```
QMainWindow
└── QWidget (central)
    └── QVBoxLayout (zero margin, zero spacing)
        ├── MenuBar          — 32px fixed height
        ├── Toolbar          — 48px fixed height
        ├── QHBoxLayout      — flex: 1, fills remaining height
        │   ├── Palette      — 200px fixed width, right border 1px #E7E9EE
        │   └── Canvas       — flex: 1, fills remaining width
        └── StatusBar        — 28px fixed height, top border 1px #E7E9EE
```

**All borders are 1px solid `#E7E9EE`** between zones. No margins between zones — everything flush.

---

## 7. Menu Bar

**Height:** 32px  
**Background:** `#FFFFFF`  
**Bottom border:** 1px solid `#ECEEF2`  
**Font:** Inter, 13px, weight 400  
**Padding:** 0 8px

### 7.1 Brand Logo + Name

Left-most item in the menu bar:

- **Logo SVG:** 16×16px water drop shape, filled `#2E86C1`
  ```
  Path: M8 1.5 C8 1.5 13 7 13 10.4 A5 5 0 0 1 3 10.4 C3 7 8 1.5 8 1.5 Z
  ```
- **Name:** "HydroSim", Inter, 13px, weight 700, letter-spacing -0.01em
- **Gap between logo and text:** 7px
- **Right padding:** 12px (creates space before first menu item)
- **Colour:** `TEXT_PRIMARY` (`#1A1A2E`)

### 7.2 Menu Items

- **Padding:** 5px 10px
- **Border radius:** 5px
- **Hover/open:** background `#EEF0F4`
- **Cursor:** default (not pointer)
- **No underline, no decoration**

### 7.3 Dropdown Menu

Appears below the menu item when clicked:

- **Background:** `#FFFFFF`
- **Border:** 1px solid `#E7E9EE`
- **Border radius:** 8px
- **Box shadow:** `SHADOW_DROPDOWN`
- **Padding:** 5px
- **Z-index:** above everything except dialogs
- **Min width:** 188px
- **Position:** `top: 28px, left: 0` relative to menu item

**Menu row:**
- Padding: 7px 10px
- Border radius: 5px
- Font: 12.5px
- Hover: background `#EEF0F4`
- Keyboard shortcut: right-aligned, `TEXT_SECONDARY`, 11px, Fira Code

**Separator:** 1px `#ECEEF2`, margin 5px 6px

---

## 8. Toolbar

**Height:** 48px  
**Background:** `#FFFFFF`  
**Bottom border:** 1px solid `#E7E9EE`  
**Padding:** 0 12px  
**Gap between items:** 6px

### 8.1 Toolbar Buttons (`.tbtn`)

Standard file operation buttons (New, Open, Save):

- **Height:** 32px
- **Padding:** 0 12px
- **Border:** 1px solid `#E2E5EB`
- **Background:** `#FFFFFF`
- **Border radius:** 7px
- **Font:** Inter, 13px, weight 500
- **Icon + label gap:** 7px
- **Icon size:** 15×15px SVG, `currentColor`
- **Hover:** background `#F4F6F9`, border `#D5D9E0`
- **Transition:** background, border-color, box-shadow — 120ms

### 8.2 Run Button

- **Background:** `#43A047` (`OK_GREEN`)
- **Border:** 1px solid `#43A047`
- **Colour:** `#FFFFFF`
- **Font weight:** 600
- **Padding:** 0 16px (wider than standard)
- **Box shadow:** `SHADOW_RUN_BTN`
- **Icon:** 13×13px play triangle, `fill="currentColor"`
- **Hover:** background `#3d9242`, border `#3d9242`
- **Disabled:** opacity 0.5, cursor not-allowed
- **Text when running:** "Running…" (button remains disabled)

### 8.3 Stop Button

- **Colour:** `#E53935` (`ERR_RED`)
- **Border:** 1px solid `#F0C6C5`
- **Background:** `#FFF6F6`
- **Font weight:** 600
- **Hover:** background `#FDECEC`
- **Disabled:** colour `#C9B6B6`, border `#ECEEF2`, background `#FAFBFC`

### 8.4 Toolbar Divider

- **Width:** 1px, height 24px
- **Colour:** `#E3E6EC`
- **Margin:** 0 6px

### 8.5 Toolbar Meta Text (right side)

Text: `Δt = 1 day · 365 steps`
- **Font:** Fira Code, 12px
- **Colour:** `TEXT_SECONDARY`
- **Position:** pushed to right by `flex: 1` spacer

### 8.6 Run Progress Bar

When simulation is running, a progress bar appears at the bottom of the toolbar:

- **Height:** 2px
- **Colour:** `SEL_BLUE` (`#2E86C1`)
- **Position:** absolute, bottom 0, left 0
- **Width:** `progress * 100%` (animated with CSS transition 0.1s linear)

---

## 9. Element Palette

**Width:** 200px (fixed)  
**Background:** `#FFFFFF`  
**Right border:** 1px solid `#E7E9EE`

### 9.1 Search Bar

- **Padding:** 10px (wrapper)
- **Bottom border:** 1px solid `#EEF0F4`
- **Search field wrapper:**
  - Height: 32px
  - Padding: 0 9px
  - Background: `#F5F6FA`
  - Border: 1px solid `#E5E7EB`
  - Border radius: 7px
  - Icon: 14×14px search SVG, colour `#9CA3AF`
  - Gap between icon and input: 7px
- **Input:** font Inter 12.5px, placeholder colour `#9CA3AF`

### 9.2 Category Header

- **Padding:** 9px 12px
- **Font:** Inter, 11px, weight 700, letter-spacing 0.06em (wide caps)
- **Colour:** Category colour (e.g., `#4CAF82` for INPUT)
- **Left swatch:** 9×9px rounded square (radius 3px), category colour, gap 8px
- **Chevron:** right-aligned, 12×12px SVG arrow, `TEXT_SECONDARY`
- **Collapsed state:** chevron rotated -90deg

### 9.3 Palette Item

- **Margin:** 3px 8px (creates inset appearance)
- **Padding:** 8px 9px
- **Border radius:** 8px
- **Border:** 1px solid transparent (default)
- **Cursor:** grab / grabbing
- **Hover:** background `#F6F8FB`, border `#E7E9EE`, box-shadow `0 1px 3px rgba(0,0,0,0.04)`
- **Layout:** flex row, gap 9px, items align-start
- **Icon:** 20×20px, category colour
- **Name:** Inter, 12.5px, weight 600, line-height 1.2
- **Description:** Inter, 10.5px, `TEXT_SECONDARY`, line-height 1.3, margin-top 2px
- **Dragging state:** opacity 0.4

---

## 10. Canvas

### 10.1 Canvas Zone

- **Background:** `#F5F6FA` (`APP_BG`)
- **Overflow:** hidden
- **Position:** relative, fills remaining space

### 10.2 Dot Grid

Implemented as a CSS `background-image` radial-gradient — in PyQt6, draw in `QGraphicsScene.drawBackground()`:

```python
def drawBackground(self, painter, rect):
    # Draw dot grid
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(GRID_DOT))  # #DEE2E8

    spacing = self.grid_spacing  # default 20
    dot_size = self.grid_dot_size  # default 1.6

    left = int(rect.left()) - (int(rect.left()) % spacing)
    top = int(rect.top()) - (int(rect.top()) % spacing)

    x = left
    while x < rect.right():
        y = top
        while y < rect.bottom():
            painter.drawEllipse(QPointF(x, y), dot_size, dot_size)
            y += spacing
        x += spacing
```

### 10.3 Canvas Content Transform

The canvas content div uses `transform: translate(pan.x, pan.y) scale(zoom)` with `transform-origin: 0 0`. In PyQt6 this is the `QGraphicsView` viewport transform — use `QGraphicsView.setTransform()`.

### 10.4 Canvas Interactions

| Interaction | Behaviour |
|---|---|
| Left drag on background | Pan canvas |
| Scroll wheel | Zoom toward cursor position |
| Left click on element | Select element |
| Left drag on element | Move element |
| Double-click on element | Open property dialog |
| Left click on empty canvas | Deselect all |
| Drag from palette, drop on canvas | Create new element at drop position |
| Drag from output port | Begin drawing connection |
| Release on input port | Complete connection |
| Release on empty canvas | Cancel connection |

### 10.5 Zoom Behaviour

- **Min:** 40% (`ZOOM_MIN = 0.4`)
- **Max:** 200% (`ZOOM_MAX = 2.0`)
- **Step:** 0.1 per scroll tick
- **Zoom toward cursor:** adjust pan offset so the point under the cursor stays fixed

```python
def wheelEvent(self, event):
    delta = event.angleDelta().y()
    factor = 1.1 if delta > 0 else 0.9
    new_zoom = max(ZOOM_MIN, min(ZOOM_MAX, self.zoom * factor))

    # Zoom toward cursor
    cursor_scene = self.mapToScene(event.position().toPoint())
    self.zoom = new_zoom
    self.centerOn(cursor_scene)
```

---

## 11. Element Cards (Nodes)

The element card is the most complex visual component. Every detail matters.

### 11.1 Card Structure

```
┌──────────────────────────────────────┐  ← CARD_WIDTH = 180px
│████████████████████████████████████  │  ← 4px top bar, solid category colour
├──────────────────────────────────────┤  ← 1px #ECEEF2
│  [icon 22px]  Element Name          │  ← head section
│               element_id            │  ← 10px mono, TEXT_SECONDARY
├──────────────────────────────────────┤  ← 1px #ECEEF2 divider
│ ●── port_name    port_name ──●      │  ← body: ports + content
│                                      │
│  [type-specific content area]        │
│                                      │
└──────────────────────────────────────┘
```

### 11.2 Card Visual Properties

```python
CARD_BACKGROUND   = "#FFFFFF"
CARD_BORDER_DEFAULT = "#E5E7EB"    # default state
CARD_BORDER_SELECTED = "#2E86C1"   # selected state (SEL_BLUE)
CARD_BORDER_WIDTH_DEFAULT = 1.0    # px
CARD_BORDER_WIDTH_SELECTED = 2.5   # px
CARD_CORNER_RADIUS = 10            # px (user-tweakable)
CARD_SHADOW = SHADOW_SUBTLE        # "0 4px 12px rgba(0,0,0,0.10)"
```

### 11.3 Card Head Section

- **Padding:** ~10px 12px
- **Layout:** flex row, gap 9px, align-items center
- **Icon:** 22×22px SVG, category colour
- **Icon container (`nicon`):** 22×22px, no background
- **Name:** Inter, 13px, weight 600, `TEXT_PRIMARY`, line-height 1.2
- **ID (below name):** Fira Code, 10px, weight 400, `TEXT_SECONDARY`
- **Divider below head:** 1px solid `#ECEEF2`

### 11.4 Card Body Section

The card body contains type-specific content followed by port rows.

**Port rows:**
- **Height:** ~20px per row
- **Layout:** flex row, align-items center
- **Input port rows:** port dot LEFT, label RIGHT of dot
- **Output port rows:** label LEFT, port dot RIGHT
- **Port label:** 10px, `TEXT_SECONDARY` (`#6B7280`)
- **Padding:** 0 12px (matching card horizontal padding)

### 11.5 Type-Specific Body Content

**TimeSeries card body:**
```
  val (mono):   "mm/day"    — TEXT_SECONDARY, 13px mono
  unit:         "daily series"  — TEXT_SECONDARY, 10px
```

**Constant card body:**
```
  val (mono):   "0.30"      — TEXT_PRIMARY, 13px mono, weight 500
  unit:         ""           — TEXT_SECONDARY, 10px (the unit string)
```

**Expression card body:**
- Inline formula display: `Daily_Rainfall × RunoffCoeff`
- `Daily_Rainfall` and `RunoffCoeff` coloured `CAT_INPUT` (`#4CAF82`), weight 600
- `×` operator coloured `SYNTAX_OP` (`#8A93A0`)
- Font: Fira Code, 12px

**WaterStore card body — mini storage bar:**
```
Track: height ~6px, border-radius 4px, background #EEF1F5
Fill:  width = (80/150 * 100)% = 53.3%
       gradient: top #4aa3da → bottom #2E86C1
Labels below: "80 mm" (mono left) and "/ 150 mm" (mono right)
Label font: 10px, TEXT_SECONDARY
```

**TimeHistoryResult card body — sparkline:**
- SVG, 156×34px
- Area fill: gradient from category colour at 22% opacity → 0%
- Line stroke: category colour (`CAT_RESULT = #E8633A`), 1.6px, round caps/joins
- Gradient ID must be unique per element to avoid SVG conflicts

### 11.6 Card States

| State | Border | Shadow | Other |
|---|---|---|---|
| Default | 1px `#E5E7EB` | `SHADOW_SUBTLE` | — |
| Hover | 1px `#E5E7EB` | `SHADOW_SUBTLE` | cursor changes |
| Selected | 2.5px `#2E86C1` | `SHADOW_SUBTLE` | — |
| Dragging | 1px `#E5E7EB` | `SHADOW_FLOATING` | opacity 0.9, cursor grabbing |
| Error | 2px `#E53935` | `SHADOW_SUBTLE` | warning triangle top-right |
| Has Results | default | default | 8px filled green dot top-right |

---

## 12. Port Dots

### 12.1 Visual Properties

```python
PORT_DIAMETER = 10         # px default
PORT_HOVER_DIAMETER = 14   # px on hover

# Input port (unconnected):
PORT_INPUT_FILL = "#FFFFFF"
PORT_INPUT_STROKE = category_colour    # 1.5px

# Input port (connected):
PORT_INPUT_FILL = category_colour
PORT_INPUT_STROKE = category_colour

# Output port:
PORT_OUTPUT_FILL = category_colour
PORT_OUTPUT_STROKE = None              # no stroke
PORT_OUTPUT_OPACITY_UNCONNECTED = 0.7
PORT_OUTPUT_OPACITY_CONNECTED = 1.0
```

### 12.2 Port Positioning

- **Input ports:** centred vertically on left edge of card, extending ~5px outside
- **Output ports:** centred vertically on right edge of card, extending ~5px outside
- Each port row is 20px tall; ports are vertically centred within their row

### 12.3 Port Hover State

- Port expands from 10px to 14px diameter (scale, not reposition)
- Tooltip appears: `"port_name (units) — description"`
- Tooltip background: `#1A1A2E`, text `#FFFFFF`, border-radius 6px, font 11px

### 12.4 Port During Connection Drag

- **Compatible target ports:** green glow ring (2px `#43A047`, 3px blur)
- **Incompatible ports:** red glow ring (2px `#E53935`, 3px blur)
- Visual feedback appears as soon as drag begins

---

## 13. Connection Arrows

### 13.1 Geometry

Cubic bezier curve between two ports:

```python
def build_bezier_path(start_x, start_y, end_x, end_y, ctrl_offset=80):
    """
    start = output port centre
    end   = input port centre
    ctrl1 = start + (ctrl_offset, 0)   — departs rightward
    ctrl2 = end   + (-ctrl_offset, 0)  — arrives leftward
    """
    path = QPainterPath()
    path.moveTo(start_x, start_y)
    path.cubicTo(
        start_x + ctrl_offset, start_y,   # ctrl1
        end_x - ctrl_offset, end_y,        # ctrl2
        end_x, end_y                       # destination
    )
    return path
```

### 13.2 Visual Properties

```python
CONN_STROKE_WIDTH   = 2.0    # px
CONN_STROKE_OPACITY = 0.8    # 80% opacity on the category colour
CONN_SELECTED_WIDTH = 3.0    # px
CONN_SELECTED_COLOR = SEL_BLUE  # #2E86C1

# Arrow colour = source element's category colour at 80% opacity
# e.g., connection from TimeSeries (input): #4CAF82 at 80%
#       connection from WaterStore (stock): #2E86C1 at 80%
```

### 13.3 Arrowhead

Small filled triangle at the destination end:

```python
ARROW_SIZE = 7  # px

def build_arrowhead(end_x, end_y, angle_radians):
    """
    Filled polygon at end point, pointing in direction of approach.
    """
    # Equilateral-ish triangle, tip at (end_x, end_y)
    tip = QPointF(end_x, end_y)
    base_left = QPointF(
        end_x - ARROW_SIZE * math.cos(angle_radians - 0.4),
        end_y - ARROW_SIZE * math.sin(angle_radians - 0.4)
    )
    base_right = QPointF(
        end_x - ARROW_SIZE * math.cos(angle_radians + 0.4),
        end_y - ARROW_SIZE * math.sin(angle_radians + 0.4)
    )
    return QPolygonF([tip, base_left, base_right])
```

### 13.4 Connection Hover State

- Stroke thickens to 2.5px
- Opacity increases to 1.0 (from 0.8)
- Tooltip: `"ElementA.output_port → ElementB.input_port (units)"`

---

## 14. Element Icons (SVG Paths)

These exact SVG paths from the prototype must be reproduced in PyQt6 using `QPainterPath`. All icons use a `20×20` viewBox with `fill="none"` where stroked.

### 14.1 TimeSeries Icon

```xml
<svg viewBox="0 0 20 20" fill="none">
  <polyline points="2,13 6,8 9,11 13,4 18,7"
    stroke="{color}" stroke-width="1.8"
    stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="2" cy="13" r="1.4" fill="{color}"/>
  <circle cx="13" cy="4" r="1.4" fill="{color}"/>
</svg>
```

### 14.2 Constant Icon

```xml
<svg viewBox="0 0 20 20" fill="none">
  <rect x="4" y="7.4" width="12" height="2" rx="1" fill="{color}"/>
  <rect x="4" y="11" width="12" height="2" rx="1" fill="{color}"/>
</svg>
```
*(Two horizontal parallel bars — like an equals sign, representing a fixed value)*

### 14.3 Expression Icon

```xml
<svg viewBox="0 0 20 20" fill="none">
  <path d="M12 3.2c-2 0-2.4 1.2-2.7 3.1L7.6 16.2C7.3 18 6.7 18.8 5.2 18.4"
    stroke="{color}" stroke-width="1.7" stroke-linecap="round" fill="none"/>
  <rect x="6.2" y="8.1" width="6.2" height="1.7" rx="0.85" fill="{color}"/>
</svg>
```
*(Integral-like curve with a horizontal bar — mathematical function)*

### 14.4 WaterStore Icon

```xml
<svg viewBox="0 0 20 20" fill="none">
  <rect x="4" y="3.5" width="12" height="13" rx="2.2"
    stroke="{color}" stroke-width="1.7"/>
  <path d="M4.9 10.5h10.2v4.1a1.9 1.9 0 0 1-1.9 1.9H6.8a1.9 1.9 0 0 1-1.9-1.9z"
    fill="{color}" opacity="0.85"/>
</svg>
```
*(Tank outline with filled lower half — water storage vessel)*

### 14.5 TimeHistoryResult Icon

```xml
<svg viewBox="0 0 20 20" fill="none">
  <rect x="3"   y="11"  width="3.2" height="6"    rx="1" fill="{color}"/>
  <rect x="8.4" y="7"   width="3.2" height="10"   rx="1" fill="{color}"/>
  <rect x="13.8" y="3.5" width="3.2" height="13.5" rx="1" fill="{color}"/>
</svg>
```
*(Three ascending bars — time history / bar chart)*

### 14.6 Application Logo

Used in menubar and statusbar:

```xml
<svg width="16" height="16" viewBox="0 0 16 16" fill="none">
  <path d="M8 1.5C8 1.5 13 7 13 10.4A5 5 0 0 1 3 10.4C3 7 8 1.5 8 1.5Z"
    fill="#2E86C1"/>
</svg>
```
*(Water droplet shape, filled ocean blue)*

### 14.7 Rendering Icons in PyQt6

```python
def draw_icon(painter: QPainter, kind: str, x: float, y: float,
              size: float, color: QColor):
    """
    Draw element icon at (x, y) in a [size × size] bounding box.
    Scale from 20×20 viewBox to [size × size].
    """
    scale = size / 20.0
    painter.save()
    painter.translate(x, y)
    painter.scale(scale, scale)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Set up pen and brush based on icon type
    pen = QPen(color)
    brush = QBrush(color)

    if kind == 'timeseries':
        pen.setWidthF(1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        # Draw polyline 2,13 6,8 9,11 13,4 18,7
        pts = [QPointF(2,13), QPointF(6,8), QPointF(9,11),
               QPointF(13,4), QPointF(18,7)]
        painter.drawPolyline(pts)
        # Draw endpoint circles
        painter.setBrush(brush)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(2, 13), 1.4, 1.4)
        painter.drawEllipse(QPointF(13, 4), 1.4, 1.4)

    # ... (similar for other icon types)
    painter.restore()
```

---

## 15. Status Bar

**Height:** 28px  
**Background:** `#FFFFFF`  
**Top border:** 1px solid `#E7E9EE`  
**Padding:** 0 14px  
**Font:** Inter, 11.5px, `TEXT_SECONDARY`

### 15.1 Layout (three zones)

```
[LEFT: logo + model name + element count] [CENTER: status pill] [RIGHT: zoom control]
```

**Left zone:**
- HydroSim logo (13×13px water drop, `#2E86C1`)
- Model name: Inter 11.5px, weight 600, `TEXT_PRIMARY`
- Dot separator: `#C2C7D0`
- Element count: Fira Code, 11.5px (e.g., `5 elements`)
- Gap: 7px between items

**Centre zone:** (absolute centred)
- Status pill (see below)

**Right zone:**
- Zoom control (see below)

### 15.2 Status Pills

Four states:

```python
# Idle / Ready
PILL_IDLE = {
    "bg": "#F0F1F5", "color": TEXT_SECONDARY,
    "text": "Ready", "dot_animate": False
}

# Running
PILL_RUNNING = {
    "bg": "#E3F0FA", "color": SEL_BLUE,
    "text": "Running… step {n} / 365", "dot_animate": True
}

# Complete
PILL_OK = {
    "bg": "#E8F5E9", "color": OK_GREEN,
    "text": "Simulation complete — 365 steps in {elapsed}", "dot_animate": False
}

# Stopped
PILL_STOPPED = {
    "bg": "#F0F1F5", "color": TEXT_SECONDARY,
    "text": "Stopped at step {n}", "dot_animate": False
}

# Pill common style:
PILL_PADDING  = "3px 11px"  # equivalent in Qt
PILL_RADIUS   = 20          # px (pill shape)
PILL_FONT_SIZE = 11.5       # px, weight 600
PILL_DOT_SIZE = 7           # px diameter circle
```

**Running dot animation:** opacity pulses 1.0 → 0.35 → 1.0 over 1 second, infinite.

### 15.3 Zoom Control

```
[−]  [100%]  [+]
```

- Buttons: 18×18px, no border, no background, 4px radius
- Hover: background `#EEF0F4`, colour `TEXT_PRIMARY`
- Percentage: Fira Code, `TEXT_SECONDARY`, min-width 40px, centred
- Click `−`: zoom -= 0.1 (min 40%)
- Click `+`: zoom += 0.1 (max 200%)

---

## 16. Property Dialogs

All dialogs share this structure. The modal is always centred in the application window.

### 16.1 Overlay (Backdrop)

- **Background:** `rgba(20, 22, 34, 0.34)`
- **Covers:** entire application window
- **Animation:** fade in 140ms ease
- **Click outside:** closes the dialog

### 16.2 Dialog Container

- **Background:** `#FFFFFF`
- **Border radius:** 14px
- **Shadow:** `SHADOW_DIALOG` — `0 24px 64px rgba(0,0,0,0.30)`
- **Max height:** 90% of window height (scroll body if needed)
- **Animation:** slide up 8px + scale from 0.98 + fade in, 160ms cubic-bezier(0.2, 0.9, 0.3, 1.1)

### 16.3 Dialog Header

- **Padding:** 18px 20px
- **Bottom border:** 1px solid `#EEF0F4`
- **Layout:** flex row, gap 12px, align-items centre

**Icon container:**
- 34×34px square, border-radius 9px
- Background: `DIALOG_ICON_BG[category]` (tinted)
- Contains 20px element icon in category colour

**Titles:**
- Primary: Inter, 15px, weight 700, letter-spacing -0.01em, `TEXT_PRIMARY`
- Subtitle: Inter, 11.5px, `TEXT_SECONDARY`, margin-top 1px

**Close button (×):**
- 28×28px, border-radius 7px, no border, no background
- Colour: `TEXT_SECONDARY`, font-size 16px
- Hover: background `#EEF0F4`, colour `TEXT_PRIMARY`
- Position: margin-left auto (pushed to right)

### 16.4 Dialog Body

- **Padding:** 20px
- **Overflow:** auto (scrollable if content exceeds max-height)

### 16.5 Dialog Footer

- **Padding:** 14px 20px
- **Top border:** 1px solid `#EEF0F4`
- **Layout:** flex row, justify-content flex-end, gap 10px
- **Buttons:** Cancel (secondary) + OK (primary `SEL_BLUE`)

---

## 17. WaterStore Dialog

**Width:** 500px

### 17.1 Field Layout

```
Name            [________________]
Description     [________________]
Units           [______] (max-width 140px)

Initial Storage [_______] mm     Lower Bound  [_______] mm
                                 Upper Bound  [_______] mm

Storage range   [████████░░░░░░░░░░░░░]
                0 mm    initial 80 of 150 mm    150 mm
```

### 17.2 Storage Indicator Bar

```python
# Track
STORAGE_TRACK_HEIGHT = 30      # px
STORAGE_TRACK_RADIUS = 8       # px
STORAGE_TRACK_BG = "#EEF1F5"
STORAGE_TRACK_BORDER = "#E5E7EB"  # 1px

# Fill (the water level)
STORAGE_FILL_GRADIENT_TOP = "#4aa3da"    # lighter blue
STORAGE_FILL_GRADIENT_BOT = "#2E86C1"   # CAT_STOCK (ocean blue)
# Fill width = ((current - lower) / (upper - lower)) * 100%

# Value label inside fill
STORAGE_VAL_COLOR = "#FFFFFF"
STORAGE_VAL_FONT = 11px, Fira Code, weight 700
STORAGE_VAL_PADDING_R = 8px  # from right edge of fill

# Scale row below track
SCALE_FONT = 10.5px, TEXT_SECONDARY
SCALE_LAYOUT = space-between
SCALE_MARGIN_TOP = 5px
```

---

## 18. Expression Dialog

**Width:** 600px

### 18.1 Field Layout

```
Name [__________]    Output Units [__________]
Description     [________________________________]

Formula
┌─────────────────────────────────────────────────────┐
│ ƒ(x)  ·  expression             [gutter bar]        │
├─────────────────────────────────────────────────────┤
│ 1 │ Daily_Rainfall * RunoffCoeff                    │
└─────────────────────────────────────────────────────┘

Available Elements
[● Daily_Rainfall .value]  [● RunoffCoeff .value]

[Test]  [result = 3.69 mm/day]   ← only shows after Test clicked
```

### 18.2 Formula Editor

```python
# Outer container
EDITOR_BORDER = BORDER_FIELD         # 1px #E5E7EB
EDITOR_RADIUS = 8                    # px
EDITOR_BG     = "#FBFBFD"

# Gutter bar (top strip)
GUTTER_BG     = "#F5F6FA"
GUTTER_BORDER_BOTTOM = "#EEF0F4"    # 1px
GUTTER_PADDING = "7px 12px"
GUTTER_FONT   = 10.5px, Fira Code, TEXT_SECONDARY
GUTTER_TEXT   = "ƒ(x)  ·  expression"

# Body
BODY_LAYOUT   = flex row
BODY_MIN_H    = 96                   # px

# Line numbers column
LINENUMS_BG       = "#F8F9FB"
LINENUMS_BORDER_R = "#EEF0F4"       # 1px
LINENUMS_PADDING  = "12px 10px"
LINENUMS_FONT     = 13px, Fira Code
LINENUMS_COLOR    = "#C2C7D0"

# Code area
CODE_PADDING  = "12px 14px"
CODE_FONT     = 13.5px, Fira Code, line-height 1.7
```

### 18.3 Syntax Token Colours

| Token type | Colour | Weight |
|---|---|---|
| Element reference (e.g., `Daily_Rainfall`) | `#4CAF82` (CAT_INPUT) | 600 |
| Operator (e.g., `*`, `+`) | `#8A93A0` (SYNTAX_OP) | 400 |
| Numeric literal (e.g., `0.3`) | `#7B68C8` (SYNTAX_NUM) | 600 |
| Function name (e.g., `sqrt`) | `#00897B` (CAT_EXPR) | 600 |
| Plain text / unknown | `TEXT_PRIMARY` | 400 |

### 18.4 Available Elements Chips

```python
CHIP_BG       = "#F2F8F4"
CHIP_BORDER   = "#D9EBE0"           # 1px
CHIP_HOVER_BG = "#E7F3EB"
CHIP_HOVER_BORDER = "#BFE0CB"
CHIP_RADIUS   = 20                  # px (pill)
CHIP_PADDING  = "6px 11px"
CHIP_FONT     = 12px, Fira Code

# Inside chip:
CHIP_DOT_SIZE = 8                   # px circle
CHIP_DOT_COLOR = CAT_INPUT          # #4CAF82
CHIP_NAME_WEIGHT = 600
CHIP_PORT_COLOR = TEXT_SECONDARY    # .port suffix
CHIP_PORT_FONT_SIZE = 10.5          # px
```

### 18.5 Test Result Pill

Appears after clicking [Test]:

```python
TEST_PILL_BG    = "#E8F5E9"
TEST_PILL_COLOR = OK_GREEN          # #43A047
TEST_PILL_FONT  = 12.5px, weight 600
TEST_PILL_MONO_COLOR = "#2f7d33"    # slightly darker green
TEST_PILL_RADIUS = 20               # px
TEST_PILL_PADDING = "6px 13px"
TEST_PILL_ANIM  = pop 180ms ease    # same as dialog entrance
```

---

## 19. Result Viewer Window

A draggable floating window, not a modal dialog.

### 19.1 Window Container

```python
WIN_WIDTH       = 800                # px
WIN_HEIGHT      = 500                # px
WIN_RADIUS      = 12                 # px
WIN_SHADOW      = SHADOW_DIALOG      # "0 24px 64px rgba(0,0,0,0.30)"
WIN_BORDER      = "#E2E5EB"          # 1px
WIN_BG          = "#FFFFFF"
WIN_Z_INDEX     = 450                # below dialogs (500)
WIN_INITIAL_X   = (window_width - 800) / 2
WIN_INITIAL_Y   = 110                # px from top
```

### 19.2 Title Bar

```python
TITLEBAR_HEIGHT = 40                 # px
TITLEBAR_BG     = "#FFFFFF"
TITLEBAR_BORDER_BOTTOM = "#EEF0F4"  # 1px
TITLEBAR_CURSOR = "grab" / "grabbing" when dragging

# Dot indicator (left side)
WIN_DOT_SIZE    = 8                  # px circle
WIN_DOT_COLOR   = CAT_RESULT        # #E8633A (coral orange)

# Title text
WIN_TITLE_FONT  = 13px, weight 700

# Right side: [Export CSV button] [× close button]
WIN_X_SIZE      = 26                 # px square
WIN_X_RADIUS    = 6                  # px
WIN_X_FONT      = 15px, TEXT_SECONDARY
```

**Dragging:** title bar `mousedown` → track mouse → update `left` and `top` of window. Constrain to `left ≥ 0, top ≥ 0`.

### 19.3 Chart Area

```python
CHART_WRAP_PADDING  = "16px 18px 4px"
LEGEND_MARGIN_BOT   = 6             # px
LEGEND_FONT         = 11.5px, TEXT_PRIMARY
LEGEND_SWATCH_W     = 14            # px
LEGEND_SWATCH_H     = 3             # px
LEGEND_SWATCH_R     = 2             # px
LEGEND_SWATCH_COLOR = CAT_STOCK    # #2E86C1
LEGEND_TEXT         = "SoilMoisture.storage"
LEGEND_FONT_MONO    = Fira Code
```

### 19.4 Chart Toolbar

```python
CHART_TOOLBAR_BG      = "#FBFBFD"
CHART_TOOLBAR_BORDER  = "#EEF0F4"   # 1px top border
CHART_TOOLBAR_PADDING = "8px 14px"

# Chart tool buttons
CTBTN_SIZE    = 30                  # px square
CTBTN_RADIUS  = 6                   # px
CTBTN_BORDER  = "#E5E7EB"          # 1px
CTBTN_BG      = "#FFFFFF"
CTBTN_HOVER_BG = "#F4F6F9"
CTBTN_COLOR   = TEXT_SECONDARY
CTBTN_HOVER_COLOR = TEXT_PRIMARY
CTBTN_ICON_SIZE = 15                # px

# Separator
CTBTN_SEP_W   = 1                   # px
CTBTN_SEP_H   = 18                  # px
CTBTN_SEP_COLOR = "#E3E6EC"

# Meta text (right side)
META_TEXT     = "365 steps · Δt = 1 day"
META_FONT     = 11px, Fira Code, TEXT_SECONDARY
```

---

## 20. Hydrograph Chart

The chart is an SVG drawn inside the result viewer. In PyQt6, use PyQtGraph embedded in the chart area.

### 20.1 Chart Margins

```python
CHART_MARGIN_LEFT   = 52    # px (for y-axis labels)
CHART_MARGIN_RIGHT  = 18    # px
CHART_MARGIN_TOP    = 14    # px
CHART_MARGIN_BOTTOM = 40    # px (for x-axis labels + title)
```

### 20.2 Grid Lines

```python
# Horizontal gridlines (y-axis)
GRID_H_COLOR    = "#EEF0F4"    # very light grey
GRID_H_WIDTH    = 1            # px

# Vertical gridlines (x-axis)
GRID_V_COLOR    = "#F3F4F7"    # even lighter grey (secondary)
GRID_V_WIDTH    = 1            # px

# Plot frame border
FRAME_BG        = "#FFFFFF"
FRAME_BORDER    = "#E5E7EB"    # 1px
```

### 20.3 Y-axis Ticks

Default ticks for soil moisture (0–150 mm): `[0, 30, 60, 90, 120, 150]`

```python
TICK_FONT       = "10.5px Fira Code"
TICK_COLOR      = TEXT_SECONDARY   # #6B7280
TICK_ALIGN      = "right"          # y-labels right-aligned
TICK_OFFSET_X   = 9               # px gap between label and plot frame
```

### 20.4 X-axis Ticks

Default ticks: `[0, 60, 120, 180, 240, 300, 365]`

```python
X_TICK_Y_OFFSET = 16    # px below plot frame bottom edge
```

### 20.5 Axis Titles

```python
AXIS_TITLE_FONT     = "11.5px Inter, weight 600"
AXIS_TITLE_COLOR    = TEXT_PRIMARY   # #1A1A2E

# Y-axis title
Y_TITLE_TEXT    = "Storage (mm)"
Y_TITLE_X       = 14                # px from left edge
Y_TITLE_ROTATE  = -90               # degrees

# X-axis title
X_TITLE_TEXT    = "Time (days)"
X_TITLE_Y       = height - 6        # px from top
```

### 20.6 Data Rendering

```python
# Area fill
AREA_GRADIENT_TOP_OPACITY = 0.18    # at colour stop 0
AREA_GRADIENT_BOT_OPACITY = 0.0     # at colour stop 1
AREA_COLOR      = CAT_STOCK         # #2E86C1

# Line
LINE_COLOR      = CAT_STOCK         # #2E86C1
LINE_WIDTH      = 1.8               # px
LINE_CAP        = "round"
LINE_JOIN       = "round"
```

### 20.7 PyQtGraph Configuration

```python
import pyqtgraph as pg

def setup_hydrograph_widget(plot_widget: pg.PlotWidget):
    plot_widget.setBackground('#FFFFFF')
    plot_widget.showGrid(x=True, y=True, alpha=0.3)
    plot_widget.setLabel('left', 'Storage', units='mm',
                         color=TEXT_PRIMARY, size='11.5pt')
    plot_widget.setLabel('bottom', 'Time', units='days',
                         color=TEXT_PRIMARY, size='11.5pt')

    # Match font
    font = QFont('Fira Code', 10)
    plot_widget.getAxis('left').setTickFont(font)
    plot_widget.getAxis('bottom').setTickFont(font)

    # Style
    plot_widget.getAxis('left').setTextPen(QColor(TEXT_SECONDARY))
    plot_widget.getAxis('bottom').setTextPen(QColor(TEXT_SECONDARY))
    plot_widget.getAxis('left').setPen(QColor(BORDER_FIELD))
    plot_widget.getAxis('bottom').setPen(QColor(BORDER_FIELD))

def plot_hydrograph(plot_widget, time_array, storage_array):
    # Area fill using FillBetweenItem or PlotDataItem with fillLevel
    curve = plot_widget.plot(
        x=time_array,
        y=storage_array,
        pen=pg.mkPen(color=CAT_STOCK, width=1.8),
        fillLevel=0,
        brush=pg.mkBrush(QColor(CAT_STOCK).lighter(180))  # ~18% opacity
    )
    return curve
```

---

## 21. Buttons

### 21.1 Secondary Button (default `.btn`)

```python
BTN_BG          = "#FFFFFF"
BTN_BORDER      = BORDER_FIELD     # #E5E7EB, 1px
BTN_COLOR       = TEXT_PRIMARY
BTN_RADIUS      = 6
BTN_PAD_V       = 8
BTN_PAD_H       = 16
BTN_FONT        = 13px, Inter, weight 600
BTN_HOVER_BG    = "#F4F6F9"
```

### 21.2 Primary Button (`.btn.primary`)

```python
BTN_PRIMARY_BG      = SEL_BLUE      # #2E86C1
BTN_PRIMARY_BORDER  = SEL_BLUE
BTN_PRIMARY_COLOR   = "#FFFFFF"
BTN_PRIMARY_HOVER   = "#2877ad"     # slightly darker blue
```

### 21.3 Ghost Button (`.btn.ghost`)

```python
BTN_GHOST_BG        = "transparent"
BTN_GHOST_BORDER    = "transparent"
BTN_GHOST_HOVER_BG  = "#EEF0F4"
```

### 21.4 Transition

All buttons: `background, border-color, box-shadow` — 120ms linear.

---

## 22. Form Fields

### 22.1 Text Input

```python
INPUT_BG        = "#FFFFFF"
INPUT_BORDER    = BORDER_FIELD     # #E5E7EB, 1px
INPUT_RADIUS    = 6
INPUT_PAD_V     = 9
INPUT_PAD_H     = 11
INPUT_FONT      = 13px, Inter (or Fira Code for `.mono` inputs)
INPUT_COLOR     = TEXT_PRIMARY

# Focus state
INPUT_FOCUS_BORDER = SEL_BLUE     # #2E86C1
INPUT_FOCUS_RING   = "0 0 0 3px rgba(46, 134, 193, 0.18)"
```

### 22.2 Field Label

```python
LABEL_FONT      = 11.5px, Inter, weight 600
LABEL_COLOR     = TEXT_SECONDARY
LABEL_MARGIN_B  = 6               # px below label, above input
```

### 22.3 Suffix (Units Overlay)

For fields with units shown inside the field (e.g., `80 mm`):

```python
SUFFIX_RIGHT    = 11              # px from right edge
SUFFIX_FONT     = 11.5px, TEXT_SECONDARY
SUFFIX_POSITION = absolute, vertically centred
```

### 22.4 Two-Column Field Grid

```python
GRID_COLS       = 2
GRID_GAP        = 14              # px
```

---

## 23. Animations & Transitions

All animations are defined here. Use Qt's `QPropertyAnimation` or `QTimeLine` for PyQt6 equivalents.

```python
# Standard transition for interactive elements
TRANSITION_FAST   = 120           # ms — buttons, borders, backgrounds
TRANSITION_MED    = 160           # ms — dialog entrance

# Dialog backdrop fade
OVERLAY_FADE      = 140           # ms, ease

# Dialog entrance
DIALOG_ENTER_DUR  = 160           # ms
DIALOG_ENTER_FROM = "translateY(8px) scale(0.98)"
DIALOG_ENTER_EASE = "cubic-bezier(0.2, 0.9, 0.3, 1.1)"

# Test pill entrance (same as dialog)
TEST_PILL_DUR     = 180           # ms, ease

# Status dot pulse (running state)
PULSE_DUR         = 1000          # ms, infinite
PULSE_FROM_OPACITY = 1.0
PULSE_TO_OPACITY   = 0.35

# Run progress bar
PROGRESS_TRANSITION = 100        # ms, linear
```

---

## 24. PyQt6 Implementation Notes

### 24.1 QSS Stylesheet Strategy

Apply global styles via `QApplication.setStyleSheet()` using a `.qss` file. This covers:
- `QMainWindow` background colour
- `QPushButton` base styles (overridden per-type with `setObjectName`)
- `QLineEdit` focus ring
- `QDialog` background
- Scrollbar style

```qss
/* hydrosim/gui/styles/stylesheet.qss */

QMainWindow, QWidget#main_container {
    background: #F5F6FA;
}

QDialog {
    background: #FFFFFF;
    border-radius: 14px;
}

QPushButton {
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 6px;
    color: #1A1A2E;
    font-family: Inter;
    font-size: 13px;
    font-weight: 600;
    padding: 8px 16px;
}
QPushButton:hover { background: #F4F6F9; }

QPushButton[primary="true"] {
    background: #2E86C1;
    border-color: #2E86C1;
    color: white;
}
QPushButton[primary="true"]:hover { background: #2877ad; }

QLineEdit {
    border: 1px solid #E5E7EB;
    border-radius: 6px;
    padding: 9px 11px;
    font-size: 13px;
    background: white;
    color: #1A1A2E;
}
QLineEdit:focus {
    border-color: #2E86C1;
}

QScrollBar:vertical {
    width: 10px;
    background: transparent;
}
QScrollBar::handle:vertical {
    background: #D5D9E0;
    border-radius: 4px;
    border: 2px solid white;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover { background: #C2C7D0; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
```

### 24.2 Canvas Items Implementation

```python
# Element card: subclass QGraphicsItem (not QGraphicsWidget — too heavy)
class ElementItem(QGraphicsItem):
    def __init__(self, element: ElementBase):
        super().__init__()
        self.element = element
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)

    def boundingRect(self):
        return QRectF(0, 0, CARD_WIDTH, self._compute_height())

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw_card_background(painter)
        self._draw_category_bar(painter)
        self._draw_head(painter)
        self._draw_divider(painter)
        self._draw_body(painter)
        self._draw_ports(painter)

# Connection: subclass QGraphicsPathItem
class ConnectionItem(QGraphicsPathItem):
    def __init__(self, source_port, dest_port, category):
        super().__init__()
        self.category = category
        color = QColor(CAT_COLOURS[category])
        color.setAlphaF(0.8)
        self.setPen(QPen(color, CONN_STROKE_WIDTH))
        self.setZValue(-1)  # draw behind cards
        self.update_path()
```

### 24.3 Font Loading

Inter and Fira Code are Google Fonts — they may not be installed on all systems. Load bundled font files:

```python
# In app.py, before QApplication.exec()
from PyQt6.QtGui import QFontDatabase

def load_fonts():
    fonts_dir = Path(__file__).parent / "resources" / "fonts"
    for font_file in fonts_dir.glob("*.ttf"):
        QFontDatabase.addApplicationFont(str(font_file))

# Bundle these font files in hydrosim/resources/fonts/:
# Inter-Regular.ttf, Inter-Medium.ttf, Inter-SemiBold.ttf, Inter-Bold.ttf
# FiraCode-Regular.ttf, FiraCode-Medium.ttf, FiraCode-SemiBold.ttf
```

### 24.4 HiDPI / Retina Support

```python
# In __main__.py, before creating QApplication
import os
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"

app = QApplication(sys.argv)
app.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
)
```

---

## 25. CSS Variable → PyQt6 Mapping

Quick reference for translating the prototype's CSS into PyQt6:

| CSS Pattern | PyQt6 Equivalent |
|---|---|
| `background: var(--app-bg)` | `setStyleSheet("background: #F5F6FA")` or `setPalette()` |
| `border-radius: 10px` | `QSS: border-radius: 10px` |
| `box-shadow: 0 4px 12px ...` | `QGraphicsDropShadowEffect` |
| `transition: 120ms` | `QPropertyAnimation` with 120ms duration |
| `display: flex; gap: 8px` | `QHBoxLayout` with `setSpacing(8)` |
| `flex: 1` | `setSizePolicy(QSizePolicy.Expanding, ...)` |
| `position: absolute` | `QGraphicsItem` in scene, or `QWidget` with fixed geometry |
| `overflow: hidden` | `setClipping(True)` on `QGraphicsView` |
| `cursor: grab` | `setCursor(Qt.CursorShape.OpenHandCursor)` |
| `cursor: grabbing` | `setCursor(Qt.CursorShape.ClosedHandCursor)` |
| `cursor: crosshair` | `setCursor(Qt.CursorShape.CrossCursor)` |
| `animation: pulse 1s infinite` | `QTimer` toggling opacity every 500ms |
| `opacity: 0.8` | `setOpacity(0.8)` on `QGraphicsItem` |
| `font-weight: 600` | `font.setWeight(QFont.Weight.DemiBold)` |
| `font-weight: 700` | `font.setWeight(QFont.Weight.Bold)` |
| `font-family: 'Fira Code'` | `QFont('Fira Code')` |
| `letter-spacing: 0.06em` | `font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 106)` |
| `white-space: nowrap` | `label.setWordWrap(False)` |
| `-webkit-user-select: none` | `setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)` |

---

*End of HydroSim Design System v1.0*
*Source: Claude Design prototype — HydroSim.html + styles.css + JSX components*
