"""
Schemas Pydantic para el módulo de Clientes Diarios (Fase 6).
Validan entradas de la API y serializan respuestas al frontend.
Separación estricta entre schemas de request y response.
"""
from __future__ import annotations

from datetime import date, datetime, time
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.constants import DailyClientStatus, DailyDenialReason, DailyIngresoStatus


# ══════════════════════════════════════════════════════════════════════════════
# CLIENTES DIARIOS
# ══════════════════════════════════════════════════════════════════════════════

class DailyClientCreate(BaseModel):
    """Payload para registrar un nuevo cliente diario."""

    nombre: str = Field(
        ...,
        min_length=2,
        max_length=200,
        description="Nombre completo del cliente diario",
        examples=["Juan Pérez García"],
    )
    documento: str | None = Field(
        default=None,
        min_length=5,
        max_length=20,
        description="DNI / pasaporte (opcional)",
        examples=["12345678"],
    )

    @field_validator("nombre")
    @classmethod
    def nombre_no_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El nombre no puede estar vacío")
        return v.strip()

    @field_validator("documento")
    @classmethod
    def documento_strip(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class DailyClientUpdate(BaseModel):
    """Payload para actualizar un cliente diario (PATCH — campos opcionales)."""

    nombre: str | None = Field(
        default=None,
        min_length=2,
        max_length=200,
        description="Nuevo nombre completo",
    )
    documento: str | None = Field(
        default=None,
        min_length=5,
        max_length=20,
        description="Nuevo documento de identidad",
    )
    estado: DailyClientStatus | None = Field(
        default=None,
        description="Nuevo estado: activo | inactivo",
    )

    @field_validator("nombre")
    @classmethod
    def nombre_strip(cls, v: str | None) -> str | None:
        return v.strip() if v else None


class DailyClientResponse(BaseModel):
    """Representación de un cliente diario en las respuestas de la API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    documento: str | None
    estado: DailyClientStatus
    created_at: datetime


class DailyClientDetailResponse(DailyClientResponse):
    """Cliente diario con contadores de actividad."""

    total_pagos: int = 0
    total_ingresos: int = 0
    pago_hoy: bool = False


# ══════════════════════════════════════════════════════════════════════════════
# PAGOS DIARIOS
# ══════════════════════════════════════════════════════════════════════════════

class DailyPaymentCreate(BaseModel):
    """Payload para registrar un pago diario."""

    monto: float = Field(
        ...,
        gt=0,
        description="Monto del pago (debe ser mayor a 0)",
        examples=[10.00],
    )
    fecha_pago: date | None = Field(
        default=None,
        description="Fecha del pago. Por defecto: hoy",
    )

    @field_validator("monto")
    @classmethod
    def monto_precision(cls, v: float) -> float:
        # Máximo 2 decimales
        rounded = round(v, 2)
        if rounded <= 0:
            raise ValueError("El monto debe ser mayor a 0")
        return rounded


class DailyPaymentResponse(BaseModel):
    """Representación de un pago diario en las respuestas de la API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_id: int
    monto: float
    fecha_pago: date
    created_at: datetime


class DailyPaymentListResponse(BaseModel):
    """Historial de pagos de un cliente diario."""

    cliente_id: int
    cliente_nombre: str
    total_pagos: int
    pagos: list[DailyPaymentResponse]


# ══════════════════════════════════════════════════════════════════════════════
# INGRESOS DIARIOS
# ══════════════════════════════════════════════════════════════════════════════

class DailyIngresoCreate(BaseModel):
    """
    Payload para registrar un intento de ingreso diario.

    El backend valida automáticamente: cliente activo + pago del día + no duplicado.
    El campo motivo es requerido si se desea denegar manualmente con causa.
    """

    fecha: date | None = Field(
        default=None,
        description="Fecha del ingreso. Por defecto: hoy",
    )
    motivo: str | None = Field(
        default=None,
        max_length=300,
        description="Motivo de denegación (solo si se deniega manualmente)",
    )


class DailyIngresoResponse(BaseModel):
    """Representación de un ingreso diario en las respuestas de la API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_id: int
    fecha: date
    hora: time
    estado: DailyIngresoStatus
    motivo: str | None
    created_at: datetime


class DailyIngresoDetailResponse(DailyIngresoResponse):
    """Ingreso diario con datos del cliente."""

    cliente_nombre: str
    cliente_documento: str | None


class DailyIngresoListResponse(BaseModel):
    """Listado paginado de ingresos diarios."""

    total: int
    page: int
    per_page: int
    items: list[DailyIngresoDetailResponse]


# ══════════════════════════════════════════════════════════════════════════════
# FRECUENCIA / ESTADÍSTICAS
# ══════════════════════════════════════════════════════════════════════════════

class DailyFrecuenciaResponse(BaseModel):
    """
    Estadísticas de frecuencia de asistencia de un cliente diario.
    Incluye conteos por período y rango de fechas.
    """

    cliente_id: int
    cliente_nombre: str
    total_ingresos_aprobados: int
    total_ingresos_denegados: int
    primer_ingreso: date | None
    ultimo_ingreso: date | None
    dias_mes_actual: int
    historial_mensual: list[dict[str, Any]]
