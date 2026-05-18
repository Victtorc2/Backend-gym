"""
Servicio de Clientes.
El correo del cliente ES su email de login (sin username).
"""
import math

from app.core.constants import (
    TEMP_PASSWORD_DEFAULT,
    ClientStatus,
    UserRole,
    UserStatus,
)
from app.core.exceptions import (
    ClientAlreadyExistsException,
    ClientNotFoundException,
    UserNotFoundException,
)
from app.models.client import Client
from app.repositories.client_repository import ClientRepository
from app.repositories.user_repository import UserRepository
from app.schemas.client_schema import (
    ClientCreateSchema,
    ClientCreatedResponseSchema,
    ClientResponseSchema,
    ClientSearchParams,
    ClientStatusUpdateSchema,
    ClientUpdateSchema,
    PaginatedClientResponseSchema,
)
from app.schemas.user_schema import UserCreateSchema
from app.utils.client_classifier import classify_age_group


class ClientService:
    """Gestiona todas las operaciones de negocio del módulo de clientes."""

    def __init__(self, client_repo: ClientRepository, user_repo: UserRepository) -> None:
        self._clients = client_repo
        self._users = user_repo

    def register_client(self, data: ClientCreateSchema) -> ClientCreatedResponseSchema:
        """
        Registra un nuevo cliente en una transacción atómica.
        El correo del cliente se usa directamente como email de login.
        No se genera username; el identificador de acceso es el correo.
        """
        self._assert_dni_available(data.dni)
        correo = str(data.correo).lower().strip()
        self._assert_correo_available(correo)

        if self._users.get_by_email(correo):
            raise ClientAlreadyExistsException("correo")

        grupo_edad = classify_age_group(data.fecha_nacimiento)

        try:
            user_data = UserCreateSchema(
                nombres=data.nombres,
                apellidos=data.apellidos,
                dni=data.dni,
                email=correo,
                password=TEMP_PASSWORD_DEFAULT,
                rol=UserRole.CLIENTE,
            )
            user = self._users.create(user_data)

            client = self._clients.create(
                nombres=data.nombres,
                apellidos=data.apellidos,
                dni=data.dni,
                telefono=data.telefono,
                correo=correo,
                sexo=data.sexo,
                fecha_nacimiento=data.fecha_nacimiento,
                ocupacion=data.ocupacion,
                direccion=data.direccion,
                grupo_edad=grupo_edad,
                estado=ClientStatus.ACTIVO,
                user_id=user.id,
            )

            self._clients.commit()

        except Exception:
            self._clients.rollback()
            raise

        return ClientCreatedResponseSchema(
            cliente=ClientResponseSchema.model_validate(client),
            credenciales={
                "email": correo,
                "password_temporal": TEMP_PASSWORD_DEFAULT,
            },
        )

    def get_client(self, client_id: int) -> ClientResponseSchema:
        """Obtiene un cliente por ID."""
        client = self._clients.get_by_id(client_id)
        if client is None:
            raise ClientNotFoundException()
        return ClientResponseSchema.model_validate(client)

    def list_clients(self, params: ClientSearchParams) -> PaginatedClientResponseSchema:
        """Lista clientes con filtros y paginación."""
        items, total = self._clients.list_paginated(
            page=params.page,
            per_page=params.per_page,
            nombre=params.nombre,
            dni=params.dni,
            estado=params.estado,
        )
        total_pages = math.ceil(total / params.per_page) if total > 0 else 1
        return PaginatedClientResponseSchema(
            items=[ClientResponseSchema.model_validate(c) for c in items],
            total=total,
            page=params.page,
            per_page=params.per_page,
            total_pages=total_pages,
        )

    def update_client(self, client_id: int, data: ClientUpdateSchema) -> ClientResponseSchema:
        """
        Partial update de un cliente.
        Si cambia el correo, sincroniza el email del usuario asociado.
        """
        client = self._get_client_or_raise(client_id)
        updates: dict = {}
        payload = data.model_dump(exclude_none=True)

        if "correo" in payload:
            new_correo = str(payload["correo"]).lower().strip()
            if new_correo != client.correo:
                self._assert_correo_available(new_correo, exclude_id=client_id)
                user = self._users.get_by_id(client.user_id)
                if user:
                    self._users.update_email(user, new_correo)
            updates["correo"] = new_correo

        if "fecha_nacimiento" in payload:
            updates["grupo_edad"] = classify_age_group(payload["fecha_nacimiento"])
            updates["fecha_nacimiento"] = payload["fecha_nacimiento"]

        for field in {"nombres", "apellidos", "telefono", "sexo", "ocupacion", "direccion"}:
            if field in payload:
                updates[field] = payload[field]

        try:
            updated = self._clients.update(client, updates)
            self._clients.commit()
        except Exception:
            self._clients.rollback()
            raise

        return ClientResponseSchema.model_validate(updated)

    def toggle_client_status(self, client_id: int, data: ClientStatusUpdateSchema) -> ClientResponseSchema:
        """Activa o desactiva cliente y usuario de forma sincronizada."""
        client = self._get_client_or_raise(client_id)
        user = self._users.get_by_id(client.user_id)
        if user is None:
            raise UserNotFoundException()

        new_user_status = UserStatus.ACTIVO if data.estado == ClientStatus.ACTIVO else UserStatus.INACTIVO
        try:
            self._clients.update(client, {"estado": data.estado})
            self._users.update_status(user, new_user_status)
            self._clients.commit()
        except Exception:
            self._clients.rollback()
            raise

        return ClientResponseSchema.model_validate(client)

    def _get_client_or_raise(self, client_id: int) -> Client:
        client = self._clients.get_by_id(client_id)
        if client is None:
            raise ClientNotFoundException()
        return client

    def _assert_dni_available(self, dni: str) -> None:
        if self._clients.get_by_dni(dni):
            raise ClientAlreadyExistsException("dni")

    def _assert_correo_available(self, correo: str, exclude_id: int | None = None) -> None:
        existing = self._clients.get_by_correo(correo)
        if existing and (exclude_id is None or existing.id != exclude_id):
            raise ClientAlreadyExistsException("correo")
