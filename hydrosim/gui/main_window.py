"""
MainWindow — the top-level application window.
Contains menu bar, toolbar, palette + canvas body, and status bar.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QAction, QColor, QFont, QIcon, QPainter, QPainterPath,
    QKeySequence, QPixmap,
)
from PyQt6.QtWidgets import (
    QApplication, QDockWidget, QFileDialog, QHBoxLayout, QLabel,
    QMainWindow, QMenuBar, QMessageBox, QPushButton,
    QSizePolicy, QStatusBar, QTextEdit, QToolBar,
    QVBoxLayout, QWidget,
)

from hydrosim.gui.simulation_thread import SimulationThread
from hydrosim.model.base import SimulationSettings
from hydrosim.model.graph import ModelGraph

from hydrosim.gui.styles.theme import (
    APP_BG, BORDER_SUBTLE, CAT_INPUT, CAT_STOCK, CAT_EXPR, CAT_RESULT,
    ERR_RED, OK_GREEN, PANEL_BG, SEL_BLUE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_FAINT,
    FONT_UI, FONT_MONO,
    MENUBAR_HEIGHT, TOOLBAR_HEIGHT, STATUSBAR_HEIGHT, PALETTE_WIDTH,
    APP_MIN_WIDTH,
)


# ── Water-drop logo painter ───────────────────────────────────────────────────

def _make_logo_pixmap(size: int, colour: str = SEL_BLUE) -> QPixmap:
    """Paint the HydroSim water-drop logo at the given pixel size."""
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p  = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    s    = size / 16.0
    path.moveTo(8*s, 1.5*s)
    path.cubicTo(8*s, 1.5*s, 13*s, 7*s, 13*s, 10.4*s)
    path.arcTo(3*s, 5.4*s, 10*s, 10*s, 0, -180)
    path.cubicTo(3*s, 7*s, 8*s, 1.5*s, 8*s, 1.5*s)
    path.closeSubpath()
    p.fillPath(path, QColor(colour))
    p.end()
    return px


# ── Toolbar ───────────────────────────────────────────────────────────────────

class _Toolbar(QWidget):
    """48px toolbar: file buttons | divider | Run | Stop | spacer | meta text."""

    run_clicked  = pyqtSignal()
    stop_clicked = pyqtSignal()
    new_clicked  = pyqtSignal()
    open_clicked = pyqtSignal()
    save_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(TOOLBAR_HEIGHT)
        self.setObjectName("toolbar")
        self.setStyleSheet(
            f"#toolbar {{ background: {PANEL_BG}; "
            f"border-bottom: 1px solid {BORDER_SUBTLE}; }}"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(6)

        # File buttons
        self._btn_new  = self._file_btn("New",  "Ctrl+N")
        self._btn_open = self._file_btn("Open", "Ctrl+O")
        self._btn_save = self._file_btn("Save", "Ctrl+S")
        for btn in (self._btn_new, self._btn_open, self._btn_save):
            layout.addWidget(btn)

        layout.addWidget(self._divider())

        # Run / Stop
        self._btn_run  = self._run_btn()
        self._btn_stop = self._stop_btn()
        layout.addWidget(self._btn_run)
        layout.addWidget(self._btn_stop)

        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(spacer)

        # Meta text (right side)
        self._meta_label = QLabel("Δt = 1 day · 365 steps")
        self._meta_label.setFont(QFont(FONT_MONO, 12))
        self._meta_label.setStyleSheet(f"color: {TEXT_SECONDARY};")
        layout.addWidget(self._meta_label)

        # Progress bar (2px strip at bottom, hidden initially)
        self._progress_bar = QWidget(self)
        self._progress_bar.setFixedHeight(2)
        self._progress_bar.setStyleSheet(f"background: {SEL_BLUE};")
        self._progress_bar.hide()
        self._progress_pct: float = 0.0

        self._btn_new.clicked.connect(self.new_clicked)
        self._btn_open.clicked.connect(self.open_clicked)
        self._btn_save.clicked.connect(self.save_clicked)
        self._btn_run.clicked.connect(self.run_clicked)
        self._btn_stop.clicked.connect(self.stop_clicked)

    def _file_btn(self, label: str, shortcut: str) -> QPushButton:
        btn = QPushButton(label)
        btn.setFixedHeight(32)
        btn.setFont(QFont(FONT_UI, 13))
        btn.setStyleSheet(
            f"QPushButton {{ border: 1px solid #E2E5EB; border-radius: 7px; "
            f"background: {PANEL_BG}; color: {TEXT_PRIMARY}; "
            f"font-weight: 500; padding: 0 12px; }}"
            f"QPushButton:hover {{ background: #F4F6F9; border-color: #D5D9E0; }}"
        )
        return btn

    def _run_btn(self) -> QPushButton:
        btn = QPushButton("▶  Run")
        btn.setFixedHeight(32)
        btn.setFont(QFont(FONT_UI, 13))
        btn.setStyleSheet(
            f"QPushButton {{ background: {OK_GREEN}; border: 1px solid {OK_GREEN}; "
            f"border-radius: 7px; color: white; font-weight: 600; padding: 0 16px; }}"
            f"QPushButton:hover {{ background: #3d9242; }}"
            f"QPushButton:disabled {{ background: #A8D5AB; border-color: #A8D5AB; }}"
        )
        return btn

    def _stop_btn(self) -> QPushButton:
        btn = QPushButton("■  Stop")
        btn.setFixedHeight(32)
        btn.setEnabled(False)
        btn.setFont(QFont(FONT_UI, 13))
        btn.setStyleSheet(
            f"QPushButton {{ color: {ERR_RED}; border: 1px solid #F0C6C5; "
            f"background: #FFF6F6; border-radius: 7px; font-weight: 600; padding: 0 16px; }}"
            f"QPushButton:hover {{ background: #FDECEC; }}"
            f"QPushButton:disabled {{ color: #C9B6B6; border-color: #ECEEF2; background: #FAFBFC; }}"
        )
        return btn

    def _divider(self) -> QWidget:
        d = QWidget()
        d.setFixedSize(1, 24)
        d.setStyleSheet("background: #E3E6EC;")
        return d

    def set_simulation_state(self, state: str, step: int = 0, total: int = 365) -> None:
        """state: 'idle' | 'running' | 'complete' | 'stopped'"""
        if state == "running":
            self._btn_run.setEnabled(False)
            self._btn_run.setText("Running…")
            self._btn_stop.setEnabled(True)
            self._progress_bar.show()
        else:
            self._btn_run.setEnabled(True)
            self._btn_run.setText("▶  Run")
            self._btn_stop.setEnabled(False)
            self._progress_bar.hide()

    def set_progress(self, fraction: float) -> None:
        self._progress_pct = max(0.0, min(1.0, fraction))
        w = int(self.width() * self._progress_pct)
        self._progress_bar.setGeometry(0, self.height() - 2, w, 2)

    def update_meta(self, dt: float, n_steps: int) -> None:
        self._meta_label.setText(f"Δt = {dt} day · {n_steps} steps")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.set_progress(self._progress_pct)


# ── Status bar ────────────────────────────────────────────────────────────────

class _StatusBar(QWidget):
    """28px status bar: [logo+name+count] [status pill] [zoom control]."""

    zoom_in_clicked  = pyqtSignal()
    zoom_out_clicked = pyqtSignal()
    zoom_reset_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(STATUSBAR_HEIGHT)
        self.setObjectName("statusbar")
        self.setStyleSheet(
            f"#statusbar {{ background: {PANEL_BG}; "
            f"border-top: 1px solid {BORDER_SUBTLE}; }}"
        )

        outer = QHBoxLayout(self)
        outer.setContentsMargins(14, 0, 14, 0)
        outer.setSpacing(0)

        # ── Left: logo + model name + element count ────────────────────────
        left = QWidget()
        left_layout = QHBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(7)

        self._logo_lbl = QLabel()
        self._logo_lbl.setPixmap(_make_logo_pixmap(13, SEL_BLUE))
        left_layout.addWidget(self._logo_lbl)

        self._model_name_lbl = QLabel("Untitled")
        self._model_name_lbl.setFont(QFont(FONT_UI, 11))
        self._model_name_lbl.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-weight: 600;"
        )
        left_layout.addWidget(self._model_name_lbl)

        dot = QLabel("·")
        dot.setStyleSheet(f"color: {TEXT_FAINT};")
        left_layout.addWidget(dot)

        self._element_count_lbl = QLabel("0 elements")
        self._element_count_lbl.setFont(QFont(FONT_MONO, 11))
        self._element_count_lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
        left_layout.addWidget(self._element_count_lbl)

        outer.addWidget(left)

        # ── Centre: status pill (absolute position) ────────────────────────
        outer.addStretch(1)
        self._pill = QLabel("Ready")
        self._pill.setFont(QFont(FONT_UI, 11))
        self._pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._pill.setStyleSheet(
            "padding: 2px 11px; border-radius: 10px; font-weight: 600; "
            f"background: #F0F1F5; color: {TEXT_SECONDARY};"
        )
        outer.addWidget(self._pill)
        outer.addStretch(1)

        # ── Right: zoom control ────────────────────────────────────────────
        right = QWidget()
        right_layout = QHBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(2)

        self._zoom_out_btn = self._zoom_btn("−")
        self._zoom_pct_lbl  = QLabel("100%")
        self._zoom_pct_lbl.setFixedWidth(40)
        self._zoom_pct_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._zoom_pct_lbl.setFont(QFont(FONT_MONO, 11))
        self._zoom_pct_lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
        self._zoom_in_btn  = self._zoom_btn("+")

        self._zoom_out_btn.clicked.connect(self.zoom_out_clicked)
        self._zoom_in_btn.clicked.connect(self.zoom_in_clicked)
        self._zoom_pct_lbl.mousePressEvent = lambda _: self.zoom_reset_clicked.emit()

        for w in (self._zoom_out_btn, self._zoom_pct_lbl, self._zoom_in_btn):
            right_layout.addWidget(w)
        outer.addWidget(right)

    def _zoom_btn(self, label: str) -> QPushButton:
        btn = QPushButton(label)
        btn.setFixedSize(18, 18)
        btn.setFont(QFont(FONT_UI, 11))
        btn.setStyleSheet(
            f"QPushButton {{ border: none; background: transparent; "
            f"color: {TEXT_SECONDARY}; border-radius: 4px; }}"
            f"QPushButton:hover {{ background: #EEF0F4; color: {TEXT_PRIMARY}; }}"
        )
        return btn

    def set_model_name(self, name: str) -> None:
        self._model_name_lbl.setText(name)

    def set_element_count(self, n: int) -> None:
        self._element_count_lbl.setText(f"{n} element{'s' if n != 1 else ''}")

    def set_zoom(self, pct: int) -> None:
        self._zoom_pct_lbl.setText(f"{pct}%")

    def set_sim_state(self, state: str, detail: str = "") -> None:
        styles = {
            "idle":     (f"background:#F0F1F5; color:{TEXT_SECONDARY};", "Ready"),
            "running":  (f"background:#E3F0FA; color:{SEL_BLUE};",       "Running…"),
            "complete": (f"background:#E8F5E9; color:{OK_GREEN};",        "Complete"),
            "stopped":  (f"background:#F0F1F5; color:{TEXT_SECONDARY};",  "Stopped"),
            "error":    (f"background:#FEF2F2; color:{ERR_RED};",          "Error"),
        }
        style, default_text = styles.get(state, styles["idle"])
        text = detail if detail else default_text
        self._pill.setStyleSheet(
            f"padding: 2px 11px; border-radius: 10px; font-weight: 600; {style}"
        )
        self._pill.setText(text)


# ── Simulation log dock ───────────────────────────────────────────────────────

class _SimLogDock(QDockWidget):
    """Dockable simulation log panel (bottom, hidden by default)."""

    def __init__(self, parent: QMainWindow):
        super().__init__("Simulation Log", parent)
        self.setObjectName("sim_log_dock")
        self.setAllowedAreas(
            Qt.DockWidgetArea.BottomDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setFont(QFont(FONT_MONO, 11))
        self._text.setStyleSheet(
            f"background: {PANEL_BG}; color: {TEXT_PRIMARY}; "
            f"border: none; padding: 8px;"
        )
        self.setWidget(self._text)
        self.setMinimumHeight(120)

    def append(self, message: str) -> None:
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        self._text.append(f"[{ts}] {message}")

    def clear_log(self) -> None:
        self._text.clear()


# ── MainWindow ────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    """
    Top-level application window.

    Layout (top to bottom):
      MenuBar   (32px, managed by QMainWindow)
      _Toolbar  (48px)
      Body      (flex: palette 200px | canvas)
      _StatusBar (28px)
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("HydroSim — Untitled")
        self.setMinimumSize(APP_MIN_WIDTH, 768)

        # Model state
        self._model_path:   Path | None = None
        self._modified:     bool        = False
        self._sim_settings  = SimulationSettings(0.0, 365.0, 1.0, "elapsed", None)
        self._results_store = None
        self._sim_thread    = None

        # Debug mode — off by default
        self._debug_mode:     bool = False
        self._debug_interval: int  = 10   # log snapshot every 10% of steps

        from hydrosim.gui.results.hydrograph_widget import ResultWindowManager
        self._result_mgr = ResultWindowManager()

        self._setup_ui()
        self._setup_menus()
        self._connect_signals()

    # ── UI construction ───────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        # Central widget
        central = QWidget()
        central.setObjectName("central_widget")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Toolbar
        self._toolbar = _Toolbar()
        root.addWidget(self._toolbar)

        # Stale-results banner (hidden by default)
        self._stale_banner = QWidget()
        self._stale_banner.setFixedHeight(28)
        self._stale_banner.setStyleSheet(
            "background: #FFF8E1; border-bottom: 1px solid #FFE082;"
        )
        sb_lay = QHBoxLayout(self._stale_banner)
        sb_lay.setContentsMargins(12, 0, 12, 0)
        _sb_lbl = QLabel("⚠  Model changed since last run — results may be out of date.")
        _sb_lbl.setFont(QFont(FONT_UI, 11))
        _sb_lbl.setStyleSheet("color: #795500; background: transparent;")
        sb_lay.addWidget(_sb_lbl)
        sb_lay.addStretch()
        _run_now = QPushButton("Run Now")
        _run_now.setFixedHeight(20)
        _run_now.setFont(QFont(FONT_UI, 10))
        _run_now.clicked.connect(self._on_run)
        sb_lay.addWidget(_run_now)
        self._stale_banner.setVisible(False)
        root.addWidget(self._stale_banner)

        # Body: palette + canvas
        body = QWidget()
        body.setObjectName("body")
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self._palette_panel = self._build_palette_placeholder()
        body_layout.addWidget(self._palette_panel)

        self._canvas_panel = self._build_canvas_placeholder()
        body_layout.addWidget(self._canvas_panel, stretch=1)

        root.addWidget(body, stretch=1)

        # Status bar
        self._statusbar = _StatusBar()
        root.addWidget(self._statusbar)

        # Simulation log dock
        self._log_dock = _SimLogDock(self)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._log_dock)
        self._log_dock.hide()

    def _build_palette_placeholder(self) -> QWidget:
        """Real palette panel (Phase 7)."""
        from hydrosim.gui.palette.palette_panel import PalettePanel
        self._palette = PalettePanel()
        self._palette.element_requested.connect(self._on_element_double_clicked_palette)
        return self._palette

    def _build_canvas_placeholder(self) -> QWidget:
        """Real canvas (Phase 7)."""
        from hydrosim.gui.canvas.scene import HydroScene
        from hydrosim.gui.canvas.view  import HydroView
        from hydrosim.model.graph      import ModelGraph

        self._graph  = ModelGraph()
        self._scene  = HydroScene()
        self._canvas = HydroView(self._scene)

        self._scene.element_moved.connect(self._on_element_moved)
        self._scene.element_double_clicked.connect(self._on_element_double_clicked)
        self._scene.connection_requested.connect(self._on_connection_requested)
        self._canvas.element_dropped.connect(self._on_element_dropped)
        self._canvas.zoom_changed.connect(self.set_zoom_pct)
        return self._canvas

    # ── Menu bar ──────────────────────────────────────────────────────────────

    def _setup_menus(self) -> None:
        mb = self.menuBar()

        # ── File ──────────────────────────────────────────────────────────
        file_menu = mb.addMenu("File")

        self._act_new  = QAction("New Model",         self, shortcut="Ctrl+N")
        self._act_open = QAction("Open Model…",       self, shortcut="Ctrl+O")
        self._act_save = QAction("Save Model",        self, shortcut="Ctrl+S")
        self._act_save_as = QAction("Save Model As…", self, shortcut="Ctrl+Shift+S")
        self._recent_menu = file_menu.addMenu("Recent Models")
        self._act_exit = QAction("Exit",              self, shortcut="Ctrl+Q")

        for act in (self._act_new, self._act_open, self._act_save,
                    self._act_save_as):
            file_menu.addAction(act)
        file_menu.addSeparator()
        file_menu.addMenu(self._recent_menu)
        file_menu.addSeparator()
        file_menu.addAction(self._act_exit)

        # ── Simulation ────────────────────────────────────────────────────
        sim_menu = mb.addMenu("Simulation")

        self._act_sim_settings = QAction("Simulation Settings…", self, shortcut="Ctrl+T")
        self._act_run   = QAction("Run Simulation",  self, shortcut="F5")
        self._act_stop  = QAction("Stop Simulation", self, shortcut="Escape")
        self._act_stop.setEnabled(False)
        self._act_clear = QAction("Clear Results",   self)

        sim_menu.addAction(self._act_sim_settings)
        sim_menu.addSeparator()
        sim_menu.addAction(self._act_run)
        sim_menu.addAction(self._act_stop)
        sim_menu.addSeparator()
        sim_menu.addAction(self._act_clear)
        sim_menu.addSeparator()

        # ── Debug mode ────────────────────────────────────────────────────
        self._act_debug = QAction("Debug Mode", self, shortcut="Ctrl+D")
        self._act_debug.setCheckable(True)
        self._act_debug.setChecked(False)
        self._act_debug.setToolTip(
            "Log detailed element values, connection data-flow, "
            "and water balance info to the Simulation Log.\n"
            "Warnings and errors are also written to the log instead of pop-ups."
        )
        sim_menu.addAction(self._act_debug)

        # Debug verbosity sub-menu
        verb_menu = sim_menu.addMenu("Debug Verbosity")
        self._verb_actions = {}
        for label, interval in [
            ("Every step  (verbose)",  1),
            ("Every 5%  (detailed)",   5),
            ("Every 10%  (summary)",  10),
            ("Every 25%  (sparse)",   25),
        ]:
            act = QAction(label, self)
            act.setCheckable(True)
            act.setChecked(interval == 10)
            act.setData(interval)
            act.triggered.connect(self._on_debug_verbosity)
            verb_menu.addAction(act)
            self._verb_actions[interval] = act

        # ── View ──────────────────────────────────────────────────────────
        view_menu = mb.addMenu("View")

        self._act_zoom_in  = QAction("Zoom In",    self, shortcut="Ctrl+=")
        self._act_zoom_out = QAction("Zoom Out",   self, shortcut="Ctrl+-")
        self._act_zoom_fit = QAction("Zoom to Fit",self, shortcut="Ctrl+Shift+F")
        self._act_zoom_reset = QAction("Reset Zoom", self, shortcut="Ctrl+0")
        self._act_toggle_log = QAction("Show Simulation Log", self, shortcut="Ctrl+L")
        self._act_toggle_log.setCheckable(True)

        view_menu.addAction(self._act_zoom_in)
        view_menu.addAction(self._act_zoom_out)
        view_menu.addAction(self._act_zoom_fit)
        view_menu.addAction(self._act_zoom_reset)
        view_menu.addSeparator()
        view_menu.addAction(self._act_toggle_log)

        # ── Help ──────────────────────────────────────────────────────────
        help_menu = mb.addMenu("Help")
        self._act_docs  = QAction("Documentation", self)
        self._act_about = QAction("About HydroSim", self)
        help_menu.addAction(self._act_docs)
        help_menu.addAction(self._act_about)

    # ── Signal wiring ─────────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        # Toolbar buttons → menu actions (single source of truth)
        self._toolbar.new_clicked.connect(self._on_new)
        self._toolbar.open_clicked.connect(self._on_open)
        self._toolbar.save_clicked.connect(self._on_save)
        self._toolbar.run_clicked.connect(self._on_run)
        self._toolbar.stop_clicked.connect(self._on_stop)

        self._act_new.triggered.connect(self._on_new)
        self._act_open.triggered.connect(self._on_open)
        self._act_save.triggered.connect(self._on_save)
        self._act_save_as.triggered.connect(self._on_save_as)
        self._act_exit.triggered.connect(self.close)

        self._act_run.triggered.connect(self._on_run)
        self._act_stop.triggered.connect(self._on_stop)
        self._act_sim_settings.triggered.connect(self._on_sim_settings)
        self._act_clear.triggered.connect(self._on_clear_results)
        self._act_debug.toggled.connect(self._on_debug_toggled)

        self._act_zoom_in.triggered.connect(self._statusbar.zoom_in_clicked)
        self._act_zoom_out.triggered.connect(self._statusbar.zoom_out_clicked)
        self._act_zoom_reset.triggered.connect(self._statusbar.zoom_reset_clicked)
        self._act_zoom_fit.triggered.connect(self._canvas.zoom_to_fit)
        self._act_toggle_log.toggled.connect(self._on_toggle_log)

        self._act_about.triggered.connect(self._on_about)

        self._statusbar.zoom_in_clicked.connect(self._canvas.zoom_in)
        self._statusbar.zoom_out_clicked.connect(self._canvas.zoom_out)
        self._statusbar.zoom_reset_clicked.connect(self._canvas.zoom_reset)

        self._scene.element_added.connect(
            lambda _: self.set_element_count(self._graph.element_count)
        )
        self._scene.element_removed.connect(
            lambda _: self.set_element_count(self._graph.element_count)
        )

        # AutoSave every 5 minutes when there are unsaved changes
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(5 * 60 * 1000)   # 5 minutes
        self._autosave_timer.timeout.connect(self._autosave)
        self._autosave_timer.start()

        # Rebuild recent-files menu from preferences
        self._rebuild_recent_menu()

    # ── Debug mode ────────────────────────────────────────────────────────────

    def _on_debug_toggled(self, checked: bool) -> None:
        self._debug_mode = checked
        state_str = "ON" if checked else "OFF"
        interval  = self._debug_interval
        self.log(
            f"Debug Mode {state_str}  "
            + (f"(logging every {interval}% of steps)" if checked else "")
        )
        if checked:
            self.log(
                "  Warnings and errors will be written here instead of pop-up dialogs.\n"
                "  Element values and water balance logged at each snapshot interval.\n"
                "  Use Simulation → Debug Verbosity to change snapshot frequency."
            )
        # Keep log panel visible when debug is on
        if checked and not self._log_dock.isVisible():
            self._log_dock.show()
            self._act_toggle_log.setChecked(True)

    def _on_debug_verbosity(self) -> None:
        act      = self.sender()
        interval = act.data()
        self._debug_interval = interval
        # Un-check all others
        for i, a in self._verb_actions.items():
            a.setChecked(i == interval)
        self.log(f"Debug verbosity: logging every {interval}% of steps")

    # ── Centralised warn / error (respect debug mode) ─────────────────────────

    def _warn(self, title: str, message: str, also_dialog: bool = True) -> None:
        """
        Show a warning. In debug mode: always log; suppress pop-up.
        In normal mode: show pop-up only.
        """
        self.log(f"WARNING — {title}: {message}")
        if not self._debug_mode and also_dialog:
            QMessageBox.warning(self, title, message)

    def _error(self, title: str, message: str) -> None:
        """
        Show an error. Always logged; always pops a dialog (even in debug mode).
        """
        self.log(f"ERROR — {title}: {message}")
        QMessageBox.critical(self, title, message)

    # ── File operations ───────────────────────────────────────────────────────

    def _on_new(self) -> None:
        if not self._confirm_discard_changes():
            return
        self._clear_canvas()
        self._graph        = ModelGraph()
        self._model_path   = None
        self._results_store = None
        self._result_mgr.close_all()
        self._scene.clear_results_markers()
        self.set_model_name("Untitled", modified=False)
        self.set_element_count(0)
        self._statusbar.set_sim_state("idle")

    def _on_open(self) -> None:
        if not self._confirm_discard_changes():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Model", "", "HydroSim files (*.hydrosim);;All files (*)"
        )
        if path:
            self._load_file(Path(path))

    def _on_save(self) -> None:
        if self._model_path is None:
            self._on_save_as()
        else:
            self._save_to(self._model_path)

    def _on_save_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Model As",
            str(self._model_path or "Untitled.hydrosim"),
            "HydroSim files (*.hydrosim);;All files (*)"
        )
        if path:
            if not path.endswith(".hydrosim"):
                path += ".hydrosim"
            self._save_to(Path(path))

    def _save_to(self, path: Path) -> None:
        from hydrosim.model.serialiser import ModelSerialiser
        try:
            settings = self._sim_settings or SimulationSettings(0, 365, 1.0, "elapsed", None)
            ModelSerialiser.save(
                self._graph, settings, path,
                metadata={"name": path.stem}
            )
            self._model_path = path
            self._add_recent_file(path)
            self.set_model_name(path.stem, modified=False)
            self._statusbar.set_sim_state("idle", "Saved")
        except Exception as exc:
            self._error("Save Error", str(exc))

    def _load_file(self, path: Path) -> None:
        from hydrosim.model.serialiser import ModelSerialiser
        from hydrosim.model.base import ModelFileError, VersionMismatchError
        try:
            graph, settings, meta = ModelSerialiser.load(path)
        except FileNotFoundError:
            self._error("File Not Found", f"Could not find:\n{path}")
            return
        except VersionMismatchError as exc:
            reply = QMessageBox.question(
                self, "Version Mismatch",
                f"{exc}\n\nTry to open anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            self._warn("Cannot Load", str(exc))
            return
        except Exception as exc:
            self._error("Could Not Open", str(exc))
            return

        self._clear_canvas()
        self._graph         = graph
        self._sim_settings  = settings
        self._model_path    = path
        self._results_store = None
        self._result_mgr.close_all()
        self._rebuild_canvas_from_graph()
        self._add_recent_file(path)
        self.set_model_name(path.stem, modified=False)
        self.set_element_count(graph.element_count)
        if self._sim_settings:
            self._toolbar.update_meta(self._sim_settings.dt, self._sim_settings.n_steps)
        self._statusbar.set_sim_state("idle", "Model loaded")
        self.log(f"Loaded: {path.name}  ({graph.element_count} elements, {len(graph.connections)} connections)")

    # ── Canvas rebuild from loaded graph ─────────────────────────────────────

    def _clear_canvas(self) -> None:
        """Remove all items from the scene without touching the graph."""
        for eid in list(self._scene.element_items.keys()):
            item = self._scene.element_items.pop(eid)
            self._scene.removeItem(item)
        for cid in list(self._scene.connection_items.keys()):
            ci = self._scene.connection_items.pop(cid)
            self._scene.removeItem(ci)

    def _rebuild_canvas_from_graph(self) -> None:
        """After loading a model, recreate all ElementItems and ConnectionItems."""
        from PyQt6.QtCore import QPointF
        from hydrosim.gui.canvas.connection_item import ConnectionItem

        # Rebuild the scene's reference (new graph was loaded)
        self._scene.element_items    = {}
        self._scene.connection_items = {}

        # Add elements
        for element in self._graph.elements.values():
            pos = QPointF(element.position[0], element.position[1])
            self._scene.add_element(element, pos)

        # Add connections (bypass graph modification — graph already has them)
        for conn in self._graph.connections.values():
            from_elem_item = self._scene.element_items.get(conn.from_element_id)
            to_elem_item   = self._scene.element_items.get(conn.to_element_id)
            if not from_elem_item or not to_elem_item:
                continue
            from_port_item = from_elem_item.get_port_item(conn.from_port_name)
            to_port_item   = to_elem_item.get_port_item(conn.to_port_name)
            if not from_port_item or not to_port_item:
                continue
            category = from_elem_item.element.category.value
            ci = ConnectionItem(conn, from_port_item, to_port_item, category)
            self._scene.add_connection_item(conn, ci)

    # ── Simulation ────────────────────────────────────────────────────────────

    def _on_run(self) -> None:
        if not hasattr(self, "_graph") or self._graph.element_count == 0:
            self._warn("Cannot Run", "Add elements to the model first.")
            return

        # Validate before threading
        from hydrosim.model.validator import ModelValidator
        validator = ModelValidator(self._graph)
        errors    = validator.validate_all()
        if errors:
            msgs = "\n".join(f"  • {e.message}" for e in errors[:8])
            if self._debug_mode:
                # In debug mode: log each error with full detail, no popup
                self.log(f"Model validation failed — {len(errors)} error(s):")
                for e in errors:
                    el_name = ""
                    if e.element_id and e.element_id in self._graph.elements:
                        el_name = f" [{self._graph.elements[e.element_id].name}]"
                    self.log(f"  ✗  {e.code}{el_name}: {e.message}"
                             + (f"  → {e.suggestion}" if e.suggestion else ""))
            else:
                QMessageBox.warning(self, f"Model has {len(errors)} error(s)", msgs)
            return

        settings = self._sim_settings or SimulationSettings(0.0, 365.0, 1.0, "elapsed", None)

        # Clear old results
        self._on_clear_results()
        self._scene.clear_results_markers()

        self.set_simulation_running(True)
        if self._debug_mode:
            self.log(
                f"[DEBUG] Run started — debug mode ON "
                f"(snapshots every {self._debug_interval}%,  "
                f"{max(1, settings.n_steps // self._debug_interval)} step interval)"
            )
        self.log(f"Run: {settings.n_steps} steps, dt={settings.dt}")

        self._sim_thread = SimulationThread(
            self._graph, settings,
            debug_mode=self._debug_mode,
            debug_interval=self._debug_interval,
        )
        self._sim_thread.progress.connect(self._on_sim_progress)
        self._sim_thread.log_msg.connect(self.log)
        self._sim_thread.finished.connect(self._on_sim_finished)
        self._sim_thread.stopped.connect(self._on_sim_stopped)
        self._sim_thread.error.connect(self._on_sim_error)
        self._sim_thread.start()

    def _on_stop(self) -> None:
        if hasattr(self, "_sim_thread") and self._sim_thread.isRunning():
            self._sim_thread.request_stop()

    def _on_sim_progress(self, fraction: float) -> None:
        self._toolbar.set_progress(fraction)

    def _on_sim_finished(self, results) -> None:
        self.set_simulation_running(False)
        self.set_simulation_complete(results.completed_steps, results.run_duration_s, results)
        self._show_stale_banner(False)
        # Auto-open dashboard and populate all result tabs
        self._open_all_result_tabs(results)
        if self._debug_mode:
            self.log(
                "[DEBUG] Run complete. Check log above for element snapshots "
                "and water balance."
            )

    def _open_all_result_tabs(self, results_store) -> None:
        """Open / refresh the Results Dashboard with all TimeHistoryResult elements."""
        from hydrosim.model.elements.timehistory import TimeHistoryResult
        result_elements = [
            el for el in self._graph.elements.values()
            if isinstance(el, TimeHistoryResult)
        ]
        if not result_elements:
            return
        for el in result_elements:
            self._result_mgr.show_result(el, results_store, self._graph, parent=self)

    def _on_sim_stopped(self, results) -> None:
        self._toolbar.set_simulation_state("stopped")
        self._act_run.setEnabled(True)
        self._act_stop.setEnabled(False)
        self._statusbar.set_sim_state("stopped")

    def _on_sim_error(self, msg: str) -> None:
        self._toolbar.set_simulation_state("idle")
        self._act_run.setEnabled(True)
        self._act_stop.setEnabled(False)
        self._statusbar.set_sim_state("error", "Error")
        self._error("Simulation Error", msg)

    # ── Simulation Settings dialog ────────────────────────────────────────────

    def _on_sim_settings(self) -> None:
        from hydrosim.gui.dialogs.sim_settings_dialog import SimulationSettingsDialog
        settings = self._sim_settings or SimulationSettings(0.0, 365.0, 1.0, "elapsed", None)
        dlg = SimulationSettingsDialog(settings, parent=self)
        if dlg.exec():
            self._sim_settings = dlg.get_settings()
            self._toolbar.update_meta(self._sim_settings.dt, self._sim_settings.n_steps)

    def _on_clear_results(self) -> None:
        self._results_store = None
        self._result_mgr.close_all()
        self._scene.clear_results_markers()
        self._statusbar.set_sim_state("idle")

    # ── Stale-results banner ──────────────────────────────────────────────────

    def _show_stale_banner(self, visible: bool) -> None:
        """Show/hide a warning strip below the toolbar when results are out of date."""
        if not hasattr(self, "_stale_banner"):
            return
        self._stale_banner.setVisible(visible)

    # ── Recent files ──────────────────────────────────────────────────────────

    def _add_recent_file(self, path: Path) -> None:
        prefs = self._load_prefs()
        recent = prefs.get("recent_files", [])
        s = str(path)
        if s in recent:
            recent.remove(s)
        recent.insert(0, s)
        prefs["recent_files"] = recent[:5]
        self._save_prefs(prefs)
        self._rebuild_recent_menu()

    def _rebuild_recent_menu(self) -> None:
        self._recent_menu.clear()
        prefs  = self._load_prefs()
        recent = prefs.get("recent_files", [])
        for p in recent:
            act = QAction(Path(p).name, self)
            act.setData(p)
            act.triggered.connect(lambda checked, path=p: self._load_file(Path(path)))
            self._recent_menu.addAction(act)
        if not recent:
            empty = QAction("(empty)", self)
            empty.setEnabled(False)
            self._recent_menu.addAction(empty)

    # ── Preferences ───────────────────────────────────────────────────────────

    @staticmethod
    def _prefs_path() -> Path:
        return Path.home() / ".hydrosim" / "preferences.json"

    def _load_prefs(self) -> dict:
        import json
        p = self._prefs_path()
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _save_prefs(self, prefs: dict) -> None:
        import json
        p = self._prefs_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(prefs, indent=2), encoding="utf-8")

    def _on_zoom_in(self)    -> None:
        if hasattr(self, "_canvas"): self._canvas.zoom_in()
    def _on_zoom_out(self)   -> None:
        if hasattr(self, "_canvas"): self._canvas.zoom_out()
    def _on_zoom_reset(self) -> None:
        if hasattr(self, "_canvas"): self._canvas.zoom_reset()

    # ── Element creation (palette drop / double-click) ────────────────────────

    def _on_element_dropped(self, type_name: str, scene_pos) -> None:
        """Called when user drops a palette item onto the canvas."""
        element = self._create_element_of_type(type_name, (scene_pos.x(), scene_pos.y()))
        if element is None:
            return
        self._graph.add_element(element)
        self._scene.add_element(element, scene_pos)
        self._set_modified(True)
        # Open property dialog immediately
        self._open_property_dialog(element)

    def _on_element_double_clicked_palette(self, type_name: str) -> None:
        """Called when user double-clicks a palette item."""
        from PyQt6.QtCore import QPointF
        # Place at centre of current viewport
        vp_centre = self._canvas.mapToScene(
            self._canvas.viewport().rect().center()
        )
        element = self._create_element_of_type(type_name, (vp_centre.x(), vp_centre.y()))
        if element is None:
            return
        self._graph.add_element(element)
        self._scene.add_element(element, vp_centre)
        self._set_modified(True)
        self._open_property_dialog(element)

    def _create_element_of_type(self, type_name: str, position: tuple) -> "ElementBase | None":  # type: ignore
        """Instantiate a default element of the given type name."""
        from hydrosim.model.elements import (
            Constant, TimeSeries, WaterStore, Expression, TimeHistoryResult,
        )
        # Count existing elements of this type for default naming
        existing = sum(
            1 for el in self._graph.elements.values()
            if el.__class__.__name__ == type_name
        )
        n = existing + 1
        defaults = {
            "Constant":          lambda: Constant(name=f"Constant_{n}",    position=position),
            "TimeSeries":        lambda: TimeSeries(name=f"TimeSeries_{n}", position=position),
            "WaterStore":        lambda: WaterStore(name=f"WaterStore_{n}", position=position),
            "Expression":        lambda: Expression(name=f"Expression_{n}", position=position),
            "TimeHistoryResult": lambda: TimeHistoryResult(name=f"Result_{n}", position=position),
        }
        factory = defaults.get(type_name)
        return factory() if factory else None

    def _open_property_dialog(self, element: "ElementBase") -> None:  # type: ignore
        """Open the appropriate property dialog for an element."""
        from hydrosim.gui.dialogs.constant_dialog    import ConstantDialog
        from hydrosim.gui.dialogs.timeseries_dialog  import TimeSeriesDialog
        from hydrosim.gui.dialogs.waterstore_dialog  import WaterStoreDialog
        from hydrosim.gui.dialogs.expression_dialog  import ExpressionDialog
        from hydrosim.gui.dialogs.timehistory_dialog import TimeHistoryDialog

        _MAP = {
            "Constant":          ConstantDialog,
            "TimeSeries":        TimeSeriesDialog,
            "WaterStore":        WaterStoreDialog,
            "Expression":        ExpressionDialog,
            "TimeHistoryResult": TimeHistoryDialog,
        }
        klass = _MAP.get(element.__class__.__name__)
        if klass is None:
            return

        dlg = klass(element, self._graph, parent=self)
        if dlg.exec():
            # Changes already applied inside dialog._on_ok → apply_changes()
            self._scene.update_element_card(element.id)
            self._set_modified(True)

    def _on_element_double_clicked(self, element_id: str) -> None:
        """Canvas double-click → open result viewer or property dialog."""
        element = self._graph.elements.get(element_id)
        if element is None:
            return
        from hydrosim.model.elements.timehistory import TimeHistoryResult
        if (isinstance(element, TimeHistoryResult)
                and self._results_store is not None):
            self._result_mgr.show_result(
                element, self._results_store, self._graph, parent=self
            )
        else:
            self._open_property_dialog(element)

    def _on_element_moved(self, element_id: str, x: float, y: float) -> None:
        """Keep ModelGraph position in sync when card is dragged."""
        element = self._graph.elements.get(element_id)
        if element:
            element.position = (x, y)
        self._set_modified(True)

    def _on_connection_requested(
        self, from_id: str, from_port: str, to_id: str, to_port: str
    ) -> None:
        """User completed a drag-connect. Create connection in graph + scene."""
        from hydrosim.model.base import Connection
        from hydrosim.gui.canvas.connection_item import ConnectionItem

        conn = Connection("", from_id, from_port, to_id, to_port)
        try:
            self._graph.add_connection(conn)
        except ValueError as exc:
            self._warn("Cannot Connect", str(exc))
            return

        # Find port items
        from_elem_item = self._scene.element_items.get(from_id)
        to_elem_item   = self._scene.element_items.get(to_id)
        if not from_elem_item or not to_elem_item:
            return

        from_port_item = from_elem_item.get_port_item(from_port)
        to_port_item   = to_elem_item.get_port_item(to_port)
        if not from_port_item or not to_port_item:
            return

        category = from_elem_item.element.category.value
        ci = ConnectionItem(conn, from_port_item, to_port_item, category)
        self._scene.add_connection_item(conn, ci)
        self._set_modified(True)

        # Only rebuild ports when TimeHistoryResult gained a new series port
        from hydrosim.model.elements.timehistory import TimeHistoryResult as _THR
        if isinstance(self._graph.get_element(to_id), _THR):
            self._scene.update_element_card(to_id)
            # Re-apply connected state to the new port items
            to_port_item_new = to_elem_item.get_port_item(conn.to_port_name)
            if to_port_item_new:
                to_port_item_new.set_connected(True)

    def _on_connection_delete_requested(self, connection_id: str) -> None:
        """User pressed Delete on a selected connection arrow."""
        try:
            self._graph.remove_connection(connection_id)
        except KeyError:
            pass
        self._scene.remove_connection_item(connection_id)
        self._set_modified(True)

    def _set_modified(self, modified: bool) -> None:
        self._modified = modified
        name = self._get_model_name()
        star = "*" if modified else ""
        self.setWindowTitle(f"HydroSim — {name}{star}")
        # Show stale banner only when model was changed after a completed run
        if modified and self._results_store is not None:
            self._show_stale_banner(True)

    def _get_model_name(self) -> str:
        if self._model_path:
            return self._model_path.stem
        return "Untitled"

    def _on_toggle_log(self, checked: bool) -> None:
        if checked:
            self._log_dock.show()
        else:
            self._log_dock.hide()

    def _on_about(self) -> None:
        QMessageBox.about(
            self,
            "About HydroSim",
            "<b>HydroSim v0.1.0</b><br><br>"
            "Open-source hydrological simulation platform.<br><br>"
            "Built with PyQt6 · Python · NumPy · NetworkX",
        )

    # ── Public API (called by canvas/simulation in later phases) ──────────────

    def set_model_name(self, name: str, modified: bool = False) -> None:
        self._modified = modified
        title = f"HydroSim — {name}{'*' if modified else ''}"
        self.setWindowTitle(title)
        self._statusbar.set_model_name(name)

    def set_element_count(self, n: int) -> None:
        self._statusbar.set_element_count(n)

    def set_zoom_pct(self, pct: int) -> None:
        self._statusbar.set_zoom(pct)

    def set_simulation_running(self, running: bool) -> None:
        state = "running" if running else "idle"
        self._toolbar.set_simulation_state(state)
        self._act_run.setEnabled(not running)
        self._act_stop.setEnabled(running)
        self._statusbar.set_sim_state(state)

    def set_simulation_complete(
        self,
        steps:         int,
        elapsed_s:     float,
        results_store: "ResultsStore | None" = None,  # type: ignore
    ) -> None:
        self._toolbar.set_simulation_state("complete")
        self._act_run.setEnabled(True)
        self._act_stop.setEnabled(False)
        elapsed_str = f"{elapsed_s*1000:.0f}ms" if elapsed_s < 1 else f"{elapsed_s:.2f}s"
        self._statusbar.set_sim_state(
            "complete", f"Complete — {steps} steps in {elapsed_str}"
        )
        if results_store is not None:
            self._results_store = results_store
            self._result_mgr.refresh_all(results_store)
            # Mark TimeHistoryResult cards with green dot
            from hydrosim.model.elements.timehistory import TimeHistoryResult
            result_ids = [
                eid for eid, el in self._graph.elements.items()
                if isinstance(el, TimeHistoryResult)
            ]
            self._scene.mark_results_available(result_ids)

    def log(self, message: str) -> None:
        self._log_dock.append(message)
        if not self._log_dock.isVisible():
            self._log_dock.show()
            self._act_toggle_log.setChecked(True)

    # ── AutoSave ──────────────────────────────────────────────────────────────

    def _autosave(self) -> None:
        """Save a backup every 5 minutes when the model has unsaved changes."""
        if not self._modified or self._graph.element_count == 0:
            return
        from hydrosim.model.serialiser import ModelSerialiser
        autosave_dir = Path.home() / ".hydrosim" / "autosave"
        autosave_dir.mkdir(parents=True, exist_ok=True)
        name = (self._model_path.stem if self._model_path else "Untitled") + "_autosave.hydrosim"
        path = autosave_dir / name
        try:
            ModelSerialiser.save(
                self._graph, self._sim_settings,
                path, metadata={"name": name}
            )
        except Exception:
            pass   # autosave failures are silent

    @staticmethod
    def autosave_path_for(model_name: str) -> Path:
        return Path.home() / ".hydrosim" / "autosave" / f"{model_name}_autosave.hydrosim"

    def check_autosave_recovery(self, model_name: str = "Untitled") -> None:
        """
        Called at startup. If an autosave exists for this model name, offer
        to restore it.
        """
        path = self.autosave_path_for(model_name)
        if not path.exists():
            return
        import json
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            modified_str = raw.get("metadata", {}).get("modified", "")
        except Exception:
            modified_str = "(unknown)"

        reply = QMessageBox.question(
            self,
            "Auto-save Found",
            f"HydroSim found an auto-saved version of '{model_name}'\n"
            f"from {modified_str}.\n\nRestore it?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._load_file(path)

    def _confirm_discard_changes(self) -> bool:
        """Returns True if it's OK to proceed (discard or save first)."""
        if not self._modified:
            return True
        reply = QMessageBox.question(
            self,
            "Unsaved Changes",
            "You have unsaved changes.\nDo you want to save before continuing?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if reply == QMessageBox.StandardButton.Save:
            self._on_save()
            return True
        elif reply == QMessageBox.StandardButton.Discard:
            return True
        return False  # Cancel

    # ── Close event ────────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        if self._modified:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes.\nDo you want to save before closing?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save,
            )
            if reply == QMessageBox.StandardButton.Save:
                self._on_save()
                event.accept()
            elif reply == QMessageBox.StandardButton.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
