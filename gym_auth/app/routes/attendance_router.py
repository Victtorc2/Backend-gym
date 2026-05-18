"""
Router del módulo de Asistencias.
Endpoints REST para control de acceso e historial.
Todas las rutas protegidas con require_admin().

Orden de rutas: segmentos fijos antes de parámetros dinámicos.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.constants import AttendanceStatus
from app.database.connection import get_db
from app.dependencies.auth_dependencies import require_admin
from app.repositories.attendance_repository import AttendanceRepository
from app.repositories.card_repository import CardRepository
from app.repositories.client_repository import ClientRepository
from app.repositories.membership_repository import MembershipRepository
from app.repositories.payment_repository import PaymentRepository
from app.schemas.attendance_schema import AttendanceCheckInSchema, AttendanceFilterSchema
from app.services.attendance_service import AttendanceService
from app.utils.responses import success_response
from datetime import date

router = APIRouter(prefix="/api/asistencias", tags=["Asistencias"])


# ── Factory de servicio ────────────────────────────────────────────────────────

def _get_attendance_service(db: Annotated[Session, Depends(get_db)]) -> AttendanceService:
    """Provee AttendanceService con todos sus repositorios inyectados."""
    return AttendanceService(
        attendance_repo=AttendanceRepository(db),
        card_repo=CardRepository(db),
        client_repo=ClientRepository(db),
        membership_repo=MembershipRepository(db),
        payment_repo=PaymentRepository(db),
    )


# ══════════════════════════════════════════════════════════════════════════════
#  ENDPOINTS — rutas fijas primero
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/validar-ingreso",
    status_code=201,
    summary="Validar acceso y registrar ingreso",
    dependencies=[Depends(require_admin)],
)
def validate_check_in(
    data: AttendanceCheckInSchema,
    service: Annotated[AttendanceService, Depends(_get_attendance_service)],
):
    """
    Valida el acceso de un cliente mediante su código de tarjeta.

    Ejecuta la cadena completa de validaciones:
    tarjeta → cliente → membresía → pagos.

    **Siempre registra el intento** (aprobado o denegado) para trazabilidad.

    **Solo administradores.**
    """
    result = service.validate_check_in(data)
    message = "Ingreso autorizado" if result.acceso_permitido else f"Ingreso denegado: {result.motivo}"
    return success_response(
        data=result.model_dump(),
        message=message,
        status_code=201,
    )


@router.get(
    "/cliente/{cliente_id}",
    summary="Historial de asistencias de un cliente",
    dependencies=[Depends(require_admin)],
)
def get_client_history(
    cliente_id: int,
    service: Annotated[AttendanceService, Depends(_get_attendance_service)],
):
    """
    Lista el historial completo de asistencias (aprobadas y denegadas)
    de un cliente, del más reciente al más antiguo.

    **Solo administradores.**
    """
    result = service.get_client_history(cliente_id)
    return success_response(
        data=[r.model_dump() for r in result],
        message=f"Historial de asistencias del cliente {cliente_id}",
    )


@router.get(
    "/frecuencia/{cliente_id}",
    summary="Estadísticas de frecuencia de un cliente",
    dependencies=[Depends(require_admin)],
)
def get_frequency(
    cliente_id: int,
    service: Annotated[AttendanceService, Depends(_get_attendance_service)],
):
    """
    Devuelve estadísticas de frecuencia de asistencia:
    - Total ingresos aprobados / denegados históricos.
    - Fecha del primer y último ingreso.
    - Asistencias en el mes actual.

    **Solo administradores.**
    """
    result = service.get_frequency(cliente_id)
    return success_response(data=result.model_dump(), message="Frecuencia de asistencia")


@router.get(
    "",
    summary="Listar asistencias",
    dependencies=[Depends(require_admin)],
)
def list_attendances(
    service: Annotated[AttendanceService, Depends(_get_attendance_service)],
    cliente_id: int | None = Query(default=None, description="Filtra por cliente"),
    estado: AttendanceStatus | None = Query(default=None, description="Filtra por resultado"),
    fecha_desde: date | None = Query(default=None, description="Rango desde"),
    fecha_hasta: date | None = Query(default=None, description="Rango hasta"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
):
    """
    Lista asistencias con filtros opcionales y paginación.

    **Solo administradores.**
    """
    filters = AttendanceFilterSchema(
        cliente_id=cliente_id,
        estado=estado,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        page=page,
        per_page=per_page,
    )
    result = service.list_attendances(filters)
    return success_response(data=result.model_dump(), message="Listado de asistencias")


@router.get(
    "/{attendance_id}",
    summary="Consultar asistencia por ID",
    dependencies=[Depends(require_admin)],
)
def get_attendance(
    attendance_id: int,
    service: Annotated[AttendanceService, Depends(_get_attendance_service)],
):
    """
    Devuelve el detalle de un registro de asistencia por ID.

    **Solo administradores.**
    """
    result = service.get_attendance(attendance_id)
    return success_response(data=result.model_dump(), message="Registro de asistencia encontrado")
