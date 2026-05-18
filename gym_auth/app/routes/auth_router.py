"""
Router de autenticación.
Define los endpoints públicos y protegidos del módulo de acceso.
La lógica de negocio está delegada completamente al AuthService.
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.auth_dependencies import get_current_user
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth_schema import LoginRequestSchema
from app.services.auth_service import AuthService
from app.utils.responses import success_response

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])


def _get_auth_service(db: Annotated[Session, Depends(get_db)]) -> AuthService:
    """Factory de AuthService inyectado por FastAPI (DI limpio)."""
    return AuthService(UserRepository(db))


@router.post("/login", summary="Iniciar sesión")
def login(
    credentials: LoginRequestSchema,
    service: Annotated[AuthService, Depends(_get_auth_service)],
):
    """
    Autentica al usuario y devuelve un JWT.

    - **email**: correo registrado
    - **password**: contraseña del usuario
    """
    result = service.login(credentials)
    return success_response(
        data=result.model_dump(),
        message="Login exitoso",
    )


@router.get("/me", summary="Datos del usuario autenticado")
def me(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AuthService, Depends(_get_auth_service)],
):
    """
    Devuelve los datos del usuario autenticado.
    Requiere token JWT válido en el header `Authorization: Bearer <token>`.
    """
    result = service.get_authenticated_user(current_user.id)
    return success_response(
        data=result.model_dump(),
        message="Usuario autenticado",
    )
