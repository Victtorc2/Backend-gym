"""
Schemas Pydantic para el módulo de Pagos.
Define contratos de entrada, salida, filtros y paginación.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.core.constants import PaymentMethod, PaymentStatus


# ── Crear pago ─────────────────────────────────────────────────────────────────

class PaymentCreateSchema(BaseModel):
    """
    Schema de entrada para registrar un pago (POST /api/pagos).
    Las fechas y el saldo son calculados automáticamente.
    """
    cliente_id: int = Field(..., gt=0, description="ID del cliente")
    membresia_id: int = Field(..., gt=0, description="ID de la membresía")
    monto_total: Decimal = Field(
        ..., gt=0, max_digits=10, decimal_places=2,
        description="Monto total a pagar por la membresía",
        examples=[["150.00"]],
    )
    monto_pagado: Decimal = Field(
        ..., gt=0, max_digits=10, decimal_places=2,
        description="Monto abonado en este pago",
        examples=[["75.00"]],
    )
    metodo_pago: PaymentMethod = Field(
        ..., description="Método: efectivo, transferencia, yape, plin"
    )

    @model_validator(mode="after")
    def monto_pagado_no_excede_total(self) -> "PaymentCreateSchema":
        """El monto pagado no puede ser mayor al monto total."""
        if self.monto_pagado > self.monto_total:
            raise ValueError(
                "El monto pagado no puede superar el monto total"
            )
        return self


# ── Abonar a un pago parcial (completar) ───────────────────────────────────────

class PaymentSettleSchema(BaseModel):
    """Registra un abono sobre un pago parcial existente (reduce el saldo)."""
    monto: Decimal = Field(
        ..., gt=0, max_digits=10, decimal_places=2,
        description="Monto a abonar (no puede superar el saldo pendiente)",
        examples=[["50.00"]],
    )
    metodo_pago: PaymentMethod | None = Field(
        default=None, description="Método del abono; si se omite, conserva el original"
    )


# ── Respuesta individual ───────────────────────────────────────────────────────

class PaymentResponseSchema(BaseModel):
    """Schema de respuesta completo para un pago."""
    id: int
    cliente_id: int
    membresia_id: int
    monto_total: Decimal
    monto_pagado: Decimal
    saldo_pendiente: Decimal
    metodo_pago: PaymentMethod
    fecha_pago: date
    estado: PaymentStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Resumen de deuda de un cliente ─────────────────────────────────────────────

class ClientDebtSummarySchema(BaseModel):
    """Resumen de deuda consolidada de un cliente."""
    cliente_id: int
    nombre_cliente: str
    total_deuda: Decimal              # suma de todos los saldos pendientes
    pagos_pendientes: int             # cantidad de pagos con saldo > 0
    ultimo_pago: date | None          # fecha del último pago registrado


# ── Filtros y paginación ───────────────────────────────────────────────────────

class PaymentFilterSchema(BaseModel):
    """Parámetros de filtro y paginación para GET /api/pagos."""
    cliente_id: int | None = Field(default=None, description="Filtra por cliente")
    estado: PaymentStatus | None = Field(default=None, description="Filtra por estado")
    metodo_pago: PaymentMethod | None = Field(default=None, description="Filtra por método")
    fecha_desde: date | None = Field(default=None, description="Filtra pagos desde esta fecha")
    fecha_hasta: date | None = Field(default=None, description="Filtra pagos hasta esta fecha")
    page: int = Field(default=1, ge=1, description="Número de página")
    per_page: int = Field(default=20, ge=1, le=100, description="Registros por página")


class PaginatedPaymentSchema(BaseModel):
    """Respuesta paginada de listado de pagos."""
    items: list[PaymentResponseSchema]
    total: int
    page: int
    per_page: int
    total_pages: int
