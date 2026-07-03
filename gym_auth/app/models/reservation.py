"""
Modelo SQLAlchemy para Reserva de Máquina por franja horaria.
Tabla 'reservas_maquina': el cliente reserva una máquina concreta en una fecha,
a una hora de inicio y por una duración. Otros clientes ven las franjas ocupadas
y eligen las libres. Una máquina con varias unidades admite reservas concurrentes
hasta agotar sus unidades.
"""
from __future__ import annotations

from datetime import date, datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, Time, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import ReservationStatus
from app.database.connection import Base
from app.models.machine import Machine

if TYPE_CHECKING:
    from app.models.client import Client


class MachineReservation(Base):
    """Reserva de una máquina por un cliente en una franja horaria concreta."""

    __tablename__ = "reservas_maquina"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)

    cliente_id: Mapped[int] = mapped_column(
        ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cliente: Mapped["Client"] = relationship("Client", lazy="select")

    maquina_id: Mapped[int] = mapped_column(
        ForeignKey("maquinas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    maquina: Mapped["Machine"] = relationship("Machine", lazy="select")

    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    hora_inicio: Mapped[time] = mapped_column(Time, nullable=False)
    hora_fin: Mapped[time] = mapped_column(Time, nullable=False)
    duracion_min: Mapped[int] = mapped_column(Integer, nullable=False)

    estado: Mapped[ReservationStatus] = mapped_column(
        Enum(ReservationStatus, name="reservation_status_enum"),
        nullable=False,
        default=ReservationStatus.ACTIVA,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<MachineReservation id={self.id} maquina={self.maquina_id} "
            f"cliente={self.cliente_id} {self.fecha} {self.hora_inicio}-{self.hora_fin}>"
        )
