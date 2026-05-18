"""
Seguridad: hashing de contraseñas y manejo de JWT.
Todas las operaciones criptográficas viven aquí (SRP).
"""
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.exceptions import InvalidCredentialsException, TokenExpiredException

# ── Hashing ────────────────────────────────────────────────────────────────────
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Genera el hash bcrypt de una contraseña en texto plano."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si la contraseña en texto plano coincide con el hash."""
    return _pwd_context.verify(plain_password, hashed_password)


# ── JWT ────────────────────────────────────────────────────────────────────────

def create_access_token(payload: dict[str, Any]) -> str:
    """
    Genera un JWT firmado con los datos del payload.

    Args:
        payload: Datos a incluir en el token (id, email, rol).

    Returns:
        Token JWT como string.
    """
    data = payload.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    data["exp"] = expire
    return jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decodifica y valida un JWT.

    Args:
        token: Token JWT a verificar.

    Returns:
        Payload decodificado.

    Raises:
        TokenExpiredException: Si el token ha expirado.
        InvalidCredentialsException: Si el token es inválido.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as exc:
        # Distingue token expirado de token malformado
        if "expired" in str(exc).lower():
            raise TokenExpiredException()
        raise InvalidCredentialsException()
