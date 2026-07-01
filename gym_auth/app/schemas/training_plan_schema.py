"""
Schemas Pydantic para la Planificación de Entrenamiento del cliente.
Incluye el valor agregado: avisos de demanda por zona y sugerencia de orden.
"""
from __future__ import annotations

from datetime import date, datetime, time

from pydantic import BaseModel, Field

from app.core.constants import DemandLevel, MuscleZone, TrainingPlanStatus


class TrainingPlanCreateSchema(BaseModel):
    """
    Datos con los que el cliente planifica su día. Debe indicar al menos una
    zona muscular o una rutina; el sistema deduce las máquinas.
    """
    fecha: date
    hora_inicio: time
    zonas: list[MuscleZone] = Field(default_factory=list, description="Zonas a entrenar")
    rutina_id: int | None = Field(default=None, description="Rutina del entrenador (opcional)")
    estado: TrainingPlanStatus = TrainingPlanStatus.PLANEADO


class TrainingPlanStatusUpdateSchema(BaseModel):
    """Cambia el nivel de compromiso del plan (confirmar, en camino, cancelar)."""
    estado: TrainingPlanStatus


class PlanMachineItemSchema(BaseModel):
    """Máquina prevista dentro del plan."""
    maquina_id: int
    nombre: str
    zona: MuscleZone


class DemandHintSchema(BaseModel):
    """Aviso de demanda para una zona en el horario del cliente."""
    zona: MuscleZone
    nivel: DemandLevel
    clientes_previstos: int
    mensaje: str


class TrainingPlanResponseSchema(BaseModel):
    """Plan del cliente con máquinas resueltas y el valor agregado de demanda."""
    id: int
    cliente_id: int
    fecha: date
    hora_inicio: str                    # "18:00"
    estado: TrainingPlanStatus
    rutina_id: int | None
    maquinas: list[PlanMachineItemSchema]
    zonas: list[MuscleZone]
    avisos_demanda: list[DemandHintSchema]     # zonas con alta demanda en su horario
    sugerencia_orden: str | None               # recomendación de orden para evitar colas
    mensaje: str
    created_at: datetime

    model_config = {"from_attributes": True}
