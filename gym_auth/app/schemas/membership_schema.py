"""
Schemas Pydantic para el módulo de Membresías.
Define contratos de entrada, salida y validaciones centralizadas.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.core.constants import MembershipStatus, MembershipType


# ── Crear membresía ────────────────────────────────────────────────────────────

class MembershipCreateSchema(BaseModel):
    """
    Schema de entrada para registrar una nueva membresía.
    Las fechas y la duración son calculadas automáticamente por el servicio.
    """
    cliente_id: int = Field(..., gt=0, description="ID del cliente")
    tipo: MembershipType = Field(..., description="Tipo: mensual, anual o diario")
    precio: Decimal = Field(
        ...,
        gt=0,
        description="Precio cobrado por esta membresía",
        examples=[["150.00"]],
    )

    @field_validator("precio")
    @classmethod
    def precio_positive(cls, value: Decimal) -> Decimal:
        """Garantiza que el precio sea mayor que cero y con 2 decimales."""
        if value <= 0:
            raise ValueError("El precio debe ser mayor a cero")

        return value.quantize(Decimal("0.01"))


# ── Actualizar membresía ───────────────────────────────────────────────────────

class MembershipUpdateSchema(BaseModel):
    """
    Schema de entrada para actualizar una membresía existente (partial update).
    Solo precio y estado son editables post-creación.
    """
    precio: Decimal | None = Field(
        default=None,
        gt=0,
        description="Precio cobrado por esta membresía"
    )
    estado: MembershipStatus | None = None

    @field_validator("precio")
    @classmethod
    def validate_precio(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return value

        if value <= 0:
            raise ValueError("El precio debe ser mayor a cero")

        return value.quantize(Decimal("0.01"))


# ── Respuestas ─────────────────────────────────────────────────────────────────

class MembershipResponseSchema(BaseModel):
    """Schema de respuesta completo para una membresía."""
    id: int
    cliente_id: int
    tipo: MembershipType
    precio: Decimal
    duracion_dias: int
    fecha_inicio: date
    fecha_fin: date
    estado: MembershipStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Respuesta con estado dinámico ──────────────────────────────────────────────

class MembershipWithStatusSchema(MembershipResponseSchema):
    """
    Membresía con estado de vigencia recalculado en tiempo real.
    Útil cuando los registros pueden estar desactualizados.
    """
    vigente: bool  # True si fecha_fin >= hoy

    model_config = {"from_attributes": True}