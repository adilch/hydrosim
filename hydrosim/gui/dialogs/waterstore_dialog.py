"""Property dialog for WaterStore elements."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter, QBrush, QPen
from PyQt6.QtWidgets import (
    QCheckBox, QDoubleSpinBox, QHBoxLayout, QLabel,
    QLineEdit, QVBoxLayout, QWidget,
)

from hydrosim.gui.dialogs import BaseElementDialog, COMMON_UNITS
from hydrosim.gui.styles.theme import FONT_MONO, FONT_UI, TEXT_SECONDARY
from hydrosim.model.elements.waterstore import WaterStore


class _StorageBar(QWidget):
    """Visual indicator: blue gradient fill showing initial storage vs bounds."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(34)
        self._lo  = 0.0
        self._hi  = 150.0
        self._val = 80.0

    def update_values(self, lo: float, hi: float | None, val: float) -> None:
        self._lo  = lo
        self._hi  = hi if hi is not None else lo + max(val - lo + 50, 100)
        self._val = val
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Track
        p.setBrush(QBrush(QColor("#EEF1F5")))
        p.setPen(QPen(QColor("#E5E7EB"), 1))
        p.drawRoundedRect(0, 4, w, h-8, 6, 6)

        # Fill
        span = self._hi - self._lo
        pct  = max(0.0, min(1.0, (self._val - self._lo) / span)) if span > 0 else 0
        fw   = int(w * pct)
        if fw > 4:
            grad = QLinearGradient(0, 0, fw, 0)
            grad.setColorAt(0, QColor("#4aa3da"))
            grad.setColorAt(1, QColor("#2E86C1"))
            p.setBrush(QBrush(grad))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(0, 4, fw, h-8, 6, 6)

        # Labels
        p.setPen(QColor("#6B7280"))
        p.setFont(QFont(FONT_MONO, 9))
        lo_str = f"{self._lo:.0f}"
        hi_str = f"{self._hi:.0f}"
        val_str = f"{self._val:.1f}"
        p.drawText(2, h-2, lo_str)
        p.drawText(w - p.fontMetrics().horizontalAdvance(hi_str) - 2, h-2, hi_str)
        # Centre label
        cx = fw // 2
        p.setPen(QColor("#FFFFFF") if fw > 40 else QColor("#2E86C1"))
        p.drawText(cx - 20, h // 2 + 4, val_str)


class WaterStoreDialog(BaseElementDialog):
    def __init__(self, element: WaterStore, graph, parent=None):
        self._name_field = None
        self._name_err   = None
        super().__init__(element, graph, parent, min_width=500)
        self.setWindowTitle(f"WaterStore — {element.name}")

    def _build_body(self) -> QWidget:
        w, lay = self._body_layout()

        # Name
        lay.addWidget(self._field_label("Name"))
        self._name_field = QLineEdit(self.element.name)
        lay.addWidget(self._name_field)
        self._name_err = self._error_label()
        lay.addWidget(self._name_err)

        # Description
        lay.addWidget(self._field_label("Description"))
        self._desc_field = QLineEdit(self.element.description)
        lay.addWidget(self._desc_field)

        # Units
        lay.addWidget(self._field_label("Units  (e.g. m3, mm, ML)"))
        self._units_field = QLineEdit(self.element.units)
        lay.addWidget(self._units_field)

        # Numeric fields: Initial | Lower | Upper (2-col grid)
        row1 = QHBoxLayout(); row1.setSpacing(14)

        ic = QVBoxLayout()
        ic.addWidget(self._field_label("Initial Storage"))
        self._initial_spin = self._make_spin(self.element.initial_storage)
        ic.addWidget(self._initial_spin)
        row1.addLayout(ic)

        lc = QVBoxLayout()
        lc.addWidget(self._field_label("Lower Bound"))
        self._lower_spin = self._make_spin(self.element.lower_bound)
        lc.addWidget(self._lower_spin)
        row1.addLayout(lc)

        lay.addLayout(row1)

        row2 = QHBoxLayout(); row2.setSpacing(14)
        uc = QVBoxLayout()
        uc.addWidget(self._field_label("Upper Bound"))
        inner = QHBoxLayout(); inner.setSpacing(8)
        self._upper_spin = self._make_spin(
            self.element.upper_bound if self.element.upper_bound is not None else 150.0
        )
        self._unbounded_cb = QCheckBox("Unbounded")
        self._unbounded_cb.setFont(QFont(FONT_UI, 11))
        self._unbounded_cb.setChecked(self.element.upper_bound is None)
        self._upper_spin.setEnabled(self.element.upper_bound is not None)
        inner.addWidget(self._upper_spin)
        inner.addWidget(self._unbounded_cb)
        uc.addLayout(inner)
        row2.addLayout(uc)
        lay.addLayout(row2)

        # Storage bar
        lay.addWidget(self._field_label("Storage Range"))
        self._bar = _StorageBar()
        self._update_bar()
        lay.addWidget(self._bar)

        # Error label
        self._bounds_err = self._error_label()
        lay.addWidget(self._bounds_err)
        lay.addStretch()

        # Wiring
        self._name_field.textChanged.connect(self._run_validation)
        self._initial_spin.valueChanged.connect(self._on_value_change)
        self._lower_spin.valueChanged.connect(self._on_value_change)
        self._upper_spin.valueChanged.connect(self._on_value_change)
        self._unbounded_cb.toggled.connect(self._on_unbounded_toggled)
        return w

    @staticmethod
    def _make_spin(value: float) -> QDoubleSpinBox:
        s = QDoubleSpinBox()
        s.setRange(-1e9, 1e9)
        s.setDecimals(4)
        s.setValue(value)
        s.setFont(QFont(FONT_MONO, 12))
        return s

    def _on_value_change(self) -> None:
        self._update_bar()
        self._run_validation()

    def _on_unbounded_toggled(self, checked: bool) -> None:
        self._upper_spin.setEnabled(not checked)
        self._update_bar()
        self._run_validation()

    def _update_bar(self) -> None:
        if not hasattr(self, "_bar"):
            return
        lo  = self._lower_spin.value()
        hi  = None if self._unbounded_cb.isChecked() else self._upper_spin.value()
        val = self._initial_spin.value()
        self._bar.update_values(lo, hi, val)

    def _validate(self) -> list[str]:
        errors = []
        if self._name_field is None:
            return errors
        e = self._validate_name(self._name_field.text().strip())
        if e:
            errors.append(e); self._show_error(self._name_err, e)
        else:
            self._show_error(self._name_err, "")

        lo  = self._lower_spin.value()
        val = self._initial_spin.value()
        unbounded = self._unbounded_cb.isChecked()
        hi  = None if unbounded else self._upper_spin.value()

        if hi is not None and hi <= lo:
            msg = "Upper bound must be greater than lower bound"
            errors.append(msg); self._show_error(self._bounds_err, msg)
            return errors
        if hi is not None and not (lo <= val <= hi):
            msg = f"Initial storage ({val:.2f}) must be within [{lo:.2f}, {hi:.2f}]"
            errors.append(msg); self._show_error(self._bounds_err, msg)
            return errors
        if val < lo:
            msg = f"Initial storage ({val:.2f}) cannot be below lower bound ({lo:.2f})"
            errors.append(msg); self._show_error(self._bounds_err, msg)
            return errors

        self._show_error(self._bounds_err, "")
        return errors

    def apply_changes(self) -> None:
        self.element.name            = self._name_field.text().strip()
        self.element.description     = self._desc_field.text().strip()
        self.element.units           = self._units_field.text().strip() or "m3"
        self.element.initial_storage = self._initial_spin.value()
        self.element.lower_bound     = self._lower_spin.value()
        self.element.upper_bound     = (
            None if self._unbounded_cb.isChecked()
            else self._upper_spin.value()
        )
