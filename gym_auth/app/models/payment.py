"""
Modelo SQLAlchemy para la entidad Pago.
Tabla 'pagos': registra cada transacción financiera del cliente.
Mantiene trazabilidad completa; nunca se eliminan registros.
Preparado para relaciones futuras: reportes, segmentación, clientes diarios.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import PaymentMethod, PaymentStatus
from app.database.connection import Base

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.membership import Membership


class Payment(Base):
    """
    Pago o abono parcial de un cliente hacia su membresía.

    Cada registro es inmutable tras su creación (append-only).
    El saldo_pendiente se calcula y almacena en el momento del registro.
    El estado puede actualizarse automáticamente si la membresía vence.
    """

    __tablename__ = "pagos"

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
        back_populates="pagos",
        lazy="select",
    )

    membresia_id: Mapped[int] = mapped_column(
        ForeignKey("membresias.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    membresia: Mapped["Membership"] = relationship(
        "Membership",
        back_populates="pagos",
        lazy="select",
    )

    # ── Montos ─────────────────────────────────────────────────────────────────
    monto_total: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2), nullable=False
    )
    monto_pagado: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2), nullable=False
    )
    saldo_pendiente: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2), nullable=False
    )

    # ── Método y fecha ─────────────────────────────────────────────────────────
    metodo_pago: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="payment_method_enum"),
        nullable=False,
    )
    fecha_pago: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # ── Estado ─────────────────────────────────────────────────────────────────
    estado: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status_enum"),
        nullable=False,
        default=PaymentStatus.PENDIENTE,
        server_default=PaymentStatus.PENDIENTE.value,
    )

    # ── Timestamps ─────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<Payment id={self.id} cliente_id={self.cliente_id} "
            f"monto_total={self.monto_total} estado={self.estado}>"
        )
