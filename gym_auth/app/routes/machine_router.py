"""
Router del catálogo de Máquinas (administrador).
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.constants import MuscleZone
from app.database.connection import get_db
from app.dependencies.auth_dependencies import require_admin
from app.repositories.machine_repository import MachineRepository
from app.schemas.machine_schema import MachineCreateSchema, MachineUpdateSchema
from app.services.machine_service import MachineService
from app.utils.responses import success_response

router = APIRouter(prefix="/api/maquinas", tags=["Máquinas"])


def _get_service(db: Annotated[Session, Depends(get_db)]) -> MachineService:
    return MachineService(MachineRepository(db))


@router.post("", status_code=201, summary="Registrar máquina", dependencies=[Depends(require_admin)])
def crear(
    payload: MachineCreateSchema,
    service: Annotated[MachineService, Depends(_get_service)],
):
    """Registra una máquina en el catálogo. **Solo administradores.**"""
    result = service.create(payload)
    return success_response(result.model_dump(), "Máquina registrada", status_code=201)


@router.get("", summary="Listar máquinas", dependencies=[Depends(require_admin)])
def listar(
    service: Annotated[MachineService, Depends(_get_service)],
    buscar: str | None = Query(default=None),
    zona: MuscleZone | None = Query(default=None),
    solo_activas: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
):
    """Lista el catálogo de máquinas con filtros. **Solo administradores.**"""
    result = service.list(page, per_page, buscar, zona, solo_activas)
    return success_response(result, "Listado de máquinas")


@router.get("/{machine_id}", summary="Detalle de máquina", dependencies=[Depends(require_admin)])
def detalle(
    machine_id: int,
    service: Annotated[MachineService, Depends(_get_service)],
):
    """Devuelve una máquina por su ID. **Solo administradores.**"""
    return success_response(service.get(machine_id).model_dump(), "Máquina encontrada")


@router.put("/{machine_id}", summary="Actualizar máquina", dependencies=[Depends(require_admin)])
def actualizar(
    machine_id: int,
    payload: MachineUpdateSchema,
    service: Annotated[MachineService, Depends(_get_service)],
):
    """Actualiza una máquina. **Solo administradores.**"""
    return success_response(service.update(machine_id, payload).model_dump(), "Máquina actualizada")


@router.delete("/{machine_id}", summary="Eliminar máquina", dependencies=[Depends(require_admin)])
def eliminar(
    machine_id: int,
    service: Annotated[MachineService, Depends(_get_service)],
):
    """Elimina una máquina del catálogo. **Solo administradores.**"""
    service.delete(machine_id)
    return success_response(message="Máquina eliminada")
