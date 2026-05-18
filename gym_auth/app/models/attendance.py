"""
Modelo SQLAlchemy para la entidad Asistencia.
Tabla 'asistencias': registro inmutable de cada intento de ingreso al gimnasio.
Vincula cliente y tarjeta, guarda resultado y motivo de denegación si aplica.
Preparado para relaciones futuras: reportes, segmentación, clientes diarios.
"""
from __future__ import annotations

from datetime import date, datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, Time, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import AttendanceStatus, DenialReason
from app.database.connection import Base

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.card import Card


class Attendance(Base):
    """
    Registro de un intento de ingreso (aprobado o denegado).

    Cada registro es inmutable tras su creación (append-only).
    El campo motivo_denegacion es None cuando el ingreso fue aprobado.
    """

    __tablename__ = "asistencias"

    # ── Identificación ─────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)

    # ── Relaciones ─────────────────────────────────────────────────────────────
    cliente_id: Mapped[int] = mapped_column(
        ForeignKey("clientes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    cliente: Mapped["Client"] = relationship(
        "Client",
        back_populates="asistencias",
        lazy="select",
    )

    tarjeta_id: Mapped[int] = mapped_column(
        ForeignKey("tarjetas.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    tarjeta: Mapped["Card"] = relationship(
        "Card",
        back_populates="asistencias",
        lazy="select",
    )

    # ── Fecha y hora ───────────────────────────────────────────────────────────
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    hora: Mapped[time] = mapped_column(Time, nullable=False)

    # ── Resultado ──────────────────────────────────────────────────────────────
    estado: Mapped[AttendanceStatus] = mapped_column(
        Enum(AttendanceStatus, name="attendance_status_enum"),
        nullable=False,
        index=True,
    )
    motivo_denegacion: Mapped[DenialReason | None] = mapped_column(
        Enum(DenialReason, name="denial_reason_enum"),
        nullable=True,
        default=None,
    )

    # ── Timestamp de creación ──────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<Attendance id={self.id} cliente_id={self.cliente_id} "
            f"fecha={self.fecha} estado={self.estado}>"
        )
