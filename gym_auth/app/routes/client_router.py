"""
Router del módulo de Clientes.
Define los 6 endpoints REST del módulo.
Toda la lógica está delegada al ClientService.
Acceso restringido a administradores mediante require_admin().
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.auth_dependencies import require_admin
from app.models.user import User
from app.repositories.client_repository import ClientRepository
from app.repositories.user_repository import UserRepository
from app.schemas.client_schema import (
    ClientCreateSchema,
    ClientSearchParams,
    ClientStatusUpdateSchema,
    ClientUpdateSchema,
)
from app.core.constants import ClientStatus
from app.services.client_service import ClientService
from app.utils.responses import success_response

router = APIRouter(prefix="/api/clientes", tags=["Clientes"])


# ── Factory de servicio ────────────────────────────────────────────────────────

def _get_client_service(db: Annotated[Session, Depends(get_db)]) -> ClientService:
    """Provee una instancia de ClientService con sus repositorios inyectados."""
    return ClientService(
        client_repo=ClientRepository(db),
        user_repo=UserRepository(db),
    )


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post(
    "",
    status_code=201,
    summary="Registrar nuevo cliente",
    dependencies=[Depends(require_admin)],
)
def register_client(
    data: ClientCreateSchema,
    service: Annotated[ClientService, Depends(_get_client_service)],
):
    """
    Registra un nuevo cliente en el sistema.

    - Valida unicidad de DNI y correo.
    - Clasifica automáticamente por edad.
    - Crea cuenta de usuario con credenciales temporales.
    - Retorna datos del cliente y credenciales para entrega.

    **Solo administradores.**
    """
    result = service.register_client(data)
    return success_response(
        data=result.model_dump(),
        message="Cliente registrado correctamente",
        status_code=201,
    )


@router.get(
    "/busqueda",
    summary="Buscar clientes por nombre o DNI",
    dependencies=[Depends(require_admin)],
)
def search_clients(
    service: Annotated[ClientService, Depends(_get_client_service)],
    nombre: str | None = Query(default=None, description="Busca por nombre o apellido"),
    dni: str | None = Query(default=None, description="Busca por DNI exacto"),
    estado: ClientStatus | None = Query(default=None, description="Filtra por estado"),
    page: int = Query(default=1, ge=1, description="Número de página"),
    per_page: int = Query(default=20, ge=1, le=100, description="Registros por página"),
):
    """
    Busca clientes aplicando filtros opcionales de nombre, DNI y estado.
    Soporta paginación.

    **Solo administradores.**
    """
    params = ClientSearchParams(
        nombre=nombre,
        dni=dni,
        estado=estado,
        page=page,
        per_page=per_page,
    )
    result = service.list_clients(params)
    return success_response(data=result.model_dump(), message="Resultados de búsqueda")


@router.get(
    "",
    summary="Listar todos los clientes",
    dependencies=[Depends(require_admin)],
)
def list_clients(
    service: Annotated[ClientService, Depends(_get_client_service)],
    estado: ClientStatus | None = Query(default=None, description="Filtra por estado"),
    page: int = Query(default=1, ge=1, description="Número de página"),
    per_page: int = Query(default=20, ge=1, le=100, description="Registros por página"),
):
    """
    Devuelve el listado paginado de todos los clientes.
    Admite filtro por estado (activo/inactivo).

    **Solo administradores.**
    """
    params = ClientSearchParams(estado=estado, page=page, per_page=per_page)
    result = service.list_clients(params)
    return success_response(data=result.model_dump(), message="Listado de clientes")


@router.get(
    "/{client_id}",
    summary="Consultar cliente por ID",
    dependencies=[Depends(require_admin)],
)
def get_client(
    client_id: int,
    service: Annotated[ClientService, Depends(_get_client_service)],
):
    """
    Devuelve los datos completos de un cliente por su ID.

    **Solo administradores.**
    """
    result = service.get_client(client_id)
    return success_response(data=result.model_dump(), message="Cliente encontrado")


@router.put(
    "/{client_id}",
    summary="Actualizar datos del cliente",
    dependencies=[Depends(require_admin)],
)
def update_client(
    client_id: int,
    data: ClientUpdateSchema,
    service: Annotated[ClientService, Depends(_get_client_service)],
):
    """
    Actualiza los campos editables de un cliente.
    Solo se modifican los campos enviados (partial update).

    **Solo administradores.**
    """
    result = service.update_client(client_id, data)
    return success_response(data=result.model_dump(), message="Cliente actualizado correctamente")


@router.patch(
    "/{client_id}/estado",
    summary="Activar o desactivar cliente",
    dependencies=[Depends(require_admin)],
)
def toggle_client_status(
    client_id: int,
    data: ClientStatusUpdateSchema,
    service: Annotated[ClientService, Depends(_get_client_service)],
):
    """
    Cambia el estado del cliente (activo ↔ inactivo).

    Al desactivar: el cliente y su usuario quedan bloqueados.
    Al activar: el cliente y su usuario recuperan acceso.

    **Solo administradores.**
    """
    result = service.toggle_client_status(client_id, data)
    action = "activado" if data.estado.value == "activo" else "desactivado"
    return success_response(
        data=result.model_dump(),
        message=f"Cliente {action} correctamente",
    )
