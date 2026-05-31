"""
Base dialog class shared by all element property dialogs.
"""
from __future__ import annotations

import re

from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor, QFont, QPixmap, QPainter
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QVBoxLayout, QWidget, QSizePolicy,
)

from hydrosim.gui.styles.theme import (
    BORDER_SUBTLE, DIALOG_ICON_BG, FONT_MONO, FONT_UI,
    PANEL_BG, SEL_BLUE, TEXT_PRIMARY, TEXT_SECONDARY,
)
from hydrosim.model.base import ElementBase

# Valid element name: alphanumeric + underscore, starts with letter/underscore
_NAME_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')

COMMON_UNITS = ["-", "m3", "m3/s", "mm", "mm/day", "m", "km2",
                "ML", "ML/day", "m2", "s/m^(1/3)", "°C", "kPa"]


def _make_icon_px(type_name: str, size: int, cat: str) -> QPixmap | None:
    from hydrosim.gui.canvas.element_item import _load_svg_icon, _ICON_MAP
    from PyQt6.QtGui import QColor
    from hydrosim.gui.styles.theme import CAT_COLOURS
    icon_kind = _ICON_MAP.get(type_name, "constant")
    col       = QColor(CAT_COLOURS.get(cat, "#888"))
    return _load_svg_icon(icon_kind, size, col)


class BaseElementDialog(QDialog):
    """
    Modal property dialog for any element type.

    Layout:
        Header  (icon + title + subtitle + × close)
        ─────── 1px separator ───────────────────
        Body    (subclass fills this)
        ─────── 1px separator ───────────────────
        Footer  (Cancel | OK)

    Subclasses must implement:
        _build_body() -> QWidget
        apply_changes() -> None
        _validate() -> list[str]   (return error strings; empty = valid)
    """

    def __init__(
        self,
        element:   ElementBase,
        graph:     "ModelGraph",  # type: ignore
        parent:    QWidget | None = None,
        min_width: int = 480,
    ):
        super().__init__(parent)
        self.element   = element
        self.graph     = graph
        self._errors:  list[str] = []

        self.setModal(True)
        self.setMinimumWidth(min_width)
        self.setStyleSheet(
            f"QDialog {{ background: {PANEL_BG}; border-radius: 14px; }}"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())
        root.addWidget(self._separator())

        # Scrollable body
        self._body_widget = self._build_body()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(self._body_widget)
        root.addWidget(scroll, stretch=1)

        root.addWidget(self._separator())
        foot, self._ok_btn = self._build_footer()
        root.addWidget(foot)

        self._run_validation()

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(64)
        w.setStyleSheet(f"background: {PANEL_BG};")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(20, 0, 16, 0)
        lay.setSpacing(12)

        # Icon container
        cat  = self.element.category.value
        bg   = DIALOG_ICON_BG.get(cat, "#F5F5F5")
        icon_w = QWidget()
        icon_w.setFixedSize(34, 34)
        icon_w.setStyleSheet(
            f"background: {bg}; border-radius: 9px;"
        )
        icon_lay = QVBoxLayout(icon_w)
        icon_lay.setContentsMargins(7, 7, 7, 7)
        px = _make_icon_px(self.element.__class__.__name__, 20, cat)
        icon_lbl = QLabel()
        if px:
            icon_lbl.setPixmap(px)
        icon_lay.addWidget(icon_lbl)
        lay.addWidget(icon_w)

        # Title + subtitle
        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        title = QLabel(self.element.__class__.__name__.replace("TimeHistoryResult", "Time History Result"))
        title.setFont(QFont(FONT_UI, 15))
        title.setStyleSheet(f"font-weight: 700; color: {TEXT_PRIMARY};")
        text_col.addWidget(title)
        sub = QLabel(self.element.name)
        sub.setFont(QFont(FONT_UI, 11))
        sub.setStyleSheet(f"color: {TEXT_SECONDARY};")
        text_col.addWidget(sub)
        lay.addLayout(text_col)

        lay.addStretch()

        # × close button
        close_btn = QPushButton("×")
        close_btn.setFixedSize(28, 28)
        close_btn.setFont(QFont(FONT_UI, 15))
        close_btn.setStyleSheet(
            f"QPushButton {{ border: none; background: transparent; "
            f"color: {TEXT_SECONDARY}; border-radius: 7px; }}"
            f"QPushButton:hover {{ background: #EEF0F4; color: {TEXT_PRIMARY}; }}"
        )
        close_btn.clicked.connect(self.reject)
        lay.addWidget(close_btn)
        return w

    # ── Footer ────────────────────────────────────────────────────────────────

    def _build_footer(self) -> tuple[QWidget, QPushButton]:
        w = QWidget()
        w.setFixedHeight(52)
        w.setStyleSheet(f"background: {PANEL_BG};")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(20, 0, 20, 0)
        lay.setSpacing(10)
        lay.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedSize(80, 34)
        cancel_btn.clicked.connect(self.reject)
        lay.addWidget(cancel_btn)

        ok_btn = QPushButton("OK")
        ok_btn.setFixedSize(80, 34)
        ok_btn.setProperty("primary", True)
        ok_btn.style().unpolish(ok_btn)
        ok_btn.style().polish(ok_btn)
        ok_btn.clicked.connect(self._on_ok)
        lay.addWidget(ok_btn)
        return w, ok_btn

    def _separator(self) -> QWidget:
        line = QWidget()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background: #EEF0F4;")
        return line

    # ── Validation ────────────────────────────────────────────────────────────

    def _run_validation(self) -> None:
        """Run all validators; update OK button and any inline error labels."""
        self._errors = self._validate()
        self._ok_btn.setEnabled(len(self._errors) == 0)

    def _validate(self) -> list[str]:
        """Override in subclasses. Return list of error strings."""
        return []

    def _validate_name(self, name: str) -> str:
        """Return error string or '' if valid."""
        if not name.strip():
            return "Name is required"
        if not _NAME_RE.match(name):
            return "Name must start with a letter/underscore and contain only letters, digits, underscores"
        # Uniqueness check (skip current element)
        existing = self.graph.get_element_by_name(name)
        if existing and existing.id != self.element.id:
            return f"Name '{name}' is already used by another element"
        return ""

    # ── OK handler ────────────────────────────────────────────────────────────

    def _on_ok(self) -> None:
        self._run_validation()
        if self._errors:
            return
        self.apply_changes()
        self.accept()

    # ── Subclass interface ────────────────────────────────────────────────────

    def _build_body(self) -> QWidget:
        raise NotImplementedError

    def apply_changes(self) -> None:
        raise NotImplementedError

    # ── Shared field builders ─────────────────────────────────────────────────

    @staticmethod
    def _field_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(QFont(FONT_UI, 11))
        lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-weight: 600;")
        return lbl

    @staticmethod
    def _error_label() -> QLabel:
        lbl = QLabel()
        lbl.setFont(QFont(FONT_UI, 10))
        lbl.setStyleSheet("color: #E53935;")
        lbl.setVisible(False)
        lbl.setWordWrap(True)
        return lbl

    def _show_error(self, lbl: QLabel, msg: str) -> None:
        lbl.setText(msg)
        lbl.setVisible(bool(msg))

    @staticmethod
    def _body_layout() -> tuple[QWidget, QVBoxLayout]:
        """A white padded widget with a VBox layout for body content."""
        w = QWidget()
        w.setStyleSheet(f"background: {PANEL_BG};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(14)
        return w, lay
