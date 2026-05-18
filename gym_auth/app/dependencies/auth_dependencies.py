"""
Dependencias de autenticación y autorización para FastAPI.
Usadas con Depends() en los endpoints para proteger rutas.
"""
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.constants import UserRole
from app.core.exceptions import AccessDeniedException, UserNotFoundException
from app.core.security import decode_access_token
from app.database.connection import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth_schema import TokenPayloadSchema

# Esquema HTTP Bearer para extracción automática del token del header
_bearer_scheme = HTTPBearer()


def get_token_payload(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer_scheme)],
) -> TokenPayloadSchema:
    """
    Extrae y valida el JWT del header Authorization.
    Devuelve el payload deserializado.
    """
    raw_payload = decode_access_token(credentials.credentials)
    return TokenPayloadSchema(**raw_payload)


def get_current_user(
    payload: Annotated[TokenPayloadSchema, Depends(get_token_payload)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """
    Resuelve el usuario autenticado a partir del JWT.
    Puede usarse en cualquier endpoint que requiera usuario autenticado.

    Raises:
        UserNotFoundException: Si el ID del token no existe en BD.
    """
    repo = UserRepository(db)
    user = repo.get_by_id(payload.id)

    if user is None:
        raise UserNotFoundException()

    return user


# ── Guards de roles ────────────────────────────────────────────────────────────

def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Restringe el acceso a usuarios con rol 'administrador'.

    Uso:
        @router.get("/ruta", dependencies=[Depends(require_admin)])
        # o
        user: User = Depends(require_admin)
    """
    if current_user.rol != UserRole.ADMINISTRADOR:
        raise AccessDeniedException("Se requiere rol de administrador")
    return current_user


def require_cliente(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Restringe el acceso a usuarios con rol 'cliente'.

    Uso:
        @router.get("/ruta", dependencies=[Depends(require_cliente)])
    """
    if current_user.rol != UserRole.CLIENTE:
        raise AccessDeniedException("Se requiere rol de cliente")
    return current_user
