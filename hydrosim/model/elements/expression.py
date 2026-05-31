"""Expression element — evaluates a user-defined formula at each timestep."""
from __future__ import annotations

from hydrosim.model.base import (
    ElementBase,
    ElementCategory,
    ERR_INVALID_FORMULA,
    SimState,
    ValidationError,
)


class Expression(ElementBase):
    """
    Computes a scalar output from a formula referencing other elements.
    Input ports are dynamic — rebuilt whenever the formula changes.
    Call prepare() once before the simulation loop.
    """

    def __init__(
        self,
        name:         str,
        formula:      str = "",
        output_units: str = "-",
        description:  str = "",
        element_id:   str | None = None,
        position:     tuple[float, float] = (0.0, 0.0),
    ):
        self.formula      = formula
        self.output_units = output_units
        self._prepared    = False
        self._parser      = None
        # super().__init__ calls _define_ports(), then we rebuild dynamic ports
        super().__init__(name=name, description=description,
                         element_id=element_id, position=position)
        if self.formula:
            self.rebuild_input_ports()

    # ── ElementBase interface ─────────────────────────────────────────────────

    @property
    def category(self) -> ElementCategory:
        return ElementCategory.EXPRESSION

    def _define_ports(self) -> None:
        # Only the fixed output port; inputs are added dynamically
        self._add_output_port("value", self.output_units, "Formula result")

    def set_formula(self, formula: str) -> None:
        """Update the formula and rebuild dynamic input ports."""
        self.formula   = formula
        self._prepared = False
        self._parser   = None
        self.rebuild_input_ports()

    def rebuild_input_ports(self) -> None:
        """
        Parse the formula, find all element name references, and create
        one input port per unique reference. Idempotent — safe to call
        multiple times.
        """
        # Import here to keep the engine dependency lazy
        from hydrosim.engine.parser import ExpressionParser
        self._input_ports.clear()
        if not self.formula:
            return
        refs = ExpressionParser.extract_references(self.formula)
        for ref in refs:
            self._add_input_port(
                name=ref,
                units="-",
                description=f"Input from {ref}",
                required=True,
            )

    def validate(self) -> list[ValidationError]:
        from hydrosim.engine.parser import ExpressionParser
        errors = []
        if not self.formula.strip():
            errors.append(ValidationError(
                code=ERR_INVALID_FORMULA,
                element_id=self.id,
                message=f"'{self.name}': formula is empty",
            ))
            return errors
        syntax_errors = ExpressionParser.validate_syntax(self.formula)
        for msg in syntax_errors:
            errors.append(ValidationError(
                code=ERR_INVALID_FORMULA,
                element_id=self.id,
                message=f"'{self.name}': {msg}",
            ))
        return errors

    def prepare(self, name_to_id: dict[str, str]) -> None:
        """
        Build the ExpressionParser with the element name→ID mapping.
        Must be called by the runner before the timestep loop.
        """
        from hydrosim.engine.parser import ExpressionParser
        self._parser   = ExpressionParser(self.formula, name_to_id)
        self._prepared = True

    def compute(self, state: SimState, connections_in: dict[str, float]) -> None:
        if not self._prepared:
            raise RuntimeError(
                f"Expression '{self.name}': prepare() must be called before compute()"
            )
        import logging
        try:
            result = self._parser.evaluate(connections_in, state.t, state.dt)
        except Exception as exc:
            logging.warning("Expression '%s' at t=%.3f: %s — using 0.0", self.name, state.t, exc)
            result = 0.0
        state.set(self.id, "value", result)

    def evaluate_test(
        self,
        input_values: dict[str, float],
        t:  float = 0.0,
        dt: float = 1.0,
    ) -> float:
        """
        Evaluate with provided values — used by the GUI Test button.
        Raises ExpressionEvaluationError on failure.
        """
        from hydrosim.engine.parser import ExpressionParser
        # Build a temporary parser with identity name mapping
        name_to_id = {k.lower(): k for k in input_values}
        parser = ExpressionParser(self.formula, name_to_id)
        return parser.evaluate(input_values, t, dt)

    def to_dict(self) -> dict:
        # Input ports are NOT persisted — they're rebuilt from the formula on load
        return {
            "id":          self.id,
            "type":        "Expression",
            "name":        self.name,
            "description": self.description,
            "position":    list(self.position),
            "parameters": {
                "formula":      self.formula,
                "output_units": self.output_units,
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Expression":
        p = data["parameters"]
        return cls(
            name=data["name"],
            formula=p.get("formula", ""),
            output_units=p.get("output_units", "-"),
            description=data.get("description", ""),
            element_id=data.get("id"),
            position=tuple(data.get("position", [0.0, 0.0])),
        )
