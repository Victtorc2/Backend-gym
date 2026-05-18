"""
Schemas Pydantic para el módulo de Clientes.
Define contratos de entrada, salida y validaciones centralizadas.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.core.constants import AgeGroup, CLIENT_MIN_AGE, ClientSex, ClientStatus


# ── Schema base ────────────────────────────────────────────────────────────────

class ClientBaseSchema(BaseModel):
    """Campos comunes compartidos entre schemas de cliente."""

    nombres: str = Field(..., min_length=2, max_length=100, examples=["Víctor"])
    apellidos: str = Field(..., min_length=2, max_length=100, examples=["Chipana"])
    dni: str = Field(..., min_length=7, max_length=20, examples=["12345678"])
    telefono: str = Field(..., min_length=7, max_length=20, examples=["987654321"])
    correo: EmailStr = Field(..., examples=["victor@gym.com"])
    sexo: ClientSex
    fecha_nacimiento: date = Field(..., examples=["1995-06-15"])
    ocupacion: str | None = Field(default=None, max_length=150, examples=["Ingeniero"])
    direccion: str | None = Field(default=None, max_length=300, examples=["Av. Lima 123"])

    @field_validator("dni")
    @classmethod
    def dni_only_digits(cls, value: str) -> str:
        """El DNI debe contener solo dígitos."""
        cleaned = value.strip()
        if not cleaned.isdigit():
            raise ValueError("El DNI debe contener únicamente dígitos")
        return cleaned

    @field_validator("telefono")
    @classmethod
    def telefono_format(cls, value: str) -> str:
        """Valida que el teléfono tenga formato numérico válido."""
        cleaned = value.strip().replace(" ", "").replace("-", "")
        if not cleaned.lstrip("+").isdigit():
            raise ValueError("El teléfono solo puede contener dígitos, espacios o el signo '+'")
        if len(cleaned.lstrip("+")) < 7:
            raise ValueError("El teléfono debe tener al menos 7 dígitos")
        return cleaned

    @field_validator("fecha_nacimiento")
    @classmethod
    def validate_age(cls, value: date) -> date:
        """Valida que el cliente tenga la edad mínima requerida."""
        today = date.today()
        age = (
            today.year - value.year
            - ((today.month, today.day) < (value.month, value.day))
        )
        if value > today:
            raise ValueError("La fecha de nacimiento no puede ser futura")
        if age < CLIENT_MIN_AGE:
            raise ValueError(
                f"El cliente debe tener al menos {CLIENT_MIN_AGE} años de edad"
            )
        return value


# ── Crear cliente ──────────────────────────────────────────────────────────────

class ClientCreateSchema(ClientBaseSchema):
    """Schema de entrada para registrar un nuevo cliente (POST /api/clientes)."""
    pass


# ── Actualizar cliente ─────────────────────────────────────────────────────────

class ClientUpdateSchema(BaseModel):
    """
    Schema de entrada para actualizar datos de un cliente (PUT /api/clientes/{id}).
    Todos los campos son opcionales (partial update).
    """
    nombres: str | None = Field(default=None, min_length=2, max_length=100)
    apellidos: str | None = Field(default=None, min_length=2, max_length=100)
    telefono: str | None = Field(default=None, min_length=7, max_length=20)
    correo: EmailStr | None = None
    sexo: ClientSex | None = None
    fecha_nacimiento: date | None = None
    ocupacion: str | None = Field(default=None, max_length=150)
    direccion: str | None = Field(default=None, max_length=300)

    @field_validator("telefono")
    @classmethod
    def telefono_format(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip().replace(" ", "").replace("-", "")
        if not cleaned.lstrip("+").isdigit():
            raise ValueError("El teléfono solo puede contener dígitos o el signo '+'")
        return cleaned

    @field_validator("fecha_nacimiento")
    @classmethod
    def validate_age(cls, value: date | None) -> date | None:
        if value is None:
            return value
        today = date.today()
        age = (
            today.year - value.year
            - ((today.month, today.day) < (value.month, value.day))
        )
        if value > today:
            raise ValueError("La fecha de nacimiento no puede ser futura")
        if age < CLIENT_MIN_AGE:
            raise ValueError(f"El cliente debe tener al menos {CLIENT_MIN_AGE} años")
        return value


# ── Cambio de estado ───────────────────────────────────────────────────────────

class ClientStatusUpdateSchema(BaseModel):
    """Schema para PATCH /api/clientes/{id}/estado."""
    estado: ClientStatus = Field(..., examples=["activo"])


# ── Respuestas ─────────────────────────────────────────────────────────────────

class ClientResponseSchema(BaseModel):
    """Schema de respuesta completo para un cliente."""
    id: int
    nombres: str
    apellidos: str
    dni: str
    telefono: str
    correo: str
    sexo: ClientSex
    fecha_nacimiento: date
    ocupacion: str | None
    direccion: str | None
    grupo_edad: AgeGroup
    estado: ClientStatus
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ClientCreatedResponseSchema(BaseModel):
    """
    Respuesta extendida al registrar un cliente.
    Incluye credenciales temporales para entrega al cliente.
    """
    cliente: ClientResponseSchema
    credenciales: dict[str, str]


# ── Búsqueda y paginación ──────────────────────────────────────────────────────

class ClientSearchParams(BaseModel):
    """Parámetros de búsqueda y paginación para GET /api/clientes."""
    nombre: str | None = Field(default=None, description="Filtra por nombre o apellido")
    dni: str | None = Field(default=None, description="Filtra por DNI exacto")
    estado: ClientStatus | None = Field(default=None, description="Filtra por estado")
    page: int = Field(default=1, ge=1, description="Número de página")
    per_page: int = Field(default=20, ge=1, le=100, description="Registros por página")


class PaginatedClientResponseSchema(BaseModel):
    """Respuesta paginada de listado de clientes."""
    items: list[ClientResponseSchema]
    total: int
    page: int
    per_page: int
    total_pages: int
