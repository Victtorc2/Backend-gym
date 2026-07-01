"""
Schemas Pydantic para la Gestión de Demanda (dashboards, vista de entrenador,
Índice de Demanda y precisión de predicción).
"""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from app.core.constants import DemandLevel, MuscleZone, TrainingPlanStatus


# ══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD DE DEMANDA PREVISTA (HOY)
# ══════════════════════════════════════════════════════════════════════════════

class MachineDemandItemSchema(BaseModel):
    """Demanda prevista para una máquina."""
    maquina_id: int
    nombre: str
    zona: MuscleZone
    clientes: int          # clientes que planean usarla
    cantidad: int          # unidades disponibles
    saturada: bool         # demanda concurrente en algún bloque supera las unidades


class HourDemandItemSchema(BaseModel):
    """Demanda prevista para un bloque horario."""
    horario: str           # "18:00-19:00"
    clientes: int
    nivel: DemandLevel


class ZoneDistributionItemSchema(BaseModel):
    """Porcentaje de demanda por zona muscular."""
    zona: MuscleZone
    clientes: int
    porcentaje: float


class TodayDemandDashboardSchema(BaseModel):
    """Panel de demanda prevista para una fecha."""
    fecha: date
    total_planes: int
    demanda_por_maquina: list[MachineDemandItemSchema]
    demanda_por_hora: list[HourDemandItemSchema]
    distribucion_zonas: list[ZoneDistributionItemSchema]
    maquinas_saturadas: list[str]
    mensaje: str


# ══════════════════════════════════════════════════════════════════════════════
#  VISTA DEL ENTRENADOR (quién asiste hoy)
# ══════════════════════════════════════════════════════════════════════════════

class TrainerClientItemSchema(BaseModel):
    """Cliente y su planificación del día (para el entrenador)."""
    cliente_id: int
    nombre: str
    zonas: list[MuscleZone]
    estado: TrainingPlanStatus | None
    planifico: bool


class TrainerTodayViewSchema(BaseModel):
    """Resumen para el entrenador: quiénes planificaron y quiénes no."""
    fecha: date
    total_clientes: int
    total_planifico: int
    total_sin_confirmar: int
    con_plan: list[TrainerClientItemSchema]
    sin_plan: list[TrainerClientItemSchema]


# ══════════════════════════════════════════════════════════════════════════════
#  ÍNDICE DE DEMANDA (histórico / inversión)
# ══════════════════════════════════════════════════════════════════════════════

class MachineDemandIndexSchema(BaseModel):
    """Índice de Demanda de una máquina y su recomendación de inversión."""
    maquina_id: int
    nombre: str
    zona: MuscleZone
    cantidad: int
    planificaciones: int             # nº de veces planificada (histórico)
    usos_reales_proxy: int           # planes cuyo cliente sí asistió (proxy de uso real)
    tiempo_espera_promedio: float    # minutos (0 hasta registrar espera real)
    indice_demanda: float
    recomienda_invertir: bool
    recomendacion: str


class InvestmentReportSchema(BaseModel):
    """Reporte de Índice de Demanda ordenado por prioridad de inversión."""
    generado_para: date
    items: list[MachineDemandIndexSchema]
    recomendaciones: list[str]


# ══════════════════════════════════════════════════════════════════════════════
#  PRECISIÓN DE PREDICCIÓN (planificado vs asistido)
# ══════════════════════════════════════════════════════════════════════════════

class PrecisionStatsSchema(BaseModel):
    """Compara planificaciones con asistencia real para medir precisión."""
    desde: date
    hasta: date
    total_planes: int
    planes_cumplidos: int            # el cliente sí asistió ese día
    precision_porcentaje: float
    mensaje: str
