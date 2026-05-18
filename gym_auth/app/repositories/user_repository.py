"""
Repositorio de Usuario.
Única capa autorizada para interactuar con la tabla 'usuarios'.
Abstrae SQLAlchemy de la lógica de negocio (Repository Pattern).
"""
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user_schema import UserCreateSchema
from app.core.security import hash_password
from app.core.constants import UserRole, UserStatus


class UserRepository:
    """Gestiona todas las operaciones de persistencia relacionadas con usuarios."""

    def __init__(self, db: Session) -> None:
        self._db = db

    # ── Consultas ──────────────────────────────────────────────────────────────

    def get_by_id(self, user_id: int) -> User | None:
        """Busca un usuario por su ID primario."""
        return self._db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> User | None:
        """Busca un usuario por email (case-insensitive)."""
        return (
            self._db.query(User)
            .filter(User.email == email.lower().strip())
            .first()
        )

    def get_by_dni(self, dni: str) -> User | None:
        """Busca un usuario por DNI."""
        return self._db.query(User).filter(User.dni == dni).first()

    def exists_admin(self) -> bool:
        """Verifica si ya existe al menos un usuario con rol administrador."""
        return (
            self._db.query(User)
            .filter(User.rol == UserRole.ADMINISTRADOR)
            .first()
        ) is not None

    def count_by_email_prefix(self, prefix: str) -> int:
        """
        Cuenta usuarios cuyo email empiece con el prefijo dado.
        Usado para generar usernames únicos al crear cuentas de cliente.
        """
        return (
            self._db.query(User)
            .filter(User.email.like(f"{prefix}%"))
            .count()
        )

    def update_status(self, user: User, status: UserStatus) -> User:
        """Actualiza el estado de un usuario existente."""
        user.estado = status
        self._db.flush()
        self._db.refresh(user)
        return user

    def update_email(self, user: User, new_email: str) -> User:
        """Actualiza el email de un usuario (usado al modificar correo del cliente)."""
        user.email = new_email.lower().strip()
        self._db.flush()
        self._db.refresh(user)
        return user

    def commit(self) -> None:
        """Confirma la transacción activa."""
        self._db.commit()

    def rollback(self) -> None:
        """Revierte la transacción activa."""
        self._db.rollback()

    # ── Escritura ──────────────────────────────────────────────────────────────

    def create(self, data: UserCreateSchema) -> User:
        """
        Crea un nuevo usuario.
        Aplica hash a la contraseña antes de persistirla.
        Usa flush para participar en transacciones coordinadas.
        """
        user = User(
            nombres=data.nombres.strip(),
            apellidos=data.apellidos.strip(),
            dni=data.dni.strip(),
            email=data.email.lower().strip(),
            password=hash_password(data.password),
            rol=data.rol,
            estado=UserStatus.ACTIVO,
        )
        self._db.add(user)
        self._db.flush()
        self._db.refresh(user)
        return user

    def create_and_commit(self, data: UserCreateSchema) -> User:
        """Crea usuario y confirma la transacción (para uso en seed y flujos simples)."""
        user = self.create(data)
        self._db.commit()
        self._db.refresh(user)
        return user
