"""Simulation Settings dialog."""
from __future__ import annotations

from datetime import date

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox, QDateEdit, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QHBoxLayout, QLabel, QRadioButton,
    QVBoxLayout, QWidget,
)

from hydrosim.gui.styles.theme import FONT_MONO, FONT_UI, PANEL_BG, TEXT_SECONDARY
from hydrosim.model.base import SimulationSettings


class SimulationSettingsDialog(QDialog):
    """
    Dialog for start time, end time, timestep, and time mode.
    Computes n_steps live; warns if > 100 000 steps.
    """

    def __init__(self, settings: SimulationSettings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Simulation Settings")
        self.setModal(True)
        self.setMinimumWidth(380)
        self.setStyleSheet(f"QDialog {{ background: {PANEL_BG}; }}")
        self._settings = settings
        self._build_ui()
        self._update_computed()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 14)
        root.setSpacing(14)

        # Time Mode
        root.addWidget(self._label("Time Mode"))
        mode_row = QHBoxLayout()
        self._elapsed_rb  = QRadioButton("Elapsed Days")
        self._calendar_rb = QRadioButton("Calendar")
        self._elapsed_rb.setFont(QFont(FONT_UI, 12))
        self._calendar_rb.setFont(QFont(FONT_UI, 12))
        if self._settings.time_mode == "elapsed":
            self._elapsed_rb.setChecked(True)
        else:
            self._calendar_rb.setChecked(True)
        mode_row.addWidget(self._elapsed_rb)
        mode_row.addWidget(self._calendar_rb)
        mode_row.addStretch()
        root.addLayout(mode_row)

        # Start Date (calendar mode only)
        self._start_date_lbl = self._label("Start Date")
        root.addWidget(self._start_date_lbl)
        self._start_date_edit = QDateEdit()
        self._start_date_edit.setCalendarPopup(True)
        self._start_date_edit.setFont(QFont(FONT_UI, 12))
        if self._settings.start_date:
            from PyQt6.QtCore import QDate
            self._start_date_edit.setDate(
                QDate(self._settings.start_date.year,
                      self._settings.start_date.month,
                      self._settings.start_date.day)
            )
        else:
            from PyQt6.QtCore import QDate
            self._start_date_edit.setDate(QDate(2020, 1, 1))
        root.addWidget(self._start_date_edit)

        # Time / End Time row
        te_row = QHBoxLayout(); te_row.setSpacing(14)

        start_col = QVBoxLayout()
        start_col.addWidget(self._label("Start Time (days)"))
        self._start_spin = self._make_spin(self._settings.start_time, 0, 1e6)
        start_col.addWidget(self._start_spin)
        te_row.addLayout(start_col)

        end_col = QVBoxLayout()
        end_col.addWidget(self._label("End Time (days)"))
        self._end_spin = self._make_spin(self._settings.end_time, 0.001, 1e6)
        end_col.addWidget(self._end_spin)
        te_row.addLayout(end_col)
        root.addLayout(te_row)

        # Timestep
        root.addWidget(self._label("Timestep (days)"))
        self._dt_spin = self._make_spin(self._settings.dt, 1e-6, 365, decimals=6)
        root.addWidget(self._dt_spin)

        # Computed info
        self._computed_lbl = QLabel()
        self._computed_lbl.setFont(QFont(FONT_MONO, 11))
        self._computed_lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
        root.addWidget(self._computed_lbl)

        self._warn_lbl = QLabel()
        self._warn_lbl.setFont(QFont(FONT_UI, 11))
        self._warn_lbl.setStyleSheet("color: #FB8C00;")
        self._warn_lbl.setWordWrap(True)
        self._warn_lbl.setVisible(False)
        root.addWidget(self._warn_lbl)

        # Buttons
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Ok
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

        # Wiring
        self._elapsed_rb.toggled.connect(self._on_mode_change)
        self._calendar_rb.toggled.connect(self._on_mode_change)
        self._start_spin.valueChanged.connect(self._update_computed)
        self._end_spin.valueChanged.connect(self._update_computed)
        self._dt_spin.valueChanged.connect(self._update_computed)
        self._on_mode_change()

    def _on_mode_change(self) -> None:
        calendar = self._calendar_rb.isChecked()
        self._start_date_lbl.setVisible(calendar)
        self._start_date_edit.setVisible(calendar)
        self._start_spin.setEnabled(not calendar)

    def _update_computed(self) -> None:
        try:
            n = max(1, round((self._end_spin.value() - self._start_spin.value())
                             / self._dt_spin.value()))
            self._computed_lbl.setText(f"Computed: {n:,} timesteps")
            if n > 100_000:
                self._warn_lbl.setText(f"⚠ {n:,} timesteps may be slow. Consider a larger Δt.")
                self._warn_lbl.setVisible(True)
            else:
                self._warn_lbl.setVisible(False)
        except ZeroDivisionError:
            self._computed_lbl.setText("Invalid timestep")

    @staticmethod
    def _label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(QFont(FONT_UI, 11))
        lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-weight: 600;")
        return lbl

    @staticmethod
    def _make_spin(value: float, lo: float, hi: float, decimals: int = 4) -> QDoubleSpinBox:
        s = QDoubleSpinBox()
        s.setRange(lo, hi)
        s.setDecimals(decimals)
        s.setValue(value)
        s.setFont(QFont(FONT_MONO, 12))
        return s

    def get_settings(self) -> SimulationSettings:
        """Return a new SimulationSettings from dialog values."""
        time_mode  = "elapsed" if self._elapsed_rb.isChecked() else "calendar"
        start_date = None
        if time_mode == "calendar":
            qd = self._start_date_edit.date()
            start_date = date(qd.year(), qd.month(), qd.day())
            start_time = 0.0
        else:
            start_time = self._start_spin.value()

        return SimulationSettings(
            start_time=start_time,
            end_time=self._end_spin.value(),
            dt=self._dt_spin.value(),
            time_mode=time_mode,
            start_date=start_date,
        )
