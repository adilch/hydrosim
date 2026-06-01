"""
Results Dashboard — GoldSim-style result viewer using Matplotlib.

Architecture:
  ResultsDashboard   QMainWindow — single window, always-on-top of canvas
    QTabWidget       one tab per TimeHistoryResult element
      ResultTab      series manager (left) | chart + table (right)
        SeriesManagerPanel   checkbox / axis / colour per series
        PlotCanvas           Matplotlib FigureCanvas + MATLAB-style toolbar
        DataTableWidget      scrollable table, rows = visible time range (Option A)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg,
    NavigationToolbar2QT,
)

from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QCheckBox, QColorDialog, QComboBox, QFileDialog, QHBoxLayout,
    QHeaderView, QLabel, QMainWindow, QMessageBox, QPushButton,
    QScrollArea, QSizePolicy, QStackedWidget, QStatusBar,
    QTabWidget, QTableView,
    QVBoxLayout, QWidget,
)

from hydrosim.gui.styles.theme import (
    BORDER_SUBTLE, FONT_MONO, FONT_UI,
    PANEL_BG, TEXT_PRIMARY, TEXT_SECONDARY,
)

if TYPE_CHECKING:
    from hydrosim.engine.results import ResultsStore
    from hydrosim.model.elements.timehistory import TimeHistoryResult
    from hydrosim.model.graph import ModelGraph

# ── Matplotlib global style (MATLAB-like) ─────────────────────────────────────

mpl.rcParams.update({
    "axes.facecolor":      "white",
    "figure.facecolor":    "white",
    "axes.edgecolor":      "#AAAAAA",
    "axes.labelcolor":     "#1A1A2E",
    "axes.labelsize":      11,
    "axes.labelweight":    "bold",
    "axes.titlesize":      12,
    "axes.titleweight":    "bold",
    "axes.titlelocation":  "left",
    "axes.grid":           True,
    "grid.color":          "#EEEEEE",
    "grid.linewidth":      0.8,
    "xtick.color":         "#1A1A2E",
    "ytick.color":         "#1A1A2E",
    "xtick.labelsize":     10,
    "ytick.labelsize":     10,
    "lines.linewidth":     1.5,
    "lines.antialiased":   True,
    "font.family":         "sans-serif",
    "font.size":           10,
    "legend.fontsize":     9,
    "legend.framealpha":   0.85,
    "legend.edgecolor":    "#DDDDDD",
    "savefig.dpi":         150,
    "savefig.bbox":        "tight",
})

# Auto-assigned line colours
_COLOURS = [
    "#2E86C1", "#E8633A", "#4CAF82", "#7B68C8",
    "#E8A020", "#00897B", "#E53935", "#795548",
]


# ── SeriesConfig ──────────────────────────────────────────────────────────────

@dataclass
class SeriesConfig:
    """
    Configuration for one plotted series.
    unc_low / unc_high are None in Phase 1; Phase 2 Monte Carlo sets them
    to arrays for the uncertainty band (fill_between).
    """
    element_id: str
    port_name:  str
    label:      str            # "ElementName.port_name"
    axis:       str = "left"   # "left" | "right"
    colour:     str = ""       # hex, auto-assigned when empty
    visible:    bool = True

    # Phase 2 ensemble support — leave None in Phase 1
    unc_low:  np.ndarray | None = None
    unc_high: np.ndarray | None = None


# ── SeriesRow ─────────────────────────────────────────────────────────────────

class _SeriesRow(QWidget):
    """One row in the series manager: [✓] label  [Left▼]  [■ colour]"""

    changed = pyqtSignal()

    def __init__(self, config: SeriesConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.setFixedHeight(38)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 0, 8, 0)
        lay.setSpacing(7)

        # Colour swatch (left, prominent)
        self._colour_btn = QPushButton()
        self._colour_btn.setFixedSize(16, 16)
        self._colour_btn.setStyleSheet(
            f"background: {config.colour}; border: none; border-radius: 3px;"
        )
        self._colour_btn.setToolTip("Click to change colour")
        self._colour_btn.clicked.connect(self._pick_colour)
        lay.addWidget(self._colour_btn)

        # Visibility checkbox
        self._cb = QCheckBox()
        self._cb.setChecked(config.visible)
        self._cb.setFixedWidth(16)
        self._cb.toggled.connect(self._on_toggle)
        lay.addWidget(self._cb)

        # Series label — elided with tooltip for long names
        short = config.label if len(config.label) <= 22 else config.label[:20] + "…"
        lbl = QLabel(short)
        lbl.setFont(QFont(FONT_MONO, 10))
        lbl.setStyleSheet(f"color: {TEXT_PRIMARY};")
        lbl.setToolTip(config.label)
        lay.addWidget(lbl, stretch=1)

        # Axis assignment: compact "L" / "R" with tooltip
        self._axis_combo = QComboBox()
        self._axis_combo.addItem("L", "left")
        self._axis_combo.addItem("R", "right")
        self._axis_combo.setCurrentIndex(0 if config.axis == "left" else 1)
        self._axis_combo.setFixedSize(40, 24)
        self._axis_combo.setFont(QFont(FONT_UI, 10))
        self._axis_combo.setToolTip("Left axis / Right axis")
        self._axis_combo.currentIndexChanged.connect(self._on_axis_change)
        lay.addWidget(self._axis_combo)

    def _on_toggle(self, checked: bool) -> None:
        self.config.visible = checked
        self.changed.emit()

    def _on_axis_change(self, index: int) -> None:
        self.config.axis = "left" if index == 0 else "right"
        self.changed.emit()

    def _pick_colour(self) -> None:
        col = QColorDialog.getColor(QColor(self.config.colour), self)
        if col.isValid():
            self.config.colour = col.name()
            self._colour_btn.setStyleSheet(
                f"background: {self.config.colour}; "
                f"border: 1px solid #CCCCCC; border-radius: 3px;"
            )
            self.changed.emit()


# ── SeriesManagerPanel ────────────────────────────────────────────────────────

class SeriesManagerPanel(QWidget):
    """Left sidebar: one _SeriesRow per connected series."""

    series_changed = pyqtSignal()

    def __init__(self, configs: list[SeriesConfig], parent=None):
        super().__init__(parent)
        self.setMinimumWidth(180)
        self.setMaximumWidth(500)
        self.setStyleSheet(
            f"background: {PANEL_BG}; border-right: 1px solid {BORDER_SUBTLE};"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header with series count badge
        hdr = QWidget()
        hdr.setFixedHeight(36)
        hdr.setStyleSheet(
            f"background: #F5F6FA; border-bottom: 1px solid {BORDER_SUBTLE};"
        )
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(12, 0, 10, 0)
        hdr_lbl = QLabel("Series")
        hdr_lbl.setFont(QFont(FONT_UI, 11))
        hdr_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-weight: 700; background: transparent;")
        hdr_lay.addWidget(hdr_lbl)
        hdr_lay.addStretch()
        badge = QLabel(str(len(configs)))
        badge.setFont(QFont(FONT_MONO, 9))
        badge.setStyleSheet(
            f"background: #E4EDF5; color: #2E86C1; border-radius: 8px; "
            f"padding: 1px 7px; font-weight: 600;"
        )
        hdr_lay.addWidget(badge)
        root.addWidget(hdr)

        # Column labels
        sub = QWidget()
        sub.setFixedHeight(22)
        sub_lay = QHBoxLayout(sub)
        sub_lay.setContentsMargins(10, 0, 8, 0)
        sub_lay.setSpacing(7)
        for text, width in [("", 16), ("", 16), ("Name", 0), ("Axis", 40)]:
            l = QLabel(text)
            l.setFont(QFont(FONT_UI, 9))
            l.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent;")
            if width:
                l.setFixedWidth(width)
            else:
                l.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            sub_lay.addWidget(l)
        sub.setStyleSheet(f"background: #F9FAFB; border-bottom: 1px solid {BORDER_SUBTLE};")
        root.addWidget(sub)

        # Rows
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        content = QWidget()
        content.setStyleSheet(f"background: {PANEL_BG};")
        self._rows_layout = QVBoxLayout(content)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(0)

        for cfg in configs:
            row = _SeriesRow(cfg)
            row.changed.connect(self.series_changed)
            self._rows_layout.addWidget(row)

        self._rows_layout.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, stretch=1)


# ── PlotCanvas ────────────────────────────────────────────────────────────────

class PlotCanvas(QWidget):
    """
    Matplotlib FigureCanvas + MATLAB-style NavigationToolbar2QT.
    Supports dual Y-axis (left + right).
    Emits xlim_changed when the user pans/zooms.
    """

    xlim_changed = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: white;")

        self.fig = Figure(facecolor="white")

        self.ax1 = self.fig.add_subplot(111)   # left Y-axis
        self.ax2 = self.ax1.twinx()            # right Y-axis
        self.ax2.set_visible(False)

        self.canvas  = FigureCanvasQTAgg(self.fig)
        self.canvas.setStyleSheet("background: white;")
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        self.toolbar.setStyleSheet(
            f"background: #F5F6FA; border-bottom: 1px solid {BORDER_SUBTLE};"
        )

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self.toolbar)
        lay.addWidget(self.canvas, stretch=1)

        pass  # no xlim signal needed — table always shows full range

    def redraw(
        self,
        time_arr:       np.ndarray,
        configs:        list[SeriesConfig],
        results_store:  "ResultsStore",
        result_element: "TimeHistoryResult",
        legend_loc:     str = "best",
    ) -> None:
        """Clear and redraw all visible series."""
        self.ax1.cla()
        self.ax2.cla()
        self.ax2.set_visible(False)

        has_right = any(c.axis == "right" and c.visible for c in configs)
        if has_right:
            self.ax2.set_visible(True)

        lines_for_legend = []

        for cfg in configs:
            if not cfg.visible:
                continue
            try:
                arr = results_store.get_series(cfg.element_id, cfg.port_name)
            except KeyError:
                continue

            n   = results_store.completed_steps
            t   = time_arr[:n]
            y   = arr[:n]
            ax  = self.ax1 if cfg.axis == "left" else self.ax2
            col = cfg.colour or _COLOURS[0]

            ln, = ax.plot(t, y, color=col, linewidth=1.5,
                          label=cfg.label, zorder=3)
            lines_for_legend.append(ln)

            # Phase 2: uncertainty band
            if cfg.unc_low is not None and cfg.unc_high is not None:
                ax.fill_between(
                    t, cfg.unc_low[:n], cfg.unc_high[:n],
                    alpha=0.18, color=col, zorder=2,
                )

        # Axis labels
        y_label = result_element.y_axis_label or ""
        y_units = result_element.y_axis_units or ""
        if y_units and y_units != "-":
            y_label = f"{y_label} ({y_units})" if y_label else y_units
        # Truncate very long axis labels so they don't crowd the axes
        y_label = (y_label[:32] + "…") if len(y_label or "") > 32 else (y_label or "Value")
        self.ax1.set_ylabel(y_label)
        self.ax1.set_xlabel("Time (days)")

        if has_right:
            self.ax2.set_ylabel("Right axis")

        # Title — left-aligned, slightly above the axes
        title = result_element.title or result_element.name
        title = (title[:50] + "…") if len(title) > 50 else title
        self.ax1.set_title(title, pad=10)

        # Manual Y-range
        if result_element.y_min is not None:
            self.ax1.set_ylim(bottom=result_element.y_min)
        if result_element.y_max is not None:
            self.ax1.set_ylim(top=result_element.y_max)

        # Legend — position controlled by caller
        # Remove any existing legend from both axes first
        for ax in (self.ax1, self.ax2):
            if ax.get_legend():
                ax.get_legend().remove()

        if lines_for_legend and legend_loc != "none":
            if legend_loc == "outside right":
                # Place legend to the right of the plot area
                self.fig.subplots_adjust(left=0.10, right=0.76, top=0.91, bottom=0.11)
                self.ax1.legend(
                    handles=lines_for_legend,
                    loc="upper left",
                    bbox_to_anchor=(1.01, 1),
                    borderaxespad=0,
                    framealpha=0.9,
                    edgecolor="#DDDDDD",
                )
            else:
                self.fig.subplots_adjust(left=0.10, right=0.93, top=0.91, bottom=0.11)
                self.ax1.legend(
                    handles=lines_for_legend,
                    loc=legend_loc,
                    framealpha=0.85,
                    edgecolor="#DDDDDD",
                )
        else:
            # "none" or no series — restore normal margins
            self.fig.subplots_adjust(left=0.09, right=0.91, top=0.93, bottom=0.10)

        # Grid on primary axis only
        self.ax1.grid(True, which="major", color="#EEEEEE", linewidth=0.8, zorder=0)
        self.ax1.set_axisbelow(True)

        # Spine styling
        for spine in self.ax1.spines.values():
            spine.set_color("#AAAAAA")
        if has_right:
            for spine in self.ax2.spines.values():
                spine.set_color("#AAAAAA")

        self.canvas.draw_idle()

    def get_xlim(self) -> tuple[float, float]:
        return self.ax1.get_xlim()

    # xlim_changed kept as a no-op signal for backward compat
    xlim_changed = pyqtSignal(float, float)


# ── Virtual table model ───────────────────────────────────────────────────────

class _ResultTableModel(QAbstractTableModel):
    """
    Read-only virtual table model backed by numpy arrays.
    Rows are rendered on-demand — O(1) to load regardless of dataset size.
    No QTableWidgetItem objects are ever created.
    """

    _FG = QColor(TEXT_PRIMARY)
    _ALIGN_RIGHT = int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def __init__(
        self,
        time_arr: np.ndarray,
        series:   list[tuple[str, np.ndarray]],  # [(label, array), ...]
        indices:  np.ndarray,                     # row indices into time_arr
        parent=None,
    ):
        super().__init__(parent)
        self._time_arr = time_arr
        self._series   = series    # [(label, data_array), ...]
        self._indices  = indices   # filtered row indices

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._indices)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 1 + len(self._series)

    def headerData(self, section: int, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            if section == 0:
                return "Time (days)"
            if 1 <= section <= len(self._series):
                return self._series[section - 1][0]
        elif orientation == Qt.Orientation.Vertical:
            return str(self._indices[section] + 1)  # 1-based row number
        return None

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row, col = index.row(), index.column()
        src_idx  = int(self._indices[row])

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return f"{self._time_arr[src_idx]:.2f}"
            arr = self._series[col - 1][1]
            if src_idx < len(arr):
                return f"{arr[src_idx]:.4f}"
            return ""

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col > 0:
                return self._ALIGN_RIGHT

        if role == Qt.ItemDataRole.ForegroundRole:
            return self._FG

        return None


# ── DataTableWidget ───────────────────────────────────────────────────────────

class DataTableWidget(QWidget):
    """
    Virtual data table — instantaneous regardless of row count.
    Uses QTableView + QAbstractTableModel so only visible rows are rendered.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {PANEL_BG};")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header bar
        hdr = QWidget()
        hdr.setFixedHeight(34)
        hdr.setStyleSheet(
            f"background: #F5F6FA; border-bottom: 1px solid {BORDER_SUBTLE};"
        )
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(12, 0, 10, 0)
        hdr_lay.setSpacing(8)

        icon_lbl = QLabel("≡")
        icon_lbl.setFont(QFont(FONT_UI, 13))
        icon_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent;")
        hdr_lay.addWidget(icon_lbl)

        title_lbl = QLabel("Data Table")
        title_lbl.setFont(QFont(FONT_UI, 11))
        title_lbl.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-weight: 700; background: transparent;"
        )
        hdr_lay.addWidget(title_lbl)
        hdr_lay.addStretch()

        self._row_count_lbl = QLabel()
        self._row_count_lbl.setFont(QFont(FONT_MONO, 10))
        self._row_count_lbl.setStyleSheet(
            f"color: {TEXT_SECONDARY}; background: transparent;"
        )
        hdr_lay.addWidget(self._row_count_lbl)

        # Copy to clipboard button
        copy_btn = QPushButton("Copy")
        copy_btn.setFixedSize(52, 24)
        copy_btn.setFont(QFont(FONT_UI, 10))
        copy_btn.setToolTip("Copy visible data to clipboard")
        copy_btn.setStyleSheet(
            f"QPushButton {{ border: 1px solid {BORDER_SUBTLE}; border-radius: 5px; "
            f"background: {PANEL_BG}; color: {TEXT_PRIMARY}; }}"
            f"QPushButton:hover {{ background: #EEF0F4; }}"
        )
        copy_btn.clicked.connect(self._copy_to_clipboard)
        hdr_lay.addWidget(copy_btn)
        root.addWidget(hdr)

        # QTableView (virtual — no items created upfront)
        self._view = QTableView()
        self._view.setAlternatingRowColors(True)
        self._view.setFont(QFont(FONT_MONO, 10))
        self._view.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self._view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._view.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self._view.verticalHeader().setDefaultSectionSize(26)
        self._view.verticalHeader().setVisible(False)
        self._view.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        self._view.horizontalHeader().setMinimumSectionSize(80)
        self._view.horizontalHeader().setStretchLastSection(True)
        self._view.setStyleSheet(
            f"QTableView {{ border: none; background: white; color: {TEXT_PRIMARY}; "
            f"alternate-background-color: #F9FAFB; gridline-color: #F0F1F5; }}"
            f"QTableView::item {{ color: {TEXT_PRIMARY}; padding: 0px 6px; }}"
            f"QHeaderView::section {{ background: #F5F6FA; color: {TEXT_PRIMARY}; "
            f"font-weight: 600; border: none; "
            f"border-bottom: 1px solid {BORDER_SUBTLE}; padding: 4px 8px; }}"
        )
        self._model: _ResultTableModel | None = None
        root.addWidget(self._view, stretch=1)

    def set_data(
        self,
        time_arr:      np.ndarray,
        configs:       list[SeriesConfig],
        results_store: "ResultsStore",
        x_lo:          float | None = None,
        x_hi:          float | None = None,
    ) -> None:
        """
        Swap in a new virtual model — O(1) regardless of row count.
        Only the rows visible in the viewport are ever rendered.
        """
        if time_arr is None or results_store is None:
            return

        n     = results_store.completed_steps
        t_all = time_arr[:n]

        # Build filtered index array
        if x_lo is not None or x_hi is not None:
            lo   = x_lo if x_lo is not None else float(t_all[0])
            hi   = x_hi if x_hi is not None else float(t_all[-1])
            indices = np.where((t_all >= lo) & (t_all <= hi))[0]
        else:
            indices = np.arange(n)

        # Build series list (only visible series, only completed rows)
        series: list[tuple[str, np.ndarray]] = []
        for cfg in configs:
            if not cfg.visible:
                continue
            try:
                arr = results_store.get_series(cfg.element_id, cfg.port_name)
                series.append((cfg.label, arr))
            except KeyError:
                continue

        # Swap model — this is the only work done on the main thread
        self._model = _ResultTableModel(t_all, series, indices)
        self._view.setModel(self._model)

        n_vis = len(indices)
        if x_lo is not None or x_hi is not None:
            self._row_count_lbl.setText(
                f"Day {x_lo:.0f} – {x_hi:.0f}  ({n_vis:,} rows)"
            )
        else:
            self._row_count_lbl.setText(f"{n_vis:,} rows")

    def _copy_to_clipboard(self) -> None:
        """Copy visible table data as tab-separated text to the clipboard."""
        if self._model is None:
            return
        from PyQt6.QtWidgets import QApplication
        lines = []
        # Header
        headers = [
            self._model.headerData(c, Qt.Orientation.Horizontal)
            for c in range(self._model.columnCount())
        ]
        lines.append("\t".join(str(h or "") for h in headers))
        # Rows
        for r in range(self._model.rowCount()):
            row_vals = [
                str(self._model.data(self._model.index(r, c)) or "")
                for c in range(self._model.columnCount())
            ]
            lines.append("\t".join(row_vals))
        QApplication.clipboard().setText("\n".join(lines))


# ── ResultTab ─────────────────────────────────────────────────────────────────

class ResultTab(QWidget):
    """
    One tab's content: SeriesManagerPanel | PlotCanvas / DataTableWidget.
    """

    def __init__(
        self,
        result_element: "TimeHistoryResult",
        results_store:  "ResultsStore",
        graph:          "ModelGraph",
        parent=None,
    ):
        super().__init__(parent)
        self._result_element = result_element
        self._results_store  = results_store
        self._graph          = graph
        self._configs:       list[SeriesConfig] = []

        self._build_configs()

        # ── Layout ────────────────────────────────────────────────────────
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Horizontal splitter: series panel | right content
        from PyQt6.QtWidgets import QSplitter as _HSplit
        self._h_splitter = _HSplit(Qt.Orientation.Horizontal)
        self._h_splitter.setHandleWidth(4)
        self._h_splitter.setChildrenCollapsible(False)
        self._h_splitter.setStyleSheet(
            "QSplitter::handle:horizontal { background: #E7E9EE; "
            "border-left: 1px solid #D5D9E0; }"
            "QSplitter::handle:horizontal:hover { background: #D0D5DE; }"
        )
        root.addWidget(self._h_splitter)

        # Left: series manager
        self._series_panel = SeriesManagerPanel(self._configs)
        self._series_panel.series_changed.connect(self._on_series_changed)
        self._h_splitter.addWidget(self._series_panel)

        # Right container: toggle bar + stacked widget
        right_w = QWidget()
        right_col = QVBoxLayout(right_w)
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.setSpacing(0)
        self._h_splitter.addWidget(right_w)
        self._h_splitter.setSizes([250, 9999])
        self._h_splitter.setStretchFactor(0, 0)
        self._h_splitter.setStretchFactor(1, 1)

        # ── Row 1: View toggle (left) + Legend position (right) ────────
        bar1 = QWidget()
        bar1.setFixedHeight(40)
        bar1.setStyleSheet(
            f"background: #F5F6FA; border-bottom: 1px solid {BORDER_SUBTLE};"
        )
        b1_lay = QHBoxLayout(bar1)
        b1_lay.setContentsMargins(12, 0, 12, 0)
        b1_lay.setSpacing(6)

        self._btn_style_active = (
            "QPushButton { background: #2E86C1; color: white; border: none; "
            "border-radius: 6px; padding: 0 16px; font-weight: 600; font-size: 12px; }"
        )
        self._btn_style_inactive = (
            f"QPushButton {{ background: transparent; color: {TEXT_SECONDARY}; "
            f"border: 1px solid {BORDER_SUBTLE}; border-radius: 6px; "
            f"padding: 0 16px; font-size: 12px; }}"
            f"QPushButton:hover {{ background: #EEF0F4; color: {TEXT_PRIMARY}; }}"
        )

        self._btn_chart = QPushButton("Chart")
        self._btn_table = QPushButton("Data Table")
        for b in (self._btn_chart, self._btn_table):
            b.setFixedHeight(28)
            b.setFont(QFont(FONT_UI, 12))
        self._btn_chart.setStyleSheet(self._btn_style_active)
        self._btn_table.setStyleSheet(self._btn_style_inactive)
        self._btn_chart.clicked.connect(lambda: self._switch_view(0))
        self._btn_table.clicked.connect(lambda: self._switch_view(1))

        b1_lay.addWidget(self._btn_chart)
        b1_lay.addWidget(self._btn_table)
        b1_lay.addStretch()

        # Legend position — right side of row 1
        leg_lbl = QLabel("Legend:")
        leg_lbl.setFont(QFont(FONT_UI, 11))
        leg_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent;")
        b1_lay.addWidget(leg_lbl)

        self._legend_combo = QComboBox()
        self._legend_combo.setFont(QFont(FONT_UI, 11))
        self._legend_combo.setFixedHeight(28)
        self._legend_combo.setFixedWidth(140)
        for display, loc in [
            ("Best (auto)",   "best"),
            ("Upper right",   "upper right"),
            ("Upper left",    "upper left"),
            ("Lower right",   "lower right"),
            ("Lower left",    "lower left"),
            ("Upper centre",  "upper center"),
            ("Lower centre",  "lower center"),
            ("Centre right",  "center right"),
            ("Outside right", "outside right"),
            ("Hidden",        "none"),
        ]:
            self._legend_combo.addItem(display, loc)
        self._legend_combo.setCurrentIndex(0)
        self._legend_combo.currentIndexChanged.connect(self._on_legend_changed)
        b1_lay.addWidget(self._legend_combo)

        right_col.addWidget(bar1)

        # ── Row 2: Axis range controls ──────────────────────────────────
        from PyQt6.QtWidgets import QDoubleSpinBox as _DSB
        bar2 = QWidget()
        bar2.setFixedHeight(44)
        bar2.setStyleSheet(
            f"background: {PANEL_BG}; border-bottom: 1px solid {BORDER_SUBTLE};"
        )
        b2_lay = QHBoxLayout(bar2)
        b2_lay.setContentsMargins(12, 0, 12, 0)
        b2_lay.setSpacing(6)

        def _axis_lbl(text):
            l = QLabel(text)
            l.setFont(QFont(FONT_UI, 11))
            l.setStyleSheet(f"color: {TEXT_PRIMARY}; font-weight: 600; background: transparent;")
            return l

        def _range_lbl(text):
            l = QLabel(text)
            l.setFont(QFont(FONT_UI, 10))
            l.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent;")
            return l

        def _spin(lo, hi, val, dec=1):
            s = _DSB()
            s.setRange(lo, hi)
            s.setDecimals(dec)
            s.setValue(val)
            s.setFixedSize(88, 28)
            s.setFont(QFont(FONT_MONO, 11))
            s.setSpecialValueText("Auto")
            return s

        # Compute data range
        _t0 = float(self._results_store.get_completed_timesteps()[0])
        _t1 = float(self._results_store.get_completed_timesteps()[-1])

        b2_lay.addWidget(_axis_lbl("X Axis:"))
        self._x_lo = _spin(_t0 - 1, _t1 + 1, _t0)
        self._x_hi = _spin(_t0 - 1, _t1 + 1, _t1)
        b2_lay.addWidget(self._x_lo)
        b2_lay.addWidget(_range_lbl("to"))
        b2_lay.addWidget(self._x_hi)

        # Vertical separator
        sep = QWidget(); sep.setFixedSize(1, 24)
        sep.setStyleSheet("background: #D5D9E0;")
        b2_lay.addSpacing(6)
        b2_lay.addWidget(sep)
        b2_lay.addSpacing(6)

        b2_lay.addWidget(_axis_lbl("Y Axis:"))
        self._y_lo = _DSB(); self._y_lo.setRange(-1e9, 1e9)
        self._y_lo.setValue(self._y_lo.minimum()); self._y_lo.setSpecialValueText("Auto")
        self._y_lo.setFixedSize(88, 28); self._y_lo.setFont(QFont(FONT_MONO, 11))
        self._y_hi = _DSB(); self._y_hi.setRange(-1e9, 1e9)
        self._y_hi.setValue(self._y_hi.maximum()); self._y_hi.setSpecialValueText("Auto")
        self._y_hi.setFixedSize(88, 28); self._y_hi.setFont(QFont(FONT_MONO, 11))
        b2_lay.addWidget(self._y_lo)
        b2_lay.addWidget(_range_lbl("to"))
        b2_lay.addWidget(self._y_hi)

        b2_lay.addStretch()

        apply_btn = QPushButton("Apply")
        apply_btn.setFixedSize(64, 28)
        apply_btn.setFont(QFont(FONT_UI, 11))
        apply_btn.setStyleSheet(
            "QPushButton { background: #2E86C1; color: white; border: none; "
            "border-radius: 6px; font-weight: 600; }"
            "QPushButton:hover { background: #2877ad; }"
        )
        apply_btn.clicked.connect(self._apply_range)

        reset_btn = QPushButton("Reset")
        reset_btn.setFixedSize(60, 28)
        reset_btn.setFont(QFont(FONT_UI, 11))
        reset_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {TEXT_SECONDARY}; "
            f"border: 1px solid {BORDER_SUBTLE}; border-radius: 6px; }}"
            f"QPushButton:hover {{ background: #EEF0F4; color: {TEXT_PRIMARY}; }}"
        )
        reset_btn.clicked.connect(self._reset_range)

        b2_lay.addWidget(apply_btn)
        b2_lay.addWidget(reset_btn)
        right_col.addWidget(bar2)

        # Store refs for reset
        self._t0 = _t0
        self._t1 = _t1

        # ── Stacked widget ─────────────────────────────────────────────
        self._stack = QStackedWidget()

        self._plot  = PlotCanvas()
        self._table = DataTableWidget()
        self._stack.addWidget(self._plot)    # index 0 = chart
        self._stack.addWidget(self._table)   # index 1 = table
        self._stack.setCurrentIndex(0)       # chart by default

        right_col.addWidget(self._stack, stretch=1)

        # Initial draw
        self._draw()

    def _on_legend_changed(self, _idx: int = 0) -> None:
        """User selected a new legend position — redraw the chart."""
        self._draw()

    def _get_legend_loc(self) -> str:
        """Return the matplotlib loc string for the current dropdown selection."""
        return self._legend_combo.currentData()

    def _switch_view(self, index: int) -> None:
        """Toggle between chart (0) and data table (1)."""
        self._stack.setCurrentIndex(index)
        if index == 0:
            self._btn_chart.setStyleSheet(self._btn_style_active)
            self._btn_table.setStyleSheet(self._btn_style_inactive)
        else:
            self._btn_chart.setStyleSheet(self._btn_style_inactive)
            self._btn_table.setStyleSheet(self._btn_style_active)
            # Populate table with current X range
            self._refresh_table()

    def _get_range(self) -> tuple[float | None, float | None, float | None, float | None]:
        """Read spin-box values. Returns (x_lo, x_hi, y_lo, y_hi); None = Auto."""
        from PyQt6.QtWidgets import QDoubleSpinBox as _DSB
        x_lo = self._x_lo.value() if self._x_lo.value() != self._x_lo.minimum() else None
        x_hi = self._x_hi.value() if self._x_hi.value() != self._x_hi.maximum() else None
        y_lo = self._y_lo.value() if self._y_lo.value() != self._y_lo.minimum() else None
        y_hi = self._y_hi.value() if self._y_hi.value() != self._y_hi.maximum() else None
        # Use spin values as set (they start at t0/t1, not min/max)
        x_lo = self._x_lo.value()
        x_hi = self._x_hi.value()
        y_lo = None if self._y_lo.value() <= -1e8 else self._y_lo.value()
        y_hi = None if self._y_hi.value() >= 1e8  else self._y_hi.value()
        return x_lo, x_hi, y_lo, y_hi

    def _apply_range(self) -> None:
        """Apply X/Y axis range to both chart and table."""
        x_lo, x_hi, y_lo, y_hi = self._get_range()
        ax = self._plot.ax1

        # X range — chart
        ax.set_xlim(x_lo, x_hi)

        # Y range — chart (left axis)
        if y_lo is not None or y_hi is not None:
            lo = y_lo if y_lo is not None else ax.get_ylim()[0]
            hi = y_hi if y_hi is not None else ax.get_ylim()[1]
            ax.set_ylim(lo, hi)

        self._plot.canvas.draw_idle()

        # Update table with filtered rows
        if self._stack.currentIndex() == 1:
            self._refresh_table()

    def _reset_range(self) -> None:
        """Reset chart to full auto-range and table to full data."""
        # Reset spinboxes
        self._x_lo.setValue(self._t0)
        self._x_hi.setValue(self._t1)
        self._y_lo.setValue(-1e9)
        self._y_hi.setValue(1e9)

        # Reset chart axes
        self._plot.ax1.autoscale()
        self._plot.canvas.draw_idle()

        # Reset table to full range
        if self._stack.currentIndex() == 1:
            time_arr = self._results_store.get_completed_timesteps()
            self._table.set_data(time_arr, self._configs, self._results_store)

    def _refresh_table(self) -> None:
        """Populate the table using the current X range from spinboxes."""
        time_arr = self._results_store.get_completed_timesteps()
        x_lo = self._x_lo.value()
        x_hi = self._x_hi.value()
        # If range == full range, pass None (shows "full range" in header)
        is_full = (abs(x_lo - self._t0) < 0.01 and abs(x_hi - self._t1) < 0.01)
        self._table.set_data(
            time_arr, self._configs, self._results_store,
            x_lo=None if is_full else x_lo,
            x_hi=None if is_full else x_hi,
        )

    def _build_configs(self) -> None:
        """Create a SeriesConfig for each connection feeding this result element."""
        conns = self._graph.get_connections_to(self._result_element.id)
        for i, conn in enumerate(conns):
            try:
                src = self._graph.get_element(conn.from_element_id)
            except KeyError:
                continue
            label = f"{src.name}.{conn.from_port_name}"
            cfg = SeriesConfig(
                element_id=conn.from_element_id,
                port_name=conn.from_port_name,
                label=label,
                colour=_COLOURS[i % len(_COLOURS)],
            )
            self._configs.append(cfg)

    def _draw(self) -> None:
        time_arr   = self._results_store.get_completed_timesteps()
        legend_loc = self._get_legend_loc()
        self._plot.redraw(time_arr, self._configs, self._results_store,
                          self._result_element, legend_loc=legend_loc)
        # Table is populated lazily when user switches to table view

    def _on_series_changed(self) -> None:
        self._draw()

    def refresh(self, results_store: "ResultsStore") -> None:
        self._results_store = results_store
        t = results_store.get_completed_timesteps()
        if len(t):
            self._t0 = float(t[0])
            self._t1 = float(t[-1])
            self._x_lo.setValue(self._t0)
            self._x_hi.setValue(self._t1)
            self._x_lo.setRange(self._t0 - 1, self._t1 + 1)
            self._x_hi.setRange(self._t0 - 1, self._t1 + 1)
        self._draw()

    def export_csv(self, filepath: str) -> None:
        try:
            df = self._results_store.export_dataframe()
            df.to_csv(filepath, index=False, float_format="%.6f")
        except Exception as exc:
            QMessageBox.warning(self, "Export Error", str(exc))


# ── ResultsDashboard ──────────────────────────────────────────────────────────

class ResultsDashboard(QMainWindow):
    """
    Single persistent window — one tab per TimeHistoryResult.
    Stays open across multiple simulation runs; tabs refresh in-place.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("HydroSim — Results")
        self.resize(1140, 700)
        self.setMinimumSize(760, 520)
        self.setStyleSheet(f"QMainWindow {{ background: {PANEL_BG}; }}")

        self._tabs:  dict[str, ResultTab] = {}  # element_id → ResultTab
        self._graph: "ModelGraph | None"  = None

        # Tab widget
        self._tab_widget = QTabWidget()
        self._tab_widget.setTabsClosable(False)
        self._tab_widget.setDocumentMode(True)
        self._tab_widget.setStyleSheet(
            f"QTabWidget::pane {{ border: none; background: {PANEL_BG}; }}"
            f"QTabBar {{ background: #F5F6FA; border-bottom: 2px solid {BORDER_SUBTLE}; }}"
            f"QTabBar::tab {{ background: transparent; color: {TEXT_SECONDARY}; "
            f"  font-family: {FONT_UI}; font-size: 12px; "
            f"  padding: 8px 20px; min-width: 160px; border: none; "
            f"  border-bottom: 3px solid transparent; margin-bottom: -2px; }}"
            f"QTabBar::tab:selected {{ color: #2E86C1; font-weight: 700; "
            f"  border-bottom: 3px solid #2E86C1; background: {PANEL_BG}; }}"
            f"QTabBar::tab:hover:!selected {{ background: #EEF0F4; color: {TEXT_PRIMARY}; }}"
        )
        self.setCentralWidget(self._tab_widget)

        # Status bar
        self._status = QStatusBar()
        self._status.setStyleSheet(
            f"QStatusBar {{ background: #F5F6FA; "
            f"border-top: 1px solid {BORDER_SUBTLE}; font-size: 11px; }}"
        )
        self.setStatusBar(self._status)

        # Menu
        self._build_menu()

    def _build_menu(self) -> None:
        mb = self.menuBar()
        mb.setStyleSheet(f"background: {PANEL_BG};")

        file_menu = mb.addMenu("File")
        file_menu.addAction("Export Current Tab CSV…", self._export_current_csv)
        file_menu.addAction("Export All Tabs CSV…",   self._export_all_csv)
        file_menu.addSeparator()
        file_menu.addAction("Close", self.close)

        view_menu = mb.addMenu("View")
        view_menu.addAction("Zoom to Fit All", self._zoom_fit_all)

    # ── Public API ─────────────────────────────────────────────────────────────

    def show_result(
        self,
        result_element: "TimeHistoryResult",
        results_store:  "ResultsStore",
        graph:          "ModelGraph",
    ) -> None:
        self._graph = graph
        eid = result_element.id

        if eid in self._tabs:
            self._tabs[eid].refresh(results_store)
            self._select_tab(eid)
        else:
            tab = ResultTab(result_element, results_store, graph)
            self._tabs[eid] = tab
            title = result_element.title or result_element.name
            self._tab_widget.addTab(tab, title)
            self._select_tab(eid)

        # Update window title with model name
        n_tabs = len(self._tabs)
        graph_name = getattr(graph, '_model_name', None)
        if graph_name is None:
            # Extract from first element name as a proxy
            names = [el.name for el in graph.elements.values()]
            graph_name = None
        suffix = f"  ({n_tabs} result{'s' if n_tabs != 1 else ''})"
        self.setWindowTitle(f"Results{suffix}")
        self._update_status(results_store)

    def refresh_all(self, results_store: "ResultsStore") -> None:
        for tab in self._tabs.values():
            tab.refresh(results_store)
        self._update_status(results_store)

    def close_all_tabs(self) -> None:
        self._tab_widget.clear()
        self._tabs.clear()

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _select_tab(self, element_id: str) -> None:
        tab = self._tabs.get(element_id)
        if tab:
            idx = self._tab_widget.indexOf(tab)
            if idx >= 0:
                self._tab_widget.setCurrentIndex(idx)

    def _update_status(self, results_store: "ResultsStore") -> None:
        if results_store:
            n   = results_store.completed_steps
            dt  = float(results_store.timesteps[1] - results_store.timesteps[0]) \
                  if len(results_store.timesteps) > 1 else 1.0
            ms  = results_store.run_duration_s * 1000
            tab_n = self._tab_widget.count()
            self._status.showMessage(
                f"  Tab {self._tab_widget.currentIndex()+1} of {tab_n}  "
                f"•  {n:,} steps  "
                f"•  Δt = {dt} day  "
                f"•  {ms:.0f} ms"
            )

    def _current_tab(self) -> ResultTab | None:
        w = self._tab_widget.currentWidget()
        return w if isinstance(w, ResultTab) else None

    def _export_current_csv(self) -> None:
        tab = self._current_tab()
        if not tab:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", "results.csv", "CSV (*.csv)"
        )
        if path:
            tab.export_csv(path)

    def _export_all_csv(self) -> None:
        from pathlib import Path
        dir_path = QFileDialog.getExistingDirectory(self, "Choose export folder")
        if not dir_path:
            return
        for eid, tab in self._tabs.items():
            name = self._tab_widget.tabText(self._tab_widget.indexOf(tab))
            path = str(Path(dir_path) / f"{name}.csv")
            tab.export_csv(path)
        QMessageBox.information(self, "Export Complete",
                                f"Exported {len(self._tabs)} file(s) to:\n{dir_path}")

    def _zoom_fit_all(self) -> None:
        tab = self._current_tab()
        if tab:
            tab._plot.ax1.autoscale()
            tab._plot.canvas.draw_idle()


# ── ResultWindowManager (backward-compatible wrapper) ─────────────────────────

class ResultWindowManager:
    """
    Thin wrapper used by MainWindow.
    Maintains a single ResultsDashboard and routes show/refresh calls to it.
    """

    def __init__(self):
        self._dashboard: ResultsDashboard | None = None

    def show_result(
        self,
        result_element: "TimeHistoryResult",
        results_store:  "ResultsStore",
        graph:          "ModelGraph",
        parent=None,
    ) -> ResultsDashboard:
        if self._dashboard is None:
            self._dashboard = ResultsDashboard(parent)

        self._dashboard.show_result(result_element, results_store, graph)
        self._dashboard.show()
        self._dashboard.raise_()
        self._dashboard.activateWindow()
        return self._dashboard

    def refresh_all(self, results_store: "ResultsStore") -> None:
        if self._dashboard and self._dashboard.isVisible():
            self._dashboard.refresh_all(results_store)

    def close_all(self) -> None:
        if self._dashboard:
            self._dashboard.close_all_tabs()
            self._dashboard.close()
            self._dashboard = None
