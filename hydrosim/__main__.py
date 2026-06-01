"""Entry point: python -m hydrosim"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _apply_light_palette(app) -> None:
    """
    Set an explicit light QPalette on the application so every colour role
    has a known value.  This prevents Windows dark mode (or any other OS
    theme) from injecting dark backgrounds / white-on-white text into native
    widget rendering (dropdown popups, scrollbars, list views, etc.).
    """
    from PyQt6.QtGui import QColor, QPalette

    c = {
        "bg":          "#F5F6FA",  # Window / Panel background
        "base":        "#FFFFFF",  # Input fields, list views
        "alt_base":    "#F9FAFB",  # Alternating row colour
        "text":        "#1A1A2E",  # Primary text
        "mid_text":    "#6B7280",  # Secondary / placeholder text
        "border":      "#E5E7EB",  # Subtle border
        "highlight":   "#2E86C1",  # Selected item background
        "hi_text":     "#FFFFFF",  # Text on highlight
        "button":      "#FFFFFF",  # Button face
        "button_text": "#1A1A2E",  # Button text
        "disabled_bg": "#F9FAFB",  # Disabled widget background
        "disabled_tx": "#9CA3AF",  # Disabled text
        "tooltip_bg":  "#1A1A2E",  # Tooltip background
        "tooltip_tx":  "#FFFFFF",  # Tooltip text
    }

    p = QPalette()

    def col(hex_str: str) -> QColor:
        return QColor(hex_str)

    # ── Active / Inactive groups ──────────────────────────────────────────
    for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive):
        p.setColor(group, QPalette.ColorRole.Window,          col(c["bg"]))
        p.setColor(group, QPalette.ColorRole.WindowText,      col(c["text"]))
        p.setColor(group, QPalette.ColorRole.Base,            col(c["base"]))
        p.setColor(group, QPalette.ColorRole.AlternateBase,   col(c["alt_base"]))
        p.setColor(group, QPalette.ColorRole.Text,            col(c["text"]))
        p.setColor(group, QPalette.ColorRole.PlaceholderText, col(c["mid_text"]))
        p.setColor(group, QPalette.ColorRole.Button,          col(c["button"]))
        p.setColor(group, QPalette.ColorRole.ButtonText,      col(c["button_text"]))
        p.setColor(group, QPalette.ColorRole.BrightText,      col(c["hi_text"]))
        p.setColor(group, QPalette.ColorRole.Highlight,       col(c["highlight"]))
        p.setColor(group, QPalette.ColorRole.HighlightedText, col(c["hi_text"]))
        p.setColor(group, QPalette.ColorRole.Link,            col(c["highlight"]))
        p.setColor(group, QPalette.ColorRole.LinkVisited,     col("#7B68C8"))
        p.setColor(group, QPalette.ColorRole.Mid,             col(c["border"]))
        p.setColor(group, QPalette.ColorRole.Light,           col(c["base"]))
        p.setColor(group, QPalette.ColorRole.Midlight,        col(c["bg"]))
        p.setColor(group, QPalette.ColorRole.Dark,            col(c["border"]))
        p.setColor(group, QPalette.ColorRole.Shadow,          col("#C9CDD4"))
        p.setColor(group, QPalette.ColorRole.ToolTipBase,     col(c["tooltip_bg"]))
        p.setColor(group, QPalette.ColorRole.ToolTipText,     col(c["tooltip_tx"]))

    # ── Disabled group ────────────────────────────────────────────────────
    g = QPalette.ColorGroup.Disabled
    p.setColor(g, QPalette.ColorRole.Window,     col(c["disabled_bg"]))
    p.setColor(g, QPalette.ColorRole.WindowText, col(c["disabled_tx"]))
    p.setColor(g, QPalette.ColorRole.Base,       col(c["disabled_bg"]))
    p.setColor(g, QPalette.ColorRole.Text,       col(c["disabled_tx"]))
    p.setColor(g, QPalette.ColorRole.Button,     col(c["disabled_bg"]))
    p.setColor(g, QPalette.ColorRole.ButtonText, col(c["disabled_tx"]))
    p.setColor(g, QPalette.ColorRole.Highlight,  col(c["border"]))
    p.setColor(g, QPalette.ColorRole.HighlightedText, col(c["mid_text"]))

    app.setPalette(p)


def main() -> None:
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"

    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QColor, QFontDatabase, QPalette
    from PyQt6.QtCore import Qt

    app = QApplication(sys.argv)
    app.setApplicationName("HydroSim")
    app.setApplicationVersion("0.1.0")
    app.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # ── Force light palette regardless of Windows dark mode ──────────────
    # Qt6 on Windows inherits the system palette (dark or light) for native
    # widget rendering.  Setting Fusion style + an explicit light palette
    # ensures consistent colours on every OS and mode.
    app.setStyle("Fusion")
    _apply_light_palette(app)

    # Load bundled fonts (Inter + Fira Code)
    fonts_dir = Path(__file__).parent / "resources" / "fonts"
    for font_file in sorted(fonts_dir.glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(font_file))

    # Apply global stylesheet (on top of the explicit palette)
    qss_path = Path(__file__).parent / "gui" / "styles" / "stylesheet.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))

    from hydrosim.gui.main_window import MainWindow
    window = MainWindow()

    prefs_path   = Path.home() / ".hydrosim" / "preferences.json"
    example_path = Path(__file__).parent / "resources" / "examples" / "simple_water_balance.hydrosim"

    if not prefs_path.exists():
        # First launch — offer the example model
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            window,
            "Welcome to HydroSim v0.1.0",
            "Welcome!\n\nWould you like to open the example water balance model to get started?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply == QMessageBox.StandardButton.Yes and example_path.exists():
            window._load_file(example_path)
    else:
        # Returning user — check for autosave recovery
        autosave_dir = Path.home() / ".hydrosim" / "autosave"
        if autosave_dir.exists():
            saves = sorted(autosave_dir.glob("*_autosave.hydrosim"),
                           key=lambda p: p.stat().st_mtime, reverse=True)
            if saves:
                window.check_autosave_recovery(
                    saves[0].stem.replace("_autosave", "")
                )

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
