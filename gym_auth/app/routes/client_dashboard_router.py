"""
Router del Portal de Cliente (Fase 10 — Módulos Cliente).
Endpoints exclusivos para el rol CLIENTE.

Seguridad:
  - Todos los endpoints requieren JWT con rol=cliente (require_client).
  - El cliente_id se extrae del token vía `get_current_client`.
  - Imposible acceder a datos de otro cliente.
  - Acceso denegado a administradores y usuarios no autenticados.

Toda la lógica está delegada al ClientDashboardService.
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.auth_dependencies import get_current_client
from app.models.client import Client
from app.repositories.client_dashboard_repository import ClientDashboardRepository
from app.services.client_dashboard_service import ClientDashboardService
from app.utils.responses import success_response

router = APIRouter(prefix="/api/cliente", tags=["Portal Cliente"])


# ── Factory de servicio ────────────────────────────────────────────────────────

def _get_service(db: Annotated[Session, Depends(get_db)]) -> ClientDashboardService:
    """Provee ClientDashboardService con su repositorio inyectado."""
    return ClientDashboardService(ClientDashboardRepository(db))


# ══════════════════════════════════════════════════════════════════════════════
#  MÓDULO 1 — MI MEMBRESÍA
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/mi-membresia", summary="Consultar mi membresía activa")
def mi_membresia(
    client: Annotated[Client, Depends(get_current_client)],
    service: Annotated[ClientDashboardService, Depends(_get_service)],
):
    """
    Devuelve la membresía activa del cliente: tipo, vigencia, estado y días restantes.
    Si no hay membresía activa, retorna una respuesta controlada.

    **Requiere rol: cliente.**
    """
    result = service.get_mi_membresia(client)
    return success_response(
        data=result.model_dump(),
        message="Información obtenida correctamente",
    )


# ══════════════════════════════════════════════════════════════════════════════
#  MÓDULO 2 — MIS PAGOS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/mis-pagos", summary="Consultar mis pagos")
def mis_pagos(
    client: Annotated[Client, Depends(get_current_client)],
    service: Annotated[ClientDashboardService, Depends(_get_service)],
):
    """
    Devuelve el resumen de pagos del cliente: total pagado, deuda pendiente y listado.

    **Requiere rol: cliente.**
    """
    result = service.get_mis_pagos(client)
    return success_response(data=result.model_dump(), message="Información obtenida correctamente")


@router.get("/mis-pagos/historial", summary="Historial completo de pagos")
def historial_pagos(
    client: Annotated[Client, Depends(get_current_client)],
    service: Annotated[ClientDashboardService, Depends(_get_service)],
):
    """
    Devuelve el historial cronológico completo de pagos del cliente.

    **Requiere rol: cliente.**
    """
    result = service.get_historial_pagos(client)
    return success_response(data=result.model_dump(), message="Historial obtenido correctamente")


@router.get("/mi-deuda", summary="Consultar mi deuda")
def mi_deuda(
    client: Annotated[Client, Depends(get_current_client)],
    service: Annotated[ClientDashboardService, Depends(_get_service)],
):
    """
    Devuelve el estado de deuda consolidado: monto total, pagos pendientes y vencidos.

    **Requiere rol: cliente.**
    """
    result = service.get_mi_deuda(client)
    return success_response(data=result.model_dump(), message="Información obtenida correctamente")


# ══════════════════════════════════════════════════════════════════════════════
#  MÓDULO 3 — MI ASISTENCIA
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/mi-asistencia", summary="Consultar mi historial de asistencia")
def mi_asistencia(
    client: Annotated[Client, Depends(get_current_client)],
    service: Annotated[ClientDashboardService, Depends(_get_service)],
):
    """
    Devuelve el historial completo de asistencia con totales aprobados/denegados.

    **Requiere rol: cliente.**
    """
    result = service.get_mi_asistencia(client)
    return success_response(data=result.model_dump(), message="Información obtenida correctamente")


@router.get("/mi-asistencia/frecuencia", summary="Consultar mi frecuencia de asistencia")
def mi_frecuencia(
    client: Annotated[Client, Depends(get_current_client)],
    service: Annotated[ClientDashboardService, Depends(_get_service)],
):
    """
    Devuelve estadísticas de frecuencia: total ingresos, asistencias del mes,
    promedio semanal de visitas, primer y último ingreso.

    **Requiere rol: cliente.**
    """
    result = service.get_mi_frecuencia(client)
    return success_response(data=result.model_dump(), message="Información obtenida correctamente")


# ══════════════════════════════════════════════════════════════════════════════
#  MÓDULO 4 — MI PERFIL
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/mi-perfil", summary="Consultar mi perfil")
def mi_perfil(
    client: Annotated[Client, Depends(get_current_client)],
    service: Annotated[ClientDashboardService, Depends(_get_service)],
):
    """
    Devuelve los datos personales del cliente: nombres, DNI, correo, edad, etc.

    **Requiere rol: cliente.**
    """
    result = service.get_mi_perfil(client)
    return success_response(data=result.model_dump(), message="Información obtenida correctamente")


# ══════════════════════════════════════════════════════════════════════════════
#  MÓDULO 5 — MI HORARIO RECOMENDADO
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/mi-horario-recomendado", summary="Consultar mi horario recomendado")
def mi_horario_recomendado(
    client: Annotated[Client, Depends(get_current_client)],
    service: Annotated[ClientDashboardService, Depends(_get_service)],
):
    """
    Devuelve los horarios recomendados para el día actual:

    - Horario recomendado (menor afluencia).
    - Horario a evitar (mayor afluencia).
    - Listado de horarios libres y horas pico de hoy.

    Integra con el módulo de Recomendación Inteligente de Horarios.

    **Requiere rol: cliente.**
    """
    result = service.get_mi_horario_recomendado(client)
    return success_response(data=result.model_dump(), message="Información obtenida correctamente")


# ══════════════════════════════════════════════════════════════════════════════
#  MÓDULO 6 — LOGOUT
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/logout", summary="Cerrar sesión")
def logout(
    client: Annotated[Client, Depends(get_current_client)],
    service: Annotated[ClientDashboardService, Depends(_get_service)],
):
    """
    Cierra la sesión del cliente.

    Con JWT stateless, el cliente debe descartar el token localmente.
    La estructura queda preparada para una blacklist de tokens futura.

    **Requiere rol: cliente.**
    """
    result = service.logout(client)
    return success_response(data=result.model_dump(), message="Sesión cerrada correctamente")
