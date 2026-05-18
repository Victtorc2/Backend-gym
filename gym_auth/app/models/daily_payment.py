"""
Modelo SQLAlchemy para Pago Diario.
Tabla 'pagos_diarios': un pago por día por cliente (constraint único).
Registro inmutable; nunca se elimina para preservar trazabilidad.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base

if TYPE_CHECKING:
    from app.models.daily_client import DailyClient


class DailyPayment(Base):
    """
    Pago de un cliente diario correspondiente a una fecha específica.

    La combinación (cliente_id, fecha_pago) es única: no se permiten
    pagos duplicados para el mismo cliente el mismo día.
    """

    __tablename__ = "pagos_diarios"

    # Constraint de unicidad a nivel de BD para reforzar la regla de negocio
    __table_args__ = (
        UniqueConstraint("cliente_id", "fecha_pago", name="uq_pago_diario_cliente_fecha"),
    )

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
        back_populates="pagos",
        lazy="select",
    )

    # ── Monto y fecha ──────────────────────────────────────────────────────────
    monto: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
    )
    fecha_pago: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # ── Timestamps ─────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<DailyPayment id={self.id} cliente_id={self.cliente_id} fecha={self.fecha_pago}>"
