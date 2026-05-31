"""
ModelValidator — validates a ModelGraph before simulation.
All checks are read-only. Zero PyQt6 dependencies.
"""
from __future__ import annotations

from hydrosim.model.base import (
    ERR_CIRCULAR_DEPENDENCY,
    ERR_MISSING_REQUIRED_INPUT,
    ERR_NO_ELEMENTS,
    ERR_UNKNOWN_REFERENCE,
    WARN_MISSING_DESCRIPTION,
    WARN_UNITS_MISMATCH,
    WARN_TIMESERIES_SHORT,
    ValidationError,
    ValidationWarning,
)

WARN_ISOLATED_ELEMENT = "ISOLATED_ELEMENT"


class ModelValidator:
    """
    Validates a ModelGraph before simulation.
    Call validate_all() to collect every blocking error.
    Call get_warnings() for non-blocking issues that are logged after the run.
    """

    def __init__(self, graph: "ModelGraph"):  # type: ignore[name-defined]
        self.graph = graph

    # ── Public API ────────────────────────────────────────────────────────────

    def validate_all(self) -> list[ValidationError]:
        """
        Run all checks. Returns combined list of errors.
        Simulation must not proceed if this list is non-empty.
        """
        errors: list[ValidationError] = []
        errors.extend(self._check_model_not_empty())
        errors.extend(self._check_element_parameters())
        errors.extend(self._check_required_ports_connected())
        errors.extend(self._check_no_circular_dependencies())
        errors.extend(self._check_expression_references())
        return errors

    def validate_element(self, element_id: str) -> list[ValidationError]:
        """Validate a single element's own parameters. Used by GUI for live feedback."""
        el = self.graph.get_element(element_id)
        return el.validate()

    def get_warnings(
        self,
        settings: "SimulationSettings | None" = None,  # type: ignore[name-defined]
    ) -> list[ValidationWarning]:
        """Non-blocking issues. Simulation proceeds but these are written to the log."""
        warnings: list[ValidationWarning] = []
        warnings.extend(self._warn_isolated_elements())
        warnings.extend(self._warn_units_mismatch())
        warnings.extend(self._warn_timeseries_too_short(settings))
        warnings.extend(self._warn_missing_descriptions())
        return warnings

    def get_isolated_element_ids(self) -> set[str]:
        """
        Return IDs of elements that have no connections whatsoever
        (neither incoming nor outgoing).  These are safe to skip.
        """
        connected: set[str] = set()
        for conn in self.graph.connections.values():
            connected.add(conn.from_element_id)
            connected.add(conn.to_element_id)
        return {eid for eid in self.graph.elements if eid not in connected}

    # ── Blocking checks ───────────────────────────────────────────────────────

    def _check_model_not_empty(self) -> list[ValidationError]:
        if self.graph.element_count == 0:
            return [ValidationError(
                code=ERR_NO_ELEMENTS,
                element_id=None,
                message="Model is empty — add elements before running",
            )]
        return []

    def _check_element_parameters(self) -> list[ValidationError]:
        """Call el.validate() on every element and collect all errors."""
        errors: list[ValidationError] = []
        for el in self.graph.elements.values():
            errors.extend(el.validate())
        return errors

    def _check_required_ports_connected(self) -> list[ValidationError]:
        """
        Every required input port must have at least one incoming connection.
        Exception: completely isolated elements (no connections at all) are
        skipped here — they generate a warning instead and are ignored at runtime.
        """
        isolated = self.get_isolated_element_ids()
        errors: list[ValidationError] = []
        for el in self.graph.elements.values():
            if el.id in isolated:
                continue   # isolated element — checked in _warn_isolated_elements
            for port_name, port in el.input_ports.items():
                if port.required:
                    connections = self.graph.get_connections_to_port(el.id, port_name)
                    if not connections:
                        errors.append(ValidationError(
                            code=ERR_MISSING_REQUIRED_INPUT,
                            element_id=el.id,
                            message=(
                                f"'{el.name}' has unconnected required "
                                f"input port '{port_name}'"
                            ),
                        ))
        return errors

    def _check_no_circular_dependencies(self) -> list[ValidationError]:
        """Detect cycles among non-stock elements."""
        if not self.graph.has_cycle():
            return []

        import networkx as nx
        # Access the internal graph to report the actual cycle paths
        try:
            cycles = list(nx.simple_cycles(self.graph._nx_graph))
        except Exception:
            cycles = []

        # Build human-readable chain
        name_map = {el.id: el.name for el in self.graph.elements.values()}
        cycle_strs = []
        for cycle in cycles:
            chain = " → ".join(name_map.get(eid, eid) for eid in cycle)
            cycle_strs.append(chain)

        return [ValidationError(
            code=ERR_CIRCULAR_DEPENDENCY,
            element_id=None,
            message=(
                f"Circular dependency detected: "
                f"{'; '.join(cycle_strs) if cycle_strs else 'unknown cycle'}"
            ),
        )]

    def _check_expression_references(self) -> list[ValidationError]:
        """
        For every Expression element, verify that every element name referenced
        in its formula actually exists in the graph (case-insensitive).
        """
        from hydrosim.model.elements.expression import Expression
        from hydrosim.engine.parser import ExpressionParser

        isolated = self.get_isolated_element_ids()
        errors: list[ValidationError] = []
        known_names = [el.name for el in self.graph.elements.values()]
        known_lower = {n.lower(): n for n in known_names}

        for el in self.graph.elements.values():
            if not isinstance(el, Expression) or not el.formula:
                continue
            if el.id in isolated:
                continue   # isolated — not used in this run

            refs = ExpressionParser.extract_references(el.formula)
            for ref in refs:
                # Strip dot-notation to get the element name
                element_name = ref.split(".")[0]
                if element_name.lower() not in known_lower:
                    suggestion = ExpressionParser.suggest_correction(
                        element_name, known_names
                    )
                    errors.append(ValidationError(
                        code=ERR_UNKNOWN_REFERENCE,
                        element_id=el.id,
                        message=(
                            f"'{el.name}': formula references unknown "
                            f"element '{element_name}'"
                        ),
                        suggestion=(
                            f"Did you mean '{suggestion}'?" if suggestion else ""
                        ),
                    ))
        return errors

    # ── Warning checks ────────────────────────────────────────────────────────

    def _warn_isolated_elements(self) -> list[ValidationWarning]:
        """
        Warn for every element that has no connections at all.
        These elements exist on the canvas but play no role in the simulation
        and will be silently skipped.
        """
        isolated = self.get_isolated_element_ids()
        warnings = []
        for eid in isolated:
            el = self.graph.elements[eid]
            warnings.append(ValidationWarning(
                code=WARN_ISOLATED_ELEMENT,
                element_id=eid,
                message=(
                    f"'{el.name}' ({el.__class__.__name__}) has no connections "
                    f"and will not be used in this simulation run."
                ),
            ))
        return warnings

    def _warn_units_mismatch(self) -> list[ValidationWarning]:
        """
        For each connection, warn if the source and destination port units differ
        and neither is '-' (dimensionless).
        """
        warnings: list[ValidationWarning] = []
        for conn in self.graph.connections.values():
            from_el = self.graph.get_element(conn.from_element_id)
            to_el   = self.graph.get_element(conn.to_element_id)
            from_port = from_el.output_ports.get(conn.from_port_name)
            to_port   = to_el.input_ports.get(conn.to_port_name)
            if from_port is None or to_port is None:
                continue
            if (
                from_port.units != to_port.units
                and from_port.units != "-"
                and to_port.units  != "-"
            ):
                warnings.append(ValidationWarning(
                    code=WARN_UNITS_MISMATCH,
                    element_id=conn.to_element_id,
                    message=(
                        f"Units mismatch: '{from_el.name}.{conn.from_port_name}' "
                        f"({from_port.units}) → "
                        f"'{to_el.name}.{conn.to_port_name}' ({to_port.units})"
                    ),
                ))
        return warnings

    def _warn_timeseries_too_short(
        self, settings: "SimulationSettings | None"
    ) -> list[ValidationWarning]:
        """Warn if any TimeSeries data doesn't cover the full simulation period."""
        if settings is None:
            return []

        from hydrosim.model.elements.timeseries import TimeSeries
        warnings: list[ValidationWarning] = []

        for el in self.graph.elements.values():
            if not isinstance(el, TimeSeries) or not el.data:
                continue
            data_end = el.data[-1][0]
            if data_end < settings.end_time:
                warnings.append(ValidationWarning(
                    code=WARN_TIMESERIES_SHORT,
                    element_id=el.id,
                    message=(
                        f"'{el.name}': data ends at t={data_end} but simulation "
                        f"runs to t={settings.end_time}. "
                        f"Flat extrapolation will be used."
                    ),
                ))
        return warnings

    def _warn_missing_descriptions(self) -> list[ValidationWarning]:
        """Warn for elements with empty description fields."""
        warnings: list[ValidationWarning] = []
        for el in self.graph.elements.values():
            if not el.description.strip():
                warnings.append(ValidationWarning(
                    code=WARN_MISSING_DESCRIPTION,
                    element_id=el.id,
                    message=f"'{el.name}': description field is empty",
                ))
        return warnings
