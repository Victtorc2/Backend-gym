"""
Schemas Pydantic para la entidad Usuario.
Define contratos de entrada/salida y validaciones centralizadas.
"""
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.constants import UserRole, UserStatus


class UserBase(BaseModel):
    """Campos comunes compartidos entre schemas de usuario."""
    nombres: str = Field(..., min_length=2, max_length=100, examples=["Juan"])
    apellidos: str = Field(..., min_length=2, max_length=100, examples=["Pérez"])
    dni: str = Field(..., min_length=7, max_length=20, examples=["12345678"])
    email: EmailStr = Field(..., examples=["juan@gym.com"])


class UserCreateSchema(UserBase):
    """Schema para crear un usuario (uso interno / seed)."""
    password: str = Field(..., min_length=6, max_length=128)
    rol: UserRole = Field(default=UserRole.CLIENTE)

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        """Valida que la contraseña tenga al menos una mayúscula y un número."""
        if not any(c.isupper() for c in value):
            raise ValueError("La contraseña debe contener al menos una mayúscula")
        if not any(c.isdigit() for c in value):
            raise ValueError("La contraseña debe contener al menos un número")
        return value


class UserResponseSchema(UserBase):
    """Schema de respuesta con datos públicos del usuario."""
    id: int
    rol: UserRole
    estado: UserStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserMeSchema(BaseModel):
    """Schema reducido para el endpoint /me."""
    id: int
    nombre: str   # nombres completos
    email: EmailStr
    rol: UserRole

    model_config = {"from_attributes": True}
