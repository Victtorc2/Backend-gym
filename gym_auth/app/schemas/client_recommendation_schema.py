"""
Schemas Pydantic para el módulo de Recomendación Personalizada a Clientes.

Contratos:
- Entrada: filtro de candidatos, creación de recomendación.
- Salida: bloques sugeridos (baja concurrencia), candidatos con su hora
  habitual, y la recomendación ya asignada.
"""
from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal

from pydantic import BaseModel, Field

from app.core.constants import (
    AffluenceLevel,
    ClientRecommendationOrigin,
    ClientRecommendationStatus,
    ClientStatus,
    WeekDay,
)


# ══════════════════════════════════════════════════════════════════════════════
#  BLOQUES SUGERIDOS (baja concurrencia) — el "menú" que elige el admin
# ══════════════════════════════════════════════════════════════════════════════

class SuggestedBlockSchema(BaseModel):
    """Bloque horario de baja concurrencia sugerido para recomendar."""
    dia_semana: WeekDay
    hora_inicio: time
    hora_fin: time
    horario: str                       # ej. "08:00-09:00"
    cantidad_promedio: Decimal
    nivel_afluencia: AffluenceLevel


# ══════════════════════════════════════════════════════════════════════════════
#  CANDIDATOS — lista de clientes para el admin, con ayuda para decidir
# ══════════════════════════════════════════════════════════════════════════════

class ClientCandidateSchema(BaseModel):
    """Cliente candidato a recibir una recomendación de horario."""
    cliente_id: int
    nombres: str
    apellidos: str
    dni: str
    estado: ClientStatus
    hora_habitual: str | None                  # ej. "19:00-20:00" (hora en que más viene)
    nivel_hora_habitual: AffluenceLevel | None  # afluencia de esa hora habitual
    viene_en_hora_pico: bool                   # True si su hora habitual es hora pico
    tiene_recomendacion_activa: bool           # ya tiene una recomendación vigente


class PaginatedCandidatesSchema(BaseModel):
    """Respuesta paginada de candidatos + sugerencia global."""
    items: list[ClientCandidateSchema]
    total: int
    page: int
    per_page: int
    total_pages: int
    mejor_sugerencia: SuggestedBlockSchema | None   # bloque más vacío disponible


class CandidateFilterSchema(BaseModel):
    """Filtro para listar candidatos."""
    buscar: str | None = Field(default=None, description="Nombre, apellido o DNI")
    solo_hora_pico: bool = Field(
        default=False,
        description="Solo clientes cuya hora habitual es hora pico",
    )
    estado: ClientStatus | None = Field(default=None, description="Filtra por estado")
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)


# ══════════════════════════════════════════════════════════════════════════════
#  CREACIÓN / ASIGNACIÓN
# ══════════════════════════════════════════════════════════════════════════════

class CreateClientRecommendationSchema(BaseModel):
    """Datos para asignar una recomendación de horario a un cliente."""
    cliente_id: int = Field(..., gt=0)
    dia_semana: WeekDay
    hora_inicio: time
    hora_fin: time
    mensaje: str | None = Field(default=None, max_length=300)


# ══════════════════════════════════════════════════════════════════════════════
#  RESPUESTA — recomendación asignada (vista admin)
# ══════════════════════════════════════════════════════════════════════════════

class ClientRecommendationResponseSchema(BaseModel):
    """Recomendación personalizada asignada a un cliente."""
    id: int
    cliente_id: int
    cliente_nombre: str
    dia_semana: WeekDay
    horario: str                       # ej. "08:00-09:00"
    cantidad_promedio_estimada: Decimal | None
    nivel_afluencia: AffluenceLevel | None
    mensaje: str | None
    origen: ClientRecommendationOrigin
    estado: ClientRecommendationStatus
    created_at: datetime


class PaginatedClientRecommendationSchema(BaseModel):
    """Respuesta paginada de recomendaciones asignadas."""
    items: list[ClientRecommendationResponseSchema]
    total: int
    page: int
    per_page: int
    total_pages: int
