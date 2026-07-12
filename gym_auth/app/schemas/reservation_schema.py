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


class MachineSlotOccupancySchema(BaseModel):
    """
    Tramo horario de una máquina con su ocupación de unidades.

    A diferencia de listar reservas sueltas, cada tramo indica cuántas
    unidades están ocupadas y cuántas quedan libres en ese rango, lo que
    permite mostrar la disponibilidad real cuando la máquina tiene varias
    unidades (cantidad > 1).
    """
    hora_inicio: str            # "18:00"
    hora_fin: str               # "18:30"
    ocupadas: int               # unidades ocupadas en el tramo
    libres: int                 # unidades libres en el tramo
    es_mia: bool                # el cliente tiene una reserva en este tramo


class MachineAvailabilitySchema(BaseModel):
    """Máquina con sus tramos de ocupación para una fecha."""
    maquina_id: int
    nombre: str
    zona: MuscleZone
    cantidad: int
    foto_url: str | None
    tramos: list[MachineSlotOccupancySchema]


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


class AdminReservationSchema(BaseModel):
    """
    Reserva vista por el administrador: incluye qué máquina, en qué horario
    y quién la reservó, para el control desde el módulo de Máquinas.
    """
    id: int
    maquina_id: int
    maquina_nombre: str
    zona: MuscleZone
    cliente_id: int
    cliente_nombre: str
    cliente_dni: str | None
    fecha: date
    hora_inicio: str
    hora_fin: str
    duracion_min: int
    estado: ReservationStatus
