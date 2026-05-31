"""
HydroSim design system constants.
All colours, dimensions, fonts, and shadows — single source of truth.
Never hardcode these values elsewhere.
"""

# ── App surfaces ───────────────────────────────────────────────────────────────
APP_BG           = "#F5F6FA"
PANEL_BG         = "#FFFFFF"
BORDER_SUBTLE    = "#E7E9EE"
BORDER_FIELD     = "#E5E7EB"
BORDER_INNER     = "#ECEEF2"
SURFACE_RAISED   = "#F4F6F9"
SURFACE_DEEPENED = "#F5F6FA"

# ── Text ───────────────────────────────────────────────────────────────────────
TEXT_PRIMARY   = "#1A1A2E"
TEXT_SECONDARY = "#6B7280"
TEXT_TERTIARY  = "#9CA3AF"
TEXT_FAINT     = "#C2C7D0"

# ── Element category colours ───────────────────────────────────────────────────
CAT_INPUT  = "#4CAF82"   # Leaf Green  — Constant, TimeSeries
CAT_STOCK  = "#2E86C1"   # Ocean Blue  — WaterStore
CAT_EXPR   = "#00897B"   # Teal        — Expression
CAT_RESULT = "#E8633A"   # Coral Orange — TimeHistoryResult

CAT_COLOURS = {
    "input":      CAT_INPUT,
    "stock":      CAT_STOCK,
    "expression": CAT_EXPR,
    "result":     CAT_RESULT,
}

# ── Semantic colours ───────────────────────────────────────────────────────────
SEL_BLUE  = "#2E86C1"
ERR_RED   = "#E53935"
OK_GREEN  = "#43A047"
WARN_AMBER = "#FB8C00"

# ── Syntax highlighting (formula editor) ──────────────────────────────────────
SYNTAX_ELEM = "#4CAF82"
SYNTAX_OP   = "#8A93A0"
SYNTAX_NUM  = "#7B68C8"
SYNTAX_FN   = "#00897B"

# ── Canvas ─────────────────────────────────────────────────────────────────────
GRID_DOT      = "#DEE2E8"
GRID_DOT_SIZE = 1.6
GRID_SPACING  = 20

# ── Overlay ────────────────────────────────────────────────────────────────────
OVERLAY_BG = "rgba(20, 22, 34, 0.34)"

# ── Dialog icon background tints ──────────────────────────────────────────────
DIALOG_ICON_BG = {
    "input":      "#E8F5EE",
    "stock":      "#E3F0FA",
    "expression": "#E0F2F1",
    "result":     "#FBE9E4",
}

# ── Fonts ──────────────────────────────────────────────────────────────────────
FONT_UI   = "Inter"
FONT_MONO = "Fira Code"
FONT_UI_FAMILY   = "Inter, Segoe UI, system-ui, sans-serif"
FONT_MONO_FAMILY = "Fira Code, ui-monospace, SF Mono, Menlo, Consolas, monospace"

# ── Type scale (pixels) ────────────────────────────────────────────────────────
TEXT_XS       = 10
TEXT_SM       = 11
TEXT_SM_PLUS  = 11.5
TEXT_MD       = 12
TEXT_MD_PLUS  = 12.5
TEXT_BASE     = 13
TEXT_BASE_PLUS = 13.5
TEXT_LG       = 15
TEXT_XL       = 13  # same size as base but weight 700

# ── Shadows ────────────────────────────────────────────────────────────────────
SHADOW_FLAT     = "0 1px 2px rgba(0, 0, 0, 0.07)"
SHADOW_SUBTLE   = "0 4px 12px rgba(0, 0, 0, 0.10)"
SHADOW_FLOATING = "0 10px 26px rgba(0, 0, 0, 0.16)"
SHADOW_DIALOG   = "0 24px 64px rgba(0, 0, 0, 0.30)"
SHADOW_DROPDOWN = "0 8px 28px rgba(0, 0, 0, 0.14)"
SHADOW_RUN_BTN  = "0 1px 2px rgba(67, 160, 71, 0.35)"

# ── Application frame ──────────────────────────────────────────────────────────
APP_MIN_WIDTH    = 1280

# ── Zone heights ───────────────────────────────────────────────────────────────
MENUBAR_HEIGHT   = 32
TOOLBAR_HEIGHT   = 48
PALETTE_WIDTH    = 200
STATUSBAR_HEIGHT = 28

# ── Element cards ──────────────────────────────────────────────────────────────
CARD_WIDTH         = 180
CARD_CORNER_R      = 10
CARD_TOP_BAR_H     = 4
CARD_PADDING_H     = 12
CARD_PADDING_V     = 10
CARD_DIVIDER_H     = 1
CARD_HEAD_HEIGHT   = 50   # icon + name + id area
CARD_MIN_HEIGHT    = 80

# ── Ports ──────────────────────────────────────────────────────────────────────
PORT_DIAMETER    = 10
PORT_HOVER_D     = 14
PORT_ROW_HEIGHT  = 20
PORT_OFFSET_X    = 6

# ── Connections ────────────────────────────────────────────────────────────────
CONN_STROKE_W      = 2.0
CONN_STROKE_OPACITY = 0.8
CONN_SELECTED_W    = 3.0
CONN_CTRL_OFFSET   = 80
ARROW_SIZE         = 7

# ── Canvas limits ──────────────────────────────────────────────────────────────
CANVAS_LOGICAL_W = 4000
CANVAS_LOGICAL_H = 3000
ZOOM_MIN         = 0.4
ZOOM_MAX         = 2.0
ZOOM_STEP        = 0.1

# ── Palette ────────────────────────────────────────────────────────────────────
PAL_ITEM_MARGIN   = 3
PAL_ITEM_PADDING_H = 9
PAL_ITEM_PADDING_V = 8
PAL_ITEM_RADIUS   = 8
PAL_ICON_SIZE     = 20
CAT_HEADER_H      = 40
CAT_SWATCH_SIZE   = 9
CAT_SWATCH_R      = 3

# ── Dialogs ────────────────────────────────────────────────────────────────────
DIALOG_RADIUS    = 14
DIALOG_HEAD_PAD  = 18
DIALOG_BODY_PAD  = 20
DIALOG_FOOT_PAD_V = 14
DIALOG_ICON_SIZE = 34
DIALOG_ICON_R    = 9
FIELD_GRID_COLS  = 2
FIELD_GRID_GAP   = 14
FIELD_ROW_GAP    = 16

# ── Buttons ────────────────────────────────────────────────────────────────────
BTN_RADIUS      = 6
BTN_PAD_V       = 8
BTN_PAD_H       = 16
BTN_FONT_SIZE   = 13
BTN_FONT_WEIGHT = 600

# ── Form fields ────────────────────────────────────────────────────────────────
FIELD_RADIUS    = 6
FIELD_PAD_V     = 9
FIELD_PAD_H     = 11
FIELD_FONT_SIZE = 13
FIELD_LABEL_SIZE = 11.5

# ── Toolbar buttons ────────────────────────────────────────────────────────────
TBTN_HEIGHT  = 32
TBTN_RADIUS  = 7
TBTN_PAD_H   = 12
TBTN_FONT_SIZE = 13
TBTN_FONT_W  = 500

# ── Chips (Available Elements in Expression dialog) ────────────────────────────
CHIP_RADIUS  = 20
CHIP_PAD_V   = 6
CHIP_PAD_H   = 11
CHIP_DOT_SIZE = 8

# ── Result viewer window ───────────────────────────────────────────────────────
WIN_WIDTH    = 800
WIN_HEIGHT   = 500
WIN_RADIUS   = 12

# ── Animations ─────────────────────────────────────────────────────────────────
TRANSITION_FAST = 120
TRANSITION_MED  = 160
OVERLAY_FADE    = 140
DIALOG_ENTER_DUR = 160
PULSE_DUR       = 1000
PROGRESS_TRANSITION = 100

# ── Status pills ───────────────────────────────────────────────────────────────
PILL_RADIUS    = 20
PILL_FONT_SIZE = 11.5
PILL_DOT_SIZE  = 7

# ── Storage indicator (WaterStore dialog) ──────────────────────────────────────
STORAGE_TRACK_HEIGHT = 30
STORAGE_TRACK_RADIUS = 8
STORAGE_TRACK_BG     = "#EEF1F5"
STORAGE_FILL_TOP     = "#4aa3da"
STORAGE_FILL_BOT     = "#2E86C1"
