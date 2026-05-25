"""
Repositorio de Recomendaciones de Horario (Fase 10).
Responsabilidades:
  - LECTURA: consulta agregada del historial de 'asistencias' (solo lectura).
  - ESCRITURA: persiste/regenera los bloques en 'recomendaciones_horario'.

Las agregaciones de afluencia se calculan en BD para máxima eficiencia.
"""
from __future__ import annotations

from datetime import time

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.constants import (
    AffluenceLevel,
    AttendanceStatus,
    WeekDay,
)
from app.models.attendance import Attendance
from app.models.recommendation import ScheduleRecommendation


class RecommendationRepository:
    """Gestiona lectura de asistencias agregadas y persistencia de recomendaciones."""

    def __init__(self, db: Session) -> None:
        self._db = db

    # ══════════════════════════════════════════════════════════════════════════
    #  LECTURA — análisis del historial de asistencias
    # ══════════════════════════════════════════════════════════════════════════

    def get_attendance_aggregates(self) -> list[dict]:
        """
        Agrupa las asistencias APROBADAS por día de la semana y hora.

        Devuelve, por cada combinación (día, hora), el total de ingresos y
        el número de fechas distintas (para calcular el promedio por ocurrencia).

        Usa funciones nativas de MySQL:
          - DAYOFWEEK(fecha): 1=domingo ... 7=sábado
          - HOUR(hora): franja horaria 0-23

        Returns:
            Lista de dicts con: dow_mysql, hora_bloque, total_ingresos, dias_distintos.
        """
        rows = (
            self._db.query(
                func.dayofweek(Attendance.fecha).label("dow"),
                func.hour(Attendance.hora).label("hora_bloque"),
                func.count(Attendance.id).label("total_ingresos"),
                func.count(func.distinct(Attendance.fecha)).label("dias_distintos"),
            )
            .filter(Attendance.estado == AttendanceStatus.INGRESO_APROBADO)
            .group_by(
                func.dayofweek(Attendance.fecha),
                func.hour(Attendance.hora),
            )
            .all()
        )
        return [
            {
                "dow_mysql": int(r.dow),
                "hora_bloque": int(r.hora_bloque),
                "total_ingresos": int(r.total_ingresos),
                "dias_distintos": int(r.dias_distintos) or 1,
            }
            for r in rows
        ]

    def count_approved_attendances(self) -> int:
        """Cuenta el total de asistencias aprobadas en el historial."""
        return (
            self._db.query(func.count(Attendance.id))
            .filter(Attendance.estado == AttendanceStatus.INGRESO_APROBADO)
            .scalar()
        ) or 0

    # ══════════════════════════════════════════════════════════════════════════
    #  ESCRITURA — persistencia de recomendaciones
    # ══════════════════════════════════════════════════════════════════════════

    def delete_all(self) -> None:
        """
        Elimina todas las recomendaciones previas.
        Se invoca antes de regenerar para reflejar el historial más reciente.
        """
        self._db.query(ScheduleRecommendation).delete()
        self._db.flush()

    def bulk_create(self, blocks: list[dict]) -> None:
        """
        Inserta en lote los bloques de recomendación calculados.

        Args:
            blocks: Lista de dicts con las claves del modelo ScheduleRecommendation.
        """
        objects = [ScheduleRecommendation(**block) for block in blocks]
        self._db.add_all(objects)
        self._db.commit()

    # ══════════════════════════════════════════════════════════════════════════
    #  CONSULTAS sobre recomendaciones almacenadas
    # ══════════════════════════════════════════════════════════════════════════

    def get_by_id(self, rec_id: int) -> ScheduleRecommendation | None:
        return (
            self._db.query(ScheduleRecommendation)
            .filter(ScheduleRecommendation.id == rec_id)
            .first()
        )

    def list_all(self) -> list[ScheduleRecommendation]:
        """Lista todas las recomendaciones almacenadas."""
        return self._db.query(ScheduleRecommendation).all()

    def list_by_day(self, dia: WeekDay) -> list[ScheduleRecommendation]:
        """Lista las recomendaciones de un día ordenadas por hora de inicio."""
        return (
            self._db.query(ScheduleRecommendation)
            .filter(ScheduleRecommendation.dia_semana == dia)
            .order_by(ScheduleRecommendation.hora_inicio.asc())
            .all()
        )

    def list_filtered(
        self,
        page: int,
        per_page: int,
        dia_semana: WeekDay | None = None,
        nivel_afluencia: AffluenceLevel | None = None,
        es_recomendado: bool | None = None,
        evitar: bool | None = None,
        orden: str = "afluencia_asc",
    ) -> tuple[list[ScheduleRecommendation], int]:
        """Lista recomendaciones con filtros, ordenamiento y paginación."""
        query = self._db.query(ScheduleRecommendation)

        if dia_semana:
            query = query.filter(ScheduleRecommendation.dia_semana == dia_semana)
        if nivel_afluencia:
            query = query.filter(ScheduleRecommendation.nivel_afluencia == nivel_afluencia)
        if es_recomendado is not None:
            query = query.filter(ScheduleRecommendation.es_recomendado == es_recomendado)
        if evitar is not None:
            query = query.filter(ScheduleRecommendation.evitar == evitar)

        # Ordenamiento
        if orden == "afluencia_desc":
            query = query.order_by(ScheduleRecommendation.cantidad_promedio.desc())
        elif orden == "dia":
            query = query.order_by(
                ScheduleRecommendation.dia_semana.asc(),
                ScheduleRecommendation.hora_inicio.asc(),
            )
        else:  # afluencia_asc (default)
            query = query.order_by(ScheduleRecommendation.cantidad_promedio.asc())

        total = query.count()
        offset = (page - 1) * per_page
        items = query.offset(offset).limit(per_page).all()
        return items, total

    def list_by_recommendation_flag(
        self, recomendado: bool
    ) -> list[ScheduleRecommendation]:
        """
        Lista bloques recomendados (recomendado=True) o a evitar (recomendado=False
        consulta el flag 'evitar').
        """
        if recomendado:
            return (
                self._db.query(ScheduleRecommendation)
                .filter(ScheduleRecommendation.es_recomendado.is_(True))
                .order_by(ScheduleRecommendation.cantidad_promedio.asc())
                .all()
            )
        return (
            self._db.query(ScheduleRecommendation)
            .filter(ScheduleRecommendation.evitar.is_(True))
            .order_by(ScheduleRecommendation.cantidad_promedio.desc())
            .all()
        )
