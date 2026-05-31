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

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QCheckBox, QColorDialog, QComboBox, QFileDialog, QHBoxLayout,
    QHeaderView, QLabel, QMainWindow, QMessageBox, QPushButton,
    QScrollArea, QSizePolicy, QStackedWidget, QStatusBar,
    QTabWidget, QTableWidget, QTableWidgetItem,
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
    "axes.labelsize":      10,
    "axes.labelweight":    "bold",
    "axes.titlesize":      11,
    "axes.titleweight":    "bold",
    "axes.grid":           True,
    "grid.color":          "#EEEEEE",
    "grid.linewidth":      0.8,
    "xtick.color":         "#1A1A2E",
    "ytick.color":         "#1A1A2E",
    "xtick.labelsize":     9,
    "ytick.labelsize":     9,
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

        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 3, 6, 3)
        lay.setSpacing(6)

        # Visibility checkbox
        self._cb = QCheckBox()
        self._cb.setChecked(config.visible)
        self._cb.setFixedWidth(18)
        self._cb.toggled.connect(self._on_toggle)
        lay.addWidget(self._cb)

        # Series label (truncated)
        lbl = QLabel(config.label)
        lbl.setFont(QFont(FONT_MONO, 9))
        lbl.setStyleSheet(f"color: {TEXT_PRIMARY};")
        lbl.setToolTip(config.label)
        lay.addWidget(lbl, stretch=1)

        # Axis assignment dropdown
        self._axis_combo = QComboBox()
        self._axis_combo.addItems(["Left", "Right"])
        self._axis_combo.setCurrentText("Left" if config.axis == "left" else "Right")
        self._axis_combo.setFixedWidth(60)
        self._axis_combo.setFont(QFont(FONT_UI, 9))
        self._axis_combo.currentTextChanged.connect(self._on_axis_change)
        lay.addWidget(self._axis_combo)

        # Colour swatch button
        self._colour_btn = QPushButton()
        self._colour_btn.setFixedSize(20, 20)
        self._colour_btn.setStyleSheet(
            f"background: {config.colour}; border: 1px solid #CCCCCC; border-radius: 3px;"
        )
        self._colour_btn.setToolTip("Change colour")
        self._colour_btn.clicked.connect(self._pick_colour)
        lay.addWidget(self._colour_btn)

    def _on_toggle(self, checked: bool) -> None:
        self.config.visible = checked
        self.changed.emit()

    def _on_axis_change(self, text: str) -> None:
        self.config.axis = "left" if text == "Left" else "right"
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
        self.setFixedWidth(250)
        self.setStyleSheet(
            f"background: {PANEL_BG}; border-right: 1px solid {BORDER_SUBTLE};"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        hdr = QLabel("  Series")
        hdr.setFixedHeight(28)
        hdr.setFont(QFont(FONT_UI, 10))
        hdr.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-weight: 600; "
            f"background: #F5F6FA; border-bottom: 1px solid {BORDER_SUBTLE};"
        )
        root.addWidget(hdr)

        # Sub-header
        sub = QWidget()
        sub_lay = QHBoxLayout(sub)
        sub_lay.setContentsMargins(6, 2, 6, 2)
        sub_lay.setSpacing(0)
        for text, width in [("", 24), ("Name", 0), ("Axis", 60), ("", 26)]:
            l = QLabel(text)
            l.setFont(QFont(FONT_UI, 8))
            l.setStyleSheet(f"color: {TEXT_SECONDARY};")
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
        self.fig.subplots_adjust(left=0.09, right=0.91, top=0.93, bottom=0.10)

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
        time_arr:      np.ndarray,
        configs:       list[SeriesConfig],
        results_store: "ResultsStore",
        result_element: "TimeHistoryResult",
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
        self.ax1.set_ylabel(y_label or "Value")
        self.ax1.set_xlabel("Time (days)")

        if has_right:
            self.ax2.set_ylabel("Secondary axis")

        # Title
        title = result_element.title or result_element.name
        self.ax1.set_title(title)

        # Manual Y-range
        if result_element.y_min is not None:
            self.ax1.set_ylim(bottom=result_element.y_min)
        if result_element.y_max is not None:
            self.ax1.set_ylim(top=result_element.y_max)

        # Legend — combine both axes
        if lines_for_legend:
            self.ax1.legend(
                handles=lines_for_legend,
                loc="best",
                framealpha=0.85,
                edgecolor="#DDDDDD",
            )

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


# ── DataTableWidget ───────────────────────────────────────────────────────────

class DataTableWidget(QWidget):
    """
    Full-range data table — shows every completed timestep.
    Populated once when set_data() is called; no xlim sync needed.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {PANEL_BG};")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header bar
        hdr = QWidget()
        hdr.setFixedHeight(30)
        hdr.setStyleSheet(
            f"background: #F5F6FA; border-bottom: 1px solid {BORDER_SUBTLE};"
        )
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(10, 0, 10, 0)
        title_lbl = QLabel("Data Table — full simulation range")
        title_lbl.setFont(QFont(FONT_UI, 9))
        title_lbl.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-weight: 600; background: transparent;"
        )
        hdr_lay.addWidget(title_lbl)
        hdr_lay.addStretch()
        self._row_count_lbl = QLabel()
        self._row_count_lbl.setFont(QFont(FONT_MONO, 9))
        self._row_count_lbl.setStyleSheet(
            f"color: {TEXT_SECONDARY}; background: transparent;"
        )
        hdr_lay.addWidget(self._row_count_lbl)
        root.addWidget(hdr)

        # Table
        self._table = QTableWidget()
        self._table.setAlternatingRowColors(True)
        self._table.setFont(QFont(FONT_MONO, 9))
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.setStyleSheet(
            f"QTableWidget {{ border: none; background: white; "
            f"alternate-background-color: #F9FAFB; gridline-color: #F0F1F5; }}"
            f"QHeaderView::section {{ background: #F5F6FA; color: {TEXT_PRIMARY}; "
            f"font-weight: 600; border: none; "
            f"border-bottom: 1px solid {BORDER_SUBTLE}; padding: 4px 8px; }}"
        )
        root.addWidget(self._table, stretch=1)

    def set_data(
        self,
        time_arr:      np.ndarray,
        configs:       list[SeriesConfig],
        results_store: "ResultsStore",
    ) -> None:
        """Populate with all completed timesteps."""
        if time_arr is None or results_store is None:
            return

        n       = results_store.completed_steps
        t_all   = time_arr[:n]
        visible = [c for c in configs if c.visible]

        cols = ["Time (days)"] + [c.label for c in visible]
        self._table.setColumnCount(len(cols))
        self._table.setHorizontalHeaderLabels(cols)
        self._table.setRowCount(n)

        for row, t in enumerate(t_all):
            self._table.setItem(row, 0, QTableWidgetItem(f"{t:.2f}"))

        for ci, cfg in enumerate(visible):
            try:
                arr = results_store.get_series(cfg.element_id, cfg.port_name)
            except KeyError:
                continue
            for row in range(n):
                item = QTableWidgetItem(f"{arr[row]:.4f}")
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
                self._table.setItem(row, 1 + ci, item)

        self._row_count_lbl.setText(f"{n} rows")


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
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Left: series manager
        self._series_panel = SeriesManagerPanel(self._configs)
        self._series_panel.series_changed.connect(self._on_series_changed)
        root.addWidget(self._series_panel)

        # Right: toggle bar + stacked widget
        right_col = QVBoxLayout()
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.setSpacing(0)

        # ── Toggle bar ─────────────────────────────────────────────────
        toggle_bar = QWidget()
        toggle_bar.setFixedHeight(34)
        toggle_bar.setStyleSheet(
            f"background: #F5F6FA; border-bottom: 1px solid {BORDER_SUBTLE};"
        )
        tb_lay = QHBoxLayout(toggle_bar)
        tb_lay.setContentsMargins(10, 0, 10, 0)
        tb_lay.setSpacing(4)

        btn_style_active = (
            f"QPushButton {{ background: #2E86C1; color: white; border: none; "
            f"border-radius: 5px; padding: 3px 14px; font-weight: 600; font-size: 11px; }}"
        )
        btn_style_inactive = (
            f"QPushButton {{ background: transparent; color: {TEXT_SECONDARY}; "
            f"border: 1px solid {BORDER_SUBTLE}; border-radius: 5px; "
            f"padding: 3px 14px; font-size: 11px; }}"
            f"QPushButton:hover {{ background: #EEF0F4; color: {TEXT_PRIMARY}; }}"
        )

        self._btn_chart = QPushButton("Chart")
        self._btn_table = QPushButton("Data Table")
        for b in (self._btn_chart, self._btn_table):
            b.setFixedHeight(24)
            b.setFont(QFont(FONT_UI, 11))
        self._btn_chart.setStyleSheet(btn_style_active)
        self._btn_table.setStyleSheet(btn_style_inactive)
        self._btn_chart.clicked.connect(lambda: self._switch_view(0))
        self._btn_table.clicked.connect(lambda: self._switch_view(1))

        tb_lay.addWidget(self._btn_chart)
        tb_lay.addWidget(self._btn_table)
        tb_lay.addStretch()
        right_col.addWidget(toggle_bar)

        # ── Stacked widget ─────────────────────────────────────────────
        self._stack = QStackedWidget()

        self._plot  = PlotCanvas()
        self._table = DataTableWidget()
        self._stack.addWidget(self._plot)    # index 0 = chart
        self._stack.addWidget(self._table)   # index 1 = table
        self._stack.setCurrentIndex(0)       # chart by default

        right_col.addWidget(self._stack, stretch=1)

        right_w = QWidget()
        right_w.setLayout(right_col)
        root.addWidget(right_w, stretch=1)

        self._btn_style_active   = btn_style_active
        self._btn_style_inactive = btn_style_inactive

        # Initial draw
        self._draw()

    def _switch_view(self, index: int) -> None:
        """Toggle between chart (0) and data table (1)."""
        self._stack.setCurrentIndex(index)
        if index == 0:
            self._btn_chart.setStyleSheet(self._btn_style_active)
            self._btn_table.setStyleSheet(self._btn_style_inactive)
        else:
            self._btn_chart.setStyleSheet(self._btn_style_inactive)
            self._btn_table.setStyleSheet(self._btn_style_active)
            # Populate table with full data when switching to table view
            time_arr = self._results_store.get_completed_timesteps()
            self._table.set_data(time_arr, self._configs, self._results_store)

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
        time_arr = self._results_store.get_completed_timesteps()
        self._plot.redraw(time_arr, self._configs, self._results_store,
                          self._result_element)
        # Table is populated lazily when user switches to table view

    def _on_series_changed(self) -> None:
        self._draw()

    def refresh(self, results_store: "ResultsStore") -> None:
        self._results_store = results_store
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
        self.resize(1000, 620)
        self.setMinimumSize(700, 480)
        self.setStyleSheet(f"QMainWindow {{ background: {PANEL_BG}; }}")

        self._tabs:  dict[str, ResultTab] = {}  # element_id → ResultTab
        self._graph: "ModelGraph | None"  = None

        # Tab widget
        self._tab_widget = QTabWidget()
        self._tab_widget.setTabsClosable(False)
        self._tab_widget.setStyleSheet(
            f"QTabBar::tab {{ padding: 6px 16px; font-family: {FONT_UI}; font-size: 12px; }}"
            f"QTabBar::tab:selected {{ font-weight: 600; }}"
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
            # Refresh existing tab
            self._tabs[eid].refresh(results_store)
            self._select_tab(eid)
        else:
            # Create new tab
            tab = ResultTab(result_element, results_store, graph)
            self._tabs[eid] = tab
            title = result_element.title or result_element.name
            self._tab_widget.addTab(tab, title)
            self._select_tab(eid)

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
            n  = results_store.completed_steps
            dt = float(results_store.timesteps[1] - results_store.timesteps[0]) \
                 if len(results_store.timesteps) > 1 else 1.0
            self._status.showMessage(
                f"  {n} steps  ·  dt = {dt} day  ·  "
                f"{results_store.run_duration_s*1000:.0f} ms"
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
