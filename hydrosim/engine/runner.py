"""
SimulationRunner — orchestrates a complete simulation run.
Reads from ModelGraph + SimulationSettings; writes to ResultsStore.
Zero PyQt6 dependencies (progress callback is a plain callable).
"""
from __future__ import annotations

import logging
import time
from typing import Callable

import numpy as np

from hydrosim.model.base import (
    SimState,
    SimulationAborted,
    SimulationError,
    SimulationSettings,
)

log = logging.getLogger(__name__)


class SimulationRunner:
    """
    Orchestrates a complete simulation run.

    Typical usage (synchronous, for tests and CLI):
        runner  = SimulationRunner(graph, settings)
        results = runner.run()

    For the GUI, call run() from a QThread and pass progress_callback
    to update a progress bar without blocking the UI thread.
    """

    def __init__(
        self,
        graph:    "ModelGraph",   # type: ignore[name-defined]
        settings: SimulationSettings,
    ):
        self.graph    = graph
        self.settings = settings
        self._stop_requested = False

    # ── Public API ────────────────────────────────────────────────────────────

    def run(
        self,
        progress_callback: Callable[[float], None] | None = None,
        debug_callback:    Callable[["SimState", list, int], None] | None = None,
        debug_interval:    int = 10,
    ) -> "ResultsStore":  # type: ignore[name-defined]
        """
        Execute the full simulation synchronously.

        Steps:
          1. validate()
          2. build_execution_order()
          3. initialise_state()
          4. prepare_elements()
          5. initialise_stocks()
          6. build_results_store()
          7. timestep_loop()
          8. return ResultsStore

        Raises SimulationError if the model is invalid.
        Raises SimulationAborted if stop() was called during the run.
        """
        self._stop_requested = False
        t_start = time.perf_counter()

        self._validate()
        execution_order = self._build_execution_order()

        log.info(
            "Starting simulation: %d elements, %d steps (dt=%.4f)",
            self.graph.element_count,
            self.settings.n_steps,
            self.settings.dt,
        )
        log.info(
            "Execution order: %s",
            [el.name for el in execution_order],
        )

        state   = self._initialise_state()
        self._prepare_elements(state)
        self._initialise_stocks(state)
        results = self._build_results_store(execution_order)

        self._timestep_loop(
            execution_order, state, results,
            progress_callback, debug_callback, debug_interval
        )

        results.run_duration_s = time.perf_counter() - t_start
        self._log_completion(results)
        return results

    def stop(self) -> None:
        """
        Signal the runner to stop after the current timestep completes.
        Thread-safe — can be called from any thread (bool write is atomic in CPython).
        """
        self._stop_requested = True

    # ── Step 1: Validation ────────────────────────────────────────────────────

    def _validate(self) -> None:
        from hydrosim.model.validator import ModelValidator
        validator = ModelValidator(self.graph)
        errors    = validator.validate_all()
        if errors:
            raise SimulationError(errors)

    # ── Step 2: Execution order ───────────────────────────────────────────────

    def _build_execution_order(self) -> list:
        """Return topologically sorted elements, excluding isolated ones."""
        from hydrosim.model.validator import ModelValidator
        isolated = ModelValidator(self.graph).get_isolated_element_ids()
        return [el for el in self.graph.get_execution_order()
                if el.id not in isolated]

    # ── Step 3: State initialisation ─────────────────────────────────────────

    def _initialise_state(self) -> SimState:
        return SimState(
            t=self.settings.start_time,
            dt=self.settings.dt,
            step=0,
            values={},
            storage={},
        )

    # ── Step 4: Element preparation ──────────────────────────────────────────

    def _prepare_elements(self, state: SimState) -> None:
        """Call prepare() on TimeSeries and Expression elements, skipping isolated ones."""
        from hydrosim.model.elements.timeseries import TimeSeries
        from hydrosim.model.elements.expression  import Expression
        from hydrosim.model.validator import ModelValidator

        isolated   = ModelValidator(self.graph).get_isolated_element_ids()
        name_to_id = self.graph.build_name_to_id_map()

        for el in self.graph.elements.values():
            if el.id in isolated:
                continue
            if isinstance(el, TimeSeries):
                el.prepare()
            elif isinstance(el, Expression):
                el.prepare(name_to_id)

    # ── Step 5: Stock initialisation ─────────────────────────────────────────

    def _initialise_stocks(self, state: SimState) -> None:
        """Call initialise() on every stock element to set initial storage."""
        for el in self.graph.elements.values():
            if el.is_stock():
                el.initialise(state)

    # ── Step 6: Results store ─────────────────────────────────────────────────

    def _build_results_store(self, execution_order: list) -> "ResultsStore":  # type: ignore
        from hydrosim.engine.results import ResultsStore
        from hydrosim.model.elements.timehistory import TimeHistoryResult

        # Collect only ports that feed into a TimeHistoryResult
        tracked: list[tuple[str, str]] = []
        seen:    set[tuple[str, str]]  = set()

        for el in self.graph.elements.values():
            if isinstance(el, TimeHistoryResult):
                for conn in self.graph.get_connections_to(el.id):
                    key = (conn.from_element_id, conn.from_port_name)
                    if key not in seen:
                        tracked.append(key)
                        seen.add(key)

        return ResultsStore(
            timesteps=self.settings.timesteps,
            tracked=tracked,
            element_names={
                el.id: el.name for el in self.graph.elements.values()
            },
        )

    # ── Step 7: Timestep loop ─────────────────────────────────────────────────

    def _timestep_loop(
        self,
        execution_order: list,
        state:           SimState,
        results:         "ResultsStore",   # type: ignore
        progress_cb:     Callable[[float], None] | None,
        debug_cb:        Callable[["SimState", list, int], None] | None = None,
        debug_interval:  int = 10,
    ) -> None:
        from hydrosim.engine.solver import TimeStepSolver
        solver    = TimeStepSolver(self.graph)
        n         = self.settings.n_steps
        dbg_every = max(1, n // debug_interval) if debug_interval > 0 else n + 1

        for i, t in enumerate(self.settings.timesteps):
            if self._stop_requested:
                results.was_stopped = True
                raise SimulationAborted(step=i, t=t)

            state.t    = t
            state.step = i

            for element in execution_order:
                connections_in = solver.resolve_inputs(element, state)
                element.compute(state, connections_in)

            results.record(i, state)

            if debug_cb is not None and (i % dbg_every == 0 or i == n - 1):
                debug_cb(state, execution_order, i)

            if progress_cb is not None:
                progress_cb((i + 1) / n)

    # ── Step 8: Completion logging ────────────────────────────────────────────

    def _log_completion(self, results: "ResultsStore") -> None:  # type: ignore
        log.info(
            "Simulation complete: %d steps in %.3fs",
            results.completed_steps,
            results.run_duration_s,
        )

        # Water balance check on all stock elements
        from hydrosim.model.elements.waterstore import WaterStore
        from hydrosim.model.base import WARN_WATER_BALANCE_ERROR
        for el in self.graph.elements.values():
            if not isinstance(el, WaterStore):
                continue
            try:
                storage_series = results.get_series(el.id, "storage")
                inflow_series  = results.get_series(el.id, "overflow")  # proxy check
            except KeyError:
                continue  # not tracked — skip balance check

            # Quick check: final storage should be within bounds
            final = storage_series[results.completed_steps - 1]
            if el.upper_bound is not None and final > el.upper_bound + 1e-6:
                log.warning(
                    "%s: final storage %.4f exceeds upper_bound %.4f",
                    el.name, final, el.upper_bound,
                )
