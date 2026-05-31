"""TimeSeries element — time-varying input from a table of (time, value) pairs."""
from __future__ import annotations

import numpy as np
from scipy.interpolate import interp1d

from hydrosim.model.base import (
    ElementBase,
    ElementCategory,
    ERR_EMPTY_TIMESERIES,
    ERR_INVALID_PARAMETER,
    InterpolationType,
    SimState,
    TimeSeriesType,
    ValidationError,
)


class TimeSeries(ElementBase):
    """
    Provides a time-varying scalar from a user-supplied table.
    Call prepare() once before the simulation loop; compute() uses the
    pre-built interpolator for O(log n) lookup each timestep.
    """

    def __init__(
        self,
        name:          str,
        units:         str                      = "-",
        data_type:     TimeSeriesType           = TimeSeriesType.PERIOD_TOTAL,
        interpolation: InterpolationType        = InterpolationType.STEP,
        data:          list[list[float]] | None = None,
        description:   str                      = "",
        element_id:    str | None               = None,
        position:      tuple[float, float]      = (0.0, 0.0),
    ):
        self.units         = units
        self.data_type     = data_type
        self.interpolation = interpolation
        self.data:  list[list[float]] = data if data is not None else []
        self._prepared     = False
        self._interpolator = None
        super().__init__(name=name, description=description,
                         element_id=element_id, position=position)

    # ── ElementBase interface ─────────────────────────────────────────────────

    @property
    def category(self) -> ElementCategory:
        return ElementCategory.INPUT

    def _define_ports(self) -> None:
        self._add_output_port("value", self.units,
                              "Interpolated value at the current timestep")

    def validate(self) -> list[ValidationError]:
        errors = []
        if not self.data:
            errors.append(ValidationError(
                code=ERR_EMPTY_TIMESERIES,
                element_id=self.id,
                message=f"'{self.name}': time series has no data rows",
            ))
            return errors

        times  = [row[0] for row in self.data]
        values = [row[1] for row in self.data]

        # Strictly increasing times
        for i in range(1, len(times)):
            if times[i] <= times[i - 1]:
                errors.append(ValidationError(
                    code=ERR_INVALID_PARAMETER,
                    element_id=self.id,
                    message=(
                        f"'{self.name}': time values must be strictly increasing "
                        f"(row {i}: {times[i]} <= {times[i-1]})"
                    ),
                ))
                break

        # No NaN / Inf
        import math
        for i, (t, v) in enumerate(zip(times, values)):
            if not math.isfinite(t) or not math.isfinite(v):
                errors.append(ValidationError(
                    code=ERR_INVALID_PARAMETER,
                    element_id=self.id,
                    message=f"'{self.name}': NaN or Inf value at row {i}",
                ))
                break

        return errors

    def prepare(self) -> None:
        """
        Build the SciPy interpolator from self.data.
        Must be called after data is set and before compute().
        """
        if not self.data:
            # Empty — prepare a zero-returning fallback
            self._interpolator = lambda t: 0.0
            self._prepared = True
            return

        times  = np.array([row[0] for row in self.data], dtype=np.float64)
        values = np.array([row[1] for row in self.data], dtype=np.float64)

        kind = "previous" if self.interpolation == InterpolationType.STEP else "linear"

        self._interpolator = interp1d(
            times, values,
            kind=kind,
            bounds_error=False,
            fill_value=(values[0], values[-1]),  # flat extrapolation at both ends
        )
        self._prepared = True

    def compute(self, state: SimState, connections_in: dict[str, float]) -> None:
        if not self._prepared:
            raise RuntimeError(
                f"TimeSeries '{self.name}': prepare() must be called before compute()"
            )
        value = float(self._interpolator(state.t))
        state.set(self.id, "value", value)

    def get_value_at(self, t: float) -> float:
        """Direct query used by the GUI preview. Calls prepare() if needed."""
        if not self._prepared:
            self.prepare()
        return float(self._interpolator(t))

    def to_dict(self) -> dict:
        return {
            "id":          self.id,
            "type":        "TimeSeries",
            "name":        self.name,
            "description": self.description,
            "position":    list(self.position),
            "parameters": {
                "units":         self.units,
                "data_type":     self.data_type.value,
                "interpolation": self.interpolation.value,
                "data":          [list(row) for row in self.data],
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TimeSeries":
        p = data["parameters"]
        return cls(
            name=data["name"],
            units=p.get("units", "-"),
            data_type=TimeSeriesType(p.get("data_type", "period_total")),
            interpolation=InterpolationType(p.get("interpolation", "step")),
            data=[list(row) for row in p.get("data", [])],
            description=data.get("description", ""),
            element_id=data.get("id"),
            position=tuple(data.get("position", [0.0, 0.0])),
        )
