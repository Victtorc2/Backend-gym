"""
Schemas Pydantic para el módulo de Tarjetas.
Define contratos de entrada, salida y validaciones centralizadas.
"""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.core.constants import CardStatus


# ── Emitir tarjeta (uso interno desde MembershipService) ──────────────────────

class CardCreateSchema(BaseModel):
    """
    Schema interno para emitir una tarjeta.
    Nunca se expone directamente en un endpoint; lo usa el servicio.
    """
    cliente_id: int = Field(..., gt=0)
    membership_id: int = Field(..., gt=0)


# ── Cambio de estado ───────────────────────────────────────────────────────────

class CardStatusUpdateSchema(BaseModel):
    """Schema para PATCH /api/tarjetas/{id}/estado."""
    estado: CardStatus = Field(..., examples=["activa"])


# ── Respuestas ─────────────────────────────────────────────────────────────────

class CardResponseSchema(BaseModel):
    """Schema de respuesta completo para una tarjeta."""
    id: int
    codigo: str
    cliente_id: int
    fecha_emision: date
    estado: CardStatus
    created_at: datetime

    model_config = {"from_attributes": True}
