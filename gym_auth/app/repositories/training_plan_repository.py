"""
Repositorio de Planificación de Entrenamiento. CRUD sobre 'planes_entrenamiento'
y su asociación con máquinas ('plan_maquinas').
"""
from __future__ import annotations

from datetime import date, time

from sqlalchemy.orm import Session

from app.core.constants import TrainingPlanStatus
from app.models.training_plan import TrainingPlan, TrainingPlanMachine


class TrainingPlanRepository:
    """Acceso a datos de planes de entrenamiento de clientes."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, plan_id: int) -> TrainingPlan | None:
        return self._db.query(TrainingPlan).filter(TrainingPlan.id == plan_id).first()

    def get_for_client_date(self, cliente_id: int, fecha: date) -> TrainingPlan | None:
        return (
            self._db.query(TrainingPlan)
            .filter(TrainingPlan.cliente_id == cliente_id, TrainingPlan.fecha == fecha)
            .first()
        )

    def list_for_client(self, cliente_id: int) -> list[TrainingPlan]:
        return (
            self._db.query(TrainingPlan)
            .filter(TrainingPlan.cliente_id == cliente_id)
            .order_by(TrainingPlan.fecha.desc())
            .all()
        )

    def list_for_date(self, fecha: date) -> list[TrainingPlan]:
        """Todos los planes de una fecha (para la vista del entrenador)."""
        return (
            self._db.query(TrainingPlan)
            .filter(TrainingPlan.fecha == fecha)
            .order_by(TrainingPlan.hora_inicio.asc())
            .all()
        )

    def upsert(
        self,
        cliente_id: int,
        fecha: date,
        hora_inicio: time,
        estado: TrainingPlanStatus,
        rutina_id: int | None,
        maquina_ids: list[int],
    ) -> TrainingPlan:
        """Crea o reemplaza el plan del cliente para esa fecha."""
        plan = self.get_for_client_date(cliente_id, fecha)
        if plan is None:
            plan = TrainingPlan(cliente_id=cliente_id, fecha=fecha)
            self._db.add(plan)

        plan.hora_inicio = hora_inicio
        plan.estado = estado
        plan.rutina_id = rutina_id
        # Reemplaza máquinas
        plan.maquinas.clear()
        self._db.flush()
        plan.maquinas = [TrainingPlanMachine(maquina_id=mid) for mid in maquina_ids]

        self._db.commit()
        self._db.refresh(plan)
        return plan

    def update_status(self, plan: TrainingPlan, estado: TrainingPlanStatus) -> TrainingPlan:
        plan.estado = estado
        self._db.commit()
        self._db.refresh(plan)
        return plan

    def delete(self, plan: TrainingPlan) -> None:
        self._db.delete(plan)
        self._db.commit()
