"""Property dialog for TimeHistoryResult elements."""
from __future__ import annotations

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox, QDoubleSpinBox, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QVBoxLayout, QWidget,
)

from hydrosim.gui.dialogs import BaseElementDialog
from hydrosim.gui.styles.theme import FONT_MONO, FONT_UI, TEXT_SECONDARY
from hydrosim.model.elements.timehistory import TimeHistoryResult


class TimeHistoryDialog(BaseElementDialog):
    def __init__(self, element: TimeHistoryResult, graph, parent=None):
        self._name_field = None
        self._name_err   = None
        super().__init__(element, graph, parent, min_width=480)
        self.setWindowTitle(f"Time History Result — {element.name}")

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

        # Chart Title + Y-axis Label (2-col)
        row1 = QHBoxLayout(); row1.setSpacing(12)
        tc = QVBoxLayout(); tc.addWidget(self._field_label("Chart Title"))
        self._title_field = QLineEdit(self.element.title or self.element.name)
        tc.addWidget(self._title_field); row1.addLayout(tc)
        yc = QVBoxLayout(); yc.addWidget(self._field_label("Y-axis Label"))
        self._ylabel_field = QLineEdit(self.element.y_axis_label)
        yc.addWidget(self._ylabel_field); row1.addLayout(yc)
        lay.addLayout(row1)

        # Y-axis Units + Show Grid (2-col)
        row2 = QHBoxLayout(); row2.setSpacing(12)
        uc = QVBoxLayout(); uc.addWidget(self._field_label("Y-axis Units"))
        self._yunits_field = QLineEdit(self.element.y_axis_units)
        uc.addWidget(self._yunits_field); row2.addLayout(uc)
        gc = QVBoxLayout(); gc.addWidget(self._field_label("Grid"))
        self._grid_cb = QCheckBox("Show grid lines")
        self._grid_cb.setFont(QFont(FONT_UI, 12))
        self._grid_cb.setChecked(self.element.show_grid)
        gc.addWidget(self._grid_cb); row2.addLayout(gc)
        lay.addLayout(row2)

        # Y-axis Min/Max with "Auto" checkboxes
        lay.addWidget(self._field_label("Y-axis Range"))
        row3 = QHBoxLayout(); row3.setSpacing(12)

        minc = QVBoxLayout(); minc.addWidget(self._field_label("Minimum"))
        mrow = QHBoxLayout(); mrow.setSpacing(6)
        self._ymin_spin = self._make_spin(
            self.element.y_min if self.element.y_min is not None else 0.0
        )
        self._ymin_auto = QCheckBox("Auto")
        self._ymin_auto.setFont(QFont(FONT_UI, 12))
        self._ymin_auto.setChecked(self.element.y_min is None)
        self._ymin_spin.setEnabled(self.element.y_min is not None)
        mrow.addWidget(self._ymin_spin); mrow.addWidget(self._ymin_auto)
        minc.addLayout(mrow); row3.addLayout(minc)

        maxc = QVBoxLayout(); maxc.addWidget(self._field_label("Maximum"))
        xrow = QHBoxLayout(); xrow.setSpacing(6)
        self._ymax_spin = self._make_spin(
            self.element.y_max if self.element.y_max is not None else 150.0
        )
        self._ymax_auto = QCheckBox("Auto")
        self._ymax_auto.setFont(QFont(FONT_UI, 12))
        self._ymax_auto.setChecked(self.element.y_max is None)
        self._ymax_spin.setEnabled(self.element.y_max is not None)
        xrow.addWidget(self._ymax_spin); xrow.addWidget(self._ymax_auto)
        maxc.addLayout(xrow); row3.addLayout(maxc)

        lay.addLayout(row3)

        # Bounds error
        self._bounds_err = self._error_label()
        lay.addWidget(self._bounds_err)

        # Connected series (read-only info)
        lay.addWidget(self._field_label("Connected Series (read-only)"))
        self._series_list = QListWidget()
        self._series_list.setMaximumHeight(90)
        self._series_list.setFont(QFont(FONT_MONO, 11))
        self._series_list.setStyleSheet(
            "border: 1px solid #E5E7EB; border-radius: 6px; background: #F9FAFB;"
        )
        # Populate with connected sources
        conns_to = self.graph.get_connections_to(self.element.id)
        if conns_to:
            for c in conns_to:
                src = self.graph.get_element(c.from_element_id)
                self._series_list.addItem(f"{src.name}.{c.from_port_name}")
        else:
            self._series_list.addItem("(no connections yet)")
        lay.addWidget(self._series_list)
        lay.addStretch()

        # Wiring
        self._name_field.textChanged.connect(self._run_validation)
        self._ymin_auto.toggled.connect(lambda v: self._ymin_spin.setEnabled(not v))
        self._ymax_auto.toggled.connect(lambda v: self._ymax_spin.setEnabled(not v))
        self._ymin_spin.valueChanged.connect(self._run_validation)
        self._ymax_spin.valueChanged.connect(self._run_validation)
        return w

    @staticmethod
    def _make_spin(value: float) -> QDoubleSpinBox:
        s = QDoubleSpinBox()
        s.setRange(-1e9, 1e9)
        s.setDecimals(2)
        s.setValue(value)
        s.setFont(QFont(FONT_MONO, 12))
        return s

    def _validate(self) -> list[str]:
        errors = []
        if self._name_field is None:
            return errors
        e = self._validate_name(self._name_field.text().strip())
        if e:
            errors.append(e); self._show_error(self._name_err, e)
        else:
            self._show_error(self._name_err, "")

        if not self._ymin_auto.isChecked() and not self._ymax_auto.isChecked():
            if self._ymin_spin.value() >= self._ymax_spin.value():
                msg = "Y-axis minimum must be less than maximum"
                errors.append(msg); self._show_error(self._bounds_err, msg)
                return errors
        self._show_error(self._bounds_err, "")
        return errors

    def apply_changes(self) -> None:
        self.element.name         = self._name_field.text().strip()
        self.element.description  = self._desc_field.text().strip()
        self.element.title        = self._title_field.text().strip()
        self.element.y_axis_label = self._ylabel_field.text().strip()
        self.element.y_axis_units = self._yunits_field.text().strip() or "-"
        self.element.show_grid    = self._grid_cb.isChecked()
        self.element.y_min        = None if self._ymin_auto.isChecked() else self._ymin_spin.value()
        self.element.y_max        = None if self._ymax_auto.isChecked() else self._ymax_spin.value()
