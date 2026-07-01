"""
Modelos SQLAlchemy para Rutinas (plantillas de entrenamiento).
Tablas:
  - 'rutinas': plantilla creada por el administrador (rol entrenador).
  - 'rutina_maquinas': asociación N:M entre rutina y máquinas involucradas.

Una rutina agrupa las máquinas que un cliente usará al ejecutarla. Al
planificar su día, el cliente puede elegir una rutina y el sistema deduce
automáticamente las máquinas.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base
from app.models.machine import Machine

if TYPE_CHECKING:
    from app.models.user import User


class Routine(Base):
    """Plantilla de rutina de entrenamiento con sus máquinas asociadas."""

    __tablename__ = "rutinas"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    descripcion: Mapped[str | None] = mapped_column(String(300), nullable=True)

    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    creada_por: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    autor: Mapped["User | None"] = relationship("User", lazy="select")

    # Máquinas de la rutina (vía asociación)
    maquinas: Mapped[list["RoutineMachine"]] = relationship(
        "RoutineMachine",
        back_populates="rutina",
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
        return f"<Routine id={self.id} {self.nombre!r}>"


class RoutineMachine(Base):
    """Asociación entre una rutina y una máquina que la compone."""

    __tablename__ = "rutina_maquinas"
    __table_args__ = (
        UniqueConstraint("rutina_id", "maquina_id", name="uq_rutina_maquina"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    rutina_id: Mapped[int] = mapped_column(
        ForeignKey("rutinas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    maquina_id: Mapped[int] = mapped_column(
        ForeignKey("maquinas.id", ondelete="CASCADE"), nullable=False, index=True
    )

    rutina: Mapped["Routine"] = relationship("Routine", back_populates="maquinas", lazy="select")
    maquina: Mapped["Machine"] = relationship("Machine", lazy="select")

    def __repr__(self) -> str:
        return f"<RoutineMachine rutina={self.rutina_id} maquina={self.maquina_id}>"
