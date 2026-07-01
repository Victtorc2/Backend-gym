"""
Modelos SQLAlchemy para la Planificación de Entrenamiento del cliente.
Tablas:
  - 'planes_entrenamiento': intención de un cliente de entrenar un día/hora,
    con un nivel de compromiso (planeado / confirmado / en_camino).
  - 'plan_maquinas': máquinas que el cliente prevé usar (resueltas desde las
    zonas seleccionadas y/o la rutina elegida).

Esto NO es una reserva: solo registra una intención de uso para anticipar la
demanda por máquina, zona y horario.
"""
from __future__ import annotations

from datetime import date, datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import TrainingPlanStatus
from app.database.connection import Base
from app.models.machine import Machine

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.routine import Routine


class TrainingPlan(Base):
    """Planificación de entrenamiento de un cliente para un día concreto."""

    __tablename__ = "planes_entrenamiento"
    __table_args__ = (
        # Un plan por cliente y fecha (se actualiza si vuelve a planificar)
        UniqueConstraint("cliente_id", "fecha", name="uq_plan_cliente_fecha"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)

    cliente_id: Mapped[int] = mapped_column(
        ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cliente: Mapped["Client"] = relationship("Client", lazy="select")

    # ── Cuándo ─────────────────────────────────────────────────────────────────
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    hora_inicio: Mapped[time] = mapped_column(Time, nullable=False, index=True)

    # ── Compromiso ─────────────────────────────────────────────────────────────
    estado: Mapped[TrainingPlanStatus] = mapped_column(
        Enum(TrainingPlanStatus, name="training_plan_status_enum"),
        nullable=False,
        default=TrainingPlanStatus.PLANEADO,
        index=True,
    )

    # ── Origen (opcional): rutina del entrenador ───────────────────────────────
    rutina_id: Mapped[int | None] = mapped_column(
        ForeignKey("rutinas.id", ondelete="SET NULL"), nullable=True
    )
    rutina: Mapped["Routine | None"] = relationship("Routine", lazy="select")

    # ── Máquinas previstas ─────────────────────────────────────────────────────
    maquinas: Mapped[list["TrainingPlanMachine"]] = relationship(
        "TrainingPlanMachine",
        back_populates="plan",
        cascade="all, delete-orphan",
        lazy="select",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<TrainingPlan id={self.id} cliente={self.cliente_id} "
            f"{self.fecha} {self.hora_inicio} estado={self.estado}>"
        )


class TrainingPlanMachine(Base):
    """Máquina que un cliente prevé usar dentro de su plan del día."""

    __tablename__ = "plan_maquinas"
    __table_args__ = (
        UniqueConstraint("plan_id", "maquina_id", name="uq_plan_maquina"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("planes_entrenamiento.id", ondelete="CASCADE"), nullable=False, index=True
    )
    maquina_id: Mapped[int] = mapped_column(
        ForeignKey("maquinas.id", ondelete="CASCADE"), nullable=False, index=True
    )

    plan: Mapped["TrainingPlan"] = relationship("TrainingPlan", back_populates="maquinas", lazy="select")
    maquina: Mapped["Machine"] = relationship("Machine", lazy="select")

    def __repr__(self) -> str:
        return f"<TrainingPlanMachine plan={self.plan_id} maquina={self.maquina_id}>"
