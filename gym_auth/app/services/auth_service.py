"""
Servicio de Autenticación.
Contiene toda la lógica de negocio relacionada con login y acceso.
No tiene contacto directo con la BD ni con HTTP.
"""
from app.core.constants import UserRole
from app.core.exceptions import (
    InactiveUserException,
    InvalidCredentialsException,
    UserNotFoundException,
)
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth_schema import LoginRequestSchema, LoginResponseSchema
from app.schemas.user_schema import UserMeSchema


class AuthService:
    """Orquesta los flujos de autenticación y consulta de usuario autenticado."""

    def __init__(self, user_repo: UserRepository) -> None:
        self._user_repo = user_repo

    # ── Login ──────────────────────────────────────────────────────────────────

    def login(self, credentials: LoginRequestSchema) -> LoginResponseSchema:
        """
        Autentica un usuario con email y contraseña.

        Flujo:
            1. Buscar usuario por email.
            2. Verificar que la cuenta esté activa.
            3. Validar contraseña con bcrypt.
            4. Generar y devolver el JWT.

        Raises:
            InvalidCredentialsException: Email no registrado o contraseña incorrecta.
            InactiveUserException: Cuenta desactivada.
        """
        user = self._user_repo.get_by_email(credentials.email)

        # Mensaje genérico para no revelar si el email existe
        if user is None:
            raise InvalidCredentialsException()

        if not self._is_active(user):
            raise InactiveUserException()

        if not verify_password(credentials.password, user.password):
            raise InvalidCredentialsException()

        token = create_access_token(
            payload={"id": user.id, "email": user.email, "rol": user.rol.value}
        )

        return LoginResponseSchema(
            access_token=token,
            rol=user.rol,
            nombre=f"{user.nombres} {user.apellidos}",
        )

    # ── Usuario autenticado ────────────────────────────────────────────────────

    def get_authenticated_user(self, user_id: int) -> UserMeSchema:
        """
        Devuelve los datos del usuario autenticado a partir de su ID (extraído del JWT).

        Raises:
            UserNotFoundException: El ID no corresponde a ningún usuario.
        """
        user = self._user_repo.get_by_id(user_id)

        if user is None:
            raise UserNotFoundException()

        return UserMeSchema(
            id=user.id,
            nombre=f"{user.nombres} {user.apellidos}",
            email=user.email,
            rol=user.rol,
        )

    # ── Helpers privados ───────────────────────────────────────────────────────

    @staticmethod
    def _is_active(user: User) -> bool:
        """Verifica si el estado del usuario es activo."""
        from app.core.constants import UserStatus
        return user.estado == UserStatus.ACTIVO
