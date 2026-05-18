"""
Modelo SQLAlchemy para Ingreso Diario.
Tabla 'ingresos_diarios': registro de cada intento de entrada (aprobado o denegado).
Append-only: nunca se elimina ni modifica para garantizar trazabilidad.
"""
from __future__ import annotations

from datetime import date, datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, Time, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import DailyEntryDenialReason, DailyEntryStatus
from app.database.connection import Base

if TYPE_CHECKING:
    from app.models.daily_client import DailyClient


class DailyEntry(Base):
    """
    Registro de un intento de ingreso de un cliente diario.

    Incluye tanto ingresos aprobados como denegados.
    El campo motivo es obligatorio cuando estado=denegado.
    """

    __tablename__ = "ingresos_diarios"

    # ── Identificación ─────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)

    # ── Relación ───────────────────────────────────────────────────────────────
    cliente_id: Mapped[int] = mapped_column(
        ForeignKey("clientes_diarios.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    cliente: Mapped["DailyClient"] = relationship(
        "DailyClient",
        back_populates="ingresos",
        lazy="select",
    )

    # ── Fecha y hora ───────────────────────────────────────────────────────────
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    hora: Mapped[time] = mapped_column(Time, nullable=False)

    # ── Resultado ──────────────────────────────────────────────────────────────
    estado: Mapped[DailyEntryStatus] = mapped_column(
        Enum(DailyEntryStatus, name="daily_entry_status_enum"),
        nullable=False,
    )
    motivo: Mapped[DailyEntryDenialReason | None] = mapped_column(
        Enum(DailyEntryDenialReason, name="daily_entry_denial_enum"),
        nullable=True,
        default=None,
    )

    # ── Timestamps ─────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<DailyEntry id={self.id} cliente_id={self.cliente_id} "
            f"fecha={self.fecha} estado={self.estado}>"
        )
