"""
Modelo SQLAlchemy para Recomendación de Horario (Fase 10).
Tabla 'recomendaciones_horario': almacena el análisis de afluencia por
bloque horario (día + franja de una hora) calculado desde 'asistencias'.

Este módulo solo consume la tabla 'asistencias'; no la modifica.
Cada generación regenera los bloques para reflejar el historial más reciente.
"""
from __future__ import annotations

from datetime import datetime, time

from sqlalchemy import Boolean, DateTime, Enum, Integer, Numeric, Time, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import AffluenceLevel, WeekDay
from app.database.connection import Base


class ScheduleRecommendation(Base):
    """
    Recomendación de afluencia para un bloque horario específico.

    Un bloque está definido por la combinación única (dia_semana, hora_inicio).
    Cada fila representa una franja de una hora dentro del horario de operación
    (07:00–22:00) para un día concreto (lunes–sábado).
    """

    __tablename__ = "recomendaciones_horario"

    # Un solo registro por bloque (día + hora de inicio)
    __table_args__ = (
        UniqueConstraint("dia_semana", "hora_inicio", name="uq_recomendacion_dia_hora"),
    )

    # ── Identificación ─────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)

    # ── Bloque horario ─────────────────────────────────────────────────────────
    dia_semana: Mapped[WeekDay] = mapped_column(
        Enum(WeekDay, name="recommendation_weekday_enum"),
        nullable=False,
        index=True,
    )
    hora_inicio: Mapped[time] = mapped_column(Time, nullable=False)
    hora_fin: Mapped[time] = mapped_column(Time, nullable=False)

    # ── Métricas calculadas ────────────────────────────────────────────────────
    cantidad_promedio: Mapped[float] = mapped_column(
        Numeric(precision=8, scale=2),
        nullable=False,
        default=0,
    )
    nivel_afluencia: Mapped[AffluenceLevel] = mapped_column(
        Enum(AffluenceLevel, name="recommendation_level_enum"),
        nullable=False,
        index=True,
    )

    # ── Flags de recomendación ─────────────────────────────────────────────────
    es_recomendado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    evitar: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

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

    def __repr__(self) -> str:
        return (
            f"<ScheduleRecommendation {self.dia_semana} "
            f"{self.hora_inicio}-{self.hora_fin} "
            f"nivel={self.nivel_afluencia} prom={self.cantidad_promedio}>"
        )
