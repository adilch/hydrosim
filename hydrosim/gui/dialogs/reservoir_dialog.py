"""Property dialog for Reservoir elements."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFileDialog,
    QHBoxLayout, QHeaderView, QLabel, QMessageBox, QPushButton,
    QSizePolicy, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from hydrosim.gui.dialogs import BaseElementDialog
from hydrosim.gui.styles.theme import (
    BORDER_SUBTLE, FONT_MONO, FONT_UI, PANEL_BG, TEXT_PRIMARY, TEXT_SECONDARY,
)
from hydrosim.model.elements.reservoir import Reservoir, VOLUME_UNITS, FLOW_UNITS


class _CurvePreviewDialog(QDialog):
    """Non-modal Matplotlib preview of the E-V (and E-A) bathymetry curves."""

    def __init__(self, bathymetry: list[list], volume_units: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bathymetry Curve Preview")
        self.setMinimumSize(620, 380)
        self.setStyleSheet(f"QDialog {{ background: {PANEL_BG}; }}")

        from matplotlib.figure import Figure
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)

        # Parse data
        ev_rows = sorted(
            [(float(r[0]), float(r[1])) for r in bathymetry
             if len(r) >= 2 and r[0] is not None and r[1] is not None],
            key=lambda x: x[0]
        )
        ea_rows = sorted(
            [(float(r[0]), float(r[2])) for r in bathymetry
             if len(r) >= 3 and r[2] is not None and r[0] is not None],
            key=lambda x: x[0]
        )

        has_area = len(ea_rows) >= 2
        ncols    = 2 if has_area else 1

        fig = Figure(facecolor="white", figsize=(ncols * 4, 3.5), tight_layout=True)
        import matplotlib as mpl
        mpl.rcParams.update({"axes.edgecolor": "#AAAAAA", "axes.labelsize": 10})

        if ev_rows:
            vols  = [r[1] for r in ev_rows]
            elevs = [r[0] for r in ev_rows]
            ax1   = fig.add_subplot(1, ncols, 1)
            ax1.plot(vols, elevs, "o-", color="#2E86C1", linewidth=1.8, markersize=5)
            ax1.set_xlabel(f"Volume ({volume_units})")
            ax1.set_ylabel("Elevation (m)")
            ax1.set_title("E-V Curve")
            ax1.grid(True, color="#EEEEEE", linewidth=0.7)
            ax1.set_axisbelow(True)

        if has_area:
            a_elevs = [r[0] for r in ea_rows]
            areas   = [r[1] for r in ea_rows]
            ax2     = fig.add_subplot(1, 2, 2)
            ax2.plot(areas, a_elevs, "o-", color="#4CAF82", linewidth=1.8, markersize=5)
            ax2.set_xlabel("Area (m²)")
            ax2.set_ylabel("Elevation (m)")
            ax2.set_title("E-A Curve")
            ax2.grid(True, color="#EEEEEE", linewidth=0.7)
            ax2.set_axisbelow(True)

        canvas = FigureCanvasQTAgg(fig)
        root.addWidget(canvas)

        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(80)
        close_btn.clicked.connect(self.accept)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)


class ReservoirDialog(BaseElementDialog):
    """Property dialog for Reservoir elements."""

    def __init__(self, element: Reservoir, graph, parent=None):
        self._name_field  = None
        self._name_err    = None
        super().__init__(element, graph, parent, min_width=560)
        self.setWindowTitle(f"Reservoir — {element.name}")
        self.resize(560, 620)

    def _build_body(self) -> QWidget:
        w, lay = self._body_layout()

        # ── Name / Description ────────────────────────────────────────────
        lay.addWidget(self._field_label("Name"))
        self._name_field = self._line_edit(self.element.name)
        lay.addWidget(self._name_field)
        self._name_err = self._error_label()
        lay.addWidget(self._name_err)

        lay.addWidget(self._field_label("Description"))
        self._desc_field = self._line_edit(self.element.description, "Optional documentation")
        lay.addWidget(self._desc_field)

        # ── Units row ─────────────────────────────────────────────────────
        units_row = QHBoxLayout(); units_row.setSpacing(14)

        vc = QVBoxLayout()
        vc.addWidget(self._field_label("Volume units"))
        self._vol_units = self._combo(VOLUME_UNITS, self.element.volume_units)
        vc.addWidget(self._vol_units)
        units_row.addLayout(vc)

        fc = QVBoxLayout()
        fc.addWidget(self._field_label("Flow units"))
        self._flow_units = self._combo(FLOW_UNITS, self.element.flow_units)
        fc.addWidget(self._flow_units)
        units_row.addLayout(fc)
        lay.addLayout(units_row)

        # ── Volume bounds ─────────────────────────────────────────────────
        lay.addWidget(self._field_label("Storage volumes"))
        vols_row = QHBoxLayout(); vols_row.setSpacing(10)

        for label, attr, default in [
            ("Initial",  "initial_volume", self.element.initial_volume),
            ("Minimum",  "min_volume",     self.element.min_volume),
        ]:
            col = QVBoxLayout()
            col.addWidget(QLabel(label))
            spin = self._spin(default)
            setattr(self, f"_{attr.lower()}_spin", spin)
            col.addWidget(spin)
            vols_row.addLayout(col)

        # Max volume + Unbounded
        max_col = QVBoxLayout()
        max_col.addWidget(QLabel("Maximum"))
        max_inner = QHBoxLayout(); max_inner.setSpacing(6)
        self._max_volume_spin = self._spin(
            self.element.max_volume if self.element.max_volume is not None else 1e6
        )
        self._unbounded_cb = QCheckBox("Unbounded")
        self._unbounded_cb.setFont(QFont(FONT_UI, 11))
        self._unbounded_cb.setChecked(self.element.max_volume is None)
        self._max_volume_spin.setEnabled(self.element.max_volume is not None)
        self._unbounded_cb.toggled.connect(
            lambda v: self._max_volume_spin.setEnabled(not v)
        )
        max_inner.addWidget(self._max_volume_spin)
        max_inner.addWidget(self._unbounded_cb)
        max_col.addLayout(max_inner)
        vols_row.addLayout(max_col)
        lay.addLayout(vols_row)

        # Bounds validation label
        self._bounds_err = self._error_label()
        lay.addWidget(self._bounds_err)

        # ── Bathymetry table ──────────────────────────────────────────────
        hdr_row = QHBoxLayout()
        hdr_row.addWidget(self._field_label("Bathymetry Table  (Elevation · Volume · Area)"))
        hdr_row.addStretch()
        preview_btn = QPushButton("Preview Curves")
        preview_btn.setFixedHeight(24)
        preview_btn.setFont(QFont(FONT_UI, 10))
        preview_btn.setStyleSheet(
            f"QPushButton {{ border: 1px solid {BORDER_SUBTLE}; border-radius: 5px; "
            f"background: {PANEL_BG}; color: {TEXT_PRIMARY}; padding: 0 10px; }}"
            f"QPushButton:hover {{ background: #EEF0F4; }}"
        )
        preview_btn.clicked.connect(self._preview_curves)
        hdr_row.addWidget(preview_btn)
        lay.addLayout(hdr_row)

        # Table
        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Elevation (m)", "Volume", "Area (m²)  optional"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setFont(QFont(FONT_MONO, 10))
        self._table.setAlternatingRowColors(True)
        self._table.setMinimumHeight(160)
        self._table.setStyleSheet(
            f"QTableWidget {{ border: 1px solid {BORDER_SUBTLE}; border-radius: 6px; "
            f"background: white; color: {TEXT_PRIMARY}; "
            f"alternate-background-color: #F9FAFB; gridline-color: #F0F1F5; }}"
            f"QHeaderView::section {{ background: #F5F6FA; color: {TEXT_PRIMARY}; "
            f"font-weight: 600; border: none; border-bottom: 1px solid {BORDER_SUBTLE}; "
            f"padding: 4px 8px; }}"
        )
        # Populate from element data
        for row in self.element.bathymetry:
            self._add_table_row(
                row[0] if len(row) > 0 else "",
                row[1] if len(row) > 1 else "",
                row[2] if len(row) > 2 else "",
            )
        lay.addWidget(self._table)

        # Table buttons
        btn_row = QHBoxLayout(); btn_row.setSpacing(6)
        for label, slot in [
            ("+ Add Row",   self._add_empty_row),
            ("− Delete",    self._delete_row),
            ("Import CSV",  self._import_csv),
            ("Clear All",   self._clear_all),
        ]:
            b = QPushButton(label)
            b.setFixedHeight(26)
            b.setFont(QFont(FONT_UI, 10))
            btn_row.addWidget(b)
            b.clicked.connect(slot)
        lay.addLayout(btn_row)

        self._table_err = self._error_label()
        lay.addWidget(self._table_err)
        lay.addStretch()

        # Wiring
        self._name_field.textChanged.connect(self._run_validation)
        self._initial_volume_spin.valueChanged.connect(self._run_validation)
        self._min_volume_spin.valueChanged.connect(self._run_validation)
        self._max_volume_spin.valueChanged.connect(self._run_validation)
        self._unbounded_cb.toggled.connect(self._run_validation)
        self._table.itemChanged.connect(self._run_validation)
        return w

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _line_edit(value: str, placeholder: str = "") -> "QLineEdit":
        from PyQt6.QtWidgets import QLineEdit
        le = QLineEdit(str(value))
        if placeholder:
            le.setPlaceholderText(placeholder)
        return le

    @staticmethod
    def _combo(options: list[str], current: str) -> QComboBox:
        cb = QComboBox()
        cb.addItems(options)
        if current in options:
            cb.setCurrentText(current)
        elif options:
            cb.addItem(current)
            cb.setCurrentText(current)
        return cb

    @staticmethod
    def _spin(value: float, lo: float = 0.0, hi: float = 1e12) -> QDoubleSpinBox:
        s = QDoubleSpinBox()
        s.setRange(lo, hi)
        s.setDecimals(4)
        s.setValue(float(value))
        s.setFont(QFont(FONT_MONO, 11))
        return s

    def _add_table_row(self, elev="", vol="", area="") -> None:
        r = self._table.rowCount()
        self._table.insertRow(r)
        for c, val in enumerate([elev, vol, area]):
            self._table.setItem(r, c, QTableWidgetItem("" if val == "" else str(val)))

    def _add_empty_row(self) -> None:
        self._add_table_row()

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
            self, "Import Bathymetry CSV", "", "CSV files (*.csv);;All files (*)"
        )
        if not path:
            return
        try:
            import pandas as pd
            df = pd.read_csv(path, header=None)
            if df.shape[1] < 2:
                raise ValueError(f"Expected ≥2 columns (Elevation, Volume [, Area]), got {df.shape[1]}")
            self._table.setRowCount(0)
            for _, row in df.iterrows():
                elev = row.iloc[0]
                vol  = row.iloc[1]
                area = row.iloc[2] if df.shape[1] > 2 else ""
                self._add_table_row(elev, vol, "" if (area == "" or str(area).strip() == "") else area)
            self._run_validation()
        except Exception as exc:
            QMessageBox.warning(self, "Import Error", str(exc))

    def _preview_curves(self) -> None:
        data = self._get_bathymetry()
        if len([r for r in data if len(r) >= 2]) < 2:
            QMessageBox.information(
                self, "No Data",
                "Enter at least 2 rows with Elevation and Volume values first."
            )
            return
        vol_units = self._vol_units.currentText()
        dlg = _CurvePreviewDialog(data, vol_units, parent=self)
        dlg.exec()

    def _get_bathymetry(self) -> list[list]:
        """Parse table rows into [[elev, vol, area?], ...], sorted by elevation."""
        rows = []
        for r in range(self._table.rowCount()):
            try:
                e_item = self._table.item(r, 0)
                v_item = self._table.item(r, 1)
                a_item = self._table.item(r, 2)
                if e_item is None or v_item is None:
                    continue
                e_str = e_item.text().strip()
                v_str = v_item.text().strip()
                a_str = a_item.text().strip() if a_item else ""
                if not e_str or not v_str:
                    continue
                elev = float(e_str)
                vol  = float(v_str)
                if a_str:
                    rows.append([elev, vol, float(a_str)])
                else:
                    rows.append([elev, vol])
            except (ValueError, AttributeError):
                continue
        return sorted(rows, key=lambda x: x[0])

    # ── Validation ─────────────────────────────────────────────────────────────

    def _validate(self) -> list[str]:
        errors = []
        if self._name_field is None:
            return errors

        # Name
        e = self._validate_name(self._name_field.text().strip())
        if e:
            errors.append(e); self._show_error(self._name_err, e)
        else:
            self._show_error(self._name_err, "")

        # Bounds
        lo  = self._min_volume_spin.value()
        ini = self._initial_volume_spin.value()
        unbounded = self._unbounded_cb.isChecked()
        hi  = None if unbounded else self._max_volume_spin.value()

        if hi is not None and hi <= lo:
            msg = "Maximum volume must be greater than minimum"
            errors.append(msg); self._show_error(self._bounds_err, msg)
            return errors
        if hi is not None and not (lo <= ini <= hi):
            msg = f"Initial volume ({ini:.2f}) must be within [{lo:.2f}, {hi:.2f}]"
            errors.append(msg); self._show_error(self._bounds_err, msg)
            return errors
        if ini < lo:
            msg = f"Initial volume ({ini:.2f}) is below minimum ({lo:.2f})"
            errors.append(msg); self._show_error(self._bounds_err, msg)
            return errors
        self._show_error(self._bounds_err, "")

        # Bathymetry
        data = self._get_bathymetry()
        if len(data) >= 2:
            elevs = [r[0] for r in data]
            vols  = [r[1] for r in data]
            for i in range(1, len(elevs)):
                if elevs[i] <= elevs[i - 1]:
                    msg = "Elevations must be strictly increasing"
                    errors.append(msg); self._show_error(self._table_err, msg)
                    return errors
            for i in range(1, len(vols)):
                if vols[i] < vols[i - 1]:
                    msg = "Volumes must be non-decreasing with elevation"
                    errors.append(msg); self._show_error(self._table_err, msg)
                    return errors
        self._show_error(self._table_err, "")
        return errors

    # ── Apply ──────────────────────────────────────────────────────────────────

    def apply_changes(self) -> None:
        self.element.name           = self._name_field.text().strip()
        self.element.description    = self._desc_field.text().strip()
        self.element.volume_units   = self._vol_units.currentText()
        self.element.flow_units     = self._flow_units.currentText()
        self.element.initial_volume = self._initial_volume_spin.value()
        self.element.min_volume     = self._min_volume_spin.value()
        self.element.max_volume     = (
            None if self._unbounded_cb.isChecked()
            else self._max_volume_spin.value()
        )
        self.element.bathymetry = self._get_bathymetry()
        # Rebuild dynamic ports (level, area) based on new data
        self.element.rebuild_output_ports()
