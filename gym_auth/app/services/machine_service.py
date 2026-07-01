"""
Servicio del catálogo de Máquinas. Lógica de negocio y validaciones.
"""
from __future__ import annotations

import math

from app.core.constants import MuscleZone
from app.core.exceptions import (
    MachineAlreadyExistsException,
    MachineNotFoundException,
)
from app.repositories.machine_repository import MachineRepository
from app.schemas.machine_schema import (
    MachineCreateSchema,
    MachineResponseSchema,
    MachineUpdateSchema,
)


class MachineService:
    """Gestiona el catálogo de máquinas del gimnasio."""

    def __init__(self, repo: MachineRepository) -> None:
        self._repo = repo

    def create(self, data: MachineCreateSchema) -> MachineResponseSchema:
        if self._repo.get_by_nombre(data.nombre) is not None:
            raise MachineAlreadyExistsException()
        machine = self._repo.create(data.model_dump())
        return MachineResponseSchema.model_validate(machine)

    def update(self, machine_id: int, data: MachineUpdateSchema) -> MachineResponseSchema:
        machine = self._repo.get_by_id(machine_id)
        if machine is None:
            raise MachineNotFoundException()

        payload = data.model_dump(exclude_unset=True)
        nuevo_nombre = payload.get("nombre")
        if nuevo_nombre and nuevo_nombre != machine.nombre:
            if self._repo.get_by_nombre(nuevo_nombre) is not None:
                raise MachineAlreadyExistsException()

        machine = self._repo.update(machine, payload)
        return MachineResponseSchema.model_validate(machine)

    def delete(self, machine_id: int) -> None:
        machine = self._repo.get_by_id(machine_id)
        if machine is None:
            raise MachineNotFoundException()
        self._repo.delete(machine)

    def get(self, machine_id: int) -> MachineResponseSchema:
        machine = self._repo.get_by_id(machine_id)
        if machine is None:
            raise MachineNotFoundException()
        return MachineResponseSchema.model_validate(machine)

    def list(
        self,
        page: int,
        per_page: int,
        buscar: str | None,
        zona: MuscleZone | None,
        solo_activas: bool,
    ) -> dict:
        items, total = self._repo.list_all(
            page=page, per_page=per_page, buscar=buscar, zona=zona, solo_activas=solo_activas
        )
        total_pages = math.ceil(total / per_page) if total > 0 else 1
        return {
            "items": [MachineResponseSchema.model_validate(m).model_dump() for m in items],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        }
