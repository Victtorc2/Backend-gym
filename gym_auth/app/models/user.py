"""
Modelo SQLAlchemy para la entidad Usuario.
Define la tabla 'usuarios' con todos sus campos y restricciones.
"""
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import UserRole, UserStatus
from app.database.connection import Base

if TYPE_CHECKING:
    from app.models.client import Client


class User(Base):
    """
    Representa un usuario del sistema.

    Preparado para futuras relaciones (membresías, pagos, asistencia).
    """

    __tablename__ = "usuarios"

    # ── Identificación ─────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    nombres: Mapped[str] = mapped_column(String(100), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(100), nullable=False)
    dni: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)

    # ── Credenciales ───────────────────────────────────────────────────────────
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)

    # ── Rol y estado ───────────────────────────────────────────────────────────
    rol: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="rol_enum"),
        nullable=False,
    )
    estado: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="estado_enum"),
        nullable=False,
        default=UserStatus.ACTIVO,
        server_default=UserStatus.ACTIVO.value,
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

    # ── Relaciones ─────────────────────────────────────────────────────────────
    # Un usuario puede tener un perfil de cliente asociado
    cliente: Mapped["Client"] = relationship(
        "Client",
        back_populates="usuario",
        uselist=False,
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} rol={self.rol}>"
