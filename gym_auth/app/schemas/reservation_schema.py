"""
Schemas Pydantic para Reservas de Máquina.
"""
from __future__ import annotations

from datetime import date, time

from pydantic import BaseModel, Field

from app.core.constants import (
    RESERVATION_MAX_DURATION,
    RESERVATION_MIN_DURATION,
    MuscleZone,
    ReservationStatus,
)


class ReservationCreateSchema(BaseModel):
    """Datos para reservar una máquina en una franja horaria."""
    maquina_id: int = Field(..., gt=0)
    fecha: date
    hora_inicio: time
    duracion_min: int = Field(
        default=30, ge=RESERVATION_MIN_DURATION, le=RESERVATION_MAX_DURATION,
        description="Duración en minutos (múltiplos de 15)",
    )


class ReservationSlotSchema(BaseModel):
    """Franja ocupada de una máquina (vista de disponibilidad)."""
    hora_inicio: str            # "18:00"
    hora_fin: str               # "18:30"
    cliente_nombre: str
    es_mia: bool


class MachineAvailabilitySchema(BaseModel):
    """Máquina con sus franjas reservadas para una fecha."""
    maquina_id: int
    nombre: str
    zona: MuscleZone
    cantidad: int
    foto_url: str | None
    reservas: list[ReservationSlotSchema]


class ReservationResponseSchema(BaseModel):
    """Reserva del cliente."""
    id: int
    maquina_id: int
    maquina_nombre: str
    zona: MuscleZone
    fecha: date
    hora_inicio: str
    hora_fin: str
    duracion_min: int
    estado: ReservationStatus
