"""
Modelo SQLAlchemy para la entidad Membresía.
Tabla 'membresias': registra contratos de acceso de cada cliente.
Preparado para relaciones futuras con pagos y asistencias.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import MembershipStatus, MembershipType
from app.database.connection import Base

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.card import Card
    from app.models.payment import Payment


class Membership(Base):
    """
    Membresía de un cliente en el gimnasio.

    Cada membresía calcula automáticamente su fecha_fin y estado
    basándose en el tipo y la fecha de inicio. Un cliente puede
    tener múltiples membresías históricas, pero solo una activa.

    Futuras relaciones: pagos, asistencias.
    """

    __tablename__ = "membresias"

    # ── Identificación ─────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)

    # ── Relación con cliente ───────────────────────────────────────────────────
    cliente_id: Mapped[int] = mapped_column(
        ForeignKey("clientes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    cliente: Mapped["Client"] = relationship(
        "Client",
        back_populates="membresias",
        lazy="select",
    )

    # ── Tipo y duración ────────────────────────────────────────────────────────
    tipo: Mapped[MembershipType] = mapped_column(
        Enum(MembershipType, name="membership_tipo_enum"),
        nullable=False,
    )
    precio: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
    )
    duracion_dias: Mapped[int] = mapped_column(nullable=False)

    # ── Vigencia (calculadas automáticamente por el servicio) ──────────────────
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_fin: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # ── Estado ─────────────────────────────────────────────────────────────────
    estado: Mapped[MembershipStatus] = mapped_column(
        Enum(MembershipStatus, name="membership_estado_enum"),
        nullable=False,
        default=MembershipStatus.ACTIVA,
        server_default=MembershipStatus.ACTIVA.value,
    )

    # ── Timestamps ─────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ── Relaciones futuras ─────────────────────────────────────────────────────
    pagos: Mapped[list["Payment"]] = relationship(
        "Payment",
        back_populates="membresia",
        lazy="select",
        order_by="Payment.fecha_pago.desc()",
    )
    # asistencias: Mapped[list["Asistencia"]] = relationship(...)

    def __repr__(self) -> str:
        return (
            f"<Membership id={self.id} cliente_id={self.cliente_id} "
            f"tipo={self.tipo} estado={self.estado}>"
        )
