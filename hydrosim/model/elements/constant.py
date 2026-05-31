"""Constant element — a fixed scalar value that never changes during simulation."""
from __future__ import annotations

import math

from hydrosim.model.base import (
    ElementBase,
    ElementCategory,
    ERR_INVALID_PARAMETER,
    SimState,
    ValidationError,
)


class Constant(ElementBase):
    """A single fixed scalar value. No inputs; one output port 'value'."""

    def __init__(
        self,
        name:        str,
        value:       float = 0.0,
        units:       str   = "-",
        description: str   = "",
        element_id:  str | None = None,
        position:    tuple[float, float] = (0.0, 0.0),
    ):
        self.value = value
        self.units = units
        super().__init__(name=name, description=description,
                         element_id=element_id, position=position)

    # ── ElementBase interface ─────────────────────────────────────────────────

    @property
    def category(self) -> ElementCategory:
        return ElementCategory.INPUT

    def _define_ports(self) -> None:
        self._add_output_port("value", self.units, "The constant scalar value")

    def validate(self) -> list[ValidationError]:
        errors = []
        if not math.isfinite(self.value):
            errors.append(ValidationError(
                code=ERR_INVALID_PARAMETER,
                element_id=self.id,
                message=f"'{self.name}': value must be a finite number (got {self.value})",
            ))
        return errors

    def compute(self, state: SimState, connections_in: dict[str, float]) -> None:
        state.set(self.id, "value", self.value)

    def to_dict(self) -> dict:
        return {
            "id":          self.id,
            "type":        "Constant",
            "name":        self.name,
            "description": self.description,
            "position":    list(self.position),
            "parameters": {
                "value": self.value,
                "units": self.units,
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Constant":
        p = data["parameters"]
        return cls(
            name=data["name"],
            value=p["value"],
            units=p.get("units", "-"),
            description=data.get("description", ""),
            element_id=data.get("id"),
            position=tuple(data.get("position", [0.0, 0.0])),
        )
