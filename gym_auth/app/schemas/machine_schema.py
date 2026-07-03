"""
Schemas Pydantic para el catálogo de Máquinas.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.constants import MuscleZone


class MachineCreateSchema(BaseModel):
    """Datos para registrar una máquina."""
    nombre: str = Field(..., min_length=1, max_length=120)
    zona: MuscleZone
    cantidad: int = Field(default=1, ge=1, le=100)
    descripcion: str | None = Field(default=None, max_length=300)
    activa: bool = True


class MachineUpdateSchema(BaseModel):
    """Datos para actualizar una máquina (todos opcionales)."""
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    zona: MuscleZone | None = None
    cantidad: int | None = Field(default=None, ge=1, le=100)
    descripcion: str | None = Field(default=None, max_length=300)
    activa: bool | None = None


class MachineResponseSchema(BaseModel):
    """Máquina del catálogo."""
    id: int
    nombre: str
    zona: MuscleZone
    cantidad: int
    descripcion: str | None
    foto_url: str | None = None
    activa: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
