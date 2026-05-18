"""
Seed del administrador inicial.
Se ejecuta automáticamente al arrancar la aplicación.
Solo crea el admin si no existe ninguno. Nunca duplica registros.
"""
import logging

from sqlalchemy.orm import Session

from app.core.constants import (
    ADMIN_DEFAULT_APELLIDOS,
    ADMIN_DEFAULT_DNI,
    ADMIN_DEFAULT_EMAIL,
    ADMIN_DEFAULT_NOMBRES,
    ADMIN_DEFAULT_PASSWORD,
    UserRole,
)
from app.repositories.user_repository import UserRepository
from app.schemas.user_schema import UserCreateSchema

logger = logging.getLogger(__name__)


def run_admin_seed(db: Session) -> None:
    """
    Verifica y crea el usuario administrador por defecto si no existe.

    Args:
        db: Sesión de base de datos activa.
    """
    repo = UserRepository(db)

    if repo.exists_admin():
        logger.info("Seed: administrador ya existe, se omite la creación.")
        return

    admin_data = UserCreateSchema(
        nombres=ADMIN_DEFAULT_NOMBRES,
        apellidos=ADMIN_DEFAULT_APELLIDOS,
        dni=ADMIN_DEFAULT_DNI,
        email=ADMIN_DEFAULT_EMAIL,
        password=ADMIN_DEFAULT_PASSWORD,
        rol=UserRole.ADMINISTRADOR,
    )

    admin = repo.create_and_commit(admin_data)
    logger.info("Seed: administrador creado → email=%s, id=%d", admin.email, admin.id)
