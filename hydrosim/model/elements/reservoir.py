"""
Reservoir element — a bounded water storage with elevation-volume (E-V)
and optional elevation-area (E-A) bathymetry curves.

Extends the WaterStore concept with:
  • Separate volume units and flow units
  • Bathymetry table [[elevation, volume, area?], …]
  • Dynamic output ports: 'level' added when E-V data present,
    'area' added when E-A data present
  • prepare() builds SciPy interpolators before the simulation loop
"""
from __future__ import annotations

import math
from typing import Optional

from hydrosim.model.base import (
    ElementBase,
    ElementCategory,
    ERR_BOUNDS_VIOLATION,
    ERR_INVALID_PARAMETER,
    SimState,
    ValidationError,
)

# Common unit presets shown in the dialog dropdowns
VOLUME_UNITS = ["m3", "ML", "GL", "Mm3", "acre-ft", "ft3"]
FLOW_UNITS   = ["m3/day", "ML/day", "GL/day", "m3/s", "ML/s", "cfs"]


class Reservoir(ElementBase):
    """
    Bounded reservoir with optional bathymetry-based level and area computation.

    Integration rule (same as WaterStore — forward Euler):
        V_new = V_prev + (inflow - outflow) × dt

    Level and area are derived from the bathymetry table via linear interpolation.
    Port availability:
        'level'  — present only when bathymetry has ≥2 valid [elevation, volume] rows
        'area'   — present only when bathymetry has ≥2 valid [elevation, area] rows
    Call rebuild_output_ports() after changing self.bathymetry.
    """

    def __init__(
        self,
        name:           str,
        initial_volume: float               = 0.0,
        min_volume:     float               = 0.0,
        max_volume:     Optional[float]     = None,
        volume_units:   str                 = "m3",
        flow_units:     str                 = "m3/day",
        bathymetry:     list[list] | None   = None,
        description:    str                 = "",
        element_id:     str | None          = None,
        position:       tuple[float, float] = (0.0, 0.0),
    ):
        self.initial_volume = initial_volume
        self.min_volume     = min_volume
        self.max_volume     = max_volume
        self.volume_units   = volume_units
        self.flow_units     = flow_units
        # bathymetry rows: [elevation, volume, area?]  — sorted by elevation internally
        self.bathymetry: list[list] = bathymetry or []

        self._ev_interp = None   # volume  → elevation
        self._ea_interp = None   # elevation → area
        self._prepared  = False

        super().__init__(name=name, description=description,
                         element_id=element_id, position=position)

    # ── ElementBase interface ─────────────────────────────────────────────────

    @property
    def category(self) -> ElementCategory:
        return ElementCategory.STOCK

    def is_stock(self) -> bool:
        return True

    def _define_ports(self) -> None:
        """Build all ports. Called once during __init__."""
        rate_units = self.flow_units
        self._add_input_port("inflow",  rate_units, "Inflow rate",  required=False)
        self._add_input_port("outflow", rate_units, "Outflow rate", required=False)
        self._add_output_port("volume",   self.volume_units, "Stored volume")
        self._add_output_port("overflow", rate_units,        "Spill rate when max exceeded")
        self._add_output_port("deficit",  rate_units,        "Unmet demand when min hit")
        # Dynamic ports
        if self._has_ev_data():
            self._add_output_port("level", "m", "Water surface elevation (E-V curve)")
        if self._has_ea_data():
            self._add_output_port("area",  "m2", "Water surface area (E-A curve)")

    def rebuild_output_ports(self) -> None:
        """
        Called by the dialog after bathymetry data changes to update which
        output ports are available. Canvas card must be refreshed after this.
        """
        self._output_ports.pop("level", None)
        self._output_ports.pop("area",  None)
        if self._has_ev_data():
            self._add_output_port("level", "m",  "Water surface elevation (E-V curve)")
        if self._has_ea_data():
            self._add_output_port("area",  "m2", "Water surface area (E-A curve)")
        self._prepared  = False
        self._ev_interp = None
        self._ea_interp = None

    # ── Data helpers ──────────────────────────────────────────────────────────

    def _valid_ev_rows(self) -> list[tuple[float, float]]:
        """Return [(elevation, volume)] from non-empty rows, sorted by elevation."""
        rows = []
        for r in self.bathymetry:
            if len(r) >= 2 and r[0] is not None and r[1] is not None:
                try:
                    rows.append((float(r[0]), float(r[1])))
                except (TypeError, ValueError):
                    pass
        return sorted(rows, key=lambda x: x[0])

    def _valid_ea_rows(self) -> list[tuple[float, float]]:
        """Return [(elevation, area)] from rows that have a non-None area value."""
        rows = []
        for r in self.bathymetry:
            if len(r) >= 3 and r[0] is not None and r[2] is not None:
                try:
                    rows.append((float(r[0]), float(r[2])))
                except (TypeError, ValueError):
                    pass
        return sorted(rows, key=lambda x: x[0])

    def _has_ev_data(self) -> bool:
        return len(self._valid_ev_rows()) >= 2

    def _has_ea_data(self) -> bool:
        return len(self._valid_ea_rows()) >= 2

    # ── Simulation lifecycle ──────────────────────────────────────────────────

    def prepare(self) -> None:
        """
        Build scipy interpolators from bathymetry data.
        Called by SimulationRunner._prepare_elements() before the timestep loop.
        """
        from scipy.interpolate import interp1d

        ev_rows = self._valid_ev_rows()
        if len(ev_rows) >= 2:
            elevs = [r[0] for r in ev_rows]
            vols  = [r[1] for r in ev_rows]
            # Sort by volume (ascending) for the volume→elevation lookup
            vol_elev = sorted(zip(vols, elevs), key=lambda x: x[0])
            v_sorted = [p[0] for p in vol_elev]
            e_sorted = [p[1] for p in vol_elev]
            self._ev_interp = interp1d(
                v_sorted, e_sorted,
                kind="linear",
                bounds_error=False,
                fill_value=(e_sorted[0], e_sorted[-1]),
            )

        ea_rows = self._valid_ea_rows()
        if len(ea_rows) >= 2:
            e_pts = [r[0] for r in ea_rows]
            a_pts = [r[1] for r in ea_rows]
            self._ea_interp = interp1d(
                e_pts, a_pts,
                kind="linear",
                bounds_error=False,
                fill_value=(a_pts[0], a_pts[-1]),
            )

        self._prepared = True

    def get_level_at(self, volume: float) -> float:
        """
        Public: water surface elevation at given volume.
        Calls prepare() internally if not yet prepared (for GUI preview).
        """
        if not self._prepared:
            self.prepare()
        if self._ev_interp is None:
            return 0.0
        return float(self._ev_interp(volume))

    def get_area_at(self, volume: float) -> float:
        """Public: surface area at given volume (via level as intermediary)."""
        if not self._prepared:
            self.prepare()
        if self._ev_interp is None or self._ea_interp is None:
            return 0.0
        level = float(self._ev_interp(volume))
        return float(self._ea_interp(level))

    def initialise(self, state: SimState) -> None:
        """Set initial conditions before the timestep loop."""
        state.storage[self.id] = self.initial_volume
        state.set(self.id, "volume",   self.initial_volume)
        state.set(self.id, "overflow", 0.0)
        state.set(self.id, "deficit",  0.0)
        if "level" in self._output_ports:
            state.set(self.id, "level", self.get_level_at(self.initial_volume))
        if "area" in self._output_ports:
            state.set(self.id, "area", self.get_area_at(self.initial_volume))

    def compute(self, state: SimState, connections_in: dict[str, float]) -> None:
        """Forward-Euler integration + level/area computation."""
        V_prev  = state.storage[self.id]
        inflow  = connections_in.get("inflow",  0.0)
        outflow = connections_in.get("outflow", 0.0)

        V_new = V_prev + (inflow - outflow) * state.dt

        # Upper bound → spill
        if self.max_volume is not None and V_new > self.max_volume:
            overflow = (V_new - self.max_volume) / state.dt
            V_new    = self.max_volume
        else:
            overflow = 0.0

        # Lower bound → deficit
        if V_new < self.min_volume:
            deficit = (self.min_volume - V_new) / state.dt
            V_new   = self.min_volume
        else:
            deficit = 0.0

        state.storage[self.id] = V_new
        state.set(self.id, "volume",   V_new)
        state.set(self.id, "overflow", overflow)
        state.set(self.id, "deficit",  deficit)

        if "level" in self._output_ports:
            level = float(self._ev_interp(V_new)) if self._ev_interp else 0.0
            state.set(self.id, "level", level)
            if "area" in self._output_ports:
                area = float(self._ea_interp(level)) if self._ea_interp else 0.0
                state.set(self.id, "area", area)

    # ── Validation ────────────────────────────────────────────────────────────

    def validate(self) -> list[ValidationError]:
        errors = []

        for name, val in [("initial_volume", self.initial_volume),
                          ("min_volume",     self.min_volume)]:
            if not math.isfinite(val):
                errors.append(ValidationError(
                    code=ERR_INVALID_PARAMETER, element_id=self.id,
                    message=f"'{self.name}': {name} must be a finite number",
                ))

        if self.max_volume is not None:
            if not math.isfinite(self.max_volume):
                errors.append(ValidationError(
                    code=ERR_INVALID_PARAMETER, element_id=self.id,
                    message=f"'{self.name}': max_volume must be a finite number",
                ))
            elif self.max_volume <= self.min_volume:
                errors.append(ValidationError(
                    code=ERR_INVALID_PARAMETER, element_id=self.id,
                    message=f"'{self.name}': max_volume must be greater than min_volume",
                ))
            elif not (self.min_volume <= self.initial_volume <= self.max_volume):
                errors.append(ValidationError(
                    code=ERR_BOUNDS_VIOLATION, element_id=self.id,
                    message=(f"'{self.name}': initial_volume ({self.initial_volume}) "
                             f"is outside bounds [{self.min_volume}, {self.max_volume}]"),
                ))
        elif self.initial_volume < self.min_volume:
            errors.append(ValidationError(
                code=ERR_BOUNDS_VIOLATION, element_id=self.id,
                message=(f"'{self.name}': initial_volume ({self.initial_volume}) "
                         f"is below min_volume ({self.min_volume})"),
            ))

        # Bathymetry checks
        ev_rows = self._valid_ev_rows()
        if len(ev_rows) >= 2:
            elevs = [r[0] for r in ev_rows]
            vols  = [r[1] for r in ev_rows]
            for i in range(1, len(elevs)):
                if elevs[i] <= elevs[i - 1]:
                    errors.append(ValidationError(
                        code=ERR_INVALID_PARAMETER, element_id=self.id,
                        message=f"'{self.name}': bathymetry elevations must be strictly increasing",
                    ))
                    break
            for i in range(1, len(vols)):
                if vols[i] < vols[i - 1]:
                    errors.append(ValidationError(
                        code=ERR_INVALID_PARAMETER, element_id=self.id,
                        message=f"'{self.name}': bathymetry volumes must be non-decreasing",
                    ))
                    break

        return errors

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "id":          self.id,
            "type":        "Reservoir",
            "name":        self.name,
            "description": self.description,
            "position":    list(self.position),
            "parameters": {
                "initial_volume": self.initial_volume,
                "min_volume":     self.min_volume,
                "max_volume":     self.max_volume,
                "volume_units":   self.volume_units,
                "flow_units":     self.flow_units,
                "bathymetry":     [list(r) for r in self.bathymetry],
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Reservoir":
        p = data["parameters"]
        return cls(
            name=data["name"],
            initial_volume=p.get("initial_volume", 0.0),
            min_volume=p.get("min_volume",     0.0),
            max_volume=p.get("max_volume"),
            volume_units=p.get("volume_units", "m3"),
            flow_units=p.get("flow_units",   "m3/day"),
            bathymetry=[list(r) for r in p.get("bathymetry", [])],
            description=data.get("description", ""),
            element_id=data.get("id"),
            position=tuple(data.get("position", [0.0, 0.0])),
        )
