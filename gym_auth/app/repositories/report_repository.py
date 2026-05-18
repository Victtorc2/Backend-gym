"""
Repositorio de Reportes.
Solo contiene consultas de lectura optimizadas con SQLAlchemy.
No modifica datos: es un repositorio 100% read-only.

Principios aplicados:
- Aggregations en BD (no en Python) para minimizar datos transferidos.
- Joins explícitos para evitar N+1 queries.
- Filtros opcionales componibles.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Session, joinedload

from app.core.constants import (
    AttendanceStatus,
    ClientStatus,
    MembershipStatus,
    PaymentMethod,
    PaymentStatus,
)
from app.models.attendance import Attendance
from app.models.client import Client
from app.models.membership import Membership
from app.models.payment import Payment


class ReportRepository:
    """
    Repositorio de solo lectura para el módulo de reportes.
    Todas las consultas están optimizadas para evitar carga innecesaria en memoria.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    # ══════════════════════════════════════════════════════════════════════════
    #  CLIENTES
    # ══════════════════════════════════════════════════════════════════════════

    def count_clients_by_status(self) -> dict[str, int]:
        """
        Retorna conteo de clientes agrupados por estado en una sola query.
        Evita múltiples round-trips a la BD.
        """
        rows = (
            self._db.query(Client.estado, func.count(Client.id).label("total"))
            .group_by(Client.estado)
            .all()
        )
        counts = {r.estado.value: r.total for r in rows}
        return {
            "activos": counts.get(ClientStatus.ACTIVO.value, 0),
            "inactivos": counts.get(ClientStatus.INACTIVO.value, 0),
        }

    def get_active_clients(self) -> list[Client]:
        """Lista todos los clientes activos con carga mínima de relaciones."""
        return (
            self._db.query(Client)
            .filter(Client.estado == ClientStatus.ACTIVO)
            .order_by(Client.created_at.desc())
            .all()
        )

    # ══════════════════════════════════════════════════════════════════════════
    #  DEUDA
    # ══════════════════════════════════════════════════════════════════════════

    def get_debt_summary_by_client(self) -> list[dict]:
        """
        Retorna resumen de deuda agrupado por cliente con una sola query agregada.

        Incluye: nombre, correo, total_deuda, pagos_pendientes,
                 pagos_vencidos, ultimo_pago.
        """
        rows = (
            self._db.query(
                Payment.cliente_id,
                (Client.nombres + " " + Client.apellidos).label("nombre_completo"),
                Client.correo,
                func.sum(Payment.saldo_pendiente).label("total_deuda"),
                func.sum(
                    case((Payment.estado == PaymentStatus.PENDIENTE, 1), else_=0)
                ).label("pagos_pendientes"),
                func.sum(
                    case((Payment.estado == PaymentStatus.VENCIDO, 1), else_=0)
                ).label("pagos_vencidos"),
                func.max(Payment.fecha_pago).label("ultimo_pago"),
            )
            .join(Client, Payment.cliente_id == Client.id)
            .filter(
                Payment.saldo_pendiente > Decimal("0"),
                Payment.estado.in_([PaymentStatus.PENDIENTE, PaymentStatus.VENCIDO]),
            )
            .group_by(
                Payment.cliente_id,
                Client.nombres,
                Client.apellidos,
                Client.correo,
            )
            .order_by(func.sum(Payment.saldo_pendiente).desc())
            .all()
        )

        return [
            {
                "cliente_id": r.cliente_id,
                "nombres": r.nombre_completo.split(" ")[0] if r.nombre_completo else "",
                "apellidos": " ".join(r.nombre_completo.split(" ")[1:]) if r.nombre_completo else "",
                "correo": r.correo,
                "total_deuda": r.total_deuda or Decimal("0"),
                "pagos_pendientes": r.pagos_pendientes or 0,
                "pagos_vencidos": r.pagos_vencidos or 0,
                "ultimo_pago": r.ultimo_pago,
            }
            for r in rows
        ]

    def get_total_debt_amount(self) -> Decimal:
        """Suma total de saldos pendientes activos en una query escalar."""
        result = (
            self._db.query(func.sum(Payment.saldo_pendiente))
            .filter(
                Payment.saldo_pendiente > Decimal("0"),
                Payment.estado.in_([PaymentStatus.PENDIENTE, PaymentStatus.VENCIDO]),
            )
            .scalar()
        )
        return result or Decimal("0")

    # ══════════════════════════════════════════════════════════════════════════
    #  MEMBRESÍAS
    # ══════════════════════════════════════════════════════════════════════════

    def get_memberships_with_client(
        self,
        solo_vigentes: bool = True,
    ) -> list[Membership]:
        """
        Lista membresías cargando el cliente asociado en el mismo query (joined load).

        Args:
            solo_vigentes: Si True, filtra solo las activas con fecha_fin >= hoy.
        """
        query = (
            self._db.query(Membership)
            .options(joinedload(Membership.cliente))
            .filter(Membership.estado == MembershipStatus.ACTIVA)
        )
        if solo_vigentes:
            query = query.filter(Membership.fecha_fin >= date.today())

        return query.order_by(Membership.fecha_fin.asc()).all()

    def count_memberships_by_status(self) -> dict[str, int]:
        """Conteo de membresías por estado en una query."""
        rows = (
            self._db.query(
                Membership.estado, func.count(Membership.id).label("total")
            )
            .group_by(Membership.estado)
            .all()
        )
        return {r.estado.value: r.total for r in rows}

    def count_memberships_by_type(self) -> dict[str, int]:
        """Conteo de membresías activas agrupadas por tipo."""
        rows = (
            self._db.query(
                Membership.tipo, func.count(Membership.id).label("total")
            )
            .filter(Membership.estado == MembershipStatus.ACTIVA)
            .group_by(Membership.tipo)
            .all()
        )
        return {r.tipo.value: r.total for r in rows}

    def get_projected_income(self) -> Decimal:
        """Suma de precios de membresías activas vigentes."""
        result = (
            self._db.query(func.sum(Membership.precio))
            .filter(
                Membership.estado == MembershipStatus.ACTIVA,
                Membership.fecha_fin >= date.today(),
            )
            .scalar()
        )
        return result or Decimal("0")

    # ══════════════════════════════════════════════════════════════════════════
    #  PAGOS
    # ══════════════════════════════════════════════════════════════════════════

    def get_payments_with_client(
        self,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
        cliente_id: int | None = None,
    ) -> list[Payment]:
        """
        Lista pagos con cliente precargado.
        Aplica filtros opcionales de fecha y cliente.
        """
        query = (
            self._db.query(Payment)
            .options(joinedload(Payment.cliente))
        )
        if fecha_desde:
            query = query.filter(Payment.fecha_pago >= fecha_desde)
        if fecha_hasta:
            query = query.filter(Payment.fecha_pago <= fecha_hasta)
        if cliente_id:
            query = query.filter(Payment.cliente_id == cliente_id)

        return query.order_by(Payment.fecha_pago.desc()).all()

    def get_payment_summary(
        self,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
    ) -> dict:
        """
        Calcula en BD todos los totales financieros del rango dado.
        Una sola query agregada para máxima eficiencia.
        """
        query = self._db.query(
            func.count(Payment.id).label("total_pagos"),
            func.sum(Payment.monto_pagado).label("total_ingresos"),
            func.sum(Payment.saldo_pendiente).label("total_deuda"),
            func.sum(
                case((Payment.estado == PaymentStatus.PAGADO, 1), else_=0)
            ).label("completados"),
            func.sum(
                case((Payment.estado == PaymentStatus.PENDIENTE, 1), else_=0)
            ).label("pendientes"),
            func.sum(
                case((Payment.estado == PaymentStatus.VENCIDO, 1), else_=0)
            ).label("vencidos"),
        )
        if fecha_desde:
            query = query.filter(Payment.fecha_pago >= fecha_desde)
        if fecha_hasta:
            query = query.filter(Payment.fecha_pago <= fecha_hasta)

        r = query.one()

        # Ingresos por método de pago en una segunda query compacta
        method_rows = (
            self._db.query(
                Payment.metodo_pago,
                func.sum(Payment.monto_pagado).label("total"),
            )
            .group_by(Payment.metodo_pago)
            .all()
        )
        por_metodo = {row.metodo_pago.value: (row.total or Decimal("0")) for row in method_rows}

        return {
            "total_pagos": r.total_pagos or 0,
            "total_ingresos": r.total_ingresos or Decimal("0"),
            "total_deuda_pendiente": r.total_deuda or Decimal("0"),
            "pagos_completados": r.completados or 0,
            "pagos_pendientes": r.pendientes or 0,
            "pagos_vencidos": r.vencidos or 0,
            "por_metodo": por_metodo,
        }

    # ══════════════════════════════════════════════════════════════════════════
    #  ASISTENCIAS
    # ══════════════════════════════════════════════════════════════════════════

    def get_attendances_with_client(
        self,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
        cliente_id: int | None = None,
    ) -> list[Attendance]:
        """Lista asistencias con cliente precargado y filtros opcionales."""
        query = (
            self._db.query(Attendance)
            .options(joinedload(Attendance.cliente))
        )
        if fecha_desde:
            query = query.filter(Attendance.fecha >= fecha_desde)
        if fecha_hasta:
            query = query.filter(Attendance.fecha <= fecha_hasta)
        if cliente_id:
            query = query.filter(Attendance.cliente_id == cliente_id)

        return query.order_by(Attendance.fecha.desc(), Attendance.hora.desc()).all()

    def get_attendance_counts(
        self,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
    ) -> dict[str, int]:
        """Conteo de asistencias aprobadas/denegadas en una query."""
        query = self._db.query(
            func.sum(
                case((Attendance.estado == AttendanceStatus.INGRESO_APROBADO, 1), else_=0)
            ).label("aprobados"),
            func.sum(
                case((Attendance.estado == AttendanceStatus.INGRESO_DENEGADO, 1), else_=0)
            ).label("denegados"),
            func.count(Attendance.id).label("total"),
        )
        if fecha_desde:
            query = query.filter(Attendance.fecha >= fecha_desde)
        if fecha_hasta:
            query = query.filter(Attendance.fecha <= fecha_hasta)

        r = query.one()
        return {
            "total": r.total or 0,
            "aprobados": r.aprobados or 0,
            "denegados": r.denegados or 0,
        }

    def get_frequency_by_client(
        self,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
    ) -> list[dict]:
        """
        Calcula frecuencia de asistencia agrupada por cliente.
        Todos los cálculos en BD con una sola query + join.
        """
        query = (
            self._db.query(
                Attendance.cliente_id,
                (Client.nombres + " " + Client.apellidos).label("nombre_cliente"),
                func.sum(
                    case((Attendance.estado == AttendanceStatus.INGRESO_APROBADO, 1), else_=0)
                ).label("total_aprobados"),
                func.sum(
                    case((Attendance.estado == AttendanceStatus.INGRESO_DENEGADO, 1), else_=0)
                ).label("total_denegados"),
                func.min(
                    case(
                        (Attendance.estado == AttendanceStatus.INGRESO_APROBADO, Attendance.fecha),
                        else_=None,
                    )
                ).label("primer_ingreso"),
                func.max(
                    case(
                        (Attendance.estado == AttendanceStatus.INGRESO_APROBADO, Attendance.fecha),
                        else_=None,
                    )
                ).label("ultimo_ingreso"),
            )
            .join(Client, Attendance.cliente_id == Client.id)
        )

        if fecha_desde:
            query = query.filter(Attendance.fecha >= fecha_desde)
        if fecha_hasta:
            query = query.filter(Attendance.fecha <= fecha_hasta)

        rows = (
            query
            .group_by(Attendance.cliente_id, Client.nombres, Client.apellidos)
            .order_by(func.sum(
                case((Attendance.estado == AttendanceStatus.INGRESO_APROBADO, 1), else_=0)
            ).desc())
            .all()
        )

        # Asistencias del mes actual por cliente (query adicional eficiente)
        today = date.today()
        mes_actual_rows = (
            self._db.query(
                Attendance.cliente_id,
                func.count(Attendance.id).label("count"),
            )
            .filter(
                Attendance.estado == AttendanceStatus.INGRESO_APROBADO,
                func.month(Attendance.fecha) == today.month,
                func.year(Attendance.fecha) == today.year,
            )
            .group_by(Attendance.cliente_id)
            .all()
        )
        mes_actual_map = {r.cliente_id: r.count for r in mes_actual_rows}

        return [
            {
                "cliente_id": r.cliente_id,
                "nombre_cliente": r.nombre_cliente,
                "total_aprobados": r.total_aprobados or 0,
                "total_denegados": r.total_denegados or 0,
                "primer_ingreso": r.primer_ingreso,
                "ultimo_ingreso": r.ultimo_ingreso,
                "asistencias_mes_actual": mes_actual_map.get(r.cliente_id, 0),
            }
            for r in rows
        ]
