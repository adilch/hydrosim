"""
ModelGraph — owns all elements and connections.
Maintains a NetworkX DiGraph for dependency analysis and topological sort.
All model mutations go through this class.
Zero PyQt6 dependencies.
"""
from __future__ import annotations

import networkx as nx

from hydrosim.model.base import (
    CircularDependencyError,
    Connection,
    ElementBase,
    ValidationError,
)


class ModelGraph:
    """
    Single source of truth for the model structure.
    The GUI canvas is a visual representation of this object.
    """

    def __init__(self):
        self._elements:    dict[str, ElementBase] = {}
        self._connections: dict[str, Connection]  = {}
        # NetworkX graph for dependency analysis.
        # Edges represent "must be computed after" relationships.
        # Stock element outputs do NOT create edges (they provide prev-step values).
        self._nx_graph: nx.DiGraph = nx.DiGraph()

    # ── Element management ────────────────────────────────────────────────────

    def add_element(self, element: ElementBase) -> None:
        """
        Add an element to the graph.
        Raises ValueError if element.id already exists.
        """
        if element.id in self._elements:
            raise ValueError(
                f"Element with id '{element.id}' already exists in graph"
            )
        self._elements[element.id] = element
        self._nx_graph.add_node(element.id, element=element)

    def remove_element(self, element_id: str) -> None:
        """
        Remove an element and all its connections from the graph.
        Raises KeyError if not found.
        """
        if element_id not in self._elements:
            raise KeyError(f"Element '{element_id}' not found")

        # Remove all connections touching this element first
        conn_ids = [
            c.id for c in self._connections.values()
            if c.from_element_id == element_id or c.to_element_id == element_id
        ]
        for cid in conn_ids:
            self.remove_connection(cid)

        del self._elements[element_id]
        self._nx_graph.remove_node(element_id)

    def get_element(self, element_id: str) -> ElementBase:
        """Raises KeyError if not found."""
        return self._elements[element_id]

    def get_element_by_name(self, name: str) -> ElementBase | None:
        """Case-insensitive search by element name. Returns None if not found."""
        name_lower = name.lower()
        for el in self._elements.values():
            if el.name.lower() == name_lower:
                return el
        return None

    def rename_element(self, element_id: str, new_name: str) -> None:
        """
        Rename an element.
        Raises ValueError if new_name is already taken by another element.
        """
        element = self._elements[element_id]
        # Check uniqueness (case-insensitive)
        existing = self.get_element_by_name(new_name)
        if existing is not None and existing.id != element_id:
            raise ValueError(
                f"Element name '{new_name}' is already used by '{existing.id}'"
            )
        element.name = new_name

        # Rebuild input ports on any Expression that references the old name
        old_name = element.name
        from hydrosim.model.elements.expression import Expression
        for el in self._elements.values():
            if isinstance(el, Expression) and el.formula:
                # Simple string replacement in formula, then rebuild ports
                if old_name in el.formula:
                    el.set_formula(el.formula.replace(old_name, new_name))

    @property
    def elements(self) -> dict[str, ElementBase]:
        """Return a shallow copy — never expose the internal dict."""
        return dict(self._elements)

    @property
    def element_count(self) -> int:
        return len(self._elements)

    # ── Connection management ─────────────────────────────────────────────────

    def add_connection(self, connection: Connection) -> None:
        """
        Add a connection between elements after full validation.

        Validates:
          1. Both element IDs exist
          2. from_port_name is an output port on the source element
          3. to_port_name is an input port on the destination element
          4. The destination port is not already connected
          5. Not a self-loop (same element on both ends)
          6. Would not create a cycle among non-stock elements

        After adding:
          - Updates the NetworkX graph (unless source is a stock element)
          - Auto-adds a new series port on TimeHistoryResult if needed
        """
        from_elem = self._elements.get(connection.from_element_id)
        to_elem   = self._elements.get(connection.to_element_id)

        if from_elem is None:
            raise ValueError(
                f"Source element '{connection.from_element_id}' not found in graph"
            )
        if to_elem is None:
            raise ValueError(
                f"Destination element '{connection.to_element_id}' not found in graph"
            )
        if connection.from_element_id == connection.to_element_id:
            raise ValueError("Cannot connect an element to itself")

        if connection.from_port_name not in from_elem.output_ports:
            raise ValueError(
                f"'{from_elem.name}' has no output port '{connection.from_port_name}'. "
                f"Available: {list(from_elem.output_ports)}"
            )
        if connection.to_port_name not in to_elem.input_ports:
            raise ValueError(
                f"'{to_elem.name}' has no input port '{connection.to_port_name}'. "
                f"Available: {list(to_elem.input_ports)}"
            )

        # Input ports accept exactly one incoming connection
        existing = self.get_connections_to_port(
            connection.to_element_id, connection.to_port_name
        )
        if existing:
            raise ValueError(
                f"Input port '{connection.to_port_name}' on '{to_elem.name}' "
                f"is already connected"
            )

        # Cycle check — only applies to non-stock sources
        if self._should_add_nx_edge(from_elem):
            self._nx_graph.add_edge(
                connection.from_element_id,
                connection.to_element_id,
                connection_id=connection.id,
            )
            if not nx.is_directed_acyclic_graph(self._nx_graph):
                # Roll back the edge we just added
                self._nx_graph.remove_edge(
                    connection.from_element_id, connection.to_element_id
                )
                raise ValueError(
                    f"Connection from '{from_elem.name}' to '{to_elem.name}' "
                    f"would create a circular dependency"
                )

        self._connections[connection.id] = connection

        # Auto-add next series port on TimeHistoryResult when the current last
        # port gets connected and we haven't hit MAX_SERIES yet.
        from hydrosim.model.elements.timehistory import TimeHistoryResult
        if isinstance(to_elem, TimeHistoryResult):
            connected_ports = {
                c.to_port_name
                for c in self._connections.values()
                if c.to_element_id == to_elem.id
            }
            all_ports = list(to_elem.input_ports.keys())
            if (
                all(p in connected_ports for p in all_ports)
                and len(all_ports) < TimeHistoryResult.MAX_SERIES
            ):
                to_elem.add_series_port()

    def remove_connection(self, connection_id: str) -> None:
        """Remove a connection. Raises KeyError if not found."""
        conn = self._connections.get(connection_id)
        if conn is None:
            raise KeyError(f"Connection '{connection_id}' not found")
        del self._connections[connection_id]
        # Remove the nx edge if it exists (stock outputs don't have edges)
        if self._nx_graph.has_edge(conn.from_element_id, conn.to_element_id):
            self._nx_graph.remove_edge(conn.from_element_id, conn.to_element_id)

    def get_connection(self, connection_id: str) -> Connection:
        return self._connections[connection_id]

    def get_connections_from(self, element_id: str) -> list[Connection]:
        """All connections where this element is the source."""
        return [c for c in self._connections.values()
                if c.from_element_id == element_id]

    def get_connections_to(self, element_id: str) -> list[Connection]:
        """All connections where this element is the destination."""
        return [c for c in self._connections.values()
                if c.to_element_id == element_id]

    def get_connections_to_port(
        self, element_id: str, port_name: str
    ) -> list[Connection]:
        """All connections feeding a specific input port."""
        return [
            c for c in self._connections.values()
            if c.to_element_id == element_id and c.to_port_name == port_name
        ]

    @property
    def connections(self) -> dict[str, Connection]:
        return dict(self._connections)

    # ── Graph analysis ────────────────────────────────────────────────────────

    def get_execution_order(self) -> list[ElementBase]:
        """
        Return elements in topologically sorted execution order.
        Raises CircularDependencyError if a cycle exists among non-stock elements.
        """
        if not nx.is_directed_acyclic_graph(self._nx_graph):
            cycles = list(nx.simple_cycles(self._nx_graph))
            raise CircularDependencyError(cycles)

        sorted_ids = list(nx.topological_sort(self._nx_graph))

        # topological_sort only includes nodes reachable in the sort order;
        # isolated nodes (no edges) are included in the nx graph but may
        # appear in any position — collect any elements not yet in the list.
        sorted_set = set(sorted_ids)
        for eid in self._elements:
            if eid not in sorted_set:
                sorted_ids.append(eid)

        return [self._elements[eid] for eid in sorted_ids if eid in self._elements]

    def has_cycle(self) -> bool:
        """True if a circular dependency exists among non-stock elements."""
        return not nx.is_directed_acyclic_graph(self._nx_graph)

    def get_upstream_elements(self, element_id: str) -> list[ElementBase]:
        """All elements that must be computed before this one."""
        return [
            self._elements[eid]
            for eid in nx.ancestors(self._nx_graph, element_id)
            if eid in self._elements
        ]

    def build_name_to_id_map(self) -> dict[str, str]:
        """
        Return {lowercase_element_name: element_id} for all elements.
        Used by Expression.prepare() to resolve formula references.
        """
        return {el.name.lower(): el.id for el in self._elements.values()}

    # ── Private helpers ───────────────────────────────────────────────────────

    def _should_add_nx_edge(self, from_element: ElementBase) -> bool:
        """
        Stock elements provide their PREVIOUS timestep value, so their output
        connections do NOT create a topological dependency.
        All other elements (Input, Expression, Result) DO create dependency edges.
        """
        return not from_element.is_stock()
