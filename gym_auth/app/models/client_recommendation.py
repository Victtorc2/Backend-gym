"""
Modelo SQLAlchemy para Recomendación de Horario Personalizada a un Cliente.
Tabla 'recomendaciones_cliente': el administrador recomienda a un cliente
concreto un bloque horario de baja concurrencia (para descongestionar las
horas pico), y el cliente lo visualiza en su panel.

A diferencia de 'recomendaciones_horario' (análisis global de afluencia,
igual para todos), esta tabla es dirigida: cada fila apunta a un cliente.
Se apoya en el análisis de afluencia para sugerir la hora, pero el admin
tiene la última palabra.
"""
from __future__ import annotations

from datetime import datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Time,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import (
    AffluenceLevel,
    ClientRecommendationOrigin,
    ClientRecommendationStatus,
    WeekDay,
)
from app.database.connection import Base

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.user import User


class ClientRecommendation(Base):
    """
    Recomendación de horario asignada por el admin a un cliente específico.

    Regla de negocio: un cliente tiene como máximo una recomendación con
    estado ACTIVA. Al asignar una nueva, la anterior se marca DESCARTADA.
    """

    __tablename__ = "recomendaciones_cliente"

    # ── Identificación ─────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)

    # ── A quién se recomienda ──────────────────────────────────────────────────
    cliente_id: Mapped[int] = mapped_column(
        ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cliente: Mapped["Client"] = relationship("Client", lazy="select")

    # ── Bloque horario recomendado ─────────────────────────────────────────────
    dia_semana: Mapped[WeekDay] = mapped_column(
        Enum(WeekDay, name="client_reco_weekday_enum"),
        nullable=False,
        index=True,
    )
    hora_inicio: Mapped[time] = mapped_column(Time, nullable=False)
    hora_fin: Mapped[time] = mapped_column(Time, nullable=False)

    # ── Datos de afluencia (snapshot al momento de asignar) ────────────────────
    cantidad_promedio_estimada: Mapped[float | None] = mapped_column(
        Numeric(precision=8, scale=2),
        nullable=True,
    )
    nivel_afluencia: Mapped[AffluenceLevel | None] = mapped_column(
        Enum(AffluenceLevel, name="client_reco_level_enum"),
        nullable=True,
    )

    # ── Mensaje del administrador ──────────────────────────────────────────────
    mensaje: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # ── Metadatos ──────────────────────────────────────────────────────────────
    origen: Mapped[ClientRecommendationOrigin] = mapped_column(
        Enum(ClientRecommendationOrigin, name="client_reco_origin_enum"),
        nullable=False,
        default=ClientRecommendationOrigin.ASISTIDA,
    )
    estado: Mapped[ClientRecommendationStatus] = mapped_column(
        Enum(ClientRecommendationStatus, name="client_reco_status_enum"),
        nullable=False,
        default=ClientRecommendationStatus.ACTIVA,
        index=True,
    )
    creado_por: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    admin: Mapped["User | None"] = relationship("User", lazy="select")

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
            f"<ClientRecommendation id={self.id} cliente_id={self.cliente_id} "
            f"{self.dia_semana} {self.hora_inicio}-{self.hora_fin} "
            f"estado={self.estado}>"
        )
