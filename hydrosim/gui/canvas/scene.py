"""
HydroScene — QGraphicsScene that owns all ElementItems and ConnectionItems.
Keeps the ModelGraph in sync with every visual change.
"""
from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen
from PyQt6.QtWidgets import QGraphicsScene

from hydrosim.gui.canvas.element_item import ElementItem
from hydrosim.gui.styles.theme import (
    APP_BG, GRID_DOT, GRID_DOT_SIZE, GRID_SPACING,
)
from hydrosim.model.base import ElementBase, PortType


class HydroScene(QGraphicsScene):
    """
    The infinite canvas.  All model-building happens here.

    Signals
    -------
    element_added(element_id)
    element_removed(element_id)
    element_moved(element_id, x, y)
    element_double_clicked(element_id)
    connection_requested(from_id, from_port, to_id, to_port)
    """

    element_added          = pyqtSignal(str)
    element_removed        = pyqtSignal(str)
    element_moved          = pyqtSignal(str, float, float)
    element_double_clicked = pyqtSignal(str)
    connection_requested   = pyqtSignal(str, str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(-2000, -1500, 4000, 3000)
        self.setBackgroundBrush(QBrush(QColor(APP_BG)))

        # element_id → ElementItem
        self.element_items:    dict[str, ElementItem]      = {}
        # connection_id → ConnectionItem
        self.connection_items: dict[str, "ConnectionItem"] = {}  # type: ignore

        self._grid_spacing  = GRID_SPACING
        self._grid_dot_size = GRID_DOT_SIZE

        # Connection-drag state
        self._dragging:        bool              = False
        self._drag_from_port:  "PortItem | None" = None   # type: ignore
        self._temp_line:       "TempConnectionItem | None" = None  # type: ignore

    # ── Background dot grid ───────────────────────────────────────────────────

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        super().drawBackground(painter, rect)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(GRID_DOT)))

        spacing = self._grid_spacing
        dot     = self._grid_dot_size

        left = int(rect.left())  - (int(rect.left())  % spacing)
        top  = int(rect.top())   - (int(rect.top())   % spacing)

        x = left
        while x <= rect.right() + spacing:
            y = top
            while y <= rect.bottom() + spacing:
                painter.drawEllipse(QPointF(x, y), dot, dot)
                y += spacing
            x += spacing

    # ── Element management ────────────────────────────────────────────────────

    def add_element(
        self, element: ElementBase, position: QPointF | None = None
    ) -> ElementItem:
        """Create and add an ElementItem for the given element."""
        if position is not None:
            element.position = (position.x(), position.y())

        item = ElementItem(element)
        self.addItem(item)
        self.element_items[element.id] = item
        self.element_added.emit(element.id)
        return item

    def remove_element(self, element_id: str) -> None:
        """Remove the ElementItem and any attached ConnectionItems from the scene."""
        item = self.element_items.pop(element_id, None)
        if item is None:
            return

        to_remove = [
            cid for cid, ci in self.connection_items.items()
            if (hasattr(ci, "connection") and (
                ci.connection.from_element_id == element_id
                or ci.connection.to_element_id == element_id
            ))
        ]
        for cid in to_remove:
            ci = self.connection_items.pop(cid)
            self.removeItem(ci)

        self.removeItem(item)
        self.element_removed.emit(element_id)

    def update_element_card(self, element_id: str) -> None:
        """Repaint one element card (called after property dialog OK)."""
        item = self.element_items.get(element_id)
        if item:
            item.refresh_ports()
            item.refresh()

    # ── Connection management ─────────────────────────────────────────────────

    def add_connection_item(
        self,
        connection: "Connection",      # type: ignore
        conn_item:  "ConnectionItem",  # type: ignore
    ) -> None:
        self.connection_items[connection.id] = conn_item
        self.addItem(conn_item)
        # Mark ports as connected
        from_item = self.element_items.get(connection.from_element_id)
        to_item   = self.element_items.get(connection.to_element_id)
        if from_item:
            pi = from_item.get_port_item(connection.from_port_name)
            if pi:
                pi.set_connected(True)
        if to_item:
            pi = to_item.get_port_item(connection.to_port_name)
            if pi:
                pi.set_connected(True)

    def remove_connection_item(self, connection_id: str) -> None:
        ci = self.connection_items.pop(connection_id, None)
        if not ci:
            return
        conn = ci.connection
        # Un-mark ports
        from_item = self.element_items.get(conn.from_element_id)
        to_item   = self.element_items.get(conn.to_element_id)
        if from_item:
            pi = from_item.get_port_item(conn.from_port_name)
            if pi:
                pi.set_connected(False)
        if to_item:
            pi = to_item.get_port_item(conn.to_port_name)
            if pi:
                pi.set_connected(False)
        self.removeItem(ci)

    def _update_connections_for(self, element_id: str) -> None:
        """Refresh all ConnectionItems attached to the given element (on move)."""
        for ci in self.connection_items.values():
            conn = getattr(ci, "connection", None)
            if conn and (
                conn.from_element_id == element_id
                or conn.to_element_id == element_id
            ):
                if hasattr(ci, "update_path"):
                    ci.update_path()

    # ── Connection drag ───────────────────────────────────────────────────────

    def start_connection_drag(self, from_port_item: "PortItem") -> None:  # type: ignore
        """Called by PortItem when user begins dragging from an output port."""
        from hydrosim.gui.canvas.connection_item import TempConnectionItem

        self._dragging     = True
        self._drag_from_port = from_port_item
        start = from_port_item.scene_connection_point()
        category = from_port_item.category

        self._temp_line = TempConnectionItem(start, category)
        self.addItem(self._temp_line)

        # Highlight all input ports (green = compatible, red = already taken)
        self._highlight_target_ports(from_port_item)

    def _highlight_target_ports(self, from_port: "PortItem") -> None:  # type: ignore
        """Show glow on all input ports during drag."""
        from_elem_id = from_port.parentItem().element.id  # type: ignore
        for elem_item in self.element_items.values():
            for pname, pi in elem_item._port_items.items():
                if pi.port.port_type != PortType.INPUT:
                    continue
                if elem_item.element.id == from_elem_id:
                    pi.set_drag_highlight("incompatible")  # no self-loops
                elif pi._connected:
                    pi.set_drag_highlight("incompatible")  # already taken
                else:
                    pi.set_drag_highlight("compatible")

    def _clear_port_highlights(self) -> None:
        for elem_item in self.element_items.values():
            for pi in elem_item._port_items.values():
                pi.set_drag_highlight("none")

    def mouseMoveEvent(self, event) -> None:
        if self._dragging and self._temp_line:
            self._temp_line.update_end(event.scenePos())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._dragging:
            target = self._find_input_port_at(event.scenePos())
            self._cancel_drag()
            if target is not None:
                from_port = self._drag_from_port  # saved before cancel clears it
                if from_port:
                    from_elem = from_port.parentItem().element   # type: ignore
                    to_elem   = target.parentItem().element       # type: ignore
                    self.connection_requested.emit(
                        from_elem.id,
                        from_port.port.name,
                        to_elem.id,
                        target.port.name,
                    )
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape and self._dragging:
            self._cancel_drag()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Delete:
            self._delete_selected_items()
            event.accept()
            return
        super().keyPressEvent(event)

    def _cancel_drag(self) -> None:
        if self._temp_line:
            self.removeItem(self._temp_line)
            self._temp_line = None
        # Keep _drag_from_port so the caller can use it; reset after use
        self._dragging = False
        self._clear_port_highlights()

    def _find_input_port_at(self, scene_pos: QPointF) -> "PortItem | None":  # type: ignore
        """Find an input PortItem near scene_pos (within ~12px)."""
        from hydrosim.gui.canvas.port_item import PortItem
        for item in self.items(scene_pos):
            if isinstance(item, PortItem) and item.port.port_type == PortType.INPUT:
                return item
        # Wider search if nothing directly under cursor
        from PyQt6.QtCore import QRectF
        search = QRectF(scene_pos.x() - 12, scene_pos.y() - 12, 24, 24)
        for item in self.items(search):
            if isinstance(item, PortItem) and item.port.port_type == PortType.INPUT:
                return item
        return None

    def _delete_selected_items(self) -> None:
        """Delete selected ConnectionItems; ElementItem deletion is in HydroView."""
        from hydrosim.gui.canvas.connection_item import ConnectionItem
        for item in list(self.selectedItems()):
            if isinstance(item, ConnectionItem):
                self.connection_removed_requested(item.connection.id)

    def connection_removed_requested(self, connection_id: str) -> None:
        """
        Called when the user deletes a connection (via Delete key or context menu).
        Emits a signal so MainWindow can update the ModelGraph.
        This is a direct call for now; wired to a signal in Phase 11.
        """
        # Delegate upward — find the MainWindow via the view
        views = self.views()
        if views:
            view = views[0]
            parent = view.parent()
            while parent:
                if hasattr(parent, "_on_connection_delete_requested"):
                    parent._on_connection_delete_requested(connection_id)
                    return
                parent = parent.parent() if hasattr(parent, "parent") else None
        # Fallback: just remove from scene
        self.remove_connection_item(connection_id)

    # ── Results highlighting ──────────────────────────────────────────────────

    def mark_results_available(self, element_ids: list[str]) -> None:
        for eid, item in self.element_items.items():
            item.set_has_results(eid in element_ids)

    def clear_results_markers(self) -> None:
        for item in self.element_items.values():
            item.set_has_results(False)
