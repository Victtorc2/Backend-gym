"""
Router de Planificación de Entrenamiento (cliente).
El cliente confirma qué rutina/zonas entrenará y recibe avisos de demanda.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.auth_dependencies import get_current_client
from app.models.client import Client
from app.repositories.demand_repository import DemandRepository
from app.repositories.machine_repository import MachineRepository
from app.repositories.routine_repository import RoutineRepository
from app.repositories.training_plan_repository import TrainingPlanRepository
from app.schemas.training_plan_schema import (
    TrainingPlanCreateSchema,
    TrainingPlanStatusUpdateSchema,
)
from app.services.routine_service import RoutineService
from app.services.training_plan_service import TrainingPlanService
from app.utils.responses import success_response

router = APIRouter(prefix="/api/mi-plan", tags=["Portal Cliente - Planificación"])


def _get_service(db: Annotated[Session, Depends(get_db)]) -> TrainingPlanService:
    return TrainingPlanService(
        TrainingPlanRepository(db),
        MachineRepository(db),
        RoutineRepository(db),
        DemandRepository(db),
    )


def _get_routine_service(db: Annotated[Session, Depends(get_db)]) -> RoutineService:
    return RoutineService(RoutineRepository(db), MachineRepository(db))


@router.get("/rutinas", summary="Rutinas disponibles para elegir")
def rutinas_disponibles(
    client: Annotated[Client, Depends(get_current_client)],
    service: Annotated[RoutineService, Depends(_get_routine_service)],
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
):
    """Lista las rutinas activas que el cliente puede seleccionar. **Rol: cliente.**"""
    return success_response(service.list(page, per_page, solo_activas=True), "Rutinas disponibles")


@router.post("", status_code=201, summary="Planificar mi entrenamiento del día")
def planificar(
    payload: TrainingPlanCreateSchema,
    client: Annotated[Client, Depends(get_current_client)],
    service: Annotated[TrainingPlanService, Depends(_get_service)],
):
    """
    Registra la planificación del día (zonas y/o rutina). No es una reserva:
    solo declara la intención de uso. Devuelve avisos de demanda y sugerencia
    de orden. **Rol: cliente.**
    """
    result = service.plan_day(client, payload)
    return success_response(result.model_dump(), "Planificación registrada", status_code=201)


@router.get("/hoy", summary="Mi plan de hoy")
def mi_plan_hoy(
    client: Annotated[Client, Depends(get_current_client)],
    service: Annotated[TrainingPlanService, Depends(_get_service)],
):
    """Devuelve el plan del cliente para hoy (o vacío). **Rol: cliente.**"""
    result = service.get_today(client)
    return success_response(
        result.model_dump() if result else None,
        "Plan de hoy" if result else "No tienes un plan para hoy",
    )


@router.get("", summary="Historial de mis planes")
def mis_planes(
    client: Annotated[Client, Depends(get_current_client)],
    service: Annotated[TrainingPlanService, Depends(_get_service)],
):
    """Lista el historial de planes del cliente. **Rol: cliente.**"""
    result = service.list_mine(client)
    return success_response([r.model_dump() for r in result], "Historial de planes")


@router.patch("/estado", summary="Actualizar compromiso (confirmar / en camino / cancelar)")
def actualizar_estado(
    payload: TrainingPlanStatusUpdateSchema,
    client: Annotated[Client, Depends(get_current_client)],
    service: Annotated[TrainingPlanService, Depends(_get_service)],
):
    """Cambia el estado del plan de hoy. **Rol: cliente.**"""
    result = service.update_status(client, payload)
    return success_response(result.model_dump(), "Estado actualizado")


@router.delete("/hoy", summary="Eliminar mi plan de hoy")
def eliminar_plan_hoy(
    client: Annotated[Client, Depends(get_current_client)],
    service: Annotated[TrainingPlanService, Depends(_get_service)],
):
    """Elimina la planificación del cliente para hoy. **Rol: cliente.**"""
    service.cancel_today(client)
    return success_response(message="Plan de hoy eliminado")
