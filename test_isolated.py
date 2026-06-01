"""Verify that unused/isolated elements don't block simulation."""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from pathlib import Path

app = QApplication(sys.argv)
from hydrosim.gui.main_window import MainWindow
w = MainWindow()

log_lines = []
orig = w.log
def capture(msg): log_lines.append(msg); orig(msg)
w.log = capture

def run():
    # Load working example model
    w._load_file(Path("Hawkesbury_Water_Balance_2020.hydrosim"))

    # Drop three extra "unused" elements directly into the graph/scene
    from hydrosim.model.elements import Constant, TimeHistoryResult, Expression
    from PyQt6.QtCore import QPointF

    orphan_c  = Constant(name="UnusedConstant", value=99.0, position=(200, 600))
    orphan_th = TimeHistoryResult(name="UnusedPlot", position=(500, 600))
    orphan_ex = Expression(name="UnusedExpr", formula="Rain * 2", position=(350, 600))

    for el in [orphan_c, orphan_th, orphan_ex]:
        w._graph.add_element(el)
        w._scene.add_element(el, QPointF(el.position[0], el.position[1]))

    print(f"Elements on canvas: {w._graph.element_count}  "
          f"(3 isolated + 11 connected)")

    # Validate — should have 0 blocking errors
    from hydrosim.model.validator import ModelValidator, WARN_ISOLATED_ELEMENT
    validator = ModelValidator(w._graph)
    errors    = validator.validate_all()
    warnings  = validator.get_warnings(w._sim_settings)
    isolated  = [ww for ww in warnings if ww.code == WARN_ISOLATED_ELEMENT]

    assert not errors, f"Unexpected errors: {errors}"
    print(f"Validation errors: {len(errors)}  (expected 0)")
    print(f"Isolated-element warnings: {len(isolated)}")
    for ww in isolated:
        el = w._graph.elements.get(ww.element_id or "")
        print(f"  ○  '{el.name if el else '?'}' — {ww.message}")

    # Run simulation — should succeed and log the isolated elements
    from hydrosim.engine.runner import SimulationRunner
    results = SimulationRunner(w._graph, w._sim_settings).run()
    assert results.is_complete
    print(f"\nSimulation: {results.completed_steps} steps  OK")

    # Simulate what SimulationThread._log_warnings does
    from hydrosim.gui.simulation_thread import SimulationThread
    t = SimulationThread(w._graph, w._sim_settings, debug_mode=False)
    t.log_msg.connect(capture)
    t._log_warnings()
    isolated_log = [l for l in log_lines if "UnusedConstant" in l
                    or "UnusedPlot" in l or "UnusedExpr" in l]
    assert isolated_log, "Isolated elements should appear in log"
    print("\nLog lines mentioning isolated elements:")
    for line in isolated_log:
        print(f"  {line}")

    print("\nTest PASSED — isolated elements are warned but never block simulation.")
    app.quit()

QTimer.singleShot(300, run)
app.exec()
