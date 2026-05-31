"""
HydrographWindow — floating result viewer.

Opens when the user double-clicks a TimeHistoryResult element after simulation.
Non-modal: multiple windows can be open simultaneously.
Uses PyQtGraph for interactive display; Matplotlib for PNG export.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import QPoint, QPointF, Qt
from PyQt6.QtGui import QColor, QFont, QMouseEvent
from PyQt6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from hydrosim.gui.styles.theme import (
    BORDER_SUBTLE, CAT_RESULT, FONT_MONO, FONT_UI,
    PANEL_BG, SEL_BLUE, TEXT_PRIMARY, TEXT_SECONDARY,
)

if TYPE_CHECKING:
    from hydrosim.engine.results import ResultsStore
    from hydrosim.model.elements.timehistory import TimeHistoryResult
    from hydrosim.model.graph import ModelGraph

# Colour palette for series lines (up to 8)
_LINE_COLOURS = [
    "#2E86C1",  # Ocean Blue
    "#E8633A",  # Coral Orange
    "#4CAF82",  # Leaf Green
    "#7B68C8",  # Slate Purple
    "#E8A020",  # Amber
    "#00897B",  # Teal
    "#E53935",  # Red
    "#795548",  # Brown
]


# ── Title bar (draggable) ─────────────────────────────────────────────────────

class _TitleBar(QWidget):
    """Draggable title bar for the floating result window."""

    def __init__(self, title: str, parent: "HydrographWindow"):
        super().__init__(parent)
        self._win      = parent
        self._dragging = False
        self._drag_pos = QPoint()

        self.setFixedHeight(40)
        self.setStyleSheet(
            f"background: {PANEL_BG}; border-bottom: 1px solid #EEF0F4;"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 10, 0)
        lay.setSpacing(10)

        # Orange dot indicator (result element colour)
        dot = QLabel("●")
        dot.setFont(QFont(FONT_UI, 9))
        dot.setStyleSheet(f"color: {CAT_RESULT}; background: transparent;")
        lay.addWidget(dot)

        # Title
        self._title_lbl = QLabel(title)
        self._title_lbl.setFont(QFont(FONT_UI, 13))
        self._title_lbl.setStyleSheet(f"font-weight: 700; color: {TEXT_PRIMARY}; background: transparent;")
        lay.addWidget(self._title_lbl, stretch=1)

        # Export CSV
        self._export_btn = QPushButton("Export CSV")
        self._export_btn.setFixedHeight(26)
        self._export_btn.setFont(QFont(FONT_UI, 11))
        self._export_btn.setStyleSheet(
            f"QPushButton {{ border: 1px solid {BORDER_SUBTLE}; border-radius: 5px; "
            f"background: {PANEL_BG}; color: {TEXT_PRIMARY}; padding: 0 10px; }}"
            f"QPushButton:hover {{ background: #EEF0F4; }}"
        )
        lay.addWidget(self._export_btn)

        # Close
        close_btn = QPushButton("×")
        close_btn.setFixedSize(26, 26)
        close_btn.setFont(QFont(FONT_UI, 14))
        close_btn.setStyleSheet(
            f"QPushButton {{ border: none; background: transparent; color: {TEXT_SECONDARY}; "
            f"border-radius: 6px; }}"
            f"QPushButton:hover {{ background: #EEF0F4; color: {TEXT_PRIMARY}; }}"
        )
        close_btn.clicked.connect(parent.hide)
        lay.addWidget(close_btn)

        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def set_title(self, title: str) -> None:
        self._title_lbl.setText(title)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_pos = event.globalPosition().toPoint() - self._win.frameGeometry().topLeft()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging:
            new_pos = event.globalPosition().toPoint() - self._drag_pos
            # Clamp to screen
            new_pos.setX(max(0, new_pos.x()))
            new_pos.setY(max(0, new_pos.y()))
            self._win.move(new_pos)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._dragging = False
        self.setCursor(Qt.CursorShape.OpenHandCursor)


# ── Legend row ────────────────────────────────────────────────────────────────

class _LegendWidget(QWidget):
    """Horizontal row of colour swatches + series names."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(14, 4, 14, 2)
        self._layout.setSpacing(16)
        self._layout.addStretch()
        self.setFixedHeight(26)

    def clear(self) -> None:
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def add_series(self, label: str, colour: str) -> None:
        row = QWidget()
        rlay = QHBoxLayout(row)
        rlay.setContentsMargins(0, 0, 0, 0)
        rlay.setSpacing(5)

        swatch = QLabel("━━")
        swatch.setFont(QFont(FONT_UI, 11))
        swatch.setStyleSheet(f"color: {colour};")
        rlay.addWidget(swatch)

        name = QLabel(label)
        name.setFont(QFont(FONT_MONO, 11))
        name.setStyleSheet(f"color: {TEXT_PRIMARY};")
        rlay.addWidget(name)

        # Insert before the stretch
        self._layout.insertWidget(self._layout.count() - 1, row)


# ── Chart toolbar ─────────────────────────────────────────────────────────────

class _ChartToolbar(QWidget):
    """Bottom toolbar: zoom/pan/home/save PNG + meta text."""

    def __init__(self, plot_widget: pg.PlotWidget, parent=None):
        super().__init__(parent)
        self._plot = plot_widget
        self.setFixedHeight(38)
        self.setStyleSheet(
            f"background: #FBFBFD; border-top: 1px solid #EEF0F4;"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 14, 0)
        lay.setSpacing(4)

        for label, tooltip, slot in [
            ("⌂", "Reset view",    self._reset_view),
            ("🔍+", "Zoom in",     self._zoom_in),
            ("🔍−", "Zoom out",    self._zoom_out),
            ("💾", "Save as PNG",  self._save_png),
        ]:
            btn = self._tbtn(label, tooltip, slot)
            lay.addWidget(btn)

        lay.addWidget(self._separator())

        self._meta_lbl = QLabel()
        self._meta_lbl.setFont(QFont(FONT_MONO, 11))
        self._meta_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent;")
        lay.addWidget(self._meta_lbl)
        lay.addStretch()

    def _tbtn(self, label: str, tip: str, slot) -> QPushButton:
        btn = QPushButton(label)
        btn.setFixedSize(30, 26)
        btn.setFont(QFont(FONT_UI, 11))
        btn.setToolTip(tip)
        btn.setStyleSheet(
            f"QPushButton {{ border: 1px solid {BORDER_SUBTLE}; border-radius: 6px; "
            f"background: {PANEL_BG}; color: {TEXT_SECONDARY}; }}"
            f"QPushButton:hover {{ background: #F4F6F9; color: {TEXT_PRIMARY}; }}"
        )
        btn.clicked.connect(slot)
        return btn

    def _separator(self) -> QWidget:
        d = QWidget(); d.setFixedSize(1, 18)
        d.setStyleSheet("background: #E3E6EC;")
        return d

    def set_meta(self, n_steps: int, dt: float) -> None:
        self._meta_lbl.setText(f"{n_steps} steps · Δt = {dt} day")

    def _reset_view(self) -> None:
        self._plot.getViewBox().autoRange()

    def _zoom_in(self) -> None:
        self._plot.getViewBox().scaleBy((0.7, 0.7))

    def _zoom_out(self) -> None:
        self._plot.getViewBox().scaleBy((1.4, 1.4))

    def _save_png(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Chart as PNG", "hydrograph.png", "PNG (*.png)"
        )
        if path:
            exporter = pg.exporters.ImageExporter(self._plot.plotItem)
            exporter.parameters()["width"] = 1200
            exporter.export(path)


# ── HydrographWindow ──────────────────────────────────────────────────────────

class HydrographWindow(QWidget):
    """
    Floating non-modal window displaying time series from a TimeHistoryResult.

    Usage:
        win = HydrographWindow(result_element, results_store, graph)
        win.show()
    """

    def __init__(
        self,
        result_element: "TimeHistoryResult",
        results_store:  "ResultsStore",
        graph:          "ModelGraph",
        parent:         QWidget | None = None,
    ):
        super().__init__(parent, Qt.WindowType.Window)
        self._result_element = result_element
        self._results_store  = results_store
        self._graph          = graph

        self.setWindowTitle(result_element.title or result_element.name)
        self.resize(800, 500)
        self.setMinimumSize(500, 350)

        self._build_ui()
        self._populate()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Title bar
        title = self._result_element.title or self._result_element.name
        self._titlebar = _TitleBar(title, self)
        self._titlebar._export_btn.clicked.connect(self._export_csv)
        root.addWidget(self._titlebar)

        # Legend
        self._legend = _LegendWidget()
        root.addWidget(self._legend)

        # PyQtGraph plot
        pg.setConfigOption("background", "w")
        pg.setConfigOption("foreground", TEXT_PRIMARY)

        self._plot = pg.PlotWidget()
        self._plot.setBackground("#FFFFFF")
        self._plot.showGrid(x=True, y=True, alpha=0.25)
        self._plot.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._plot.setLabel(
            "left",
            self._result_element.y_axis_label or "Value",
            units=self._result_element.y_axis_units or "-",
            color=TEXT_PRIMARY,
        )
        self._plot.setLabel("bottom", "Time", units="days", color=TEXT_PRIMARY)

        # Style axes
        for axis_name in ("left", "bottom"):
            ax = self._plot.getAxis(axis_name)
            ax.setTextPen(QColor(TEXT_SECONDARY))
            ax.setPen(QColor(BORDER_SUBTLE))
            ax.setTickFont(QFont(FONT_MONO, 9))

        # Manual Y range if specified
        if self._result_element.y_min is not None and self._result_element.y_max is not None:
            self._plot.setYRange(self._result_element.y_min, self._result_element.y_max)

        # Crosshair cursor
        self._vline = pg.InfiniteLine(angle=90, movable=False,
                                      pen=pg.mkPen(color="#AAAAAA", width=1, style=Qt.PenStyle.DashLine))
        self._hline = pg.InfiniteLine(angle=0,  movable=False,
                                      pen=pg.mkPen(color="#AAAAAA", width=1, style=Qt.PenStyle.DashLine))
        self._plot.addItem(self._vline, ignoreBounds=True)
        self._plot.addItem(self._hline, ignoreBounds=True)
        self._coord_label = pg.TextItem(anchor=(0, 1), color=TEXT_SECONDARY)
        self._plot.addItem(self._coord_label)
        self._plot.scene().sigMouseMoved.connect(self._on_mouse_moved)

        root.addWidget(self._plot, stretch=1)

        # Chart toolbar
        self._toolbar = _ChartToolbar(self._plot)
        root.addWidget(self._toolbar)

    # ── Data population ───────────────────────────────────────────────────────

    def _populate(self) -> None:
        """Draw all series connected to this TimeHistoryResult."""
        self._plot.clear()
        self._plot.addItem(self._vline, ignoreBounds=True)
        self._plot.addItem(self._hline, ignoreBounds=True)
        self._plot.addItem(self._coord_label)
        self._legend.clear()

        connections = self._graph.get_connections_to(self._result_element.id)
        time_arr = self._results_store.get_completed_timesteps()
        n_steps  = len(time_arr)

        self._series_data: list[tuple[str, str, np.ndarray]] = []

        for i, conn in enumerate(connections):
            try:
                src_elem = self._graph.get_element(conn.from_element_id)
                arr      = self._results_store.get_series(
                    conn.from_element_id, conn.from_port_name
                )
            except KeyError:
                continue

            label  = f"{src_elem.name}.{conn.from_port_name}"
            colour = _LINE_COLOURS[i % len(_LINE_COLOURS)]

            # Area fill (18% opacity)
            fill_col = QColor(colour)
            fill_col.setAlphaF(0.18)

            curve = self._plot.plot(
                x=time_arr,
                y=arr[:n_steps],
                pen=pg.mkPen(color=colour, width=1.8),
                fillLevel=0,
                brush=pg.mkBrush(fill_col),
                name=label,
            )

            self._series_data.append((label, colour, arr[:n_steps]))
            self._legend.add_series(label, colour)

        dt = float(self._results_store.timesteps[1] - self._results_store.timesteps[0]) \
            if len(self._results_store.timesteps) > 1 else 1.0
        self._toolbar.set_meta(n_steps, dt)

        # Apply grid visibility
        self._plot.showGrid(
            x=self._result_element.show_grid,
            y=self._result_element.show_grid,
            alpha=0.25,
        )

    def refresh(self, results_store: "ResultsStore") -> None:
        """Update with new results (called after re-run)."""
        self._results_store = results_store
        self._populate()

    # ── Crosshair + tooltip ───────────────────────────────────────────────────

    def _on_mouse_moved(self, pos: QPointF) -> None:
        if not self._plot.sceneBoundingRect().contains(pos):
            return
        mp = self._plot.getPlotItem().vb.mapSceneToView(pos)
        self._vline.setPos(mp.x())
        self._hline.setPos(mp.y())

        # Show nearest value
        if self._series_data:
            label, _, arr = self._series_data[0]
            time_arr = self._results_store.get_completed_timesteps()
            idx = int(np.clip(np.searchsorted(time_arr, mp.x()), 0, len(arr)-1))
            t   = time_arr[idx] if idx < len(time_arr) else mp.x()
            v   = arr[idx]      if idx < len(arr)       else mp.y()
            self._coord_label.setText(f"t={t:.1f}  {v:.4g}", color=TEXT_SECONDARY)
            self._coord_label.setPos(mp.x(), mp.y())

    # ── Export CSV ────────────────────────────────────────────────────────────

    def _export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", "results.csv", "CSV files (*.csv)"
        )
        if not path:
            return
        try:
            df = self._results_store.export_dataframe()
            df.to_csv(path, index=False, float_format="%.6f")
            QMessageBox.information(self, "Export Complete", f"Saved to:\n{path}")
        except Exception as exc:
            QMessageBox.warning(self, "Export Error", str(exc))


# ── ResultWindowManager ───────────────────────────────────────────────────────

class ResultWindowManager:
    """
    Tracks open HydrographWindows.
    MainWindow uses this to show/reuse windows and update them after re-run.
    """

    def __init__(self):
        self._windows: dict[str, HydrographWindow] = {}  # element_id → window

    def show_result(
        self,
        result_element: "TimeHistoryResult",
        results_store:  "ResultsStore",
        graph:          "ModelGraph",
        parent:         QWidget | None = None,
    ) -> HydrographWindow:
        eid = result_element.id
        if eid in self._windows and not self._windows[eid].isHidden():
            win = self._windows[eid]
            win.refresh(results_store)
            win.raise_()
            win.activateWindow()
            return win

        win = HydrographWindow(result_element, results_store, graph, parent)
        self._windows[eid] = win
        win.show()
        return win

    def refresh_all(self, results_store: "ResultsStore") -> None:
        """Called after every simulation re-run."""
        for win in self._windows.values():
            if not win.isHidden():
                win.refresh(results_store)

    def close_all(self) -> None:
        for win in self._windows.values():
            win.close()
        self._windows.clear()
