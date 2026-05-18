"""
Schemas Pydantic del módulo Segmentación y Seguimiento (Fase 7).
Todos los campos son de solo lectura (respuesta): la segmentación es calculada,
no ingresada manualmente.

Separación estricta request / response.
"""
from __future__ import annotations

from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import (
    ActivitySegment,
    AgeGroup,
    ClientSex,
    ClientStatus,
    FinancialSegment,
)


# ══════════════════════════════════════════════════════════════════════════════
# SEGMENTACIÓN DE UN CLIENTE
# ══════════════════════════════════════════════════════════════════════════════

class ClientSegmentationResponse(BaseModel):
    """
    Segmentación completa calculada de un cliente.
    Combina dimensiones demográfica, de actividad y financiera.
    """

    model_config = ConfigDict(from_attributes=True)

    # ── Identificación ─────────────────────────────────────────────────────────
    cliente_id: int
    nombres: str
    apellidos: str
    dni: str
    estado: ClientStatus

    # ── Demográfico ────────────────────────────────────────────────────────────
    sexo: ClientSex
    edad: int = Field(description="Edad calculada en años cumplidos")
    grupo_edad: AgeGroup = Field(
        description="joven (14-25) | adulto (26+)"
    )

    # ── Actividad ──────────────────────────────────────────────────────────────
    asistencias_mes_actual: int = Field(
        description="Ingresos aprobados en el mes y año en curso"
    )
    ultimo_ingreso: date | None = Field(
        description="Fecha del último ingreso aprobado registrado"
    )
    segmento_actividad: ActivitySegment = Field(
        description="activo | poco_activo | inactivo"
    )

    # ── Financiero ─────────────────────────────────────────────────────────────
    pagos_pendientes: int = Field(
        description="Cantidad de pagos con estado pendiente o vencido"
    )
    deuda_total: float = Field(
        description="Suma de saldos pendientes en pagos no completados"
    )
    segmento_financiero: FinancialSegment = Field(
        description="sin_deuda | con_deuda"
    )


# ══════════════════════════════════════════════════════════════════════════════
# RESUMEN GENERAL (estadísticas agregadas)
# ══════════════════════════════════════════════════════════════════════════════

class ActivityBreakdown(BaseModel):
    """Distribución de clientes por segmento de actividad."""
    activo: int
    poco_activo: int
    inactivo: int
    total: int


class FinancialBreakdown(BaseModel):
    """Distribución de clientes por segmento financiero."""
    sin_deuda: int
    con_deuda: int
    total: int
    deuda_total_sistema: float = Field(
        description="Suma total de saldos pendientes en todo el sistema"
    )


class DemographicBreakdown(BaseModel):
    """Distribución de clientes por dimensiones demográficas."""
    masculino: int
    femenino: int
    otro: int
    joven: int       # AgeGroup.JOVEN
    adulto: int      # AgeGroup.ADULTO
    total: int


class SegmentationSummaryResponse(BaseModel):
    """
    Resumen estadístico de segmentación para todos los clientes activos.
    Útil como punto de partida para campañas y análisis de retención.
    """
    total_clientes_activos: int
    demografico: DemographicBreakdown
    actividad: ActivityBreakdown
    financiero: FinancialBreakdown


# ══════════════════════════════════════════════════════════════════════════════
# FILTROS DE CONSULTA (query params)
# ══════════════════════════════════════════════════════════════════════════════

class SegmentationFilter(BaseModel):
    """
    Parámetros de filtrado para el listado de segmentación.
    Todos opcionales; se combinan con AND si se envían múltiples.
    """

    sexo: ClientSex | None = None
    grupo_edad: AgeGroup | None = None
    segmento_actividad: ActivitySegment | None = None
    segmento_financiero: FinancialSegment | None = None
    edad_min: Annotated[int | None, Field(ge=0)] = None
    edad_max: Annotated[int | None, Field(ge=0)] = None
