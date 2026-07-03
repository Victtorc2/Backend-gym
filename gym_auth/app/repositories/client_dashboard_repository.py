"""
Repositorio del Portal de Cliente (Fase 10).
Consultas de solo lectura, siempre acotadas a un único cliente_id.

Reutiliza las tablas existentes (membresias, pagos, asistencias,
recomendaciones_horario) sin modificarlas. Todas las consultas reciben
el cliente_id ya resuelto desde el JWT por la capa de dependencias.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.constants import (
    ACTIVE_PLAN_STATES,
    AttendanceStatus,
    ClientRecommendationStatus,
    MembershipStatus,
    PaymentStatus,
    TrainingPlanStatus,
    WeekDay,
)
from app.models.attendance import Attendance
from app.models.client_recommendation import ClientRecommendation
from app.models.membership import Membership
from app.models.payment import Payment
from app.models.recommendation import ScheduleRecommendation
from app.models.training_plan import TrainingPlan

_ACTIVE_PLAN_STATES = [TrainingPlanStatus(s) for s in ACTIVE_PLAN_STATES]


class ClientDashboardRepository:
    """Consultas read-only del portal cliente, acotadas por cliente_id."""

    def __init__(self, db: Session) -> None:
        self._db = db

    # ── Membresía ──────────────────────────────────────────────────────────────

    def get_active_membership(self, cliente_id: int) -> Membership | None:
        """Retorna la membresía activa del cliente, si existe."""
        return (
            self._db.query(Membership)
            .filter(
                Membership.cliente_id == cliente_id,
                Membership.estado == MembershipStatus.ACTIVA,
            )
            .order_by(Membership.fecha_fin.desc())
            .first()
        )

    # ── Pagos ──────────────────────────────────────────────────────────────────

    def get_payments(self, cliente_id: int) -> list[Payment]:
        """Lista todos los pagos del cliente, del más reciente al más antiguo."""
        return (
            self._db.query(Payment)
            .filter(Payment.cliente_id == cliente_id)
            .order_by(Payment.fecha_pago.desc())
            .all()
        )

    def get_debt_aggregates(self, cliente_id: int) -> dict:
        """
        Calcula la deuda consolidada del cliente en una sola query agregada.

        Returns:
            Dict con total_deuda, pagos_pendientes, pagos_vencidos.
        """
        from sqlalchemy import case

        row = (
            self._db.query(
                func.coalesce(func.sum(Payment.saldo_pendiente), 0).label("total_deuda"),
                func.sum(
                    case((Payment.estado == PaymentStatus.PENDIENTE, 1), else_=0)
                ).label("pendientes"),
                func.sum(
                    case((Payment.estado == PaymentStatus.VENCIDO, 1), else_=0)
                ).label("vencidos"),
            )
            .filter(
                Payment.cliente_id == cliente_id,
                Payment.saldo_pendiente > 0,
                Payment.estado.in_([PaymentStatus.PENDIENTE, PaymentStatus.VENCIDO]),
            )
            .one()
        )
        return {
            "total_deuda": row.total_deuda or 0,
            "pagos_pendientes": row.pendientes or 0,
            "pagos_vencidos": row.vencidos or 0,
        }

    # ── Asistencia ─────────────────────────────────────────────────────────────

    def get_attendances(self, cliente_id: int) -> list[Attendance]:
        """Lista todas las asistencias del cliente, de la más reciente a la más antigua."""
        return (
            self._db.query(Attendance)
            .filter(Attendance.cliente_id == cliente_id)
            .order_by(Attendance.fecha.desc(), Attendance.hora.desc())
            .all()
        )

    def get_attendance_frequency(self, cliente_id: int) -> dict:
        """
        Calcula estadísticas de frecuencia del cliente en una query agregada.

        Returns:
            Dict con total_ingresos, asistencias_mes_actual,
            primer_ingreso, ultimo_ingreso.
        """
        today = date.today()

        total = (
            self._db.query(func.count(Attendance.id))
            .filter(
                Attendance.cliente_id == cliente_id,
                Attendance.estado == AttendanceStatus.INGRESO_APROBADO,
            )
            .scalar()
        ) or 0

        mes_actual = (
            self._db.query(func.count(Attendance.id))
            .filter(
                Attendance.cliente_id == cliente_id,
                Attendance.estado == AttendanceStatus.INGRESO_APROBADO,
                func.month(Attendance.fecha) == today.month,
                func.year(Attendance.fecha) == today.year,
            )
            .scalar()
        ) or 0

        primer = (
            self._db.query(func.min(Attendance.fecha))
            .filter(
                Attendance.cliente_id == cliente_id,
                Attendance.estado == AttendanceStatus.INGRESO_APROBADO,
            )
            .scalar()
        )

        ultimo = (
            self._db.query(func.max(Attendance.fecha))
            .filter(
                Attendance.cliente_id == cliente_id,
                Attendance.estado == AttendanceStatus.INGRESO_APROBADO,
            )
            .scalar()
        )

        return {
            "total_ingresos": total,
            "asistencias_mes_actual": mes_actual,
            "primer_ingreso": primer,
            "ultimo_ingreso": ultimo,
        }

    # ── Recomendaciones ────────────────────────────────────────────────────────

    def get_recommendations_by_day(self, dia: WeekDay) -> list[ScheduleRecommendation]:
        """Lista las recomendaciones de un día ordenadas por hora de inicio."""
        return (
            self._db.query(ScheduleRecommendation)
            .filter(ScheduleRecommendation.dia_semana == dia)
            .order_by(ScheduleRecommendation.hora_inicio.asc())
            .all()
        )

    def get_active_personal_recommendation(
        self, cliente_id: int
    ) -> ClientRecommendation | None:
        """Devuelve la recomendación personalizada ACTIVA asignada al cliente."""
        return (
            self._db.query(ClientRecommendation)
            .filter(
                ClientRecommendation.cliente_id == cliente_id,
                ClientRecommendation.estado == ClientRecommendationStatus.ACTIVA,
            )
            .order_by(ClientRecommendation.created_at.desc())
            .first()
        )

    # ── Afluencia declarada (planes de otros clientes) ─────────────────────────

    def count_declared_plans(self, fecha: date) -> int:
        """Total de clientes que declararon asistencia (plan activo) para la fecha."""
        return (
            self._db.query(func.count(TrainingPlan.id))
            .filter(TrainingPlan.fecha == fecha, TrainingPlan.estado.in_(_ACTIVE_PLAN_STATES))
            .scalar()
        ) or 0

    def declared_plans_by_hour(self, fecha: date) -> dict[int, int]:
        """{hora: nº de clientes que declararon esa hora} para la fecha."""
        rows = (
            self._db.query(
                func.hour(TrainingPlan.hora_inicio).label("h"),
                func.count(TrainingPlan.id).label("c"),
            )
            .filter(TrainingPlan.fecha == fecha, TrainingPlan.estado.in_(_ACTIVE_PLAN_STATES))
            .group_by(func.hour(TrainingPlan.hora_inicio))
            .all()
        )
        return {int(r.h): int(r.c) for r in rows}
