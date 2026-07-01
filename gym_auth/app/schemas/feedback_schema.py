"""
Schemas Pydantic para Comentarios / Sugerencias del Cliente.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.constants import FeedbackStatus, FeedbackType


class FeedbackCreateSchema(BaseModel):
    """Datos con los que el cliente envía un mensaje."""
    tipo: FeedbackType = FeedbackType.COMENTARIO
    asunto: str | None = Field(default=None, max_length=150)
    mensaje: str = Field(..., min_length=1, max_length=2000)


class FeedbackStatusUpdateSchema(BaseModel):
    """El admin cambia el estado de gestión del mensaje."""
    estado: FeedbackStatus


class FeedbackResponseSchema(BaseModel):
    """Mensaje del cliente (vista del cliente)."""
    id: int
    tipo: FeedbackType
    asunto: str | None
    mensaje: str
    estado: FeedbackStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class FeedbackAdminItemSchema(BaseModel):
    """Mensaje del cliente enriquecido para la vista del administrador."""
    id: int
    cliente_id: int
    cliente_nombre: str
    tipo: FeedbackType
    asunto: str | None
    mensaje: str
    estado: FeedbackStatus
    created_at: datetime


class PaginatedFeedbackSchema(BaseModel):
    """Respuesta paginada de mensajes para el administrador."""
    items: list[FeedbackAdminItemSchema]
    total: int
    nuevos: int
    page: int
    per_page: int
    total_pages: int
