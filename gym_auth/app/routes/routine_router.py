"""
Router de Rutinas (administrador / entrenador).
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.auth_dependencies import require_admin
from app.models.user import User
from app.repositories.machine_repository import MachineRepository
from app.repositories.routine_repository import RoutineRepository
from app.schemas.routine_schema import RoutineCreateSchema, RoutineUpdateSchema
from app.services.routine_service import RoutineService
from app.utils.responses import success_response

router = APIRouter(prefix="/api/rutinas", tags=["Rutinas"])


def _get_service(db: Annotated[Session, Depends(get_db)]) -> RoutineService:
    return RoutineService(RoutineRepository(db), MachineRepository(db))


@router.post("", status_code=201, summary="Crear rutina")
def crear(
    payload: RoutineCreateSchema,
    service: Annotated[RoutineService, Depends(_get_service)],
    admin: Annotated[User, Depends(require_admin)],
):
    """Crea una rutina (plantilla) con sus máquinas. **Solo administradores.**"""
    result = service.create(payload, creada_por=admin.id)
    return success_response(result.model_dump(), "Rutina creada", status_code=201)


@router.get("", summary="Listar rutinas", dependencies=[Depends(require_admin)])
def listar(
    service: Annotated[RoutineService, Depends(_get_service)],
    solo_activas: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
):
    """Lista las rutinas. **Solo administradores.**"""
    return success_response(service.list(page, per_page, solo_activas), "Listado de rutinas")


@router.get("/{routine_id}", summary="Detalle de rutina", dependencies=[Depends(require_admin)])
def detalle(
    routine_id: int,
    service: Annotated[RoutineService, Depends(_get_service)],
):
    """Devuelve una rutina con sus máquinas. **Solo administradores.**"""
    return success_response(service.get(routine_id).model_dump(), "Rutina encontrada")


@router.put("/{routine_id}", summary="Actualizar rutina", dependencies=[Depends(require_admin)])
def actualizar(
    routine_id: int,
    payload: RoutineUpdateSchema,
    service: Annotated[RoutineService, Depends(_get_service)],
):
    """Actualiza una rutina (incluye reemplazar sus máquinas). **Solo administradores.**"""
    return success_response(service.update(routine_id, payload).model_dump(), "Rutina actualizada")


@router.delete("/{routine_id}", summary="Eliminar rutina", dependencies=[Depends(require_admin)])
def eliminar(
    routine_id: int,
    service: Annotated[RoutineService, Depends(_get_service)],
):
    """Elimina una rutina. **Solo administradores.**"""
    service.delete(routine_id)
    return success_response(message="Rutina eliminada")
