"""
Schemas Pydantic para Rutinas (plantillas de entrenamiento).
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.constants import MuscleZone


class RoutineMachineItemSchema(BaseModel):
    """Máquina incluida en una rutina."""
    maquina_id: int
    nombre: str
    zona: MuscleZone


class RoutineCreateSchema(BaseModel):
    """Datos para crear una rutina con sus máquinas."""
    nombre: str = Field(..., min_length=1, max_length=120)
    descripcion: str | None = Field(default=None, max_length=300)
    maquina_ids: list[int] = Field(..., min_length=1, description="IDs de las máquinas de la rutina")


class RoutineUpdateSchema(BaseModel):
    """Datos para actualizar una rutina (todos opcionales)."""
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    descripcion: str | None = Field(default=None, max_length=300)
    activa: bool | None = None
    maquina_ids: list[int] | None = Field(default=None, description="Reemplaza las máquinas de la rutina")


class RoutineResponseSchema(BaseModel):
    """Rutina con sus máquinas y zonas involucradas."""
    id: int
    nombre: str
    descripcion: str | None
    activa: bool
    creada_por: int | None
    maquinas: list[RoutineMachineItemSchema]
    zonas: list[MuscleZone]
    created_at: datetime

    model_config = {"from_attributes": True}
