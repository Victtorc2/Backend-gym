"""
Rutas del módulo Segmentación y Seguimiento (Fase 7).
Prefijo: /api/segmentacion

Todos los endpoints:
  - Requieren JWT válido con rol ADMINISTRADOR.
  - No contienen lógica de negocio (delegan al SegmentationService).
  - Devuelven el formato de respuesta estándar del sistema.

Nota: la segmentación es calculada dinámicamente, no persiste en BD.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.constants import ActivitySegment, AgeGroup, ClientSex, FinancialSegment
from app.database.connection import get_db
from app.dependencies.auth_dependencies import require_admin
from app.schemas.segmentation_schema import SegmentationFilter
from app.services.segmentation_service import SegmentationService
from app.utils.responses import success_response

router = APIRouter(
    prefix="/api/segmentacion",
    tags=["Segmentación y Seguimiento"],
    dependencies=[Depends(require_admin)],
)


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/clientes",
    summary="Segmentación de todos los clientes activos",
    description=(
        "Retorna la segmentación completa (demográfica, actividad, financiera) "
        "calculada dinámicamente para cada cliente activo del sistema. "
        "Acepta filtros combinados por sexo, grupo de edad, actividad y estado financiero."
    ),
)
def listar_segmentacion_clientes(
    db: Annotated[Session, Depends(get_db)],
    sexo: Annotated[
        ClientSex | None,
        Query(description="Filtrar por sexo: masculino | femenino | otro"),
    ] = None,
    grupo_edad: Annotated[
        AgeGroup | None,
        Query(description="Filtrar por grupo de edad: joven | adulto"),
    ] = None,
    segmento_actividad: Annotated[
        ActivitySegment | None,
        Query(description="Filtrar por actividad: activo | poco_activo | inactivo"),
    ] = None,
    segmento_financiero: Annotated[
        FinancialSegment | None,
        Query(description="Filtrar por estado financiero: sin_deuda | con_deuda"),
    ] = None,
    edad_min: Annotated[
        int | None,
        Query(ge=0, description="Edad mínima (inclusive)"),
    ] = None,
    edad_max: Annotated[
        int | None,
        Query(ge=0, description="Edad máxima (inclusive)"),
    ] = None,
):
    filters = SegmentationFilter(
        sexo=sexo,
        grupo_edad=grupo_edad,
        segmento_actividad=segmento_actividad,
        segmento_financiero=segmento_financiero,
        edad_min=edad_min,
        edad_max=edad_max,
    )
    service = SegmentationService(db)
    data = service.list_clients_segmentation(filters=filters)

    return success_response(
        data=[s.model_dump() for s in data],
        message=f"Segmentación generada para {len(data)} cliente(s)",
    )


@router.get(
    "/resumen",
    summary="Resumen estadístico de segmentación",
    description=(
        "Retorna estadísticas agregadas de segmentación para todos los clientes activos: "
        "distribución por sexo, grupo de edad, actividad y estado financiero, "
        "más el total de deuda del sistema."
    ),
)
def resumen_segmentacion(
    db: Annotated[Session, Depends(get_db)],
):
    service = SegmentationService(db)
    data = service.get_segmentation_summary()

    return success_response(
        data=data.model_dump(),
        message="Resumen de segmentación generado exitosamente",
    )


@router.get(
    "/cliente/{client_id}",
    summary="Segmentación de un cliente específico",
    description=(
        "Calcula y retorna la segmentación completa de un cliente por su ID. "
        "Incluye dimensiones demográfica, de actividad y financiera."
    ),
)
def segmentacion_cliente(
    client_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    service = SegmentationService(db)
    data = service.get_client_segmentation(client_id)

    return success_response(
        data=data.model_dump(),
        message="Segmentación del cliente generada exitosamente",
    )
