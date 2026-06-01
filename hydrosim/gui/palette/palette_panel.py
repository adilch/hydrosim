"""
PalettePanel — left sidebar listing all available element types.
Items are draggable onto the canvas. Double-click creates at viewport centre.
"""
from __future__ import annotations

from PyQt6.QtCore import (
    QByteArray, QMimeData, QPointF, QSize, Qt, pyqtSignal,
)
from PyQt6.QtGui import (
    QColor, QDrag, QFont, QFontMetrics, QPainter, QPixmap,
)
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from hydrosim.gui.canvas.view import PALETTE_MIME
from hydrosim.gui.styles.theme import (
    APP_BG, BORDER_SUBTLE, CAT_COLOURS,
    FONT_MONO, FONT_UI,
    PALETTE_WIDTH, PAL_ICON_SIZE,
    PANEL_BG, SEL_BLUE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY,
)

# ── Element catalogue ─────────────────────────────────────────────────────────

_ELEMENTS = [
    # (type_name, display_name, description, category_key)
    ("Constant",          "Constant",        "Fixed scalar value",            "input"),
    ("TimeSeries",        "Time Series",     "Time-varying input from table", "input"),
    ("WaterStore",        "Water Store",     "Bounded storage with routing",  "stock"),
    ("Reservoir",         "Reservoir",       "Storage with E-V bathymetry",   "stock"),
    ("Expression",        "Expression",      "Formula using other elements",  "expression"),
    ("TimeHistoryResult", "Time History",    "Hydrograph result viewer",      "result"),
]

_CATEGORY_LABELS = {
    "input":      "INPUT",
    "stock":      "STOCK",
    "expression": "EXPRESSION",
    "result":     "RESULT",
}


# ── Small icon renderer ───────────────────────────────────────────────────────

_ICON_MAP = {
    "Constant":          "constant",
    "TimeSeries":        "timeseries",
    "WaterStore":        "waterstore",
    "Reservoir":         "reservoir",
    "Expression":        "expression",
    "TimeHistoryResult": "timehistory",
}


def _icon_pixmap(type_name: str, size: int, colour: QColor) -> QPixmap | None:
    from PyQt6.QtSvg import QSvgRenderer
    from pathlib import Path

    icons_dir = Path(__file__).parent.parent.parent / "resources" / "icons"
    key  = _ICON_MAP.get(type_name, "constant")
    path = icons_dir / f"{key}.svg"
    if not path.exists():
        return None

    svg  = path.read_text(encoding="utf-8").replace("currentColor", colour.name())
    r    = QSvgRenderer()
    r.load(svg.encode("utf-8"))
    px   = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p    = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    r.render(p)
    p.end()
    return px


# ── Palette Item widget ───────────────────────────────────────────────────────

class _PaletteItem(QWidget):
    """One draggable element type row."""

    double_clicked = pyqtSignal(str)   # emits type_name

    def __init__(self, type_name: str, display_name: str,
                 description: str, category: str, parent=None):
        super().__init__(parent)
        self._type_name   = type_name
        self._category    = category
        self._cat_colour  = QColor(CAT_COLOURS.get(category, "#888888"))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 9, 10, 9)
        layout.setSpacing(10)

        # Icon
        icon_lbl = QLabel()
        px = _icon_pixmap(type_name, PAL_ICON_SIZE, self._cat_colour)
        if px:
            icon_lbl.setPixmap(px)
        icon_lbl.setFixedSize(PAL_ICON_SIZE, PAL_ICON_SIZE)
        layout.addWidget(icon_lbl)

        # Text column
        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(1)

        name_lbl = QLabel(display_name)
        name_lbl.setFont(QFont(FONT_UI, 12))
        name_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-weight: 600;")
        text_col.addWidget(name_lbl)

        desc_lbl = QLabel(description)
        desc_lbl.setFont(QFont(FONT_UI, 10))
        desc_lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
        desc_lbl.setWordWrap(True)          # allow wrapping so nothing is cut off
        desc_lbl.setMinimumHeight(14)
        text_col.addWidget(desc_lbl)

        layout.addLayout(text_col)
        layout.addStretch()

        self.setToolTip(f"<b>{display_name}</b><br>{description}<br>"
                        f"<small>Drag to canvas or double-click</small>")
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._normal_style  = (
            f"background: transparent; border: 1px solid transparent; "
            f"border-radius: 8px;"
        )
        self._hover_style   = (
            f"background: #F6F8FB; border: 1px solid {BORDER_SUBTLE}; "
            f"border-radius: 8px;"
        )
        self.setStyleSheet(self._normal_style)
        self._drag_start = None

    def enterEvent(self, event) -> None:
        self.setStyleSheet(self._hover_style)

    def leaveEvent(self, event) -> None:
        self.setStyleSheet(self._normal_style)

    def mouseDoubleClickEvent(self, event) -> None:
        self.double_clicked.emit(self._type_name)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if (self._drag_start is not None
                and event.buttons() & Qt.MouseButton.LeftButton):
            if ((event.position().toPoint() - self._drag_start).manhattanLength() > 6):
                self._start_drag()
        super().mouseMoveEvent(event)

    def _start_drag(self) -> None:
        mime = QMimeData()
        mime.setData(PALETTE_MIME,
                     QByteArray(self._type_name.encode("utf-8")))

        drag = QDrag(self)
        drag.setMimeData(mime)

        # Drag pixmap: 50% opacity copy of the widget
        px = QPixmap(self.size())
        px.fill(Qt.GlobalColor.transparent)
        p  = QPainter(px)
        p.setOpacity(0.5)
        self.render(p)
        p.end()
        drag.setPixmap(px)
        drag.setHotSpot(self._drag_start)
        self.setStyleSheet(self._normal_style)
        drag.exec(Qt.DropAction.CopyAction)
        self._drag_start = None


# ── Category section ──────────────────────────────────────────────────────────

class _CategorySection(QWidget):
    """Collapsible section header + items for one element category."""

    item_double_clicked = pyqtSignal(str)

    def __init__(self, category: str, parent=None):
        super().__init__(parent)
        self._category  = category
        self._expanded  = True
        self._items: list[_PaletteItem] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        self._header = QPushButton()
        self._header.setFlat(True)
        self._header.setFixedHeight(36)
        cat_col = CAT_COLOURS.get(category, "#888888")
        self._header.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; "
            f"text-align: left; padding: 0 12px; color: {cat_col}; "
            f"font-family: {FONT_UI}; font-size: 11px; font-weight: 700; "
            f"letter-spacing: 0.06em; }}"
            f"QPushButton:hover {{ background: {APP_BG}; }}"
        )
        self._update_header()
        self._header.clicked.connect(self._toggle)
        layout.addWidget(self._header)

        # Items container
        self._items_widget = QWidget()
        self._items_layout = QVBoxLayout(self._items_widget)
        self._items_layout.setContentsMargins(0, 0, 0, 4)
        self._items_layout.setSpacing(0)
        layout.addWidget(self._items_widget)

    def _update_header(self) -> None:
        arrow = "▼" if self._expanded else "▶"
        label = _CATEGORY_LABELS.get(self._category, self._category.upper())
        self._header.setText(f"  {arrow}  {label}")

    def _toggle(self) -> None:
        self._expanded = not self._expanded
        self._items_widget.setVisible(self._expanded)
        self._update_header()

    def add_item(self, item: _PaletteItem) -> None:
        self._items.append(item)
        self._items_layout.addWidget(item)
        item.double_clicked.connect(self.item_double_clicked)

    def filter(self, query: str) -> bool:
        """Show/hide items matching query. Returns True if any visible."""
        q = query.lower().strip()
        any_visible = False
        for item in self._items:
            visible = (not q
                       or q in item._type_name.lower()
                       or q in item.toolTip().lower())
            item.setVisible(visible)
            if visible:
                any_visible = True
        self.setVisible(any_visible or not q)
        return any_visible


# ── PalettePanel ──────────────────────────────────────────────────────────────

class PalettePanel(QWidget):
    """
    200px fixed-width left sidebar.
    Search bar → collapsible category sections → draggable element items.
    """

    element_requested = pyqtSignal(str)  # type_name — double-click or enter in search

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(140)
        self.setMaximumWidth(480)
        self.setObjectName("palette_panel")
        self.setStyleSheet(
            f"#palette_panel {{ background: {PANEL_BG}; "
            f"border-right: 1px solid {BORDER_SUBTLE}; }}"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Search bar ─────────────────────────────────────────────────────
        search_wrap = QWidget()
        search_wrap.setFixedHeight(48)
        search_wrap.setStyleSheet(
            f"background: {PANEL_BG}; border-bottom: 1px solid #EEF0F4;"
        )
        sw_layout = QHBoxLayout(search_wrap)
        sw_layout.setContentsMargins(10, 8, 10, 8)

        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍  Search elements…")
        self._search.setFont(QFont(FONT_UI, 12))
        self._search.setStyleSheet(
            f"border: 1px solid {BORDER_SUBTLE}; border-radius: 7px; "
            f"padding: 4px 8px; background: {APP_BG}; color: {TEXT_PRIMARY};"
        )
        self._search.textChanged.connect(self._filter)
        sw_layout.addWidget(self._search)
        root.addWidget(search_wrap)

        # ── Scroll area for categories ─────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content.setStyleSheet(f"background: {PANEL_BG};")
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setContentsMargins(0, 4, 0, 4)
        self._content_layout.setSpacing(0)

        self._sections: dict[str, _CategorySection] = {}
        self._build_sections()
        self._content_layout.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll, stretch=1)

    def _build_sections(self) -> None:
        # Group elements by category, preserving order
        from collections import OrderedDict
        categories: dict[str, list] = OrderedDict()
        for el in _ELEMENTS:
            cat = el[3]
            categories.setdefault(cat, []).append(el)

        for cat, elements in categories.items():
            section = _CategorySection(cat)
            for type_name, display_name, description, _ in elements:
                item = _PaletteItem(type_name, display_name, description, cat)
                section.add_item(item)
            section.item_double_clicked.connect(self.element_requested)
            self._content_layout.addWidget(section)
            self._sections[cat] = section

    def _filter(self, query: str) -> None:
        for section in self._sections.values():
            section.filter(query)
