"""
ModelSerialiser — converts between ModelGraph objects and .hydrosim JSON files.
Uses Pydantic v2 for schema validation on load.
Zero PyQt6 dependencies.
"""
from __future__ import annotations

import json
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, field_validator, model_validator

from hydrosim.model.base import (
    Connection,
    ModelFileError,
    SimulationSettings,
    VersionMismatchError,
)

CURRENT_FORMAT_VERSION = "1"
HYDROSIM_VERSION       = "1.0"


# ── Pydantic schemas (validate on load) ───────────────────────────────────────

class ConnectionSchema(BaseModel):
    id:              str
    from_element_id: str
    from_port_name:  str
    to_element_id:   str
    to_port_name:    str


class SimSettingsSchema(BaseModel):
    start_time: float
    end_time:   float
    dt:         float
    time_mode:  Literal["elapsed", "calendar"]
    start_date: str | None = None  # ISO date string or null

    @field_validator("dt")
    @classmethod
    def dt_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("dt must be positive")
        return v

    @field_validator("end_time")
    @classmethod
    def end_must_be_after_start(cls, v: float) -> float:
        # Can't cross-validate with start_time in a field_validator in Pydantic v2
        # — just ensure it's finite
        import math
        if not math.isfinite(v):
            raise ValueError("end_time must be finite")
        return v


class CanvasStateSchema(BaseModel):
    zoom:  float = 1.0
    pan_x: float = 0.0
    pan_y: float = 0.0


class HydroSimFileSchema(BaseModel):
    hydrosim_version:    str
    file_format_version: str
    metadata:            dict
    simulation_settings: SimSettingsSchema
    elements:            list[dict]       # validated individually by element class
    connections:         list[ConnectionSchema]
    canvas_state:        CanvasStateSchema | None = None


# ── Element type registry ─────────────────────────────────────────────────────

def _build_registry() -> dict:
    from hydrosim.model.elements.constant    import Constant
    from hydrosim.model.elements.timeseries  import TimeSeries
    from hydrosim.model.elements.waterstore  import WaterStore
    from hydrosim.model.elements.expression  import Expression
    from hydrosim.model.elements.timehistory import TimeHistoryResult
    return {
        "Constant":          Constant,
        "TimeSeries":        TimeSeries,
        "WaterStore":        WaterStore,
        "Expression":        Expression,
        "TimeHistoryResult": TimeHistoryResult,
    }


# ── ModelSerialiser ────────────────────────────────────────────────────────────

class ModelSerialiser:
    """Save and load .hydrosim JSON model files."""

    # ── Save ──────────────────────────────────────────────────────────────────

    @staticmethod
    def save(
        graph:    "ModelGraph",  # type: ignore[name-defined]
        settings: SimulationSettings,
        filepath: Path,
        metadata: dict | None = None,
        canvas_state: dict | None = None,
    ) -> None:
        """Serialise graph + settings to a .hydrosim JSON file."""
        data = ModelSerialiser.to_dict(graph, settings, metadata, canvas_state)
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def to_dict(
        graph:    "ModelGraph",  # type: ignore[name-defined]
        settings: SimulationSettings,
        metadata: dict | None = None,
        canvas_state: dict | None = None,
    ) -> dict:
        """Serialise to a plain dict (without writing to disk)."""
        now = datetime.now(timezone.utc).isoformat()
        meta = {
            "name":        metadata.get("name",        "Untitled") if metadata else "Untitled",
            "description": metadata.get("description", "")         if metadata else "",
            "author":      metadata.get("author",      "")         if metadata else "",
            "created":     metadata.get("created",     now)        if metadata else now,
            "modified":    now,
        }

        sim = {
            "start_time": settings.start_time,
            "end_time":   settings.end_time,
            "dt":         settings.dt,
            "time_mode":  settings.time_mode,
            "start_date": settings.start_date.isoformat()
                          if settings.start_date else None,
        }

        return {
            "hydrosim_version":    HYDROSIM_VERSION,
            "file_format_version": CURRENT_FORMAT_VERSION,
            "metadata":            meta,
            "simulation_settings": sim,
            "elements":            [el.to_dict() for el in graph.elements.values()],
            "connections":         [
                {
                    "id":              c.id,
                    "from_element_id": c.from_element_id,
                    "from_port_name":  c.from_port_name,
                    "to_element_id":   c.to_element_id,
                    "to_port_name":    c.to_port_name,
                }
                for c in graph.connections.values()
            ],
            "canvas_state": canvas_state or {"zoom": 1.0, "pan_x": 0.0, "pan_y": 0.0},
        }

    # ── Load ──────────────────────────────────────────────────────────────────

    @staticmethod
    def load(
        filepath: Path,
    ) -> tuple["ModelGraph", SimulationSettings, dict]:  # type: ignore[name-defined]
        """
        Load a .hydrosim file.
        Returns: (graph, settings, metadata)
        Raises: FileNotFoundError, ModelFileError, VersionMismatchError
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except json.JSONDecodeError as exc:
            raise ModelFileError(
                f"Could not open file — file may be corrupted: {exc}"
            ) from exc

        return ModelSerialiser.from_dict(raw)

    @staticmethod
    def from_dict(
        data: dict,
    ) -> tuple["ModelGraph", SimulationSettings, dict]:  # type: ignore[name-defined]
        """
        Deserialise from a dict (inverse of to_dict()).
        Validates with Pydantic schema before deserialising.
        """
        # Version check
        file_version = str(data.get("file_format_version", "0"))
        if int(file_version) > int(CURRENT_FORMAT_VERSION):
            raise VersionMismatchError(file_version, CURRENT_FORMAT_VERSION)

        # Pydantic validation
        try:
            from pydantic import ValidationError as PydanticValidationError
            schema = HydroSimFileSchema.model_validate(data)
        except Exception as exc:
            raise ModelFileError(f"Invalid model file: {exc}") from exc

        # Rebuild SimulationSettings
        ss = schema.simulation_settings
        start_date = None
        if ss.start_date:
            try:
                start_date = date.fromisoformat(ss.start_date)
            except ValueError:
                pass

        settings = SimulationSettings(
            start_time=ss.start_time,
            end_time=ss.end_time,
            dt=ss.dt,
            time_mode=ss.time_mode,
            start_date=start_date,
        )

        # Rebuild ModelGraph
        from hydrosim.model.graph import ModelGraph
        graph   = ModelGraph()
        registry = _build_registry()

        for elem_data in schema.elements:
            elem_type = elem_data.get("type")
            klass = registry.get(elem_type)
            if klass is None:
                raise ModelFileError(
                    f"Unknown element type '{elem_type}'. "
                    f"Known types: {list(registry)}"
                )
            try:
                element = klass.from_dict(elem_data)
            except Exception as exc:
                raise ModelFileError(
                    f"Could not load element '{elem_data.get('name', '?')}': {exc}"
                ) from exc
            graph.add_element(element)

        for conn_schema in schema.connections:
            conn = Connection(
                id=conn_schema.id,
                from_element_id=conn_schema.from_element_id,
                from_port_name=conn_schema.from_port_name,
                to_element_id=conn_schema.to_element_id,
                to_port_name=conn_schema.to_port_name,
            )
            try:
                graph.add_connection(conn)
            except Exception as exc:
                raise ModelFileError(
                    f"Could not restore connection '{conn_schema.id}': {exc}"
                ) from exc

        metadata = dict(schema.metadata)
        return graph, settings, metadata
