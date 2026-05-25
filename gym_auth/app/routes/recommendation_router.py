"""
Router del módulo de Recomendación de Horarios (Fase 10).
Endpoints de análisis de afluencia y recomendaciones.
Toda la lógica delegada al RecommendationService.
Acceso restringido a administradores mediante require_admin().

Orden: rutas fijas antes de rutas con parámetros dinámicos.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.constants import AffluenceLevel, WeekDay
from app.core.exceptions import InvalidWeekDayException
from app.database.connection import get_db
from app.dependencies.auth_dependencies import require_admin
from app.repositories.recommendation_repository import RecommendationRepository
from app.schemas.recommendation_schema import RecommendationFilterSchema
from app.services.recommendation_service import RecommendationService
from app.utils.responses import success_response

router = APIRouter(prefix="/api/recomendaciones", tags=["Recomendación de Horarios"])


# ── Factory de servicio ────────────────────────────────────────────────────────

def _get_recommendation_service(
    db: Annotated[Session, Depends(get_db)],
) -> RecommendationService:
    """Provee RecommendationService con su repositorio inyectado."""
    return RecommendationService(RecommendationRepository(db))


# ══════════════════════════════════════════════════════════════════════════════
#  GENERACIÓN
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/generar",
    status_code=201,
    summary="Generar recomendaciones automáticamente",
    dependencies=[Depends(require_admin)],
)
def generar_recomendaciones(
    service: Annotated[RecommendationService, Depends(_get_recommendation_service)],
):
    """
    Analiza el historial de asistencia y regenera todas las recomendaciones.

    Proceso:
    1. Agrupa asistencias aprobadas por día y hora.
    2. Calcula el promedio de ingresos por bloque.
    3. Clasifica la afluencia (BAJA / MEDIA / ALTA).
    4. Marca horarios recomendados (baja) y a evitar (alta).
    5. Reemplaza los datos anteriores con el análisis actualizado.

    **Solo administradores.**
    """
    result = service.generate_recommendations()
    return success_response(
        data=result.model_dump(),
        message="Recomendaciones generadas correctamente",
        status_code=201,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  CONSULTAS — rutas fijas primero
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/estadisticas",
    summary="Estadísticas generales de afluencia",
    dependencies=[Depends(require_admin)],
)
def estadisticas_generales(
    service: Annotated[RecommendationService, Depends(_get_recommendation_service)],
):
    """
    Devuelve estadísticas globales de afluencia:

    - Total semanal y promedios por día/hora.
    - Horario más y menos concurrido.
    - Porcentaje de ocupación.
    - Desglose por día con hora pico y hora libre.

    **Solo administradores.**
    """
    result = service.get_statistics()
    return success_response(
        data=result.model_dump(),
        message="Estadísticas generadas correctamente",
    )


@router.get(
    "/pico",
    summary="Consultar horas pico (a evitar)",
    dependencies=[Depends(require_admin)],
)
def horas_pico(
    service: Annotated[RecommendationService, Depends(_get_recommendation_service)],
):
    """
    Lista los bloques horarios con afluencia ALTA (recomendado evitarlos),
    ordenados de mayor a menor concurrencia.

    **Solo administradores.**
    """
    result = service.get_peak_hours()
    return success_response(
        data=[r.model_dump() for r in result],
        message="Horas pico identificadas",
    )


@router.get(
    "/libres",
    summary="Consultar horarios libres (recomendados)",
    dependencies=[Depends(require_admin)],
)
def horarios_libres(
    service: Annotated[RecommendationService, Depends(_get_recommendation_service)],
):
    """
    Lista los bloques horarios con afluencia BAJA (recomendados),
    ordenados de menor a mayor concurrencia.

    **Solo administradores.**
    """
    result = service.get_free_hours()
    return success_response(
        data=[r.model_dump() for r in result],
        message="Horarios libres identificados",
    )


@router.get(
    "/dia/{dia}",
    summary="Horarios recomendados por día",
    dependencies=[Depends(require_admin)],
)
def recomendaciones_por_dia(
    dia: str,
    service: Annotated[RecommendationService, Depends(_get_recommendation_service)],
):
    """
    Devuelve todos los bloques de un día con su horario recomendado
    (menor afluencia) y su hora pico (mayor afluencia).

    El día debe ser uno de: lunes, martes, miercoles, jueves, viernes, sabado.

    **Solo administradores.**
    """
    try:
        weekday = WeekDay(dia.lower())
    except ValueError:
        raise InvalidWeekDayException()

    result = service.get_day_schedule(weekday)
    return success_response(
        data=result.model_dump(),
        message=f"Recomendaciones para {weekday.value}",
    )


@router.get(
    "",
    summary="Listar recomendaciones",
    dependencies=[Depends(require_admin)],
)
def listar_recomendaciones(
    service: Annotated[RecommendationService, Depends(_get_recommendation_service)],
    dia_semana: WeekDay | None = Query(default=None, description="Filtra por día"),
    nivel_afluencia: AffluenceLevel | None = Query(default=None, description="Filtra por nivel"),
    es_recomendado: bool | None = Query(default=None, description="Solo recomendados"),
    evitar: bool | None = Query(default=None, description="Solo a evitar"),
    orden: str = Query(default="afluencia_asc", description="afluencia_asc | afluencia_desc | dia"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
):
    """
    Lista todas las recomendaciones con filtros, ordenamiento y paginación.

    **Solo administradores.**
    """
    filters = RecommendationFilterSchema(
        dia_semana=dia_semana,
        nivel_afluencia=nivel_afluencia,
        es_recomendado=es_recomendado,
        evitar=evitar,
        orden=orden,
        page=page,
        per_page=per_page,
    )
    result = service.list_recommendations(filters)
    return success_response(
        data=result.model_dump(),
        message="Listado de recomendaciones",
    )
