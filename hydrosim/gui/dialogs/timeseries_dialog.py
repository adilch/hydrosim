"""Property dialog for TimeSeries elements."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox, QFileDialog, QHBoxLayout, QHeaderView,
    QLineEdit, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from hydrosim.gui.dialogs import BaseElementDialog, COMMON_UNITS
from hydrosim.gui.styles.theme import FONT_MONO, FONT_UI, TEXT_SECONDARY
from hydrosim.model.base import InterpolationType, TimeSeriesType
from hydrosim.model.elements.timeseries import TimeSeries


class TimeSeriesDialog(BaseElementDialog):
    def __init__(self, element: TimeSeries, graph, parent=None):
        self._name_field  = None
        self._name_err    = None
        super().__init__(element, graph, parent, min_width=520)
        self.setWindowTitle(f"TimeSeries — {element.name}")
        self.resize(520, 580)

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
        self._desc_field.setPlaceholderText("Optional documentation")
        lay.addWidget(self._desc_field)

        # Units / Data Type / Interpolation in one row
        row = QHBoxLayout(); row.setSpacing(10)

        uc = QVBoxLayout(); uc.addWidget(self._field_label("Units"))
        self._units_field = QLineEdit(self.element.units)
        uc.addWidget(self._units_field); row.addLayout(uc)

        dtc = QVBoxLayout(); dtc.addWidget(self._field_label("Data Type"))
        self._dtype_combo = QComboBox()
        for t in TimeSeriesType:
            self._dtype_combo.addItem(t.value.replace("_", " ").title(), t)
        idx = [self._dtype_combo.itemData(i) for i in range(self._dtype_combo.count())].index(self.element.data_type)
        self._dtype_combo.setCurrentIndex(idx)
        dtc.addWidget(self._dtype_combo); row.addLayout(dtc)

        ic = QVBoxLayout(); ic.addWidget(self._field_label("Interpolation"))
        self._interp_combo = QComboBox()
        for t in InterpolationType:
            self._interp_combo.addItem(t.value.title(), t)
        idx2 = [self._interp_combo.itemData(i) for i in range(self._interp_combo.count())].index(self.element.interpolation)
        self._interp_combo.setCurrentIndex(idx2)
        ic.addWidget(self._interp_combo); row.addLayout(ic)

        lay.addLayout(row)

        # Data table
        lay.addWidget(self._field_label("Data  (Time [days] / Value)"))
        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["Time (days)", "Value"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setFont(QFont(FONT_MONO, 11))
        self._table.setAlternatingRowColors(True)
        self._table.setMinimumHeight(160)
        for t, v in self.element.data:
            self._add_table_row(t, v)
        lay.addWidget(self._table)

        # Table buttons
        btn_row = QHBoxLayout(); btn_row.setSpacing(6)
        for label, slot in [
            ("+ Add Row",      self._add_empty_row),
            ("− Delete Row",   self._delete_row),
            ("Import CSV…",    self._import_csv),
            ("Clear All",      self._clear_all),
        ]:
            b = QPushButton(label)
            b.setFixedHeight(28)
            b.setFont(QFont(FONT_UI, 11))
            b.clicked.connect(slot)
            btn_row.addWidget(b)
        lay.addLayout(btn_row)

        # Validation error
        self._data_err = self._error_label()
        lay.addWidget(self._data_err)

        self._name_field.textChanged.connect(self._run_validation)
        self._table.itemChanged.connect(self._run_validation)
        return w

    # ── Table helpers ─────────────────────────────────────────────────────────

    def _add_table_row(self, t: float = 0.0, v: float = 0.0) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setItem(row, 0, QTableWidgetItem(str(t)))
        self._table.setItem(row, 1, QTableWidgetItem(str(v)))

    def _add_empty_row(self) -> None:
        last_t = 0.0
        if self._table.rowCount() > 0:
            try:
                last_t = float(self._table.item(self._table.rowCount()-1, 0).text()) + 1.0
            except (ValueError, AttributeError):
                pass
        self._add_table_row(last_t, 0.0)

    def _delete_row(self) -> None:
        row = self._table.currentRow()
        if row >= 0:
            self._table.removeRow(row)
        self._run_validation()

    def _clear_all(self) -> None:
        self._table.setRowCount(0)
        self._run_validation()

    def _import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import CSV", "", "CSV files (*.csv);;All files (*)"
        )
        if not path:
            return
        try:
            import pandas as pd
            df = pd.read_csv(path, header=None)
            if df.shape[1] < 2:
                raise ValueError(f"Expected 2 columns, got {df.shape[1]}")
            df = df.iloc[:, :2]
            df.columns = ["time", "value"]
            df["time"]  = pd.to_numeric(df["time"],  errors="coerce")
            df["value"] = pd.to_numeric(df["value"], errors="coerce")
            df = df.dropna().sort_values("time").reset_index(drop=True)
            self._table.setRowCount(0)
            for _, row in df.iterrows():
                self._add_table_row(float(row["time"]), float(row["value"]))
            self._run_validation()
        except Exception as exc:
            QMessageBox.warning(self, "Import Error", str(exc))

    def _get_data(self) -> list[list[float]]:
        data = []
        for r in range(self._table.rowCount()):
            try:
                t = float(self._table.item(r, 0).text())
                v = float(self._table.item(r, 1).text())
                data.append([t, v])
            except (ValueError, AttributeError):
                pass
        return data

    def _validate(self) -> list[str]:
        errors = []
        if self._name_field is None:
            return errors
        e = self._validate_name(self._name_field.text().strip())
        if e:
            errors.append(e)
            self._show_error(self._name_err, e)
        else:
            self._show_error(self._name_err, "")

        data = self._get_data()
        if not data:
            msg = "Time series must have at least one row"
            errors.append(msg)
            self._show_error(self._data_err, msg)
            return errors

        times = [r[0] for r in data]
        for i in range(1, len(times)):
            if times[i] <= times[i-1]:
                msg = f"Time values must be strictly increasing (row {i+1})"
                errors.append(msg)
                self._show_error(self._data_err, msg)
                return errors
        self._show_error(self._data_err, "")
        return errors

    def apply_changes(self) -> None:
        self.element.name          = self._name_field.text().strip()
        self.element.description   = self._desc_field.text().strip()
        self.element.units         = self._units_field.text().strip() or "-"
        self.element.data_type     = self._dtype_combo.currentData()
        self.element.interpolation = self._interp_combo.currentData()
        self.element.data          = self._get_data()
        self.element._prepared     = False   # force rebuild on next simulate
