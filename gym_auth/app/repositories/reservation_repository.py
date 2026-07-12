"""
Repositorio de Reservas de Máquina.
"""
from __future__ import annotations

from datetime import date, time

from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload

from app.core.constants import ReservationStatus
from app.models.reservation import MachineReservation


class ReservationRepository:
    """Persistencia y consultas de reservas de máquina."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, rid: int) -> MachineReservation | None:
        return self._db.query(MachineReservation).filter(MachineReservation.id == rid).first()

    def create(self, data: dict) -> MachineReservation:
        obj = MachineReservation(**data)
        self._db.add(obj)
        self._db.commit()
        self._db.refresh(obj)
        return obj

    def cancel(self, reserva: MachineReservation) -> None:
        reserva.estado = ReservationStatus.CANCELADA
        self._db.commit()

    def overlapping_count(
        self, maquina_id: int, fecha: date, hora_inicio: time, hora_fin: time
    ) -> int:
        """Nº de reservas activas de la máquina que se solapan con la franja dada."""
        return (
            self._db.query(MachineReservation)
            .filter(
                MachineReservation.maquina_id == maquina_id,
                MachineReservation.fecha == fecha,
                MachineReservation.estado == ReservationStatus.ACTIVA,
                # Dos intervalos se solapan si inicio_a < fin_b y inicio_b < fin_a
                and_(
                    MachineReservation.hora_inicio < hora_fin,
                    MachineReservation.hora_fin > hora_inicio,
                ),
            )
            .count()
        )

    def list_for_machines_date(
        self, maquina_ids: list[int], fecha: date
    ) -> list[MachineReservation]:
        """Reservas activas de un conjunto de máquinas en una fecha."""
        if not maquina_ids:
            return []
        return (
            self._db.query(MachineReservation)
            .filter(
                MachineReservation.maquina_id.in_(maquina_ids),
                MachineReservation.fecha == fecha,
                MachineReservation.estado == ReservationStatus.ACTIVA,
            )
            .order_by(MachineReservation.hora_inicio.asc())
            .all()
        )

    def list_admin(
        self,
        maquina_id: int | None = None,
        fecha: date | None = None,
        incluir_canceladas: bool = False,
    ) -> list[MachineReservation]:
        """
        Lista reservas para el administrador, con cliente y máquina cargados.
        Filtra opcionalmente por máquina y/o fecha. Por defecto omite canceladas.
        """
        query = self._db.query(MachineReservation).options(
            joinedload(MachineReservation.cliente),
            joinedload(MachineReservation.maquina),
        )
        if not incluir_canceladas:
            query = query.filter(MachineReservation.estado == ReservationStatus.ACTIVA)
        if maquina_id is not None:
            query = query.filter(MachineReservation.maquina_id == maquina_id)
        if fecha is not None:
            query = query.filter(MachineReservation.fecha == fecha)
        return query.order_by(
            MachineReservation.fecha.desc(),
            MachineReservation.hora_inicio.asc(),
        ).all()

    def list_for_client(
        self, cliente_id: int, fecha: date | None = None
    ) -> list[MachineReservation]:
        query = self._db.query(MachineReservation).filter(
            MachineReservation.cliente_id == cliente_id,
            MachineReservation.estado == ReservationStatus.ACTIVA,
        )
        if fecha is not None:
            query = query.filter(MachineReservation.fecha == fecha)
        return query.order_by(
            MachineReservation.fecha.desc(), MachineReservation.hora_inicio.asc()
        ).all()
