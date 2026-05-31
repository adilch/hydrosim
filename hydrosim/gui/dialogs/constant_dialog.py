"""Property dialog for Constant elements."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCompleter, QDoubleSpinBox, QHBoxLayout,
    QLineEdit, QVBoxLayout, QWidget,
)

from hydrosim.gui.dialogs import BaseElementDialog, COMMON_UNITS
from hydrosim.gui.styles.theme import FONT_MONO, FONT_UI
from hydrosim.model.elements.constant import Constant


class ConstantDialog(BaseElementDialog):
    def __init__(self, element: Constant, graph, parent=None):
        self._name_field  = None
        self._desc_field  = None
        self._value_spin  = None
        self._units_field = None
        self._name_err    = None
        super().__init__(element, graph, parent, min_width=460)
        self.setWindowTitle(f"Constant — {element.name}")

    def _build_body(self) -> QWidget:
        w, lay = self._body_layout()

        # Name
        lay.addWidget(self._field_label("Name"))
        self._name_field = QLineEdit(self.element.name)
        self._name_field.setPlaceholderText("e.g. Manning_n")
        lay.addWidget(self._name_field)
        self._name_err = self._error_label()
        lay.addWidget(self._name_err)

        # Description
        lay.addWidget(self._field_label("Description"))
        self._desc_field = QLineEdit(self.element.description)
        self._desc_field.setPlaceholderText("Optional documentation")
        lay.addWidget(self._desc_field)

        # Value + Units side by side
        row = QHBoxLayout()
        row.setSpacing(12)

        val_col = QVBoxLayout()
        val_col.addWidget(self._field_label("Value"))
        self._value_spin = QDoubleSpinBox()
        self._value_spin.setRange(-1e15, 1e15)
        self._value_spin.setDecimals(6)
        self._value_spin.setValue(self.element.value)
        self._value_spin.setFont(QFont(FONT_MONO, 13))
        val_col.addWidget(self._value_spin)
        row.addLayout(val_col)

        unit_col = QVBoxLayout()
        unit_col.addWidget(self._field_label("Units"))
        self._units_field = QLineEdit(self.element.units)
        self._units_field.setPlaceholderText("-")
        comp = QCompleter(COMMON_UNITS)
        comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._units_field.setCompleter(comp)
        unit_col.addWidget(self._units_field)
        row.addLayout(unit_col)

        lay.addLayout(row)
        lay.addStretch()

        # Wire live validation
        self._name_field.textChanged.connect(self._run_validation)
        self._value_spin.valueChanged.connect(self._run_validation)

        return w

    def _validate(self) -> list[str]:
        errors = []
        if self._name_field is None:
            return errors
        name_err = self._validate_name(self._name_field.text().strip())
        if name_err:
            errors.append(name_err)
            if self._name_err:
                self._show_error(self._name_err, name_err)
        elif self._name_err:
            self._show_error(self._name_err, "")

        import math
        val = self._value_spin.value() if self._value_spin else 0.0
        if not math.isfinite(val):
            errors.append("Value must be a finite number")
        return errors

    def apply_changes(self) -> None:
        self.element.name        = self._name_field.text().strip()
        self.element.description = self._desc_field.text().strip()
        self.element.value       = self._value_spin.value()
        self.element.units       = self._units_field.text().strip() or "-"
        # Rebuild output port units
        if "value" in self.element._output_ports:
            self.element._output_ports["value"].units = self.element.units
