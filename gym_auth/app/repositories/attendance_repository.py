"""
Repositorio de Asistencias.
Única capa autorizada para interactuar con la tabla 'asistencias'.
Registros inmutables (append-only): nunca se eliminan ni sobrescriben.
"""
from __future__ import annotations

import math
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.constants import AttendanceStatus, DenialReason
from app.models.attendance import Attendance


class AttendanceRepository:
    """Gestiona todas las operaciones de persistencia del modelo Attendance."""

    def __init__(self, db: Session) -> None:
        self._db = db

    # ── Consultas individuales ─────────────────────────────────────────────────

    def get_by_id(self, attendance_id: int) -> Attendance | None:
        """Busca un registro de asistencia por ID, cargando relaciones."""
        return (
            self._db.query(Attendance)
            .options(
                joinedload(Attendance.cliente),
                joinedload(Attendance.tarjeta),
            )
            .filter(Attendance.id == attendance_id)
            .first()
        )

    def get_by_cliente(self, cliente_id: int) -> list[Attendance]:
        """Lista todas las asistencias de un cliente, del más reciente al más antiguo."""
        return (
            self._db.query(Attendance)
            .filter(Attendance.cliente_id == cliente_id)
            .order_by(Attendance.fecha.desc(), Attendance.hora.desc())
            .all()
        )

    # ── Consultas paginadas ────────────────────────────────────────────────────

    def list_paginated(
        self,
        page: int,
        per_page: int,
        cliente_id: int | None = None,
        estado: AttendanceStatus | None = None,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
    ) -> tuple[list[Attendance], int]:
        """
        Lista asistencias con filtros opcionales y paginación.

        Returns:
            Tupla (lista de la página, total de registros).
        """
        query = self._db.query(Attendance).options(
            joinedload(Attendance.cliente),
            joinedload(Attendance.tarjeta),
        )

        if cliente_id:
            query = query.filter(Attendance.cliente_id == cliente_id)
        if estado:
            query = query.filter(Attendance.estado == estado)
        if fecha_desde:
            query = query.filter(Attendance.fecha >= fecha_desde)
        if fecha_hasta:
            query = query.filter(Attendance.fecha <= fecha_hasta)

        total = query.count()
        offset = (page - 1) * per_page
        items = (
            query
            .order_by(Attendance.fecha.desc(), Attendance.hora.desc())
            .offset(offset)
            .limit(per_page)
            .all()
        )
        return items, total

    # ── Consultas agregadas (frecuencia) ───────────────────────────────────────

    def get_frequency_stats(self, cliente_id: int) -> dict:
        """
        Calcula estadísticas de frecuencia para un cliente.

        Returns:
            Dict con total_ingresos, total_denegados, primer_ingreso,
            ultimo_ingreso y dias_del_mes_actual.
        """
        today = date.today()

        total_aprobados = (
            self._db.query(func.count(Attendance.id))
            .filter(
                Attendance.cliente_id == cliente_id,
                Attendance.estado == AttendanceStatus.INGRESO_APROBADO,
            )
            .scalar() or 0
        )

        total_denegados = (
            self._db.query(func.count(Attendance.id))
            .filter(
                Attendance.cliente_id == cliente_id,
                Attendance.estado == AttendanceStatus.INGRESO_DENEGADO,
            )
            .scalar() or 0
        )

        primer_ingreso = (
            self._db.query(func.min(Attendance.fecha))
            .filter(
                Attendance.cliente_id == cliente_id,
                Attendance.estado == AttendanceStatus.INGRESO_APROBADO,
            )
            .scalar()
        )

        ultimo_ingreso = (
            self._db.query(func.max(Attendance.fecha))
            .filter(
                Attendance.cliente_id == cliente_id,
                Attendance.estado == AttendanceStatus.INGRESO_APROBADO,
            )
            .scalar()
        )

        # Ingresos aprobados en el mes y año actuales
        dias_mes_actual = (
            self._db.query(func.count(Attendance.id))
            .filter(
                Attendance.cliente_id == cliente_id,
                Attendance.estado == AttendanceStatus.INGRESO_APROBADO,
                func.month(Attendance.fecha) == today.month,
                func.year(Attendance.fecha) == today.year,
            )
            .scalar() or 0
        )

        return {
            "total_ingresos": total_aprobados,
            "total_denegados": total_denegados,
            "primer_ingreso": primer_ingreso,
            "ultimo_ingreso": ultimo_ingreso,
            "dias_del_mes_actual": dias_mes_actual,
        }

    # ── Escritura ──────────────────────────────────────────────────────────────

    def create(
        self,
        *,
        cliente_id: int,
        tarjeta_id: int,
        fecha: date,
        hora,
        estado: AttendanceStatus,
        motivo_denegacion: DenialReason | None,
    ) -> Attendance:
        """Persiste un nuevo registro de asistencia (siempre append-only)."""
        attendance = Attendance(
            cliente_id=cliente_id,
            tarjeta_id=tarjeta_id,
            fecha=fecha,
            hora=hora,
            estado=estado,
            motivo_denegacion=motivo_denegacion,
        )
        self._db.add(attendance)
        self._db.commit()
        self._db.refresh(attendance)
        return attendance

    def commit(self) -> None:
        self._db.commit()

    def rollback(self) -> None:
        self._db.rollback()
