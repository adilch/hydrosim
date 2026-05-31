"""
SimulationThread — runs SimulationRunner in a background QThread.
Emits progress, log, finished, and error signals back to the GUI thread.
Supports an optional debug mode that logs detailed per-step data.
"""
from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal

from hydrosim.model.base import SimulationSettings, SimulationAborted


class SimulationThread(QThread):
    """
    Wraps SimulationRunner so the GUI stays responsive during simulation.

    Signals:
        progress(float)   — 0.0 → 1.0 as steps complete
        log_msg(str)      — lines for the simulation log panel
        finished(object)  — ResultsStore on success
        stopped(object)   — None on user stop
        error(str)        — error message on failure
    """

    progress = pyqtSignal(float)
    log_msg  = pyqtSignal(str)
    finished = pyqtSignal(object)
    stopped  = pyqtSignal(object)
    error    = pyqtSignal(str)

    def __init__(
        self,
        graph:          "ModelGraph",    # type: ignore
        settings:       SimulationSettings,
        debug_mode:     bool = False,
        debug_interval: int  = 10,       # log every N% of total steps
    ):
        super().__init__()
        self._graph          = graph
        self._settings       = settings
        self._debug_mode     = debug_mode
        self._debug_interval = debug_interval
        self._runner         = None

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _dbg(self, msg: str) -> None:
        """Emit a log line prefixed with [DEBUG]."""
        self.log_msg.emit(f"[DEBUG] {msg}")

    def _emit_step_snapshot(self, state, execution_order, step_idx: int) -> None:
        """Emit a formatted snapshot of all element outputs at this timestep."""
        lines = [f"  ── Step {step_idx}  t={state.t:.2f} ──"]
        for el in execution_order:
            vals = state.values.get(el.id, {})
            if not vals:
                continue
            parts = "  ".join(f"{k}={v:.4g}" for k, v in vals.items())
            lines.append(f"    {el.name:<22s}  {parts}")
        # Also show storage for stock elements
        for el in execution_order:
            if el.is_stock() and el.id in state.storage:
                self._dbg(f"  [STOCK] {el.name}.storage = {state.storage[el.id]:.4g}")
        self.log_msg.emit("\n".join(lines))

    def _log_warnings(self) -> None:
        """Log all non-blocking validation warnings, always."""
        from hydrosim.model.validator import ModelValidator, WARN_ISOLATED_ELEMENT
        validator = ModelValidator(self._graph)
        warnings  = validator.get_warnings(self._settings)

        # Split isolated-element warnings out for prominent display
        isolated_warns = [w for w in warnings if w.code == WARN_ISOLATED_ELEMENT]
        other_warns    = [w for w in warnings if w.code != WARN_ISOLATED_ELEMENT]

        # Isolated elements — always shown (not just in debug mode)
        if isolated_warns:
            self.log_msg.emit(
                f"Unused elements ({len(isolated_warns)}) — "
                f"these will be skipped this run:"
            )
            for w in isolated_warns:
                el = self._graph.elements.get(w.element_id or "")
                name = f"'{el.name}'" if el else "?"
                cls  = el.__class__.__name__ if el else ""
                self.log_msg.emit(f"  [unused]  {name}  ({cls}) -- not connected to anything")

        # Other warnings
        if other_warns:
            self.log_msg.emit(f"Validation warnings ({len(other_warns)}):")
            for w in other_warns:
                el_name = ""
                if w.element_id:
                    el = self._graph.elements.get(w.element_id)
                    el_name = f" [{el.name}]" if el else ""
                self.log_msg.emit(f"  ⚠  {w.code}{el_name}: {w.message}")

        if not warnings and self._debug_mode:
            self._dbg("No validation warnings.")

    def _log_model_details(self, execution_order) -> None:
        """Log full model structure when debug mode is active."""
        self._dbg("─── Model Structure ────────────────────────────")
        self._dbg(f"Elements ({self._graph.element_count}):")
        for el in execution_order:
            in_ports  = list(el.input_ports.keys())
            out_ports = list(el.output_ports.keys())
            self._dbg(
                f"  {el.__class__.__name__:<20s} '{el.name}'"
                f"  in=[{', '.join(in_ports)}]"
                f"  out=[{', '.join(out_ports)}]"
            )
        conns = list(self._graph.connections.values())
        self._dbg(f"Connections ({len(conns)}):")
        for c in conns:
            from_el = self._graph.elements.get(c.from_element_id)
            to_el   = self._graph.elements.get(c.to_element_id)
            if from_el and to_el:
                self._dbg(
                    f"  {from_el.name}.{c.from_port_name}"
                    f"  ──►  {to_el.name}.{c.to_port_name}"
                )
        self._dbg(
            f"Settings: t={self._settings.start_time}..{self._settings.end_time}"
            f"  dt={self._settings.dt}  ({self._settings.n_steps} steps)"
        )
        self._dbg("────────────────────────────────────────────────")

    def _log_water_balance(self, results) -> None:
        """Log water balance summary for every WaterStore."""
        from hydrosim.model.elements.waterstore import WaterStore
        for el in self._graph.elements.values():
            if not isinstance(el, WaterStore):
                continue
            try:
                storage  = results.get_series(el.id, "storage")
                overflow = results.get_series(el.id, "overflow")
                deficit  = results.get_series(el.id, "deficit")
                delta_s  = storage[-1] - el.initial_storage
                n        = results.completed_steps
                self._dbg(
                    f"WaterStore '{el.name}': "
                    f"ΔS={delta_s:+.3f}  "
                    f"overflow_total={overflow[:n].sum():.3f}  "
                    f"deficit_total={deficit[:n].sum():.3f}  "
                    f"final={storage[-1]:.3f} mm"
                )
                # Overflow-day count
                over_days = (overflow[:n] > 0).sum()
                if over_days:
                    self._dbg(
                        f"  → Overflow occurred on {over_days}/{n} days "
                        f"({100*over_days/n:.1f}%)"
                    )
            except KeyError:
                pass   # not tracked

    # ── Main run ──────────────────────────────────────────────────────────────

    def run(self) -> None:
        from hydrosim.engine.runner import SimulationRunner
        from hydrosim.model.base    import SimulationError

        self._runner = SimulationRunner(self._graph, self._settings)

        # ── Header ────────────────────────────────────────────────────────
        self.log_msg.emit(
            f"Starting simulation: {self._graph.element_count} elements, "
            f"{self._settings.n_steps} steps  (dt={self._settings.dt} day)"
        )

        order = self._graph.get_execution_order()
        self.log_msg.emit(
            "Execution order: " + "  ►  ".join(el.name for el in order)
        )

        # ── Validation warnings ────────────────────────────────────────────
        self._log_warnings()

        # ── Debug: full model details ──────────────────────────────────────
        if self._debug_mode:
            self._log_model_details(order)

        # ── Build debug callback ───────────────────────────────────────────
        debug_cb = None
        if self._debug_mode:
            def debug_cb(state, exec_order, step_idx):
                self._emit_step_snapshot(state, exec_order, step_idx)

        try:
            results = self._runner.run(
                progress_callback=lambda p: self.progress.emit(p),
                debug_callback=debug_cb,
                debug_interval=self._debug_interval,
            )

            # ── Completion summary ─────────────────────────────────────────
            self.log_msg.emit(
                f"Simulation complete: {results.completed_steps} steps "
                f"in {results.run_duration_s*1000:.0f} ms"
            )

            if self._debug_mode:
                self._log_water_balance(results)
                self._dbg(
                    f"Results tracked: "
                    f"{', '.join(f'{n}.{p}' for n,p in [(self._graph.elements.get(eid,type('',(),{'name':eid})()).name, pname) for eid,pname in results.tracked_ports])}"
                )

            self.finished.emit(results)

        except SimulationAborted as exc:
            self.log_msg.emit(
                f"Simulation stopped by user at step {exc.step}  (t={exc.t:.2f})"
            )
            self.stopped.emit(None)

        except Exception as exc:
            import traceback
            self.log_msg.emit(f"ERROR: {exc}")
            if self._debug_mode:
                self.log_msg.emit(traceback.format_exc())
            self.error.emit(str(exc))

    def request_stop(self) -> None:
        """Thread-safe — can be called from the GUI thread."""
        if self._runner is not None:
            self._runner.stop()

