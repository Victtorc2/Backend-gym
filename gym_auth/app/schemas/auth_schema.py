"""
Schemas Pydantic para los endpoints de autenticación.
"""
from pydantic import BaseModel, EmailStr, Field

from app.core.constants import TOKEN_TYPE, UserRole


class LoginRequestSchema(BaseModel):
    """Payload de entrada para POST /api/auth/login."""
    email: EmailStr = Field(..., examples=["admin@gym.com"])
    password: str = Field(..., min_length=1, examples=["Admin123"])


class LoginResponseSchema(BaseModel):
    """Respuesta del endpoint de login."""
    access_token: str
    token_type: str = TOKEN_TYPE
    rol: UserRole
    nombre: str


class TokenPayloadSchema(BaseModel):
    """Estructura interna del payload JWT."""
    id: int
    email: str
    rol: UserRole
    exp: int | None = None
