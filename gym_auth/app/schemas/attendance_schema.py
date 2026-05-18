"""
Schemas Pydantic para el módulo de Asistencias.
Define contratos de entrada, salida, filtros, paginación y frecuencia.
"""
from __future__ import annotations

from datetime import date, datetime, time

from pydantic import BaseModel, Field

from app.core.constants import AttendanceStatus, DenialReason


# ── Validar ingreso (entrada) ──────────────────────────────────────────────────

class AttendanceCheckInSchema(BaseModel):
    """
    Schema de entrada para POST /api/asistencias/validar-ingreso.
    El único dato requerido es el código de tarjeta del cliente.
    """
    codigo_tarjeta: str = Field(
        ...,
        min_length=3,
        max_length=20,
        description="Código único de la tarjeta (ej. GYM-00001)",
        examples=["GYM-00001"],
    )


# ── Respuesta de asistencia ────────────────────────────────────────────────────

class AttendanceResponseSchema(BaseModel):
    """Schema de respuesta completo para un registro de asistencia."""
    id: int
    cliente_id: int
    tarjeta_id: int
    fecha: date
    hora: time
    estado: AttendanceStatus
    motivo_denegacion: DenialReason | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Resultado del validar-ingreso ──────────────────────────────────────────────

class CheckInResultSchema(BaseModel):
    """
    Respuesta enriquecida del endpoint validar-ingreso.
    Incluye nombre del cliente para feedback visual en recepción.
    """
    asistencia: AttendanceResponseSchema
    nombre_cliente: str
    acceso_permitido: bool
    motivo: str | None = None     # Mensaje legible del resultado


# ── Frecuencia de asistencia ───────────────────────────────────────────────────

class AttendanceFrequencySchema(BaseModel):
    """Resumen de frecuencia de asistencia de un cliente."""
    cliente_id: int
    nombre_cliente: str
    total_ingresos: int           # aprobados
    total_denegados: int
    primer_ingreso: date | None
    ultimo_ingreso: date | None
    dias_del_mes_actual: int      # ingresos aprobados en el mes en curso


# ── Filtros y paginación ───────────────────────────────────────────────────────

class AttendanceFilterSchema(BaseModel):
    """Parámetros de filtro y paginación para GET /api/asistencias."""
    cliente_id: int | None = Field(default=None, description="Filtra por cliente")
    estado: AttendanceStatus | None = Field(default=None, description="Filtra por resultado")
    fecha_desde: date | None = Field(default=None, description="Rango desde")
    fecha_hasta: date | None = Field(default=None, description="Rango hasta")
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)


class PaginatedAttendanceSchema(BaseModel):
    """Respuesta paginada de listado de asistencias."""
    items: list[AttendanceResponseSchema]
    total: int
    page: int
    per_page: int
    total_pages: int
