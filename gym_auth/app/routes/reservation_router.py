"""
Router de Reservas de Máquina (cliente).
El cliente ve la disponibilidad de las máquinas y reserva una franja horaria.
"""
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.constants import MuscleZone
from app.database.connection import get_db
from app.dependencies.auth_dependencies import get_current_client
from app.models.client import Client
from app.repositories.machine_repository import MachineRepository
from app.repositories.reservation_repository import ReservationRepository
from app.schemas.reservation_schema import ReservationCreateSchema
from app.services.reservation_service import ReservationService
from app.utils.responses import success_response

router = APIRouter(prefix="/api/reservas", tags=["Portal Cliente - Reservas"])


def _get_service(db: Annotated[Session, Depends(get_db)]) -> ReservationService:
    return ReservationService(ReservationRepository(db), MachineRepository(db))


def _parse_zonas(zonas: str | None) -> list[MuscleZone] | None:
    if not zonas:
        return None
    out: list[MuscleZone] = []
    for z in zonas.split(","):
        z = z.strip()
        try:
            out.append(MuscleZone(z))
        except ValueError:
            continue
    return out or None


@router.post("", status_code=201, summary="Reservar una máquina")
def reservar(
    payload: ReservationCreateSchema,
    client: Annotated[Client, Depends(get_current_client)],
    service: Annotated[ReservationService, Depends(_get_service)],
):
    """Reserva una máquina en una franja horaria. **Rol: cliente.**"""
    result = service.create_reservation(client, payload)
    return success_response(result.model_dump(), "Máquina reservada", status_code=201)


@router.get("/maquinas", summary="Disponibilidad de máquinas por fecha")
def disponibilidad(
    client: Annotated[Client, Depends(get_current_client)],
    service: Annotated[ReservationService, Depends(_get_service)],
    fecha: date | None = Query(default=None, description="Fecha (por defecto hoy)"),
    zonas: str | None = Query(default=None, description="Zonas separadas por coma (ej. pecho,espalda)"),
):
    """
    Lista las máquinas activas con sus franjas ya reservadas para la fecha, para
    que el cliente vea la disponibilidad y elija una hora libre. **Rol: cliente.**
    """
    objetivo = fecha or date.today()
    result = service.machines_availability(client, objetivo, _parse_zonas(zonas))
    return success_response([r.model_dump() for r in result], "Disponibilidad de máquinas")


@router.get("/mias", summary="Mis reservas")
def mis_reservas(
    client: Annotated[Client, Depends(get_current_client)],
    service: Annotated[ReservationService, Depends(_get_service)],
    fecha: date | None = Query(default=None),
):
    """Lista las reservas activas del cliente. **Rol: cliente.**"""
    result = service.list_my_reservations(client, fecha)
    return success_response([r.model_dump() for r in result], "Mis reservas")


@router.delete("/{rid}", summary="Cancelar una reserva")
def cancelar(
    rid: int,
    client: Annotated[Client, Depends(get_current_client)],
    service: Annotated[ReservationService, Depends(_get_service)],
):
    """Cancela una reserva propia. **Rol: cliente.**"""
    service.cancel_reservation(client, rid)
    return success_response(message="Reserva cancelada")
