"""
Router del módulo de Pagos y Deudas.
Define los endpoints REST del módulo.
Toda la lógica está delegada al PaymentService.
Acceso restringido a administradores mediante require_admin().

Nota sobre el orden de rutas:
FastAPI resuelve rutas en orden de declaración.
Las rutas con segmentos fijos (/deudas, /pendientes) se declaran
ANTES de las rutas con parámetros (/{id}) para evitar conflictos.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.constants import PaymentMethod, PaymentStatus
from app.database.connection import get_db
from app.dependencies.auth_dependencies import require_admin
from app.repositories.client_repository import ClientRepository
from app.repositories.membership_repository import MembershipRepository
from app.repositories.payment_repository import PaymentRepository
from app.schemas.payment_schema import PaymentCreateSchema, PaymentFilterSchema
from app.services.payment_service import PaymentService
from app.utils.responses import success_response
from datetime import date

router = APIRouter(prefix="/api/pagos", tags=["Pagos"])


# ── Factory de servicio ────────────────────────────────────────────────────────

def _get_payment_service(db: Annotated[Session, Depends(get_db)]) -> PaymentService:
    """Provee PaymentService con todos sus repositorios inyectados."""
    return PaymentService(
        payment_repo=PaymentRepository(db),
        client_repo=ClientRepository(db),
        membership_repo=MembershipRepository(db),
    )


# ══════════════════════════════════════════════════════════════════════════════
#  ENDPOINTS — orden: rutas fijas primero, luego rutas con parámetros
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "",
    status_code=201,
    summary="Registrar pago",
    dependencies=[Depends(require_admin)],
)
def register_payment(
    data: PaymentCreateSchema,
    service: Annotated[PaymentService, Depends(_get_payment_service)],
):
    """
    Registra un pago completo o parcial hacia una membresía.

    - Calcula **automáticamente** el saldo pendiente y el estado.
    - Pago completo → estado `pagado`, saldo = 0.
    - Pago parcial  → estado `pendiente`, saldo = total − pagado.
    - No se permiten montos pagados mayores al total.

    **Solo administradores.**
    """
    result = service.register_payment(data)
    return success_response(
        data=result.model_dump(),
        message="Pago registrado correctamente",
        status_code=201,
    )


@router.get(
    "/deudas",
    summary="Clientes con deuda",
    dependencies=[Depends(require_admin)],
)
def get_clients_with_debt(
    service: Annotated[PaymentService, Depends(_get_payment_service)],
):
    """
    Devuelve el resumen consolidado de deuda por cliente.

    Agrupa todos los saldos pendientes de cada cliente y
    retorna solo los que tienen deuda activa (saldo > 0).

    **Solo administradores.**
    """
    result = service.get_clients_with_debt()
    return success_response(
        data=[r.model_dump() for r in result],
        message="Clientes con deuda pendiente",
    )


@router.get(
    "/pendientes",
    summary="Pagos en estado pendiente",
    dependencies=[Depends(require_admin)],
)
def list_pending_payments(
    service: Annotated[PaymentService, Depends(_get_payment_service)],
):
    """
    Lista todos los pagos en estado `pendiente`, ordenados por fecha ascendente.

    **Solo administradores.**
    """
    result = service.list_pending_payments()
    return success_response(
        data=[r.model_dump() for r in result],
        message="Pagos pendientes",
    )


@router.get(
    "/cliente/{cliente_id}",
    summary="Historial de pagos de un cliente",
    dependencies=[Depends(require_admin)],
)
def get_client_payment_history(
    cliente_id: int,
    service: Annotated[PaymentService, Depends(_get_payment_service)],
):
    """
    Lista el historial completo de pagos de un cliente específico,
    del más reciente al más antiguo.

    **Solo administradores.**
    """
    result = service.get_client_history(cliente_id)
    return success_response(
        data=[r.model_dump() for r in result],
        message=f"Historial de pagos del cliente {cliente_id}",
    )


@router.get(
    "",
    summary="Listar pagos",
    dependencies=[Depends(require_admin)],
)
def list_payments(
    service: Annotated[PaymentService, Depends(_get_payment_service)],
    cliente_id: int | None = Query(default=None, description="Filtra por cliente"),
    estado: PaymentStatus | None = Query(default=None, description="Filtra por estado"),
    metodo_pago: PaymentMethod | None = Query(default=None, description="Filtra por método de pago"),
    fecha_desde: date | None = Query(default=None, description="Fecha de inicio del rango"),
    fecha_hasta: date | None = Query(default=None, description="Fecha de fin del rango"),
    page: int = Query(default=1, ge=1, description="Número de página"),
    per_page: int = Query(default=20, ge=1, le=100, description="Registros por página"),
):
    """
    Lista todos los pagos con filtros y paginación.

    Filtra por: cliente, estado, método de pago y rango de fechas.

    **Solo administradores.**
    """
    filters = PaymentFilterSchema(
        cliente_id=cliente_id,
        estado=estado,
        metodo_pago=metodo_pago,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        page=page,
        per_page=per_page,
    )
    result = service.list_payments(filters)
    return success_response(data=result.model_dump(), message="Listado de pagos")


@router.get(
    "/{payment_id}",
    summary="Consultar pago por ID",
    dependencies=[Depends(require_admin)],
)
def get_payment(
    payment_id: int,
    service: Annotated[PaymentService, Depends(_get_payment_service)],
):
    """
    Devuelve el detalle completo de un pago por su ID.

    **Solo administradores.**
    """
    result = service.get_payment(payment_id)
    return success_response(data=result.model_dump(), message="Pago encontrado")
