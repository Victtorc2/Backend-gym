"""
Router del Módulo de Reportes (Fase 8).
Endpoints de solo lectura para información administrativa.
Toda la lógica delegada al ReportService.
Acceso restringido a administradores mediante require_admin().

Orden: rutas fijas antes de rutas con parámetros.
"""
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.auth_dependencies import require_admin
from app.repositories.report_repository import ReportRepository
from app.services.report_service import ReportService
from app.utils.responses import success_response

router = APIRouter(prefix="/api/reportes", tags=["Reportes"])


# ── Factory de servicio ────────────────────────────────────────────────────────

def _get_report_service(db: Annotated[Session, Depends(get_db)]) -> ReportService:
    """Provee ReportService con su repositorio inyectado."""
    return ReportService(ReportRepository(db))


# ══════════════════════════════════════════════════════════════════════════════
#  CLIENTES
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/clientes/activos",
    summary="Reporte de clientes activos",
    dependencies=[Depends(require_admin)],
)
def reporte_clientes_activos(
    service: Annotated[ReportService, Depends(_get_report_service)],
):
    """
    Devuelve el listado completo de clientes activos con estadísticas:

    - Total activos, inactivos y general.
    - Porcentaje de clientes activos.
    - Listado de clientes activos con datos completos.

    **Solo administradores.**
    """
    result = service.get_clientes_activos()
    return success_response(
        data=result.model_dump(),
        message="Reporte de clientes activos generado correctamente",
    )


@router.get(
    "/clientes/deuda",
    summary="Reporte de clientes con deuda",
    dependencies=[Depends(require_admin)],
)
def reporte_clientes_con_deuda(
    service: Annotated[ReportService, Depends(_get_report_service)],
):
    """
    Devuelve el listado de clientes con saldo pendiente o vencido:

    - Total de clientes con deuda activa.
    - Monto total acumulado de deuda del gimnasio.
    - Desglose por cliente con pagos pendientes y vencidos.

    **Solo administradores.**
    """
    result = service.get_reporte_deuda()
    return success_response(
        data=result.model_dump(),
        message="Reporte de deuda generado correctamente",
    )


# ══════════════════════════════════════════════════════════════════════════════
#  MEMBRESÍAS
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/membresias/vigentes",
    summary="Reporte de membresías vigentes",
    dependencies=[Depends(require_admin)],
)
def reporte_membresias_vigentes(
    service: Annotated[ReportService, Depends(_get_report_service)],
):
    """
    Devuelve el reporte de membresías activas y vigentes:

    - Conteo por estado (activa, vencida, pendiente).
    - Ingresos proyectados de membresías vigentes.
    - Distribución por tipo (mensual, anual, diario).
    - Listado con días restantes calculados en tiempo real.

    **Solo administradores.**
    """
    result = service.get_reporte_membresias()
    return success_response(
        data=result.model_dump(),
        message="Reporte de membresías vigentes generado correctamente",
    )


# ══════════════════════════════════════════════════════════════════════════════
#  PAGOS
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/pagos/resumen",
    summary="Resumen financiero de pagos",
    dependencies=[Depends(require_admin)],
)
def reporte_resumen_pagos(
    service: Annotated[ReportService, Depends(_get_report_service)],
    fecha_desde: date | None = Query(default=None, description="Fecha de inicio del rango"),
    fecha_hasta: date | None = Query(default=None, description="Fecha de fin del rango"),
):
    """
    Devuelve solo los KPIs financieros sin el listado detallado:

    - Total de pagos registrados.
    - Total de ingresos generados (monto_pagado acumulado).
    - Deuda total pendiente.
    - Conteo por estado (completados, pendientes, vencidos).
    - Ingresos por método de pago.

    **Solo administradores.**
    """
    result = service.get_resumen_pagos(fecha_desde, fecha_hasta)
    return success_response(
        data=result.model_dump(),
        message="Resumen financiero generado correctamente",
    )


@router.get(
    "/pagos",
    summary="Reporte completo de pagos",
    dependencies=[Depends(require_admin)],
)
def reporte_pagos(
    service: Annotated[ReportService, Depends(_get_report_service)],
    fecha_desde: date | None = Query(default=None, description="Fecha de inicio del rango"),
    fecha_hasta: date | None = Query(default=None, description="Fecha de fin del rango"),
    cliente_id: int | None = Query(default=None, description="Filtrar por cliente específico"),
):
    """
    Devuelve resumen financiero + listado detallado de pagos.

    Soporta filtros por rango de fechas y cliente específico.

    **Solo administradores.**
    """
    result = service.get_reporte_pagos(fecha_desde, fecha_hasta, cliente_id)
    return success_response(
        data=result.model_dump(),
        message="Reporte de pagos generado correctamente",
    )


# ══════════════════════════════════════════════════════════════════════════════
#  ASISTENCIA
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/asistencia/frecuencia",
    summary="Reporte de frecuencia de asistencia por cliente",
    dependencies=[Depends(require_admin)],
)
def reporte_frecuencia_asistencia(
    service: Annotated[ReportService, Depends(_get_report_service)],
    fecha_desde: date | None = Query(default=None, description="Rango desde"),
    fecha_hasta: date | None = Query(default=None, description="Rango hasta"),
):
    """
    Devuelve estadísticas de frecuencia de asistencia por cliente:

    - Total ingresos aprobados y denegados.
    - Asistencias en el mes actual.
    - Primer y último ingreso registrado.
    - Promedio mensual calculado automáticamente.

    **Solo administradores.**
    """
    result = service.get_reporte_frecuencia(fecha_desde, fecha_hasta)
    return success_response(
        data=result.model_dump(),
        message="Reporte de frecuencia de asistencia generado correctamente",
    )


@router.get(
    "/asistencia",
    summary="Reporte de asistencias registradas",
    dependencies=[Depends(require_admin)],
)
def reporte_asistencia(
    service: Annotated[ReportService, Depends(_get_report_service)],
    fecha_desde: date | None = Query(default=None, description="Rango desde"),
    fecha_hasta: date | None = Query(default=None, description="Rango hasta"),
    cliente_id: int | None = Query(default=None, description="Filtrar por cliente"),
):
    """
    Devuelve el reporte de asistencias con métricas de aprobación:

    - Total registros, aprobados y denegados.
    - Porcentaje de aprobación.
    - Listado cronológico con hora legible (HH:MM).

    **Solo administradores.**
    """
    result = service.get_reporte_asistencia(fecha_desde, fecha_hasta, cliente_id)
    return success_response(
        data=result.model_dump(),
        message="Reporte de asistencia generado correctamente",
    )
