"""
Repositorio de Segmentación (Fase 7).
Única capa autorizada para consultar datos necesarios para calcular
la segmentación de clientes.

No contiene lógica de segmentación: solo extrae datos de las tablas
existentes (clientes, pagos, asistencias).

Principios:
  - Sin lógica de negocio (solo queries SQLAlchemy)
  - Consultas optimizadas con agregaciones en BD (no en Python)
  - Tipado fuerte en todos los retornos
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.constants import AttendanceStatus, ClientStatus, PaymentStatus
from app.models.attendance import Attendance
from app.models.client import Client
from app.models.payment import Payment


class SegmentationRepository:
    """
    Provee acceso a datos agregados para el cálculo de segmentación.
    Consume los modelos existentes: Client, Payment, Attendance.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    # ── Clientes ───────────────────────────────────────────────────────────────

    def get_client_by_id(self, client_id: int) -> Client | None:
        """Obtiene un cliente por ID."""
        return (
            self._db.query(Client)
            .filter(Client.id == client_id)
            .first()
        )

    def list_active_clients(self) -> list[Client]:
        """Lista todos los clientes con estado ACTIVO."""
        return (
            self._db.query(Client)
            .filter(Client.estado == ClientStatus.ACTIVO)
            .order_by(Client.apellidos.asc(), Client.nombres.asc())
            .all()
        )

    def list_all_clients(self) -> list[Client]:
        """Lista todos los clientes independientemente del estado."""
        return (
            self._db.query(Client)
            .order_by(Client.apellidos.asc(), Client.nombres.asc())
            .all()
        )

    # ── Asistencia ─────────────────────────────────────────────────────────────

    def count_approved_attendances_current_month(self, client_id: int) -> int:
        """
        Cuenta los ingresos APROBADOS del cliente en el mes y año actuales.
        Usa func.month / func.year para delegar el cálculo a MySQL.
        """
        today = date.today()
        return (
            self._db.query(func.count(Attendance.id))
            .filter(
                Attendance.cliente_id == client_id,
                Attendance.estado == AttendanceStatus.INGRESO_APROBADO,
                func.month(Attendance.fecha) == today.month,
                func.year(Attendance.fecha) == today.year,
            )
            .scalar() or 0
        )

    def get_last_approved_attendance_date(self, client_id: int) -> date | None:
        """
        Devuelve la fecha del último ingreso APROBADO del cliente.
        None si nunca tuvo un ingreso aprobado.
        """
        return (
            self._db.query(func.max(Attendance.fecha))
            .filter(
                Attendance.cliente_id == client_id,
                Attendance.estado == AttendanceStatus.INGRESO_APROBADO,
            )
            .scalar()
        )

    def bulk_count_approved_current_month(
        self,
    ) -> dict[int, int]:
        """
        Cuenta los ingresos aprobados del mes actual para TODOS los clientes
        en una sola query (para evitar N+1 en el listado).

        Returns:
            Dict {cliente_id: total_ingresos_mes_actual}
        """
        today = date.today()
        rows = (
            self._db.query(
                Attendance.cliente_id,
                func.count(Attendance.id).label("total"),
            )
            .filter(
                Attendance.estado == AttendanceStatus.INGRESO_APROBADO,
                func.month(Attendance.fecha) == today.month,
                func.year(Attendance.fecha) == today.year,
            )
            .group_by(Attendance.cliente_id)
            .all()
        )
        return {row.cliente_id: row.total for row in rows}

    def bulk_last_attendance_date(self) -> dict[int, date | None]:
        """
        Devuelve la última fecha de ingreso aprobado para TODOS los clientes
        en una sola query.

        Returns:
            Dict {cliente_id: ultima_fecha | None}
        """
        rows = (
            self._db.query(
                Attendance.cliente_id,
                func.max(Attendance.fecha).label("ultima"),
            )
            .filter(Attendance.estado == AttendanceStatus.INGRESO_APROBADO)
            .group_by(Attendance.cliente_id)
            .all()
        )
        return {row.cliente_id: row.ultima for row in rows}

    # ── Pagos ──────────────────────────────────────────────────────────────────

    def count_pending_payments(self, client_id: int) -> int:
        """
        Cuenta los pagos con estado PENDIENTE o VENCIDO del cliente.
        Cualquiera de los dos indica deuda activa.
        """
        return (
            self._db.query(func.count(Payment.id))
            .filter(
                Payment.cliente_id == client_id,
                Payment.estado.in_([PaymentStatus.PENDIENTE, PaymentStatus.VENCIDO]),
            )
            .scalar() or 0
        )

    def sum_pending_balance(self, client_id: int) -> Decimal:
        """
        Suma el saldo_pendiente de todos los pagos no completados del cliente.
        Devuelve Decimal(0) si no hay deuda.
        """
        result = (
            self._db.query(func.sum(Payment.saldo_pendiente))
            .filter(
                Payment.cliente_id == client_id,
                Payment.estado.in_([PaymentStatus.PENDIENTE, PaymentStatus.VENCIDO]),
            )
            .scalar()
        )
        return result or Decimal("0.00")

    def bulk_pending_payments(self) -> dict[int, tuple[int, Decimal]]:
        """
        Obtiene conteo y suma de saldo pendiente para TODOS los clientes
        en una sola query (evita N+1).

        Returns:
            Dict {cliente_id: (count_pendientes, suma_saldo_pendiente)}
        """
        rows = (
            self._db.query(
                Payment.cliente_id,
                func.count(Payment.id).label("count_pend"),
                func.sum(Payment.saldo_pendiente).label("suma_saldo"),
            )
            .filter(
                Payment.estado.in_([PaymentStatus.PENDIENTE, PaymentStatus.VENCIDO])
            )
            .group_by(Payment.cliente_id)
            .all()
        )
        return {
            row.cliente_id: (row.count_pend, row.suma_saldo or Decimal("0.00"))
            for row in rows
        }

    def sum_total_pending_balance_system(self) -> Decimal:
        """Suma total de saldos pendientes en todo el sistema (para el resumen)."""
        result = (
            self._db.query(func.sum(Payment.saldo_pendiente))
            .filter(
                Payment.estado.in_([PaymentStatus.PENDIENTE, PaymentStatus.VENCIDO])
            )
            .scalar()
        )
        return result or Decimal("0.00")
