"""
Modelos SQLAlchemy para el módulo de Clientes Diarios (Fase 6).
Tablas: clientes_diarios, pagos_diarios, ingresos_diarios
Registros inmutables (append-only) — nunca se sobrescriben datos históricos.
"""
from __future__ import annotations

from datetime import date, datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, Time, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import DailyClientStatus, DailyIngresoStatus
from app.database.connection import Base

if TYPE_CHECKING:
    pass


class DailyClient(Base):
    """
    Cliente de acceso diario al gimnasio.

    Entidad independiente de 'clientes' (membresías). Permite gestionar
    personas que pagan por día sin necesidad de registrarse con usuario
    en el sistema ni adquirir una membresía.
    """

    __tablename__ = "clientes_diarios"

    # ── Identificación ─────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    documento: Mapped[str | None] = mapped_column(
        String(20), nullable=True, unique=True, index=True
    )

    # ── Estado ────────────────────────────────────────────────────────────────
    estado: Mapped[DailyClientStatus] = mapped_column(
        Enum(DailyClientStatus, name="daily_client_estado_enum"),
        nullable=False,
        default=DailyClientStatus.ACTIVO,
        server_default=DailyClientStatus.ACTIVO.value,
        index=True,
    )

    # ── Timestamps ─────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ── Relaciones ─────────────────────────────────────────────────────────────
    pagos: Mapped[list["DailyPayment"]] = relationship(
        "DailyPayment",
        back_populates="cliente",
        lazy="select",
        order_by="DailyPayment.fecha_pago.desc()",
    )
    ingresos: Mapped[list["DailyIngreso"]] = relationship(
        "DailyIngreso",
        back_populates="cliente",
        lazy="select",
        order_by="DailyIngreso.fecha.desc()",
    )

    def __repr__(self) -> str:
        return f"<DailyClient id={self.id} nombre={self.nombre} estado={self.estado}>"


class DailyPayment(Base):
    """
    Pago diario de un cliente diario.

    Cada registro representa el pago de un día específico.
    No se permiten pagos duplicados en la misma fecha para el mismo cliente.
    Append-only: nunca se elimina ni sobrescribe.
    """

    __tablename__ = "pagos_diarios"

    # ── Identificación ─────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)

    # ── Relación con cliente diario ────────────────────────────────────────────
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

    # ── Datos del pago ─────────────────────────────────────────────────────────
    monto: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    fecha_pago: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # ── Timestamp de creación ──────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<DailyPayment id={self.id} cliente_id={self.cliente_id} "
            f"monto={self.monto} fecha={self.fecha_pago}>"
        )


class DailyIngreso(Base):
    """
    Registro de ingreso de un cliente diario al gimnasio.

    Flujo de validación obligatorio antes de crear:
      1. Cliente existe y está activo
      2. Tiene pago registrado para la fecha
      3. No existe ya un ingreso aprobado ese día

    Append-only: nunca se elimina ni sobrescribe.
    El campo 'motivo' es requerido cuando estado == DENEGADO.
    """

    __tablename__ = "ingresos_diarios"

    # ── Identificación ─────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)

    # ── Relación con cliente diario ────────────────────────────────────────────
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

    # ── Resultado del intento ──────────────────────────────────────────────────
    estado: Mapped[DailyIngresoStatus] = mapped_column(
        Enum(DailyIngresoStatus, name="daily_ingreso_status_enum"),
        nullable=False,
        index=True,
    )
    motivo: Mapped[str | None] = mapped_column(String(300), nullable=True, default=None)

    # ── Timestamp de creación ──────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<DailyIngreso id={self.id} cliente_id={self.cliente_id} "
            f"fecha={self.fecha} estado={self.estado}>"
        )
