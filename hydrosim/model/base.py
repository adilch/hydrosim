"""
Core data structures, enums, error types, and the ElementBase abstract class.
Zero PyQt6 dependencies — pure Python throughout.
"""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from enum import Enum, auto
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    pass


# ── Enums ──────────────────────────────────────────────────────────────────────

class PortType(Enum):
    INPUT  = auto()
    OUTPUT = auto()


class ElementCategory(Enum):
    INPUT      = "input"
    STOCK      = "stock"
    EXPRESSION = "expression"
    RESULT     = "result"


class TimeSeriesType(Enum):
    INSTANTANEOUS  = "instantaneous"
    PERIOD_TOTAL   = "period_total"
    PERIOD_AVERAGE = "period_average"


class InterpolationType(Enum):
    LINEAR = "linear"
    STEP   = "step"


# ── Core dataclasses ───────────────────────────────────────────────────────────

@dataclass
class Port:
    name:        str
    port_type:   PortType
    units:       str
    description: str
    required:    bool

    # Runtime value — not persisted, not compared
    _current_value: float = field(default=0.0, repr=False, compare=False)


@dataclass
class Connection:
    id:              str
    from_element_id: str
    from_port_name:  str
    to_element_id:   str
    to_port_name:    str

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())


@dataclass
class SimulationSettings:
    start_time: float
    end_time:   float
    dt:         float
    time_mode:  str          # "elapsed" | "calendar"
    start_date: date | None  # only used when time_mode == "calendar"

    @property
    def n_steps(self) -> int:
        return int(round((self.end_time - self.start_time) / self.dt))

    @property
    def timesteps(self) -> np.ndarray:
        """Array of time values at the start of each step."""
        return np.linspace(self.start_time, self.end_time, self.n_steps, endpoint=False)


@dataclass
class SimState:
    t:       float
    dt:      float
    step:    int
    values:  dict[str, dict[str, float]]  # values[element_id][port_name]
    storage: dict[str, float]             # storage[element_id] for stock elements

    def get(self, element_id: str, port_name: str) -> float:
        """Safe read — returns 0.0 if the key is not yet present."""
        return self.values.get(element_id, {}).get(port_name, 0.0)

    def set(self, element_id: str, port_name: str, value: float) -> None:
        if element_id not in self.values:
            self.values[element_id] = {}
        self.values[element_id][port_name] = value


# ── Validation result types (data objects, NOT exceptions) ────────────────────

@dataclass
class ValidationError:
    code:       str
    element_id: str | None
    message:    str
    suggestion: str = ""


@dataclass
class ValidationWarning:
    code:       str
    element_id: str | None
    message:    str


# Error code constants
ERR_NO_ELEMENTS            = "NO_ELEMENTS"
ERR_MISSING_REQUIRED_INPUT = "MISSING_REQUIRED_INPUT"
ERR_CIRCULAR_DEPENDENCY    = "CIRCULAR_DEPENDENCY"
ERR_INVALID_FORMULA        = "INVALID_FORMULA"
ERR_UNKNOWN_REFERENCE      = "UNKNOWN_REFERENCE"
ERR_INVALID_PARAMETER      = "INVALID_PARAMETER"
ERR_EMPTY_TIMESERIES       = "EMPTY_TIMESERIES"
ERR_BOUNDS_VIOLATION       = "BOUNDS_VIOLATION"

# Warning code constants
WARN_UNITS_MISMATCH      = "UNITS_MISMATCH"
WARN_TIMESERIES_SHORT    = "TIMESERIES_SHORT"
WARN_MISSING_DESCRIPTION = "MISSING_DESCRIPTION"
WARN_WATER_BALANCE_ERROR = "WATER_BALANCE_ERROR"


# ── Exception hierarchy ────────────────────────────────────────────────────────

class HydroSimError(Exception):
    """Base for all HydroSim exceptions."""


class SimulationError(HydroSimError):
    """Raised when model validation fails before simulation starts."""
    def __init__(self, errors: list[ValidationError]):
        self.errors = errors
        super().__init__(f"{len(errors)} validation error(s)")


class SimulationAborted(HydroSimError):
    """Raised when stop() is called during a run."""
    def __init__(self, step: int, t: float):
        self.step = step
        self.t    = t
        super().__init__(f"Simulation aborted at step {step} (t={t:.2f})")


class CircularDependencyError(HydroSimError):
    """Raised by ModelGraph when a cycle is detected among non-stock elements."""
    def __init__(self, cycles: list[list[str]]):
        self.cycles = cycles
        super().__init__(f"Circular dependency: {cycles}")


class ExpressionEvaluationError(HydroSimError):
    """Raised by ExpressionParser when formula evaluation fails."""


class ModelFileError(HydroSimError):
    """Raised by ModelSerialiser when a file cannot be parsed."""


class VersionMismatchError(HydroSimError):
    """Raised when file_format_version > CURRENT_FORMAT_VERSION."""
    def __init__(self, file_version: str, current_version: str):
        self.file_version    = file_version
        self.current_version = current_version
        super().__init__(
            f"File requires HydroSim format v{file_version}; "
            f"this version supports up to v{current_version}"
        )


# ── ElementBase abstract class ────────────────────────────────────────────────

class ElementBase(ABC):
    """
    Abstract base class for all HydroSim elements.
    Subclass this for each element type — never instantiate directly.
    """

    def __init__(
        self,
        name:        str,
        description: str = "",
        element_id:  str | None = None,
        position:    tuple[float, float] = (0.0, 0.0),
    ):
        self.id:          str                 = element_id or str(uuid.uuid4())
        self.name:        str                 = name
        self.description: str                 = description
        self.position:    tuple[float, float] = position

        self._input_ports:  dict[str, Port] = {}
        self._output_ports: dict[str, Port] = {}

        # Subclass version of _define_ports() is called here via Python MRO.
        self._define_ports()

    # ── Port definition ───────────────────────────────────────────────────────

    @abstractmethod
    def _define_ports(self) -> None:
        """
        Populate ports by calling _add_input_port() / _add_output_port().
        Called exactly once during __init__.
        """

    def _add_input_port(
        self, name: str, units: str, description: str, required: bool = False
    ) -> None:
        self._input_ports[name] = Port(name, PortType.INPUT, units, description, required)

    def _add_output_port(self, name: str, units: str, description: str) -> None:
        self._output_ports[name] = Port(
            name, PortType.OUTPUT, units, description, required=False
        )

    # ── Port accessors ────────────────────────────────────────────────────────

    @property
    def input_ports(self) -> dict[str, Port]:
        return dict(self._input_ports)

    @property
    def output_ports(self) -> dict[str, Port]:
        return dict(self._output_ports)

    @property
    def all_ports(self) -> dict[str, Port]:
        return {**self._input_ports, **self._output_ports}

    def get_port(self, name: str) -> Port | None:
        return self.all_ports.get(name)

    # ── Abstract interface ────────────────────────────────────────────────────

    @property
    @abstractmethod
    def category(self) -> ElementCategory:
        """Return the ElementCategory for this element type."""

    @abstractmethod
    def validate(self) -> list[ValidationError]:
        """
        Validate element parameters independently of graph connections.
        Returns a list of ValidationError; empty list means valid.
        """

    @abstractmethod
    def compute(self, state: SimState, connections_in: dict[str, float]) -> None:
        """
        Compute outputs for the current timestep and write them to state.

        Args:
            state:           Current SimState. Read previous stock values from
                             state.storage; write outputs via state.set().
            connections_in:  {port_name: value} resolved by the solver.

        Must call state.set(self.id, port_name, value) for every output port.
        """

    @abstractmethod
    def to_dict(self) -> dict:
        """
        Serialise to a JSON-compatible dict.
        Must include: id, type (class name string), name, description,
        position, and a 'parameters' sub-dict.
        """

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict) -> "ElementBase":
        """Deserialise from a dict produced by to_dict()."""

    # ── Concrete helpers ──────────────────────────────────────────────────────

    def is_stock(self) -> bool:
        """True for stock elements (WaterStore) that carry state across timesteps."""
        return False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id!r}, name={self.name!r})"
