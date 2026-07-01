"""
Modelo SQLAlchemy para Comentarios / Sugerencias del Cliente.
Tabla 'comentarios_cliente': mensajes (comentario, sugerencia, recomendación o
queja) que el cliente envía y el administrador visualiza y gestiona.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import FeedbackStatus, FeedbackType
from app.database.connection import Base

if TYPE_CHECKING:
    from app.models.client import Client


class Feedback(Base):
    """Mensaje enviado por un cliente al gimnasio."""

    __tablename__ = "comentarios_cliente"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)

    cliente_id: Mapped[int] = mapped_column(
        ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cliente: Mapped["Client"] = relationship("Client", lazy="select")

    tipo: Mapped[FeedbackType] = mapped_column(
        Enum(FeedbackType, name="feedback_type_enum"), nullable=False, index=True
    )
    asunto: Mapped[str | None] = mapped_column(String(150), nullable=True)
    mensaje: Mapped[str] = mapped_column(Text, nullable=False)

    estado: Mapped[FeedbackStatus] = mapped_column(
        Enum(FeedbackStatus, name="feedback_status_enum"),
        nullable=False,
        default=FeedbackStatus.NUEVO,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Feedback id={self.id} cliente={self.cliente_id} tipo={self.tipo} estado={self.estado}>"
