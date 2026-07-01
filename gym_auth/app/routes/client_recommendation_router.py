"""
Router de Recomendación Personalizada a Clientes.
Endpoints para que el administrador recomiende una hora de baja concurrencia
a un cliente concreto. Acceso restringido a administradores.

Toda la lógica se delega al ClientRecommendationService.
Orden: rutas fijas antes de rutas con parámetros dinámicos.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.constants import ClientRecommendationStatus, ClientStatus
from app.database.connection import get_db
from app.dependencies.auth_dependencies import require_admin
from app.models.user import User
from app.repositories.client_recommendation_repository import (
    ClientRecommendationRepository,
)
from app.schemas.client_recommendation_schema import (
    CandidateFilterSchema,
    CreateClientRecommendationSchema,
)
from app.services.client_recommendation_service import ClientRecommendationService
from app.utils.responses import success_response

router = APIRouter(
    prefix="/api/recomendaciones-cliente",
    tags=["Recomendación a Clientes"],
)


# ── Factory de servicio ────────────────────────────────────────────────────────

def _get_service(
    db: Annotated[Session, Depends(get_db)],
) -> ClientRecommendationService:
    """Provee ClientRecommendationService con su repositorio inyectado."""
    return ClientRecommendationService(ClientRecommendationRepository(db))


# ══════════════════════════════════════════════════════════════════════════════
#  SUGERENCIAS — horas con poca gente
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/sugerencias",
    summary="Horas de baja concurrencia sugeridas",
    dependencies=[Depends(require_admin)],
)
def sugerencias(
    service: Annotated[ClientRecommendationService, Depends(_get_service)],
    limit: int = Query(default=10, ge=1, le=50),
):
    """
    Devuelve los bloques horarios con poca gente (baja afluencia), del más
    vacío al menos vacío. Es el "menú" del que el admin elige la mejor hora
    para recomendar.

    **Solo administradores.**
    """
    result = service.get_suggested_blocks(limit=limit)
    return success_response(
        data=[r.model_dump() for r in result],
        message="Horas de baja concurrencia sugeridas",
    )


# ══════════════════════════════════════════════════════════════════════════════
#  CANDIDATOS — clientes a los que recomendar
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/candidatos",
    summary="Listar clientes candidatos con su hora habitual",
    dependencies=[Depends(require_admin)],
)
def candidatos(
    service: Annotated[ClientRecommendationService, Depends(_get_service)],
    buscar: str | None = Query(default=None, description="Nombre, apellido o DNI"),
    solo_hora_pico: bool = Query(
        default=False, description="Solo clientes que vienen en hora pico"
    ),
    estado: ClientStatus | None = Query(default=None, description="Filtra por estado"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
):
    """
    Lista clientes (con búsqueda por nombre/DNI) mostrando su hora habitual,
    si esa hora es hora pico, y si ya tienen una recomendación activa.
    Incluye la mejor sugerencia global de horario vacío.

    **Solo administradores.**
    """
    filters = CandidateFilterSchema(
        buscar=buscar,
        solo_hora_pico=solo_hora_pico,
        estado=estado,
        page=page,
        per_page=per_page,
    )
    result = service.list_candidates(filters)
    return success_response(
        data=result.model_dump(),
        message="Listado de candidatos",
    )


# ══════════════════════════════════════════════════════════════════════════════
#  ASIGNACIÓN
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "",
    status_code=201,
    summary="Recomendar una hora a un cliente",
)
def recomendar(
    payload: CreateClientRecommendationSchema,
    service: Annotated[ClientRecommendationService, Depends(_get_service)],
    admin: Annotated[User, Depends(require_admin)],
):
    """
    Asigna una recomendación de horario a un cliente. Si el cliente ya tenía
    una recomendación activa, se reemplaza por la nueva.

    **Solo administradores.**
    """
    result = service.create_recommendation(admin.id, payload)
    return success_response(
        data=result.model_dump(),
        message="Recomendación asignada al cliente correctamente",
        status_code=201,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  GESTIÓN
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "",
    summary="Listar recomendaciones asignadas",
    dependencies=[Depends(require_admin)],
)
def listar(
    service: Annotated[ClientRecommendationService, Depends(_get_service)],
    cliente_id: int | None = Query(default=None, ge=1),
    estado: ClientRecommendationStatus | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
):
    """
    Lista las recomendaciones asignadas a clientes, con filtros por cliente y
    estado (activa / descartada).

    **Solo administradores.**
    """
    result = service.list_recommendations(
        page=page, per_page=per_page, cliente_id=cliente_id, estado=estado
    )
    return success_response(
        data=result.model_dump(),
        message="Listado de recomendaciones asignadas",
    )


@router.delete(
    "/{rec_id}",
    summary="Descartar una recomendación",
    dependencies=[Depends(require_admin)],
)
def descartar(
    rec_id: int,
    service: Annotated[ClientRecommendationService, Depends(_get_service)],
):
    """
    Descarta (da de baja) una recomendación asignada. Deja de mostrarse al
    cliente.

    **Solo administradores.**
    """
    service.discard_recommendation(rec_id)
    return success_response(message="Recomendación descartada correctamente")
