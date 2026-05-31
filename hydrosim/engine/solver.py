"""
TimeStepSolver — resolves input values for each element at the current timestep.
Reads from SimState; never writes to it.
Zero PyQt6 dependencies.
"""
from __future__ import annotations

from hydrosim.model.base import ElementBase, SimState


class TimeStepSolver:
    """
    For each element, builds the connections_in dict that element.compute()
    receives: {port_name: summed_value_from_all_incoming_connections}.
    """

    def __init__(self, graph: "ModelGraph"):  # type: ignore[name-defined]
        self.graph = graph

    def resolve_inputs(
        self,
        element: ElementBase,
        state:   SimState,
    ) -> dict[str, float]:
        """
        Build the connections_in dict for element.compute().

        For each input port:
          - Find all connections feeding that port.
          - Sum their source values from state (fan-in support).
          - If no connections and port is optional: omit from dict (element
            uses its default of 0.0 via .get()).
          - Required unconnected ports are caught by the validator before we
            ever reach this point, so no error is raised here.

        Returns {port_name: float_value} for every connected input port.
        """
        result: dict[str, float] = {}

        for port_name in element.input_ports:
            connections = self.graph.get_connections_to_port(element.id, port_name)
            if not connections:
                continue  # optional unconnected port — omit, let element use 0.0

            total = 0.0
            for conn in connections:
                total += state.get(conn.from_element_id, conn.from_port_name)

            result[port_name] = total

        return result
