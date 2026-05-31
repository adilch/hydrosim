"""WaterStore element — bounded water storage with forward-Euler integration."""
from __future__ import annotations

import math

from hydrosim.model.base import (
    ElementBase,
    ElementCategory,
    ERR_BOUNDS_VIOLATION,
    ERR_INVALID_PARAMETER,
    SimState,
    ValidationError,
)


class WaterStore(ElementBase):
    """
    Integrates net flux (inflow - outflow) over time using forward Euler.
    This is a STATE VARIABLE — its output at timestep t uses its stored
    value from t-1. Call initialise() before the timestep loop.
    """

    def __init__(
        self,
        name:            str,
        initial_storage: float        = 0.0,
        lower_bound:     float        = 0.0,
        upper_bound:     float | None = None,  # None = unbounded
        units:           str          = "m3",
        description:     str          = "",
        element_id:      str | None   = None,
        position:        tuple[float, float] = (0.0, 0.0),
    ):
        self.initial_storage = initial_storage
        self.lower_bound     = lower_bound
        self.upper_bound     = upper_bound
        self.units           = units
        super().__init__(name=name, description=description,
                         element_id=element_id, position=position)

    # ── ElementBase interface ─────────────────────────────────────────────────

    @property
    def category(self) -> ElementCategory:
        return ElementCategory.STOCK

    def is_stock(self) -> bool:
        return True

    def _define_ports(self) -> None:
        rate_units = self.units + "/day"
        self._add_input_port("inflow",   rate_units, "Volume inflow rate",   required=False)
        self._add_input_port("outflow",  rate_units, "Volume outflow rate",  required=False)
        self._add_output_port("storage",  self.units,  "Current storage volume")
        self._add_output_port("overflow", rate_units,  "Overflow rate when upper bound exceeded")
        self._add_output_port("deficit",  rate_units,  "Unmet demand rate when lower bound hit")

    def validate(self) -> list[ValidationError]:
        errors = []
        if not math.isfinite(self.lower_bound):
            errors.append(ValidationError(
                code=ERR_INVALID_PARAMETER,
                element_id=self.id,
                message=f"'{self.name}': lower_bound must be a finite number",
            ))
        if self.upper_bound is not None:
            if not math.isfinite(self.upper_bound):
                errors.append(ValidationError(
                    code=ERR_INVALID_PARAMETER,
                    element_id=self.id,
                    message=f"'{self.name}': upper_bound must be a finite number",
                ))
            elif self.upper_bound <= self.lower_bound:
                errors.append(ValidationError(
                    code=ERR_INVALID_PARAMETER,
                    element_id=self.id,
                    message=(
                        f"'{self.name}': upper_bound ({self.upper_bound}) must be "
                        f"greater than lower_bound ({self.lower_bound})"
                    ),
                ))
            elif not (self.lower_bound <= self.initial_storage <= self.upper_bound):
                errors.append(ValidationError(
                    code=ERR_BOUNDS_VIOLATION,
                    element_id=self.id,
                    message=(
                        f"'{self.name}': initial_storage ({self.initial_storage}) "
                        f"outside bounds [{self.lower_bound}, {self.upper_bound}]"
                    ),
                ))
        else:
            if self.initial_storage < self.lower_bound:
                errors.append(ValidationError(
                    code=ERR_BOUNDS_VIOLATION,
                    element_id=self.id,
                    message=(
                        f"'{self.name}': initial_storage ({self.initial_storage}) "
                        f"is below lower_bound ({self.lower_bound})"
                    ),
                ))
        return errors

    def initialise(self, state: SimState) -> None:
        """Set initial storage in state before the timestep loop begins."""
        state.storage[self.id] = self.initial_storage
        state.set(self.id, "storage",  self.initial_storage)
        state.set(self.id, "overflow", 0.0)
        state.set(self.id, "deficit",  0.0)

    def compute(self, state: SimState, connections_in: dict[str, float]) -> None:
        """
        Forward Euler integration.
        Reads previous storage from state.storage (NOT state.get) to avoid
        reading a value written in the same timestep.
        """
        s_prev  = state.storage[self.id]
        inflow  = connections_in.get("inflow",  0.0)
        outflow = connections_in.get("outflow", 0.0)

        s_new = s_prev + (inflow - outflow) * state.dt

        # Upper bound — compute overflow before clamping
        if self.upper_bound is not None and s_new > self.upper_bound:
            overflow = (s_new - self.upper_bound) / state.dt
            s_new    = self.upper_bound
        else:
            overflow = 0.0

        # Lower bound — compute deficit before clamping
        if s_new < self.lower_bound:
            deficit = (self.lower_bound - s_new) / state.dt
            s_new   = self.lower_bound
        else:
            deficit = 0.0

        state.storage[self.id] = s_new
        state.set(self.id, "storage",  s_new)
        state.set(self.id, "overflow", overflow)
        state.set(self.id, "deficit",  deficit)

    def get_water_balance_error(
        self,
        s_prev:          float,
        s_new:           float,
        inflow:          float,
        outflow:         float,
        overflow:        float,
        deficit:         float,
        dt:              float,
    ) -> float:
        """
        Returns |ΔS - (inflow - outflow - overflow + deficit) * dt|.
        Should be ~0.0 for correct integration. Used by the runner for diagnostics.
        """
        delta_s   = s_new - s_prev
        net_flux  = (inflow - outflow - overflow + deficit) * dt
        return abs(delta_s - net_flux)

    def to_dict(self) -> dict:
        return {
            "id":          self.id,
            "type":        "WaterStore",
            "name":        self.name,
            "description": self.description,
            "position":    list(self.position),
            "parameters": {
                "initial_storage": self.initial_storage,
                "lower_bound":     self.lower_bound,
                "upper_bound":     self.upper_bound,   # None serialises as JSON null
                "units":           self.units,
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WaterStore":
        p = data["parameters"]
        return cls(
            name=data["name"],
            initial_storage=p.get("initial_storage", 0.0),
            lower_bound=p.get("lower_bound", 0.0),
            upper_bound=p.get("upper_bound"),  # None if absent or null
            units=p.get("units", "m3"),
            description=data.get("description", ""),
            element_id=data.get("id"),
            position=tuple(data.get("position", [0.0, 0.0])),
        )
