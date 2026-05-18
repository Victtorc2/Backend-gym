"""
Router del módulo de Membresías y Tarjetas.
Define todos los endpoints REST del módulo.
Toda la lógica está delegada a MembershipService y CardService.
Acceso restringido a administradores mediante require_admin().
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.constants import CardStatus, MembershipStatus, MembershipType
from app.database.connection import get_db
from app.dependencies.auth_dependencies import require_admin
from app.repositories.card_repository import CardRepository
from app.repositories.client_repository import ClientRepository
from app.repositories.membership_repository import MembershipRepository
from app.schemas.card_schema import CardStatusUpdateSchema
from app.schemas.membership_schema import MembershipCreateSchema, MembershipUpdateSchema
from app.services.card_service import CardService
from app.services.membership_service import MembershipService
from app.utils.responses import success_response

# ── Sub-routers ────────────────────────────────────────────────────────────────
membership_router = APIRouter(
    prefix="/api/membresias",
    tags=["Membresías"],
)
card_router = APIRouter(
    prefix="/api/tarjetas",
    tags=["Tarjetas"],
)


# ── Factories de servicios ─────────────────────────────────────────────────────

def _get_membership_service(db: Annotated[Session, Depends(get_db)]) -> MembershipService:
    """Provee MembershipService con repositorios inyectados."""
    return MembershipService(
        membership_repo=MembershipRepository(db),
        card_repo=CardRepository(db),
        client_repo=ClientRepository(db),
    )


def _get_card_service(db: Annotated[Session, Depends(get_db)]) -> CardService:
    """Provee CardService con repositorios inyectados."""
    return CardService(
        card_repo=CardRepository(db),
        client_repo=ClientRepository(db),
    )


# ══════════════════════════════════════════════════════════════════════════════
#  MEMBRESÍAS
# ══════════════════════════════════════════════════════════════════════════════

@membership_router.post(
    "",
    status_code=201,
    summary="Registrar membresía",
    dependencies=[Depends(require_admin)],
)
def register_membership(
    data: MembershipCreateSchema,
    service: Annotated[MembershipService, Depends(_get_membership_service)],
):
    """
    Registra una membresía para un cliente.

    - Calcula **automáticamente** fecha_inicio, fecha_fin y duración.
    - Emite **tarjeta** automáticamente para membresías mensual o anual.
    - Devuelve membresía y tarjeta (si corresponde) en una sola respuesta.

    **Solo administradores.**
    """
    result = service.register_membership(data)
    return success_response(
        data=result,
        message="Membresía registrada correctamente",
        status_code=201,
    )


@membership_router.get(
    "/cliente/{cliente_id}",
    summary="Membresías por cliente",
    dependencies=[Depends(require_admin)],
)
def get_memberships_by_client(
    cliente_id: int,
    service: Annotated[MembershipService, Depends(_get_membership_service)],
):
    """
    Lista todas las membresías de un cliente con vigencia recalculada.

    **Solo administradores.**
    """
    result = service.get_by_cliente(cliente_id)
    return success_response(
        data=[r.model_dump() for r in result],
        message=f"Membresías del cliente {cliente_id}",
    )


@membership_router.get(
    "",
    summary="Listar membresías",
    dependencies=[Depends(require_admin)],
)
def list_memberships(
    service: Annotated[MembershipService, Depends(_get_membership_service)],
    estado: MembershipStatus | None = Query(default=None, description="Filtra por estado"),
    tipo: MembershipType | None = Query(default=None, description="Filtra por tipo"),
):
    """
    Lista todas las membresías con filtros opcionales y vigencia en tiempo real.

    **Solo administradores.**
    """
    result = service.list_memberships(estado=estado, tipo=tipo)
    return success_response(
        data=[r.model_dump() for r in result],
        message="Listado de membresías",
    )


@membership_router.get(
    "/{membership_id}",
    summary="Consultar membresía",
    dependencies=[Depends(require_admin)],
)
def get_membership(
    membership_id: int,
    service: Annotated[MembershipService, Depends(_get_membership_service)],
):
    """
    Devuelve una membresía por ID con estado de vigencia recalculado.

    **Solo administradores.**
    """
    result = service.get_membership(membership_id)
    return success_response(data=result.model_dump(), message="Membresía encontrada")


@membership_router.put(
    "/{membership_id}",
    summary="Actualizar membresía",
    dependencies=[Depends(require_admin)],
)
def update_membership(
    membership_id: int,
    data: MembershipUpdateSchema,
    service: Annotated[MembershipService, Depends(_get_membership_service)],
):
    """
    Actualiza precio y/o estado de una membresía (partial update).

    **Solo administradores.**
    """
    result = service.update_membership(membership_id, data)
    return success_response(
        data=result.model_dump(),
        message="Membresía actualizada correctamente",
    )


# ══════════════════════════════════════════════════════════════════════════════
#  TARJETAS
# ══════════════════════════════════════════════════════════════════════════════

@card_router.get(
    "/cliente/{cliente_id}",
    summary="Tarjetas por cliente",
    dependencies=[Depends(require_admin)],
)
def get_cards_by_client(
    cliente_id: int,
    service: Annotated[CardService, Depends(_get_card_service)],
):
    """
    Lista todas las tarjetas de un cliente.

    **Solo administradores.**
    """
    result = service.get_by_cliente(cliente_id)
    return success_response(
        data=[r.model_dump() for r in result],
        message=f"Tarjetas del cliente {cliente_id}",
    )


@card_router.get(
    "",
    summary="Listar tarjetas",
    dependencies=[Depends(require_admin)],
)
def list_cards(
    service: Annotated[CardService, Depends(_get_card_service)],
    estado: CardStatus | None = Query(default=None, description="Filtra por estado"),
):
    """
    Lista todas las tarjetas con filtro opcional de estado.

    **Solo administradores.**
    """
    result = service.list_cards(estado=estado)
    return success_response(
        data=[r.model_dump() for r in result],
        message="Listado de tarjetas",
    )


@card_router.get(
    "/{card_id}",
    summary="Consultar tarjeta",
    dependencies=[Depends(require_admin)],
)
def get_card(
    card_id: int,
    service: Annotated[CardService, Depends(_get_card_service)],
):
    """
    Devuelve una tarjeta por ID.

    **Solo administradores.**
    """
    result = service.get_card(card_id)
    return success_response(data=result.model_dump(), message="Tarjeta encontrada")


@card_router.patch(
    "/{card_id}/estado",
    summary="Activar o desactivar tarjeta",
    dependencies=[Depends(require_admin)],
)
def toggle_card_status(
    card_id: int,
    data: CardStatusUpdateSchema,
    service: Annotated[CardService, Depends(_get_card_service)],
):
    """
    Cambia el estado de una tarjeta (activa ↔ inactiva).

    **Solo administradores.**
    """
    result = service.toggle_card_status(card_id, data)
    action = "activada" if data.estado.value == "activa" else "desactivada"
    return success_response(
        data=result.model_dump(),
        message=f"Tarjeta {action} correctamente",
    )
