"""
Repositorio de Gestión de Demanda (solo lectura / agregaciones).

Calcula la demanda prevista a partir de 'planes_entrenamiento' + 'plan_maquinas',
la cruza con el catálogo de 'maquinas' y con 'asistencias' (proxy de uso real).
No modifica ninguna tabla.
"""
from __future__ import annotations

from datetime import date, time

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.core.constants import (
    ACTIVE_PLAN_STATES,
    AttendanceStatus,
    ClientStatus,
    MuscleZone,
    TrainingPlanStatus,
)
from app.models.attendance import Attendance
from app.models.client import Client
from app.models.machine import Machine
from app.models.recommendation import ScheduleRecommendation
from app.models.reservation import MachineReservation
from app.models.training_plan import TrainingPlan, TrainingPlanMachine
from app.core.constants import ReservationStatus, WeekDay

# Estados de plan que cuentan como demanda (enum, para filtros)
_ACTIVE_STATES = [TrainingPlanStatus(s) for s in ACTIVE_PLAN_STATES]


class DemandRepository:
    """Agregaciones de demanda prevista e histórica."""

    def __init__(self, db: Session) -> None:
        self._db = db

    # ── Clientes (para la vista del entrenador) ────────────────────────────────

    def list_active_clients(self) -> list[Client]:
        """Lista los clientes activos, ordenados por apellido/nombre."""
        return (
            self._db.query(Client)
            .filter(Client.estado == ClientStatus.ACTIVO)
            .order_by(Client.apellidos.asc(), Client.nombres.asc())
            .all()
        )

    # ── Demanda prevista para una fecha ────────────────────────────────────────

    def count_plans(self, fecha: date) -> int:
        return (
            self._db.query(func.count(TrainingPlan.id))
            .filter(TrainingPlan.fecha == fecha, TrainingPlan.estado.in_(_ACTIVE_STATES))
            .scalar()
        ) or 0

    def demand_by_machine(self, fecha: date) -> dict[int, int]:
        """{maquina_id: nº de planes que la incluyen} para la fecha."""
        rows = (
            self._db.query(
                TrainingPlanMachine.maquina_id.label("mid"),
                func.count(func.distinct(TrainingPlan.id)).label("c"),
            )
            .join(TrainingPlan, TrainingPlan.id == TrainingPlanMachine.plan_id)
            .filter(TrainingPlan.fecha == fecha, TrainingPlan.estado.in_(_ACTIVE_STATES))
            .group_by(TrainingPlanMachine.maquina_id)
            .all()
        )
        return {int(r.mid): int(r.c) for r in rows}

    def demand_by_machine_hour(self, fecha: date) -> dict[tuple[int, int], int]:
        """{(maquina_id, hora): nº de planes concurrentes} — para detectar saturación."""
        rows = (
            self._db.query(
                TrainingPlanMachine.maquina_id.label("mid"),
                func.hour(TrainingPlan.hora_inicio).label("h"),
                func.count(func.distinct(TrainingPlan.id)).label("c"),
            )
            .join(TrainingPlan, TrainingPlan.id == TrainingPlanMachine.plan_id)
            .filter(TrainingPlan.fecha == fecha, TrainingPlan.estado.in_(_ACTIVE_STATES))
            .group_by(TrainingPlanMachine.maquina_id, func.hour(TrainingPlan.hora_inicio))
            .all()
        )
        return {(int(r.mid), int(r.h)): int(r.c) for r in rows}

    def demand_by_hour(self, fecha: date) -> dict[int, int]:
        """{hora: nº de planes} para la fecha."""
        rows = (
            self._db.query(
                func.hour(TrainingPlan.hora_inicio).label("h"),
                func.count(TrainingPlan.id).label("c"),
            )
            .filter(TrainingPlan.fecha == fecha, TrainingPlan.estado.in_(_ACTIVE_STATES))
            .group_by(func.hour(TrainingPlan.hora_inicio))
            .all()
        )
        return {int(r.h): int(r.c) for r in rows}

    def zone_distribution(self, fecha: date, hora: int | None = None) -> dict[MuscleZone, int]:
        """{zona: nº de planes que la tocan} para la fecha (opcionalmente una hora)."""
        query = (
            self._db.query(
                Machine.zona.label("z"),
                func.count(func.distinct(TrainingPlan.id)).label("c"),
            )
            .join(TrainingPlanMachine, TrainingPlanMachine.maquina_id == Machine.id)
            .join(TrainingPlan, TrainingPlan.id == TrainingPlanMachine.plan_id)
            .filter(TrainingPlan.fecha == fecha, TrainingPlan.estado.in_(_ACTIVE_STATES))
        )
        if hora is not None:
            query = query.filter(func.hour(TrainingPlan.hora_inicio) == hora)
        rows = query.group_by(Machine.zona).all()
        return {MuscleZone(r.z) if not isinstance(r.z, MuscleZone) else r.z: int(r.c) for r in rows}

    # ── Reservas de máquina (fuente adicional de intención) ────────────────────

    def _client_hours(self, rows) -> dict[int, set[int]]:
        out: dict[int, set[int]] = {}
        for h, cid in rows:
            out.setdefault(int(h), set()).add(int(cid))
        return out

    def plan_client_hours(self, fecha: date) -> dict[int, set[int]]:
        """{hora: {cliente_ids}} de los planes activos de la fecha."""
        rows = (
            self._db.query(func.hour(TrainingPlan.hora_inicio), TrainingPlan.cliente_id)
            .filter(TrainingPlan.fecha == fecha, TrainingPlan.estado.in_(_ACTIVE_STATES))
            .all()
        )
        return self._client_hours(rows)

    def reservation_client_hours(self, fecha: date) -> dict[int, set[int]]:
        """{hora: {cliente_ids}} de las reservas activas de la fecha."""
        rows = (
            self._db.query(func.hour(MachineReservation.hora_inicio), MachineReservation.cliente_id)
            .filter(
                MachineReservation.fecha == fecha,
                MachineReservation.estado == ReservationStatus.ACTIVA,
            )
            .all()
        )
        return self._client_hours(rows)

    def reservations_by_machine(self, fecha: date) -> dict[int, int]:
        """{maquina_id: nº de reservas activas} para la fecha."""
        rows = (
            self._db.query(
                MachineReservation.maquina_id.label("mid"),
                func.count(MachineReservation.id).label("c"),
            )
            .filter(
                MachineReservation.fecha == fecha,
                MachineReservation.estado == ReservationStatus.ACTIVA,
            )
            .group_by(MachineReservation.maquina_id)
            .all()
        )
        return {int(r.mid): int(r.c) for r in rows}

    def reservations_by_machine_hour(self, fecha: date) -> dict[tuple[int, int], int]:
        """{(maquina_id, hora): nº de reservas} — para saturación concurrente."""
        rows = (
            self._db.query(
                MachineReservation.maquina_id.label("mid"),
                func.hour(MachineReservation.hora_inicio).label("h"),
                func.count(MachineReservation.id).label("c"),
            )
            .filter(
                MachineReservation.fecha == fecha,
                MachineReservation.estado == ReservationStatus.ACTIVA,
            )
            .group_by(MachineReservation.maquina_id, func.hour(MachineReservation.hora_inicio))
            .all()
        )
        return {(int(r.mid), int(r.h)): int(r.c) for r in rows}

    def reservation_zone_counts(self, fecha: date) -> dict[MuscleZone, int]:
        """{zona: nº de clientes distintos con reserva} para la fecha."""
        rows = (
            self._db.query(
                Machine.zona.label("z"),
                func.count(func.distinct(MachineReservation.cliente_id)).label("c"),
            )
            .join(Machine, Machine.id == MachineReservation.maquina_id)
            .filter(
                MachineReservation.fecha == fecha,
                MachineReservation.estado == ReservationStatus.ACTIVA,
            )
            .group_by(Machine.zona)
            .all()
        )
        return {r.z if isinstance(r.z, MuscleZone) else MuscleZone(r.z): int(r.c) for r in rows}

    def historical_affluence_by_hour(self, dia: WeekDay) -> dict[int, float]:
        """
        {hora: promedio histórico de personas} para un día de la semana,
        desde el análisis de afluencia ('recomendaciones_horario').
        """
        rows = (
            self._db.query(ScheduleRecommendation.hora_inicio, ScheduleRecommendation.cantidad_promedio)
            .filter(ScheduleRecommendation.dia_semana == dia)
            .all()
        )
        return {r[0].hour: float(r[1]) for r in rows}

    # ── Índice de Demanda (histórico) ──────────────────────────────────────────

    def plan_count_per_machine(self) -> dict[int, int]:
        """{maquina_id: nº total de veces planificada} (todo el histórico)."""
        rows = (
            self._db.query(
                TrainingPlanMachine.maquina_id.label("mid"),
                func.count(TrainingPlanMachine.id).label("c"),
            )
            .join(TrainingPlan, TrainingPlan.id == TrainingPlanMachine.plan_id)
            .filter(TrainingPlan.estado.in_(_ACTIVE_STATES))
            .group_by(TrainingPlanMachine.maquina_id)
            .all()
        )
        return {int(r.mid): int(r.c) for r in rows}

    def real_usage_proxy_per_machine(self) -> dict[int, int]:
        """
        {maquina_id: nº de planes cuyo cliente SÍ asistió ese día}.
        Proxy de uso real hasta que se registre el uso efectivo de máquina.
        """
        rows = (
            self._db.query(
                TrainingPlanMachine.maquina_id.label("mid"),
                func.count(func.distinct(TrainingPlan.id)).label("c"),
            )
            .join(TrainingPlan, TrainingPlan.id == TrainingPlanMachine.plan_id)
            .join(
                Attendance,
                and_(
                    Attendance.cliente_id == TrainingPlan.cliente_id,
                    Attendance.fecha == TrainingPlan.fecha,
                    Attendance.estado == AttendanceStatus.INGRESO_APROBADO,
                ),
            )
            .group_by(TrainingPlanMachine.maquina_id)
            .all()
        )
        return {int(r.mid): int(r.c) for r in rows}

    # ── Precisión de predicción ────────────────────────────────────────────────

    def precision_counts(self, desde: date, hasta: date) -> tuple[int, int]:
        """(total_planes, planes_cumplidos) en el rango [desde, hasta]."""
        total = (
            self._db.query(func.count(TrainingPlan.id))
            .filter(
                TrainingPlan.fecha >= desde,
                TrainingPlan.fecha <= hasta,
                TrainingPlan.estado.in_(_ACTIVE_STATES),
            )
            .scalar()
        ) or 0

        cumplidos = (
            self._db.query(func.count(func.distinct(TrainingPlan.id)))
            .join(
                Attendance,
                and_(
                    Attendance.cliente_id == TrainingPlan.cliente_id,
                    Attendance.fecha == TrainingPlan.fecha,
                    Attendance.estado == AttendanceStatus.INGRESO_APROBADO,
                ),
            )
            .filter(
                TrainingPlan.fecha >= desde,
                TrainingPlan.fecha <= hasta,
                TrainingPlan.estado.in_(_ACTIVE_STATES),
            )
            .scalar()
        ) or 0

        return int(total), int(cumplidos)
