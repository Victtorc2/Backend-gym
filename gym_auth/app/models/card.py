"""
Modelo SQLAlchemy para la entidad Tarjeta.
Tabla 'tarjetas': credencial física emitida a clientes con membresía mensual o anual.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import CardStatus
from app.database.connection import Base

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.attendance import Attendance


class Card(Base):
    """
    Tarjeta de acceso del cliente al gimnasio.

    Solo se emite para membresías mensuales o anuales.
    Cada cliente puede tener una única tarjeta vigente.
    El código tiene formato GYM-NNNNN (ej. GYM-00001).
    """

    __tablename__ = "tarjetas"

    # ── Identificación ─────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)

    # ── Código único ───────────────────────────────────────────────────────────
    codigo: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
    )

    # ── Relación con cliente ───────────────────────────────────────────────────
    cliente_id: Mapped[int] = mapped_column(
        ForeignKey("clientes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    cliente: Mapped["Client"] = relationship(
        "Client",
        back_populates="tarjetas",
        lazy="select",
    )

    # ── Fechas ─────────────────────────────────────────────────────────────────
    fecha_emision: Mapped[date] = mapped_column(Date, nullable=False)

    # ── Estado ─────────────────────────────────────────────────────────────────
    estado: Mapped[CardStatus] = mapped_column(
        Enum(CardStatus, name="card_estado_enum"),
        nullable=False,
        default=CardStatus.ACTIVA,
        server_default=CardStatus.ACTIVA.value,
    )

    # ── Timestamps ─────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ── Relaciones futuras ─────────────────────────────────────────────────────
    asistencias: Mapped[list["Attendance"]] = relationship(
        "Attendance",
        back_populates="tarjeta",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Card id={self.id} codigo={self.codigo} cliente_id={self.cliente_id}>"
