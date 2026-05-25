"""
Schemas Pydantic para el módulo de Recomendación de Horarios (Fase 10).
Define contratos de salida para recomendaciones, estadísticas y filtros.
"""
from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal

from pydantic import BaseModel, Field

from app.core.constants import AffluenceLevel, WeekDay


# ══════════════════════════════════════════════════════════════════════════════
#  RECOMENDACIÓN INDIVIDUAL
# ══════════════════════════════════════════════════════════════════════════════

class RecommendationResponseSchema(BaseModel):
    """Schema de respuesta para un bloque horario analizado."""
    id: int
    dia_semana: WeekDay
    hora_inicio: time
    hora_fin: time
    cantidad_promedio: Decimal
    nivel_afluencia: AffluenceLevel
    es_recomendado: bool
    evitar: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════════════════
#  RESULTADO DE GENERACIÓN
# ══════════════════════════════════════════════════════════════════════════════

class GenerationResultSchema(BaseModel):
    """Resumen del proceso de generación de recomendaciones."""
    bloques_analizados: int
    bloques_recomendados: int
    bloques_a_evitar: int
    total_asistencias_procesadas: int
    mensaje: str


# ══════════════════════════════════════════════════════════════════════════════
#  HORARIOS POR DÍA
# ══════════════════════════════════════════════════════════════════════════════

class DayScheduleSchema(BaseModel):
    """Recomendaciones de un día específico ordenadas por afluencia."""
    dia_semana: WeekDay
    bloques: list[RecommendationResponseSchema]
    horario_recomendado: RecommendationResponseSchema | None  # menor afluencia
    horario_pico: RecommendationResponseSchema | None         # mayor afluencia


# ══════════════════════════════════════════════════════════════════════════════
#  ESTADÍSTICAS
# ══════════════════════════════════════════════════════════════════════════════

class DayStatsSchema(BaseModel):
    """Estadísticas resumidas de un día."""
    dia_semana: WeekDay
    promedio_por_hora: float
    total_ingresos: int
    hora_pico: str | None              # ej. "18:00-19:00"
    hora_libre: str | None             # ej. "08:00-09:00"


class GeneralStatsSchema(BaseModel):
    """Estadísticas generales de afluencia del gimnasio."""
    total_semanal: int
    promedio_por_dia: float
    promedio_por_hora: float
    horario_mas_concurrido: str | None       # ej. "viernes 19:00-20:00"
    horario_menos_concurrido: str | None      # ej. "lunes 08:00-09:00"
    porcentaje_ocupacion: float                # respecto a la capacidad pico observada
    por_dia: list[DayStatsSchema]


# ══════════════════════════════════════════════════════════════════════════════
#  FILTROS Y PAGINACIÓN
# ══════════════════════════════════════════════════════════════════════════════

class RecommendationFilterSchema(BaseModel):
    """Parámetros de filtro, orden y paginación para GET /api/recomendaciones."""
    dia_semana: WeekDay | None = Field(default=None, description="Filtra por día")
    nivel_afluencia: AffluenceLevel | None = Field(default=None, description="Filtra por nivel")
    es_recomendado: bool | None = Field(default=None, description="Solo recomendados")
    evitar: bool | None = Field(default=None, description="Solo a evitar")
    orden: str = Field(
        default="afluencia_asc",
        description="afluencia_asc | afluencia_desc | dia",
    )
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=50, ge=1, le=200)


class PaginatedRecommendationSchema(BaseModel):
    """Respuesta paginada de recomendaciones."""
    items: list[RecommendationResponseSchema]
    total: int
    page: int
    per_page: int
    total_pages: int
