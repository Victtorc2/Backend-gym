"""
Router de Gestión de Demanda (administrador).
Dashboards predictivos, vista del entrenador, Índice de Demanda y precisión.
"""
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.auth_dependencies import require_admin
from app.repositories.demand_repository import DemandRepository
from app.repositories.machine_repository import MachineRepository
from app.repositories.training_plan_repository import TrainingPlanRepository
from app.services.demand_service import DemandService
from app.utils.responses import success_response

router = APIRouter(prefix="/api/demanda", tags=["Gestión de Demanda"])


def _get_service(db: Annotated[Session, Depends(get_db)]) -> DemandService:
    return DemandService(
        DemandRepository(db),
        MachineRepository(db),
        TrainingPlanRepository(db),
    )


@router.get("/hoy", summary="Demanda prevista para hoy", dependencies=[Depends(require_admin)])
def demanda_hoy(
    service: Annotated[DemandService, Depends(_get_service)],
    fecha: date | None = Query(default=None, description="Fecha (por defecto hoy)"),
):
    """
    Panel de demanda prevista: por máquina (con saturación), por hora (con nivel)
    y distribución por zonas. **Solo administradores.**
    """
    result = service.today_dashboard(fecha)
    return success_response(result.model_dump(), "Demanda prevista")


@router.get("/entrenador", summary="Vista del entrenador (quién asiste hoy)", dependencies=[Depends(require_admin)])
def vista_entrenador(
    service: Annotated[DemandService, Depends(_get_service)],
    fecha: date | None = Query(default=None, description="Fecha (por defecto hoy)"),
):
    """
    Lista qué clientes planificaron (con sus zonas y estado) y quiénes no
    confirmaron. **Solo administradores.**
    """
    result = service.trainer_today_view(fecha)
    return success_response(result.model_dump(), "Vista del entrenador")


@router.get("/indice", summary="Índice de Demanda e inversión", dependencies=[Depends(require_admin)])
def indice_demanda(
    service: Annotated[DemandService, Depends(_get_service)],
):
    """
    Índice de Demanda por máquina (planificaciones + uso real proxy + espera) /
    unidades, ordenado por prioridad de inversión. **Solo administradores.**
    """
    result = service.demand_index_report()
    return success_response(result.model_dump(), "Índice de Demanda")


@router.get("/precision", summary="Precisión de la predicción", dependencies=[Depends(require_admin)])
def precision(
    service: Annotated[DemandService, Depends(_get_service)],
    desde: date = Query(..., description="Fecha inicial (YYYY-MM-DD)"),
    hasta: date = Query(..., description="Fecha final (YYYY-MM-DD)"),
):
    """
    Compara planificaciones con asistencia real para medir la precisión de las
    predicciones en un rango. **Solo administradores.**
    """
    result = service.precision_stats(desde, hasta)
    return success_response(result.model_dump(), "Precisión de predicción")
