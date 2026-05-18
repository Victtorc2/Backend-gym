"""
Modelo SQLAlchemy para la entidad Cliente.
Define la tabla 'clientes' con clasificación demográfica/socioeconómica
y relación 1-a-1 con la tabla 'usuarios'.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import AgeGroup, ClientSex, ClientStatus
from app.database.connection import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.membership import Membership
    from app.models.card import Card
    from app.models.payment import Payment
    from app.models.attendance import Attendance


class Client(Base):
    """
    Perfil de cliente del gimnasio.

    Cada cliente está asociado a exactamente un usuario del sistema
    (relación 1-a-1 con la tabla 'usuarios').
    Preparado para futuras relaciones: membresías, pagos, asistencia.
    """

    __tablename__ = "clientes"

    # ── Identificación ─────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    nombres: Mapped[str] = mapped_column(String(100), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(100), nullable=False)
    dni: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)

    # ── Contacto ───────────────────────────────────────────────────────────────
    telefono: Mapped[str] = mapped_column(String(20), nullable=False)
    correo: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    direccion: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # ── Datos personales ───────────────────────────────────────────────────────
    sexo: Mapped[ClientSex] = mapped_column(
        Enum(ClientSex, name="sexo_enum"),
        nullable=False,
    )
    fecha_nacimiento: Mapped[date] = mapped_column(Date, nullable=False)
    ocupacion: Mapped[str | None] = mapped_column(String(150), nullable=True)

    # ── Clasificación automática ───────────────────────────────────────────────
    grupo_edad: Mapped[AgeGroup] = mapped_column(
        Enum(AgeGroup, name="grupo_edad_enum"),
        nullable=False,
    )

    # ── Estado ────────────────────────────────────────────────────────────────
    estado: Mapped[ClientStatus] = mapped_column(
        Enum(ClientStatus, name="client_estado_enum"),
        nullable=False,
        default=ClientStatus.ACTIVO,
        server_default=ClientStatus.ACTIVO.value,
    )

    # ── Relación con usuario ───────────────────────────────────────────────────
    user_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
        index=True,
    )
    usuario: Mapped["User"] = relationship(
        "User",
        back_populates="cliente",
        lazy="select",
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

    # ── Relaciones futuras (declaradas aquí para escalabilidad) ─────────────────
    membresias: Mapped[list["Membership"]] = relationship(
        "Membership",
        back_populates="cliente",
        lazy="select",
        order_by="Membership.created_at.desc()",
    )
    tarjetas: Mapped[list["Card"]] = relationship(
        "Card",
        back_populates="cliente",
        lazy="select",
    )
    pagos: Mapped[list["Payment"]] = relationship(
        "Payment",
        back_populates="cliente",
        lazy="select",
        order_by="Payment.fecha_pago.desc()",
    )
    asistencias: Mapped[list["Attendance"]] = relationship(
        "Attendance",
        back_populates="cliente",
        lazy="select",
        order_by="Attendance.fecha.desc()",
    )

    def __repr__(self) -> str:
        return f"<Client id={self.id} dni={self.dni} estado={self.estado}>"
