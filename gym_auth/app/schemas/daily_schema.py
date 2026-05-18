"""
Schemas Pydantic para el módulo de Clientes Diarios.
Define contratos de entrada, salida, filtros y estadísticas de frecuencia.
"""
from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.core.constants import (
    DailyClientStatus,
    DailyEntryDenialReason,
    DailyEntryStatus,
)


# ══════════════════════════════════════════════════════════════════════════════
#  CLIENTE DIARIO
# ══════════════════════════════════════════════════════════════════════════════

class DailyClientCreateSchema(BaseModel):
    """Entrada para registrar un nuevo cliente diario (POST /api/clientes-diarios)."""
    nombre: str = Field(..., min_length=2, max_length=200, examples=["Juan Pérez"])
    documento: str | None = Field(
        default=None, max_length=20, description="DNI u otro documento (opcional)",
        examples=["12345678"],
    )


class DailyClientUpdateSchema(BaseModel):
    """Entrada para PATCH /api/clientes-diarios/{id} — solo nombre, documento y estado."""
    nombre: str | None = Field(default=None, min_length=2, max_length=200)
    documento: str | None = Field(default=None, max_length=20)
    estado: DailyClientStatus | None = None


class DailyClientResponseSchema(BaseModel):
    """Schema de respuesta completo para un cliente diario."""
    id: int
    nombre: str
    documento: str | None
    estado: DailyClientStatus
    created_at: datetime

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════════════════
#  PAGO DIARIO
# ══════════════════════════════════════════════════════════════════════════════

class DailyPaymentCreateSchema(BaseModel):
    """Entrada para registrar un pago diario (POST /api/clientes-diarios/{id}/pago)."""
    monto: Decimal = Field(
        ..., gt=0, max_digits=10, decimal_places=2,
        description="Monto cobrado por el acceso del día",
        examples=[["15.00"]],
    )

    @field_validator("monto")
    @classmethod
    def monto_positivo(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("El monto debe ser mayor a cero")
        return value


class DailyPaymentResponseSchema(BaseModel):
    """Schema de respuesta para un pago diario."""
    id: int
    cliente_id: int
    monto: Decimal
    fecha_pago: date
    created_at: datetime

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════════════════
#  INGRESO DIARIO
# ══════════════════════════════════════════════════════════════════════════════

class DailyEntryResponseSchema(BaseModel):
    """Schema de respuesta para un registro de ingreso diario."""
    id: int
    cliente_id: int
    fecha: date
    hora: time
    estado: DailyEntryStatus
    motivo: DailyEntryDenialReason | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DailyEntryCheckInResultSchema(BaseModel):
    """
    Respuesta enriquecida del endpoint de registro de ingreso.
    Incluye nombre del cliente para feedback visual en recepción.
    """
    ingreso: DailyEntryResponseSchema
    nombre_cliente: str
    acceso_permitido: bool
    mensaje: str


# ══════════════════════════════════════════════════════════════════════════════
#  FRECUENCIA
# ══════════════════════════════════════════════════════════════════════════════

class DailyFrequencySchema(BaseModel):
    """Resumen de frecuencia de asistencia de un cliente diario."""
    cliente_id: int
    nombre_cliente: str
    total_ingresos_aprobados: int
    total_ingresos_denegados: int
    primer_ingreso: date | None
    ultimo_ingreso: date | None
    ingresos_mes_actual: int


# ══════════════════════════════════════════════════════════════════════════════
#  FILTROS Y PAGINACIÓN
# ══════════════════════════════════════════════════════════════════════════════

class DailyEntryFilterSchema(BaseModel):
    """Parámetros de filtro y paginación para GET /api/ingresos-diarios."""
    cliente_id: int | None = Field(default=None, description="Filtra por cliente")
    estado: DailyEntryStatus | None = Field(default=None, description="Filtra por resultado")
    fecha_desde: date | None = Field(default=None, description="Rango desde")
    fecha_hasta: date | None = Field(default=None, description="Rango hasta")
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)


class PaginatedDailyEntrySchema(BaseModel):
    """Respuesta paginada de listado de ingresos diarios."""
    items: list[DailyEntryResponseSchema]
    total: int
    page: int
    per_page: int
    total_pages: int
