"""
Repositorio de Rutinas. CRUD sobre 'rutinas' y su asociación con máquinas.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.routine import Routine, RoutineMachine


class RoutineRepository:
    """Acceso a datos de rutinas y sus máquinas."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, routine_id: int) -> Routine | None:
        return self._db.query(Routine).filter(Routine.id == routine_id).first()

    def list_all(
        self, page: int, per_page: int, solo_activas: bool = False
    ) -> tuple[list[Routine], int]:
        query = self._db.query(Routine)
        if solo_activas:
            query = query.filter(Routine.activa.is_(True))
        total = query.count()
        items = (
            query.order_by(Routine.nombre.asc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return items, total

    def create(self, nombre: str, descripcion: str | None, creada_por: int | None,
               maquina_ids: list[int]) -> Routine:
        routine = Routine(nombre=nombre, descripcion=descripcion, creada_por=creada_por)
        routine.maquinas = [RoutineMachine(maquina_id=mid) for mid in maquina_ids]
        self._db.add(routine)
        self._db.commit()
        self._db.refresh(routine)
        return routine

    def update(self, routine: Routine, data: dict, maquina_ids: list[int] | None) -> Routine:
        for key, value in data.items():
            setattr(routine, key, value)
        if maquina_ids is not None:
            # Reemplaza el conjunto de máquinas
            routine.maquinas.clear()
            self._db.flush()
            routine.maquinas = [RoutineMachine(maquina_id=mid) for mid in maquina_ids]
        self._db.commit()
        self._db.refresh(routine)
        return routine

    def delete(self, routine: Routine) -> None:
        self._db.delete(routine)
        self._db.commit()
