"""
Rutas del módulo Clientes Diarios (Fase 6).
Prefijos:
  /api/clientes-diarios  → gestión de clientes diarios y sus pagos
  /api/ingresos-diarios  → registro y consulta de ingresos diarios

Seguridad: todos los endpoints requieren JWT válido con rol ADMINISTRADOR.
Los routes solo coordinan: no contienen lógica de negocio.
"""
from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.constants import DailyClientStatus, DailyIngresoStatus
from app.database.connection import get_db
from app.dependencies.auth_dependencies import require_admin
from app.schemas.daily_client_schema import (
    DailyClientCreate,
    DailyClientDetailResponse,
    DailyClientResponse,
    DailyClientUpdate,
    DailyFrecuenciaResponse,
    DailyIngresoCreate,
    DailyIngresoDetailResponse,
    DailyIngresoListResponse,
    DailyPaymentCreate,
    DailyPaymentListResponse,
    DailyPaymentResponse,
)
from app.services.daily_client_service import (
    DailyClientService,
    DailyIngresoService,
    DailyPaymentService,
)
from app.utils.responses import success_response

# ── Routers ────────────────────────────────────────────────────────────────────

daily_client_router = APIRouter(
    prefix="/api/clientes-diarios",
    tags=["Clientes Diarios"],
    dependencies=[Depends(require_admin)],
)

daily_ingreso_router = APIRouter(
    prefix="/api/ingresos-diarios",
    tags=["Ingresos Diarios"],
    dependencies=[Depends(require_admin)],
)


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS: CLIENTES DIARIOS
# ══════════════════════════════════════════════════════════════════════════════

@daily_client_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Registrar cliente diario",
    description=(
        "Registra un nuevo cliente de acceso diario. "
        "El campo 'documento' es opcional pero debe ser único si se proporciona."
    ),
)
def registrar_cliente_diario(
    payload: DailyClientCreate,
    db: Annotated[Session, Depends(get_db)],
):
    service = DailyClientService(db)
    data = service.registrar_cliente(payload)
    return success_response(
        data=data.model_dump(),
        message="Cliente diario registrado exitosamente",
        status_code=status.HTTP_201_CREATED,
    )


@daily_client_router.get(
    "",
    summary="Listar clientes diarios",
    description="Lista todos los clientes diarios con contadores de actividad. "
                "Filtros opcionales: estado y búsqueda por nombre.",
)
def listar_clientes_diarios(
    db: Annotated[Session, Depends(get_db)],
    estado: Annotated[
        DailyClientStatus | None,
        Query(description="Filtrar por estado: activo | inactivo"),
    ] = None,
    nombre: Annotated[
        str | None,
        Query(description="Búsqueda parcial por nombre"),
    ] = None,
):
    service = DailyClientService(db)
    data = service.listar_clientes(estado=estado, nombre_contains=nombre)
    return success_response(
        data=[c.model_dump() for c in data],
        message=f"Se encontraron {len(data)} cliente(s) diario(s)",
    )


@daily_client_router.patch(
    "/{client_id}",
    summary="Actualizar cliente diario",
    description=(
        "Actualiza campos de un cliente diario (PATCH semántico). "
        "Solo se modifican los campos enviados en el body."
    ),
)
def actualizar_cliente_diario(
    client_id: int,
    payload: DailyClientUpdate,
    db: Annotated[Session, Depends(get_db)],
):
    service = DailyClientService(db)
    data = service.actualizar_cliente(client_id, payload)
    return success_response(
        data=data.model_dump(),
        message="Cliente diario actualizado exitosamente",
    )


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS: PAGOS DIARIOS (sub-rutas de /api/clientes-diarios/{id})
# ══════════════════════════════════════════════════════════════════════════════

@daily_client_router.post(
    "/{client_id}/pago",
    status_code=status.HTTP_201_CREATED,
    summary="Registrar pago diario",
    description=(
        "Registra el pago diario de un cliente. "
        "No se permiten pagos duplicados en la misma fecha. "
        "El cliente debe estar activo."
    ),
)
def registrar_pago_diario(
    client_id: int,
    payload: DailyPaymentCreate,
    db: Annotated[Session, Depends(get_db)],
):
    service = DailyPaymentService(db)
    data = service.registrar_pago(
        client_id=client_id,
        monto=payload.monto,
        fecha_pago=payload.fecha_pago,
    )
    return success_response(
        data=data.model_dump(),
        message="Pago diario registrado exitosamente",
        status_code=status.HTTP_201_CREATED,
    )


@daily_client_router.get(
    "/{client_id}/pagos",
    summary="Historial de pagos de un cliente diario",
    description="Retorna el historial completo de pagos del cliente diario especificado.",
)
def historial_pagos_cliente(
    client_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    service = DailyPaymentService(db)
    data = service.historial_pagos(client_id)
    return success_response(
        data=data.model_dump(),
        message="Historial de pagos obtenido exitosamente",
    )


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS: INGRESOS — registro (sub-ruta de clientes-diarios)
# ══════════════════════════════════════════════════════════════════════════════

@daily_client_router.post(
    "/{client_id}/ingreso",
    status_code=status.HTTP_201_CREATED,
    summary="Registrar ingreso diario",
    description=(
        "Registra el ingreso de un cliente diario al gimnasio. "
        "Validaciones automáticas: cliente activo, pago del día, sin ingreso duplicado. "
        "Si alguna validación falla, se registra un ingreso DENEGADO con el motivo."
    ),
)
def registrar_ingreso_diario(
    client_id: int,
    payload: DailyIngresoCreate,
    db: Annotated[Session, Depends(get_db)],
):
    service = DailyIngresoService(db)
    data = service.registrar_ingreso(
        client_id=client_id,
        fecha=payload.fecha,
        motivo_manual=payload.motivo,
    )
    estado_msg = "aprobado" if data.estado.value == "aprobado" else "denegado"
    return success_response(
        data=data.model_dump(),
        message=f"Ingreso diario {estado_msg}",
        status_code=status.HTTP_201_CREATED,
    )


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS: INGRESOS DIARIOS (/api/ingresos-diarios)
# ══════════════════════════════════════════════════════════════════════════════

@daily_ingreso_router.get(
    "",
    summary="Listar ingresos diarios",
    description=(
        "Lista ingresos diarios con filtros opcionales y paginación. "
        "Filtros: cliente_id, estado, fecha_desde, fecha_hasta."
    ),
)
def listar_ingresos_diarios(
    db: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=1, description="Número de página")] = 1,
    per_page: Annotated[
        int, Query(ge=1, le=100, description="Resultados por página")
    ] = 20,
    cliente_id: Annotated[
        int | None, Query(description="Filtrar por ID de cliente diario")
    ] = None,
    estado: Annotated[
        DailyIngresoStatus | None,
        Query(description="Filtrar por estado: aprobado | denegado"),
    ] = None,
    fecha_desde: Annotated[
        date | None, Query(description="Fecha inicio del rango (YYYY-MM-DD)")
    ] = None,
    fecha_hasta: Annotated[
        date | None, Query(description="Fecha fin del rango (YYYY-MM-DD)")
    ] = None,
):
    service = DailyIngresoService(db)
    data = service.listar_ingresos(
        page=page,
        per_page=per_page,
        cliente_id=cliente_id,
        estado=estado,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )
    return success_response(
        data=data.model_dump(),
        message=f"Se encontraron {data.total} ingreso(s)",
    )


@daily_ingreso_router.get(
    "/frecuencia/{client_id}",
    summary="Frecuencia de asistencia de un cliente diario",
    description=(
        "Calcula y retorna estadísticas de frecuencia de asistencia: "
        "total de ingresos, primer/último ingreso, días del mes actual, "
        "historial mensual agrupado."
    ),
)
def frecuencia_cliente_diario(
    client_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    service = DailyIngresoService(db)
    data = service.calcular_frecuencia(client_id)
    return success_response(
        data=data.model_dump(),
        message="Frecuencia de asistencia calculada exitosamente",
    )


@daily_ingreso_router.get(
    "/cliente/{client_id}",
    summary="Ingresos de un cliente diario específico",
    description="Retorna el historial completo de ingresos del cliente diario especificado.",
)
def ingresos_por_cliente_diario(
    client_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    service = DailyIngresoService(db)
    data = service.ingresos_por_cliente(client_id)
    return success_response(
        data=data.model_dump(),
        message=f"Se encontraron {data.total} ingreso(s) para el cliente",
    )


@daily_ingreso_router.get(
    "/{ingreso_id}",
    summary="Obtener un ingreso diario por ID",
    description="Retorna el detalle completo de un registro de ingreso diario.",
)
def obtener_ingreso_diario(
    ingreso_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    service = DailyIngresoService(db)
    data = service.obtener_ingreso(ingreso_id)
    return success_response(
        data=data.model_dump(),
        message="Ingreso diario obtenido exitosamente",
    )
