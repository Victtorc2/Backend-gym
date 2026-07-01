"""
Repositorio del catálogo de Máquinas. CRUD sobre la tabla 'maquinas'.
"""
from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.constants import MuscleZone
from app.models.machine import Machine


class MachineRepository:
    """Acceso a datos de máquinas del gimnasio."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, machine_id: int) -> Machine | None:
        return self._db.query(Machine).filter(Machine.id == machine_id).first()

    def get_by_nombre(self, nombre: str) -> Machine | None:
        return self._db.query(Machine).filter(Machine.nombre == nombre).first()

    def get_many_by_ids(self, ids: list[int]) -> list[Machine]:
        if not ids:
            return []
        return self._db.query(Machine).filter(Machine.id.in_(ids)).all()

    def list_active_by_zones(self, zonas: list[MuscleZone]) -> list[Machine]:
        """Máquinas activas cuyas zonas están en la lista dada."""
        if not zonas:
            return []
        return (
            self._db.query(Machine)
            .filter(Machine.activa.is_(True), Machine.zona.in_(zonas))
            .all()
        )

    def list_all(
        self,
        page: int,
        per_page: int,
        buscar: str | None = None,
        zona: MuscleZone | None = None,
        solo_activas: bool = False,
    ) -> tuple[list[Machine], int]:
        query = self._db.query(Machine)
        if buscar:
            like = f"%{buscar.strip()}%"
            query = query.filter(or_(Machine.nombre.ilike(like), Machine.descripcion.ilike(like)))
        if zona is not None:
            query = query.filter(Machine.zona == zona)
        if solo_activas:
            query = query.filter(Machine.activa.is_(True))

        total = query.count()
        items = (
            query.order_by(Machine.zona.asc(), Machine.nombre.asc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return items, total

    def create(self, data: dict) -> Machine:
        obj = Machine(**data)
        self._db.add(obj)
        self._db.commit()
        self._db.refresh(obj)
        return obj

    def update(self, machine: Machine, data: dict) -> Machine:
        for key, value in data.items():
            setattr(machine, key, value)
        self._db.commit()
        self._db.refresh(machine)
        return machine

    def delete(self, machine: Machine) -> None:
        self._db.delete(machine)
        self._db.commit()

    def count(self) -> int:
        from sqlalchemy import func
        return self._db.query(func.count(Machine.id)).scalar() or 0
