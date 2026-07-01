"""
Servicio de Rutinas. Valida las máquinas y construye la respuesta con zonas.
"""
from __future__ import annotations

import math

from app.core.exceptions import RoutineInvalidException, RoutineNotFoundException
from app.repositories.machine_repository import MachineRepository
from app.repositories.routine_repository import RoutineRepository
from app.schemas.routine_schema import (
    RoutineCreateSchema,
    RoutineMachineItemSchema,
    RoutineResponseSchema,
    RoutineUpdateSchema,
)


class RoutineService:
    """Gestiona las plantillas de rutina y sus máquinas."""

    def __init__(self, repo: RoutineRepository, machine_repo: MachineRepository) -> None:
        self._repo = repo
        self._machines = machine_repo

    # ── Validación de máquinas ──────────────────────────────────────────────────

    def _validate_machine_ids(self, maquina_ids: list[int]) -> None:
        unique_ids = list(dict.fromkeys(maquina_ids))  # sin duplicados, preserva orden
        found = self._machines.get_many_by_ids(unique_ids)
        if len(found) != len(unique_ids):
            raise RoutineInvalidException("Una o más máquinas indicadas no existen")

    # ── CRUD ────────────────────────────────────────────────────────────────────

    def create(self, data: RoutineCreateSchema, creada_por: int | None) -> RoutineResponseSchema:
        maquina_ids = list(dict.fromkeys(data.maquina_ids))
        self._validate_machine_ids(maquina_ids)
        routine = self._repo.create(
            nombre=data.nombre,
            descripcion=data.descripcion,
            creada_por=creada_por,
            maquina_ids=maquina_ids,
        )
        return self._to_response(routine)

    def update(self, routine_id: int, data: RoutineUpdateSchema) -> RoutineResponseSchema:
        routine = self._repo.get_by_id(routine_id)
        if routine is None:
            raise RoutineNotFoundException()

        maquina_ids = None
        if data.maquina_ids is not None:
            maquina_ids = list(dict.fromkeys(data.maquina_ids))
            if not maquina_ids:
                raise RoutineInvalidException("La rutina debe tener al menos una máquina")
            self._validate_machine_ids(maquina_ids)

        fields = data.model_dump(exclude_unset=True, exclude={"maquina_ids"})
        routine = self._repo.update(routine, fields, maquina_ids)
        return self._to_response(routine)

    def delete(self, routine_id: int) -> None:
        routine = self._repo.get_by_id(routine_id)
        if routine is None:
            raise RoutineNotFoundException()
        self._repo.delete(routine)

    def get(self, routine_id: int) -> RoutineResponseSchema:
        routine = self._repo.get_by_id(routine_id)
        if routine is None:
            raise RoutineNotFoundException()
        return self._to_response(routine)

    def list(self, page: int, per_page: int, solo_activas: bool) -> dict:
        items, total = self._repo.list_all(page, per_page, solo_activas)
        total_pages = math.ceil(total / per_page) if total > 0 else 1
        return {
            "items": [self._to_response(r).model_dump() for r in items],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        }

    # ── Helpers ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _to_response(routine) -> RoutineResponseSchema:
        maquinas = [
            RoutineMachineItemSchema(
                maquina_id=rm.maquina.id,
                nombre=rm.maquina.nombre,
                zona=rm.maquina.zona,
            )
            for rm in routine.maquinas
            if rm.maquina is not None
        ]
        zonas = list(dict.fromkeys(m.zona for m in maquinas))
        return RoutineResponseSchema(
            id=routine.id,
            nombre=routine.nombre,
            descripcion=routine.descripcion,
            activa=routine.activa,
            creada_por=routine.creada_por,
            maquinas=maquinas,
            zonas=zonas,
            created_at=routine.created_at,
        )
