"""Entry point: python -m hydrosim"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> None:
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"

    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QFontDatabase
    from PyQt6.QtCore import Qt

    app = QApplication(sys.argv)
    app.setApplicationName("HydroSim")
    app.setApplicationVersion("0.1.0")
    app.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # Load bundled fonts (Inter + Fira Code)
    fonts_dir = Path(__file__).parent / "resources" / "fonts"
    for font_file in sorted(fonts_dir.glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(font_file))

    # Apply global stylesheet
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
