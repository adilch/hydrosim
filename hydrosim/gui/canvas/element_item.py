"""
ElementItem — the visual card representing one element on the canvas.
Subclass of QGraphicsItem; draws entirely via QPainter.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QBrush, QColor, QFont, QFontMetrics, QPainter,
    QPainterPath, QPen, QRadialGradient,
)
from PyQt6.QtWidgets import (
    QGraphicsDropShadowEffect, QGraphicsItem,
    QGraphicsSceneMouseEvent, QStyleOptionGraphicsItem,
)

from hydrosim.gui.canvas.port_item import PortItem
from hydrosim.gui.styles.theme import (
    BORDER_FIELD, BORDER_INNER,
    CARD_PADDING_H, CARD_TOP_BAR_H, CARD_WIDTH, CARD_CORNER_R,
    CAT_COLOURS,
    FONT_MONO, FONT_UI,
    PORT_DIAMETER, PORT_ROW_HEIGHT, PORT_OFFSET_X,
    SEL_BLUE, TEXT_PRIMARY, TEXT_SECONDARY,
)
from hydrosim.model.base import ElementBase, ElementCategory, PortType

if TYPE_CHECKING:
    pass

# Minimum body height (content area below the divider)
_BODY_MIN_H  = 40
# Head section height (icon + name + id + padding)
_HEAD_H      = 52
# Divider height
_DIVIDER_H   = 1

# Category → colour string
_CAT_STR: dict[ElementCategory, str] = {
    ElementCategory.INPUT:      CAT_COLOURS["input"],
    ElementCategory.STOCK:      CAT_COLOURS["stock"],
    ElementCategory.EXPRESSION: CAT_COLOURS["expression"],
    ElementCategory.RESULT:     CAT_COLOURS["result"],
}


def _load_svg_icon(kind: str, size: int, colour: QColor) -> "QPixmap | None":
    """Render one of the 5 SVG icons at the given size and colour."""
    from PyQt6.QtSvg import QSvgRenderer
    from PyQt6.QtGui import QPixmap
    from pathlib import Path
    import re

    icons_dir = Path(__file__).parent.parent.parent / "resources" / "icons"
    svg_path  = icons_dir / f"{kind}.svg"
    if not svg_path.exists():
        return None

    svg_text = svg_path.read_text(encoding="utf-8")
    # Replace currentColor with the actual hex colour
    hex_col  = colour.name()
    svg_text = svg_text.replace("currentColor", hex_col)

    renderer = QSvgRenderer()
    renderer.load(svg_text.encode("utf-8"))

    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p  = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(p)
    p.end()
    return px


# Map element class names to icon filenames
_ICON_MAP = {
    "Constant":          "constant",
    "TimeSeries":        "timeseries",
    "WaterStore":        "waterstore",
    "Expression":        "expression",
    "TimeHistoryResult": "timehistory",
}


class ElementItem(QGraphicsItem):
    """
    Visual card for one HydroSim element.
    Renders category colour bar, head (icon + name + id), divider, body
    (type-specific content + port labels), and child PortItem dots.
    """

    def __init__(self, element: ElementBase, parent: QGraphicsItem | None = None):
        super().__init__(parent)
        self.element    = element
        self._cat_str   = _CAT_STR.get(element.category, "#888888")
        self._cat_col   = QColor(self._cat_str)
        self._port_items: dict[str, PortItem] = {}
        self._has_results = False
        self._has_error   = False
        self._error_msg   = ""

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.setPos(element.position[0], element.position[1])
        self.setZValue(1)

        self._setup_shadow()
        self._create_port_items()

    # ── Geometry ──────────────────────────────────────────────────────────────

    def _card_height(self) -> float:
        n_rows = max(
            len(self.element.input_ports),
            len(self.element.output_ports),
            1,
        )
        content_h = _BODY_MIN_H + (n_rows - 1) * PORT_ROW_HEIGHT
        return CARD_TOP_BAR_H + _HEAD_H + _DIVIDER_H + max(content_h, n_rows * PORT_ROW_HEIGHT + 10)

    def boundingRect(self) -> QRectF:
        # Extra space on sides for port dots that extend outside the card
        margin = PORT_DIAMETER
        h = self._card_height()
        return QRectF(-margin, -margin, CARD_WIDTH + margin * 2, h + margin * 2)

    def _card_rect(self) -> QRectF:
        return QRectF(0, 0, CARD_WIDTH, self._card_height())

    # ── Shadow ────────────────────────────────────────────────────────────────

    def _setup_shadow(self) -> None:
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(12)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 26))
        self.setGraphicsEffect(shadow)

    # ── Port items ────────────────────────────────────────────────────────────

    def _create_port_items(self) -> None:
        category = self.element.category.value
        h        = self._card_height()
        body_top = CARD_TOP_BAR_H + _HEAD_H + _DIVIDER_H

        # Input ports — left edge
        in_ports  = list(self.element.input_ports.values())
        n_in      = len(in_ports)
        for i, port in enumerate(in_ports):
            item = PortItem(port, category, parent=self)
            y    = body_top + PORT_ROW_HEIGHT * i + PORT_ROW_HEIGHT / 2
            item.setPos(0, y)
            self._port_items[port.name] = item

        # Output ports — right edge
        out_ports = list(self.element.output_ports.values())
        n_out     = len(out_ports)
        for i, port in enumerate(out_ports):
            item = PortItem(port, category, parent=self)
            y    = body_top + PORT_ROW_HEIGHT * i + PORT_ROW_HEIGHT / 2
            item.setPos(CARD_WIDTH, y)
            self._port_items[port.name] = item

    def get_port_item(self, port_name: str) -> PortItem | None:
        return self._port_items.get(port_name)

    def refresh_ports(self) -> None:
        """Rebuild port items after element ports change (e.g. Expression formula edit)."""
        for item in self._port_items.values():
            item.setParentItem(None)
        self._port_items.clear()
        self._create_port_items()
        self.prepareGeometryChange()

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paint(
        self,
        painter:  QPainter,
        option:   QStyleOptionGraphicsItem,
        widget=None,
    ) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(0, 0, CARD_WIDTH, self._card_height())

        self._paint_background(painter, r)
        self._paint_category_bar(painter)
        self._paint_head(painter)
        self._paint_divider(painter)
        self._paint_body(painter, r)
        self._paint_status_indicators(painter)

    def _paint_background(self, painter: QPainter, r: QRectF) -> None:
        path = QPainterPath()
        path.addRoundedRect(r, CARD_CORNER_R, CARD_CORNER_R)

        painter.fillPath(path, QColor("#FFFFFF"))

        if self.isSelected():
            pen = QPen(QColor(SEL_BLUE), 2.5)
        elif self._has_error:
            pen = QPen(QColor("#E53935"), 2.0)
        else:
            pen = QPen(QColor(BORDER_FIELD), 1.0)
        painter.strokePath(path, pen)

    def _paint_category_bar(self, painter: QPainter) -> None:
        bar = QPainterPath()
        bar.addRoundedRect(
            QRectF(0, 0, CARD_WIDTH, CARD_TOP_BAR_H + CARD_CORNER_R),
            CARD_CORNER_R, CARD_CORNER_R,
        )
        # Clip to top CARD_TOP_BAR_H only
        clip = QPainterPath()
        clip.addRect(QRectF(0, 0, CARD_WIDTH, CARD_TOP_BAR_H))
        painter.fillPath(bar.intersected(clip), QColor(self._cat_str))

    def _paint_head(self, painter: QPainter) -> None:
        top = CARD_TOP_BAR_H
        # Icon
        icon_kind = _ICON_MAP.get(self.element.__class__.__name__, "constant")
        icon_size = 22
        px = _load_svg_icon(icon_kind, icon_size, self._cat_col)
        icon_x = CARD_PADDING_H
        icon_y = top + ((_HEAD_H - icon_size) // 2)
        if px:
            painter.drawPixmap(icon_x, icon_y, px)

        text_x = icon_x + icon_size + 9
        text_w = CARD_WIDTH - text_x - CARD_PADDING_H

        # Element name
        name_font = QFont(FONT_UI, 13)
        name_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(name_font)
        painter.setPen(QColor(TEXT_PRIMARY))
        name_y = top + 18
        painter.drawText(
            QRectF(text_x, name_y, text_w, 18),
            Qt.TextFlag.TextSingleLine,
            self.element.name,
        )

        # Element ID (small monospace)
        id_font = QFont(FONT_MONO, 9)
        painter.setFont(id_font)
        painter.setPen(QColor(TEXT_SECONDARY))
        short_id = self.element.id[:8]
        painter.drawText(
            QRectF(text_x, name_y + 18, text_w, 14),
            Qt.TextFlag.TextSingleLine,
            short_id,
        )

    def _paint_divider(self, painter: QPainter) -> None:
        y = CARD_TOP_BAR_H + _HEAD_H
        painter.setPen(QPen(QColor(BORDER_INNER), 1))
        painter.drawLine(QPointF(0, y), QPointF(CARD_WIDTH, y))

    def _paint_body(self, painter: QPainter, card_rect: QRectF) -> None:
        body_top = CARD_TOP_BAR_H + _HEAD_H + _DIVIDER_H

        # Port labels
        lbl_font = QFont(FONT_UI, 10)
        painter.setFont(lbl_font)
        painter.setPen(QColor(TEXT_SECONDARY))

        for i, (name, port) in enumerate(self.element.input_ports.items()):
            y = body_top + PORT_ROW_HEIGHT * i + PORT_ROW_HEIGHT / 2 - 6
            painter.drawText(
                QRectF(CARD_PADDING_H, y, CARD_WIDTH / 2 - CARD_PADDING_H, 14),
                Qt.TextFlag.TextSingleLine,
                name,
            )

        for i, (name, port) in enumerate(self.element.output_ports.items()):
            y = body_top + PORT_ROW_HEIGHT * i + PORT_ROW_HEIGHT / 2 - 6
            painter.drawText(
                QRectF(CARD_WIDTH / 2, y, CARD_WIDTH / 2 - CARD_PADDING_H, 14),
                Qt.AlignmentFlag.AlignRight | Qt.TextFlag.TextSingleLine,
                name,
            )

        # Type-specific content preview
        class_name = self.element.__class__.__name__
        if class_name == "Constant":
            self._paint_constant_body(painter, body_top)
        elif class_name == "WaterStore":
            self._paint_waterstore_body(painter, body_top, card_rect)
        elif class_name == "Expression":
            self._paint_expression_body(painter, body_top)
        elif class_name == "TimeSeries":
            self._paint_timeseries_body(painter, body_top)

    def _paint_constant_body(self, painter: QPainter, body_top: float) -> None:
        val_font = QFont(FONT_MONO, 13)
        val_font.setWeight(QFont.Weight.Medium)
        painter.setFont(val_font)
        painter.setPen(QColor(TEXT_PRIMARY))
        val_str = str(self.element.value) if hasattr(self.element, "value") else ""
        y = body_top + PORT_ROW_HEIGHT + 4
        painter.drawText(
            QRectF(CARD_PADDING_H, y, CARD_WIDTH - CARD_PADDING_H * 2, 18),
            Qt.TextFlag.TextSingleLine,
            val_str,
        )
        units_font = QFont(FONT_MONO, 9)
        painter.setFont(units_font)
        painter.setPen(QColor(TEXT_SECONDARY))
        units = getattr(self.element, "units", "")
        painter.drawText(
            QRectF(CARD_PADDING_H, y + 16, CARD_WIDTH - CARD_PADDING_H * 2, 12),
            Qt.TextFlag.TextSingleLine,
            units,
        )

    def _paint_waterstore_body(
        self, painter: QPainter, body_top: float, card_rect: QRectF
    ) -> None:
        n_rows   = max(len(self.element.input_ports), len(self.element.output_ports))
        bar_top  = body_top + PORT_ROW_HEIGHT * n_rows + 6
        bar_h    = 8
        bar_w    = CARD_WIDTH - CARD_PADDING_H * 2
        bar_x    = CARD_PADDING_H

        # Track
        track = QRectF(bar_x, bar_top, bar_w, bar_h)
        painter.setBrush(QBrush(QColor("#EEF1F5")))
        painter.setPen(QPen(QColor("#E5E7EB"), 1))
        painter.drawRoundedRect(track, 4, 4)

        # Fill
        lo  = getattr(self.element, "lower_bound",     0.0)
        hi  = getattr(self.element, "upper_bound",     None)
        val = getattr(self.element, "initial_storage", 0.0)
        if hi and hi > lo:
            pct  = max(0.0, min(1.0, (val - lo) / (hi - lo)))
            fill = QRectF(bar_x, bar_top, bar_w * pct, bar_h)
            grad = QRadialGradient(fill.center(), fill.width())
            grad.setColorAt(0, QColor("#4aa3da"))
            grad.setColorAt(1, QColor("#2E86C1"))
            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(fill, 4, 4)

    def _paint_expression_body(self, painter: QPainter, body_top: float) -> None:
        formula = getattr(self.element, "formula", "")
        if not formula:
            return
        display = formula[:30] + ("…" if len(formula) > 30 else "")
        f = QFont(FONT_MONO, 10)
        painter.setFont(f)
        painter.setPen(QColor(CAT_COLOURS["expression"]))
        n_rows = max(len(self.element.input_ports), len(self.element.output_ports))
        y = body_top + PORT_ROW_HEIGHT * n_rows + 4
        painter.drawText(
            QRectF(CARD_PADDING_H, y, CARD_WIDTH - CARD_PADDING_H * 2, 16),
            Qt.TextFlag.TextSingleLine,
            display,
        )

    def _paint_timeseries_body(self, painter: QPainter, body_top: float) -> None:
        units = getattr(self.element, "units", "")
        n_pts = len(getattr(self.element, "data", []))
        f     = QFont(FONT_MONO, 10)
        painter.setFont(f)
        painter.setPen(QColor(TEXT_SECONDARY))
        y = body_top + PORT_ROW_HEIGHT + 4
        painter.drawText(
            QRectF(CARD_PADDING_H, y, CARD_WIDTH - CARD_PADDING_H * 2, 14),
            Qt.TextFlag.TextSingleLine,
            units or "—",
        )
        sm_f = QFont(FONT_MONO, 9)
        painter.setFont(sm_f)
        painter.drawText(
            QRectF(CARD_PADDING_H, y + 13, CARD_WIDTH - CARD_PADDING_H * 2, 12),
            Qt.TextFlag.TextSingleLine,
            f"{n_pts} rows",
        )

    def _paint_status_indicators(self, painter: QPainter) -> None:
        r = self._card_rect()
        # Green dot when results available
        if self._has_results:
            painter.setBrush(QBrush(QColor("#43A047")))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(r.right() - 12, r.top() + 12), 5, 5)
        # Warning triangle on error
        if self._has_error:
            painter.setPen(QColor("#E53935"))
            painter.setFont(QFont(FONT_UI, 9))
            painter.drawText(
                QRectF(r.right() - 20, r.top() + 4, 16, 16),
                Qt.AlignmentFlag.AlignCenter,
                "⚠",
            )

    # ── State setters ─────────────────────────────────────────────────────────

    def set_has_results(self, v: bool) -> None:
        self._has_results = v
        self.update()

    def set_error(self, v: bool, msg: str = "") -> None:
        self._has_error = v
        self._error_msg = msg
        self.update()

    def refresh(self) -> None:
        """Redraw after element data changes."""
        self.prepareGeometryChange()
        self.update()

    # ── Interaction ───────────────────────────────────────────────────────────

    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        scene = self.scene()
        if scene and hasattr(scene, "element_double_clicked"):
            scene.element_double_clicked.emit(self.element.id)
        super().mouseDoubleClickEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            scene = self.scene()
            if scene and hasattr(scene, "element_moved"):
                scene.element_moved.emit(
                    self.element.id,
                    float(self.pos().x()),
                    float(self.pos().y()),
                )
            # Update any connection arrows (Phase 8)
            if scene and hasattr(scene, "_update_connections_for"):
                scene._update_connections_for(self.element.id)
        return super().itemChange(change, value)
