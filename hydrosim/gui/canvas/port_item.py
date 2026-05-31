"""
PortItem — small circular connector dot on an element card edge.
Child of ElementItem; positioned at card edge.
"""
from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QPen
from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsItem, QToolTip

from hydrosim.gui.styles.theme import (
    CAT_COLOURS,
    PORT_DIAMETER, PORT_HOVER_D,
)
from hydrosim.model.base import Port, PortType


class PortItem(QGraphicsEllipseItem):
    """
    A 10px circle on the left (input) or right (output) edge of an ElementItem.
    Grows to 14px on hover and shows a tooltip.
    Used in Phase 8 as the drag-start anchor for drawing connections.
    """

    def __init__(
        self,
        port:          Port,
        category:      str,          # "input" | "stock" | "expression" | "result"
        parent:        QGraphicsItem,
    ):
        r = PORT_DIAMETER / 2
        super().__init__(-r, -r, PORT_DIAMETER, PORT_DIAMETER, parent=parent)

        self.port          = port
        self.category      = category
        self._connected    = False
        self._cat_colour   = QColor(CAT_COLOURS.get(category, "#888888"))

        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setToolTip(
            f"{port.name}  ({port.units})\n{port.description}"
            + ("  [required]" if port.required else "")
        )
        self._apply_style()

    # ── Style ─────────────────────────────────────────────────────────────────

    def set_connected(self, connected: bool) -> None:
        self._connected = connected
        self._apply_style()

    def _apply_style(self) -> None:
        col = self._cat_colour
        if self.port.port_type == PortType.OUTPUT:
            filled = QColor(col)
            if not self._connected:
                filled.setAlphaF(0.70)
            self.setBrush(QBrush(filled))
            self.setPen(QPen(Qt.PenStyle.NoPen))
        else:   # INPUT
            if self._connected:
                self.setBrush(QBrush(col))
                self.setPen(QPen(Qt.PenStyle.NoPen))
            else:
                self.setBrush(QBrush(QColor("#FFFFFF")))
                pen = QPen(col, 1.5)
                self.setPen(pen)

    # ── Drag glow (shown during connection drag) ─────────────────────────────

    def set_drag_highlight(self, state: str) -> None:
        """
        state: 'compatible' | 'incompatible' | 'none'
        Shows a coloured glow ring around the port.
        """
        if state == "compatible":
            self.setPen(QPen(QColor("#43A047"), 2.5))
        elif state == "incompatible":
            self.setPen(QPen(QColor("#E53935"), 2.5))
        else:
            self._apply_style()

    # ── Hover ─────────────────────────────────────────────────────────────────

    def hoverEnterEvent(self, event) -> None:
        r = PORT_HOVER_D / 2
        self.setRect(-r, -r, PORT_HOVER_D, PORT_HOVER_D)
        self.setZValue(10)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        r = PORT_DIAMETER / 2
        self.setRect(-r, -r, PORT_DIAMETER, PORT_DIAMETER)
        self.setZValue(0)
        super().hoverLeaveEvent(event)

    # ── Mouse — initiate connection drag from OUTPUT port ─────────────────────

    def mousePressEvent(self, event) -> None:
        if (event.button() == Qt.MouseButton.LeftButton
                and self.port.port_type == PortType.OUTPUT):
            scene = self.scene()
            if scene and hasattr(scene, "start_connection_drag"):
                scene.start_connection_drag(self)
                event.accept()
                return
        super().mousePressEvent(event)

    # ── Geometry helpers ──────────────────────────────────────────────────────

    def scene_centre(self) -> QPointF:
        """Scene-coordinate centre of this port dot."""
        return self.mapToScene(QPointF(0, 0))
