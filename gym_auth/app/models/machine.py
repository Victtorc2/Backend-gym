"""
Modelo SQLAlchemy para la entidad Máquina (equipo del gimnasio).
Tabla 'maquinas': catálogo de máquinas con su zona muscular y la cantidad
de unidades disponibles. Es la base para calcular la demanda prevista y el
Índice de Demanda del módulo de Planificación Inteligente.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import MuscleZone
from app.database.connection import Base


class Machine(Base):
    """Máquina/equipo del gimnasio, con su zona muscular y unidades disponibles."""

    __tablename__ = "maquinas"

    # ── Identificación ─────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    descripcion: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # Ruta relativa de la foto servida por el backend (ej. /static/maquinas/3_ab12.jpg)
    foto_url: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # ── Clasificación ──────────────────────────────────────────────────────────
    zona: Mapped[MuscleZone] = mapped_column(
        Enum(MuscleZone, name="machine_zone_enum"),
        nullable=False,
        index=True,
    )

    # ── Capacidad ──────────────────────────────────────────────────────────────
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # ── Estado ─────────────────────────────────────────────────────────────────
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # ── Timestamps ─────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Machine id={self.id} {self.nombre!r} zona={self.zona} x{self.cantidad}>"
