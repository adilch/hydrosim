"""
ConnectionItem — bezier curve arrow connecting an output port to an input port.
"""
from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QBrush, QColor, QPainter, QPainterPath, QPen, QPolygonF,
)
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsPathItem

from hydrosim.gui.styles.theme import (
    CAT_COLOURS,
    CONN_CTRL_OFFSET, CONN_STROKE_OPACITY, CONN_STROKE_W,
    CONN_SELECTED_W, CONN_ENDPOINT_R, SEL_BLUE, ARROW_SIZE,
)
from hydrosim.model.base import Connection


def _adaptive_offset(start: QPointF, end: QPointF) -> float:
    """
    Scale the bezier control-point offset with the horizontal distance so that:
    - Short connections have a tighter, more compact curve
    - Long connections have a gentler, more readable S-curve
    Clamped to [50, 200] px.
    """
    dx = abs(end.x() - start.x())
    return max(50.0, min(dx * 0.45, 200.0))


def _bezier_path(start: QPointF, end: QPointF, offset: float | None = None) -> tuple:
    """
    Cubic bezier departing rightward from start, arriving leftward at end.
    P0 = start,  P1 = start + (offset, 0),
    P2 = end - (offset, 0),  P3 = end.
    offset is adaptive by default.
    """
    if offset is None:
        offset = _adaptive_offset(start, end)
    ctrl1 = QPointF(start.x() + offset, start.y())
    ctrl2 = QPointF(end.x()   - offset, end.y())
    path  = QPainterPath()
    path.moveTo(start)
    path.cubicTo(ctrl1, ctrl2, end)
    return path, ctrl2


def _arrowhead(end: QPointF, ctrl2: QPointF) -> QPolygonF:
    """
    Filled triangle at `end` pointing in the arrival direction (ctrl2 → end).
    """
    angle = math.atan2(end.y() - ctrl2.y(), end.x() - ctrl2.x())
    tip   = end
    bl    = QPointF(
        end.x() - ARROW_SIZE * math.cos(angle - 0.42),
        end.y() - ARROW_SIZE * math.sin(angle - 0.42),
    )
    br    = QPointF(
        end.x() - ARROW_SIZE * math.cos(angle + 0.42),
        end.y() - ARROW_SIZE * math.sin(angle + 0.42),
    )
    return QPolygonF([tip, bl, br])


class ConnectionItem(QGraphicsPathItem):
    """
    Visual representation of one Connection between two ports.
    Renders as a cubic bezier with a filled arrowhead at the destination.
    """

    def __init__(
        self,
        connection:      Connection,
        from_port_item:  "PortItem",   # type: ignore
        to_port_item:    "PortItem",   # type: ignore
        category:        str,          # source element category
    ):
        super().__init__()
        self.connection     = connection
        self.from_port_item = from_port_item
        self.to_port_item   = to_port_item
        self._category      = category

        # Cached geometry — updated by update_path(), read by paint()
        # so paint() never calls mapToScene() independently (avoids drag glitch)
        self._start = QPointF()
        self._end   = QPointF()
        self._ctrl2 = QPointF()

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        self.setZValue(-1)   # render behind element cards

        self.setToolTip(
            f"{from_port_item.port.name}  →  {to_port_item.port.name}"
        )
        self._update_style(selected=False)
        self.update_path()

    # ── Geometry ──────────────────────────────────────────────────────────────

    def update_path(self) -> None:
        """
        Recalculate bezier from current port outer-edge positions.
        Uses scene_connection_point() so the wire visually starts/ends
        at the outer edge of the port dot, not its hidden centre.
        Called whenever either connected element moves.
        """
        self._start = self.from_port_item.scene_connection_point()
        self._end   = self.to_port_item.scene_connection_point()
        path, self._ctrl2 = _bezier_path(self._start, self._end)
        self.setPath(path)
        self.update()

    # ── Style ─────────────────────────────────────────────────────────────────

    def _update_style(self, selected: bool) -> None:
        col   = QColor(CAT_COLOURS.get(self._category, "#888888"))
        if selected:
            col   = QColor(SEL_BLUE)
            width = CONN_SELECTED_W
        else:
            col.setAlphaF(CONN_STROKE_OPACITY)
            width = CONN_STROKE_W
        self.setPen(QPen(col, width))
        self._selected_style = selected

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        selected  = self.isSelected()
        base_col  = QColor(SEL_BLUE) if selected \
                    else QColor(CAT_COLOURS.get(self._category, "#888888"))
        wire_col  = QColor(base_col)
        if not selected:
            wire_col.setAlphaF(CONN_STROKE_OPACITY)
        width = CONN_SELECTED_W if selected else CONN_STROKE_W

        # ── Wire ────────────────────────────────────────────────────────
        painter.setPen(QPen(wire_col, width, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(self.path())

        # ── Filled circle at source end ──────────────────────────────────
        # Marks exactly where the wire leaves the output port dot.
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(base_col))
        painter.drawEllipse(self._start, CONN_ENDPOINT_R, CONN_ENDPOINT_R)

        # ── Arrowhead at destination ─────────────────────────────────────
        arrow = _arrowhead(self._end, self._ctrl2)
        painter.drawPolygon(arrow)

    # ── Hover ─────────────────────────────────────────────────────────────────

    def hoverEnterEvent(self, event) -> None:
        col = QColor(CAT_COLOURS.get(self._category, "#888888"))
        self.setPen(QPen(col, CONN_STROKE_W + 0.5))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self._update_style(self.isSelected())
        super().hoverLeaveEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self._update_style(bool(value))
            self.update()
        return super().itemChange(change, value)


# ── Temporary rubber-band line used during drag ───────────────────────────────

class TempConnectionItem(QGraphicsPathItem):
    """
    Dashed bezier drawn while the user is dragging a connection.
    Destroyed when the drag ends.
    """

    def __init__(self, start: QPointF, category: str):
        super().__init__()
        self._start    = start
        self._category = category
        self.setZValue(100)   # above everything

        col = QColor(CAT_COLOURS.get(category, "#888888"))
        col.setAlphaF(0.7)
        pen = QPen(col, CONN_STROKE_W)
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        self.setPen(pen)

    def update_end(self, end: QPointF) -> None:
        path, _ = _bezier_path(self._start, end)
        self.setPath(path)
