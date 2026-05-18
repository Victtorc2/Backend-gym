"""
Repositorio de Ingresos Diarios.
Única capa autorizada para interactuar con la tabla 'ingresos_diarios'.
Registros append-only: nunca se eliminan para garantizar trazabilidad.
"""
from __future__ import annotations

import math
from datetime import date, time

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.constants import DailyEntryDenialReason, DailyEntryStatus
from app.models.daily_entry import DailyEntry


class DailyEntryRepository:
    """Gestiona todas las operaciones de persistencia del modelo DailyEntry."""

    def __init__(self, db: Session) -> None:
        self._db = db

    # ── Consultas individuales ─────────────────────────────────────────────────

    def get_by_id(self, entry_id: int) -> DailyEntry | None:
        return (
            self._db.query(DailyEntry)
            .options(joinedload(DailyEntry.cliente))
            .filter(DailyEntry.id == entry_id)
            .first()
        )

    def get_by_cliente(self, cliente_id: int) -> list[DailyEntry]:
        """Lista todos los ingresos de un cliente, del más reciente al más antiguo."""
        return (
            self._db.query(DailyEntry)
            .filter(DailyEntry.cliente_id == cliente_id)
            .order_by(DailyEntry.fecha.desc(), DailyEntry.hora.desc())
            .all()
        )

    def get_approved_today(self, cliente_id: int) -> DailyEntry | None:
        """
        Busca un ingreso aprobado de hoy para el cliente.
        Usado para prevenir ingresos duplicados en el mismo día.
        """
        return (
            self._db.query(DailyEntry)
            .filter(
                DailyEntry.cliente_id == cliente_id,
                DailyEntry.fecha == date.today(),
                DailyEntry.estado == DailyEntryStatus.APROBADO,
            )
            .first()
        )

    # ── Consultas paginadas ────────────────────────────────────────────────────

    def list_paginated(
        self,
        page: int,
        per_page: int,
        cliente_id: int | None = None,
        estado: DailyEntryStatus | None = None,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
    ) -> tuple[list[DailyEntry], int]:
        """Lista ingresos con filtros opcionales y paginación."""
        query = self._db.query(DailyEntry).options(joinedload(DailyEntry.cliente))

        if cliente_id:
            query = query.filter(DailyEntry.cliente_id == cliente_id)
        if estado:
            query = query.filter(DailyEntry.estado == estado)
        if fecha_desde:
            query = query.filter(DailyEntry.fecha >= fecha_desde)
        if fecha_hasta:
            query = query.filter(DailyEntry.fecha <= fecha_hasta)

        total = query.count()
        offset = (page - 1) * per_page
        items = (
            query
            .order_by(DailyEntry.fecha.desc(), DailyEntry.hora.desc())
            .offset(offset)
            .limit(per_page)
            .all()
        )
        return items, total

    # ── Estadísticas de frecuencia ─────────────────────────────────────────────

    def get_frequency_stats(self, cliente_id: int) -> dict:
        """
        Calcula estadísticas de frecuencia de ingresos aprobados para un cliente.

        Returns:
            Dict con total_ingresos_aprobados, total_ingresos_denegados,
            primer_ingreso, ultimo_ingreso, ingresos_mes_actual.
        """
        today = date.today()

        total_aprobados = (
            self._db.query(func.count(DailyEntry.id))
            .filter(
                DailyEntry.cliente_id == cliente_id,
                DailyEntry.estado == DailyEntryStatus.APROBADO,
            )
            .scalar() or 0
        )

        total_denegados = (
            self._db.query(func.count(DailyEntry.id))
            .filter(
                DailyEntry.cliente_id == cliente_id,
                DailyEntry.estado == DailyEntryStatus.DENEGADO,
            )
            .scalar() or 0
        )

        primer_ingreso = (
            self._db.query(func.min(DailyEntry.fecha))
            .filter(
                DailyEntry.cliente_id == cliente_id,
                DailyEntry.estado == DailyEntryStatus.APROBADO,
            )
            .scalar()
        )

        ultimo_ingreso = (
            self._db.query(func.max(DailyEntry.fecha))
            .filter(
                DailyEntry.cliente_id == cliente_id,
                DailyEntry.estado == DailyEntryStatus.APROBADO,
            )
            .scalar()
        )

        ingresos_mes_actual = (
            self._db.query(func.count(DailyEntry.id))
            .filter(
                DailyEntry.cliente_id == cliente_id,
                DailyEntry.estado == DailyEntryStatus.APROBADO,
                func.month(DailyEntry.fecha) == today.month,
                func.year(DailyEntry.fecha) == today.year,
            )
            .scalar() or 0
        )

        return {
            "total_ingresos_aprobados": total_aprobados,
            "total_ingresos_denegados": total_denegados,
            "primer_ingreso": primer_ingreso,
            "ultimo_ingreso": ultimo_ingreso,
            "ingresos_mes_actual": ingresos_mes_actual,
        }

    # ── Escritura ──────────────────────────────────────────────────────────────

    def create(
        self,
        *,
        cliente_id: int,
        fecha: date,
        hora: time,
        estado: DailyEntryStatus,
        motivo: DailyEntryDenialReason | None,
    ) -> DailyEntry:
        """Persiste un nuevo registro de ingreso (siempre append-only)."""
        entry = DailyEntry(
            cliente_id=cliente_id,
            fecha=fecha,
            hora=hora,
            estado=estado,
            motivo=motivo,
        )
        self._db.add(entry)
        self._db.commit()
        self._db.refresh(entry)
        return entry
