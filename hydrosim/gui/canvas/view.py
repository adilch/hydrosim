"""
HydroView — QGraphicsView wrapper for the HydroScene.
Handles zoom (scroll wheel, buttons), pan (space+drag / middle-drag),
and palette drag-drop.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QPointF, pyqtSignal
from PyQt6.QtGui import QCursor, QTransform, QWheelEvent
from PyQt6.QtWidgets import (
    QGraphicsView, QSizePolicy,
)

from hydrosim.gui.canvas.scene import HydroScene
from hydrosim.gui.styles.theme import ZOOM_MIN, ZOOM_MAX, ZOOM_STEP

# MIME type used by the palette for drag events
PALETTE_MIME = "application/x-hydrosim-element-type"


class HydroView(QGraphicsView):
    """
    The viewport on the infinite canvas.

    Zoom  — scroll wheel (toward cursor) or ±buttons
    Pan   — Space+drag  OR  middle-mouse drag
    Drop  — accepts palette drops and emits element_dropped(type_name, scene_pos)
    """

    zoom_changed     = pyqtSignal(int)          # emits zoom percentage 40..200
    element_dropped  = pyqtSignal(str, QPointF) # (element_type_name, scene_pos)

    def __init__(self, scene: HydroScene, parent=None):
        super().__init__(scene, parent)
        self._zoom: float = 1.0
        self._panning     = False
        self._pan_start   = QPointF()
        self._space_held  = False

        self.setRenderHint(self.renderHints().__class__.Antialiasing, True)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._apply_zoom()

    # ── Zoom ──────────────────────────────────────────────────────────────────

    def _apply_zoom(self) -> None:
        t = QTransform()
        t.scale(self._zoom, self._zoom)
        self.setTransform(t)
        self.zoom_changed.emit(int(round(self._zoom * 100)))

    def _zoom_by(self, factor: float, anchor: QPointF | None = None) -> None:
        new_zoom = max(ZOOM_MIN, min(ZOOM_MAX, self._zoom * factor))
        if abs(new_zoom - self._zoom) < 1e-6:
            return

        if anchor is None:
            anchor = self.mapToScene(self.viewport().rect().center())

        old_scene_pos = anchor
        self._zoom = new_zoom
        self._apply_zoom()
        new_viewport_pos = self.mapFromScene(old_scene_pos)
        delta = self.mapToScene(self.viewport().rect().center()) - \
                self.mapToScene(new_viewport_pos)
        self.centerOn(old_scene_pos.x() - delta.x(),
                      old_scene_pos.y() - delta.y())

    def zoom_in(self)    -> None: self._zoom_by(1.0 + ZOOM_STEP)
    def zoom_out(self)   -> None: self._zoom_by(1.0 / (1.0 + ZOOM_STEP))
    def zoom_reset(self) -> None:
        self._zoom = 1.0
        self._apply_zoom()

    def zoom_to_fit(self) -> None:
        items = [i for i in self.scene().items() if i.isVisible()]
        if not items:
            return
        from PyQt6.QtCore import QRectF
        br = items[0].sceneBoundingRect()
        for item in items[1:]:
            br = br.united(item.sceneBoundingRect())
        br = br.adjusted(-40, -40, 40, 40)
        self.fitInView(br, Qt.AspectRatioMode.KeepAspectRatio)
        self._zoom = self.transform().m11()
        self._zoom = max(ZOOM_MIN, min(ZOOM_MAX, self._zoom))
        self.zoom_changed.emit(int(round(self._zoom * 100)))

    # ── Wheel zoom ────────────────────────────────────────────────────────────

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1.0 / 1.15
            anchor = self.mapToScene(event.position().toPoint())
            self._zoom_by(factor, anchor)
            event.accept()
        else:
            factor = 1.12 if event.angleDelta().y() > 0 else 1.0 / 1.12
            anchor = self.mapToScene(event.position().toPoint())
            self._zoom_by(factor, anchor)
            event.accept()

    # ── Pan ───────────────────────────────────────────────────────────────────

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self._space_held = True
            self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
            event.accept()
            return
        if event.key() == Qt.Key.Key_Delete:
            self._delete_selected()
            event.accept()
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self._space_held = False
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            event.accept()
            return
        super().keyReleaseEvent(event)

    def mousePressEvent(self, event) -> None:
        if (event.button() == Qt.MouseButton.MiddleButton
                or (event.button() == Qt.MouseButton.LeftButton and self._space_held)):
            self._panning   = True
            self._pan_start = event.position()
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x())
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y())
            )
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._panning:
            self._panning = False
            cursor = (QCursor(Qt.CursorShape.OpenHandCursor)
                      if self._space_held
                      else QCursor(Qt.CursorShape.ArrowCursor))
            self.setCursor(cursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    # ── Delete ────────────────────────────────────────────────────────────────

    def _delete_selected(self) -> None:
        """Ask scene to remove selected element items."""
        scene = self.scene()
        if not isinstance(scene, HydroScene):
            return
        selected = [
            item for item in scene.selectedItems()
            if item.__class__.__name__ == "ElementItem"
        ]
        if not selected:
            return
        from PyQt6.QtWidgets import QMessageBox
        names = ", ".join(f"'{i.element.name}'" for i in selected)
        reply = QMessageBox.question(
            self,
            "Delete Elements",
            f"Delete {names} and their connections?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Yes:
            for item in selected:
                scene.remove_element(item.element.id)

    # ── Drag-drop from palette ─────────────────────────────────────────────────

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasFormat(PALETTE_MIME):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasFormat(PALETTE_MIME):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        if event.mimeData().hasFormat(PALETTE_MIME):
            type_name  = event.mimeData().data(PALETTE_MIME).data().decode("utf-8")
            scene_pos  = self.mapToScene(event.position().toPoint())
            self.element_dropped.emit(type_name, scene_pos)
            event.acceptProposedAction()
        else:
            event.ignore()
