"""TimeHistoryResult element — collects time histories for display as hydrographs."""
from __future__ import annotations

from hydrosim.model.base import (
    ElementBase,
    ElementCategory,
    ERR_INVALID_PARAMETER,
    SimState,
    ValidationError,
)


class TimeHistoryResult(ElementBase):
    """
    Terminal/sink element. Collects connected outputs during simulation.
    compute() is a no-op — the ResultsStore handles data recording.
    New series ports are added dynamically as connections are made.
    """

    MAX_SERIES = 8

    def __init__(
        self,
        name:         str,
        title:        str        = "",
        y_axis_label: str        = "",
        y_axis_units: str        = "-",
        show_grid:    bool       = True,
        y_min:        float | None = None,
        y_max:        float | None = None,
        description:  str        = "",
        element_id:   str | None = None,
        position:     tuple[float, float] = (0.0, 0.0),
    ):
        self.title        = title
        self.y_axis_label = y_axis_label
        self.y_axis_units = y_axis_units
        self.show_grid    = show_grid
        self.y_min        = y_min
        self.y_max        = y_max
        super().__init__(name=name, description=description,
                         element_id=element_id, position=position)

    # ── ElementBase interface ─────────────────────────────────────────────────

    @property
    def category(self) -> ElementCategory:
        return ElementCategory.RESULT

    def _define_ports(self) -> None:
        self._add_input_port("series_1", "-", "First time series to display", required=True)

    def add_series_port(self) -> str:
        """
        Add the next series input port (series_2, series_3 …).
        Called by ModelGraph when the current last port gets connected.
        Returns the new port name.
        """
        n = len(self._input_ports) + 1
        if n > self.MAX_SERIES:
            raise ValueError(f"Maximum {self.MAX_SERIES} series per TimeHistoryResult")
        port_name = f"series_{n}"
        self._add_input_port(port_name, "-", f"Series {n} to display", required=False)
        return port_name

    def validate(self) -> list[ValidationError]:
        errors = []
        if self.y_min is not None and self.y_max is not None:
            if self.y_min >= self.y_max:
                errors.append(ValidationError(
                    code=ERR_INVALID_PARAMETER,
                    element_id=self.id,
                    message=(
                        f"'{self.name}': y_min ({self.y_min}) must be "
                        f"less than y_max ({self.y_max})"
                    ),
                ))
        return errors

    def compute(self, state: SimState, connections_in: dict[str, float]) -> None:
        """No-op — data recording is handled by ResultsStore."""

    def to_dict(self) -> dict:
        return {
            "id":          self.id,
            "type":        "TimeHistoryResult",
            "name":        self.name,
            "description": self.description,
            "position":    list(self.position),
            "parameters": {
                "title":        self.title,
                "y_axis_label": self.y_axis_label,
                "y_axis_units": self.y_axis_units,
                "show_grid":    self.show_grid,
                "y_min":        self.y_min,
                "y_max":        self.y_max,
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TimeHistoryResult":
        p = data["parameters"]
        return cls(
            name=data["name"],
            title=p.get("title", ""),
            y_axis_label=p.get("y_axis_label", ""),
            y_axis_units=p.get("y_axis_units", "-"),
            show_grid=p.get("show_grid", True),
            y_min=p.get("y_min"),
            y_max=p.get("y_max"),
            description=data.get("description", ""),
            element_id=data.get("id"),
            position=tuple(data.get("position", [0.0, 0.0])),
        )
