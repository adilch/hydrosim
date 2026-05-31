"""
ResultsStore — holds the complete time history of tracked output ports.
Pre-allocated at simulation start; populated by record() at each timestep.
Zero PyQt6 dependencies.
"""
from __future__ import annotations

import numpy as np

from hydrosim.model.base import SimState


class ResultsStore:
    """
    Stores simulation output as pre-allocated NumPy arrays.
    Only ports that feed into a TimeHistoryResult are tracked (memory efficiency).
    """

    def __init__(
        self,
        timesteps:     np.ndarray,
        tracked:       list[tuple[str, str]],   # [(element_id, port_name), ...]
        element_names: dict[str, str],           # {element_id: element_name}
    ):
        self.timesteps     = timesteps
        self.element_names = element_names
        self._n            = len(timesteps)

        # Pre-allocate one float64 array per tracked (element_id, port_name) pair
        self._arrays: dict[tuple[str, str], np.ndarray] = {
            key: np.zeros(self._n, dtype=np.float64)
            for key in tracked
        }

        # Runtime metadata
        self.completed_steps: int   = 0
        self.was_stopped:     bool  = False
        self.run_duration_s:  float = 0.0

    # ── Write ─────────────────────────────────────────────────────────────────

    def record(self, step: int, state: SimState) -> None:
        """
        Record all tracked port values from state at the given step index.
        Called once per timestep by the runner.
        """
        for (element_id, port_name), array in self._arrays.items():
            array[step] = state.get(element_id, port_name)
        self.completed_steps = step + 1

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_series(self, element_id: str, port_name: str) -> np.ndarray:
        """Return the recorded array for a specific port. Raises KeyError if not tracked."""
        key = (element_id, port_name)
        if key not in self._arrays:
            raise KeyError(
                f"Port ({element_id!r}, {port_name!r}) is not tracked. "
                f"Tracked ports: {list(self._arrays)}"
            )
        return self._arrays[key]

    def get_series_by_name(self, element_name: str, port_name: str) -> np.ndarray:
        """Lookup by human-readable element name instead of UUID."""
        element_id = next(
            (eid for eid, name in self.element_names.items() if name == element_name),
            None,
        )
        if element_id is None:
            raise KeyError(f"No element named {element_name!r} in results")
        return self.get_series(element_id, port_name)

    def get_all_series(self) -> dict[str, dict[str, np.ndarray]]:
        """
        Return all tracked series as a nested dict:
        {element_name: {port_name: np.ndarray}}
        """
        result: dict[str, dict[str, np.ndarray]] = {}
        for (element_id, port_name), array in self._arrays.items():
            name = self.element_names.get(element_id, element_id)
            result.setdefault(name, {})[port_name] = array
        return result

    def get_completed_timesteps(self) -> np.ndarray:
        """Return only the timesteps that were actually completed (handles early stop)."""
        return self.timesteps[: self.completed_steps]

    def export_dataframe(self) -> "pd.DataFrame":  # type: ignore[name-defined]
        """Export all tracked series as a Pandas DataFrame."""
        import pandas as pd
        data: dict[str, np.ndarray] = {
            "time_days": self.get_completed_timesteps()
        }
        for (eid, port), array in self._arrays.items():
            name = self.element_names.get(eid, eid)
            data[f"{name}.{port}"] = array[: self.completed_steps]
        return pd.DataFrame(data)

    # ── State ─────────────────────────────────────────────────────────────────

    @property
    def is_complete(self) -> bool:
        return self.completed_steps >= self._n and not self.was_stopped

    @property
    def tracked_ports(self) -> list[tuple[str, str]]:
        return list(self._arrays.keys())
