"""
Repositorio de Recomendación Personalizada a Clientes.

Responsabilidades:
  - LECTURA de apoyo: candidatos (clientes) + su hora habitual (desde
    'asistencias') y los bloques de baja concurrencia (desde
    'recomendaciones_horario'). Solo lectura sobre esas tablas.
  - ESCRITURA: gestiona la tabla 'recomendaciones_cliente'.
"""
from __future__ import annotations

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.constants import (
    AttendanceStatus,
    ClientRecommendationStatus,
    ClientStatus,
    WeekDay,
)
from app.models.attendance import Attendance
from app.models.client import Client
from app.models.client_recommendation import ClientRecommendation
from app.models.recommendation import ScheduleRecommendation


class ClientRecommendationRepository:
    """Lectura de apoyo (asistencias/afluencia) y CRUD de recomendaciones a clientes."""

    def __init__(self, db: Session) -> None:
        self._db = db

    # ══════════════════════════════════════════════════════════════════════════
    #  CANDIDATOS — clientes y su comportamiento
    # ══════════════════════════════════════════════════════════════════════════

    def list_clients(
        self,
        page: int,
        per_page: int,
        buscar: str | None = None,
        estado: ClientStatus | None = None,
    ) -> tuple[list[Client], int]:
        """Lista clientes con búsqueda por nombre/apellido/DNI y paginación."""
        query = self._db.query(Client)

        if buscar:
            like = f"%{buscar.strip()}%"
            query = query.filter(
                or_(
                    Client.nombres.ilike(like),
                    Client.apellidos.ilike(like),
                    Client.dni.ilike(like),
                )
            )
        if estado is not None:
            query = query.filter(Client.estado == estado)

        total = query.count()
        items = (
            query.order_by(Client.apellidos.asc(), Client.nombres.asc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return items, total

    def get_habitual_hours(self, cliente_ids: list[int]) -> dict[int, int]:
        """
        Devuelve, por cliente, la hora (0-23) en la que registra más ingresos
        aprobados (su "hora habitual").

        Returns:
            Dict {cliente_id: hora_mas_frecuente}. Clientes sin asistencias
            aprobadas no aparecen en el dict.
        """
        if not cliente_ids:
            return {}

        rows = (
            self._db.query(
                Attendance.cliente_id.label("cid"),
                func.hour(Attendance.hora).label("h"),
                func.count(Attendance.id).label("c"),
            )
            .filter(
                Attendance.cliente_id.in_(cliente_ids),
                Attendance.estado == AttendanceStatus.INGRESO_APROBADO,
            )
            .group_by(Attendance.cliente_id, func.hour(Attendance.hora))
            .all()
        )

        best: dict[int, tuple[int, int]] = {}  # cid -> (hora, conteo)
        for r in rows:
            cid, h, c = int(r.cid), int(r.h), int(r.c)
            if cid not in best or c > best[cid][1]:
                best[cid] = (h, c)
        return {cid: hora for cid, (hora, _) in best.items()}

    def get_client_ids_with_active_recommendation(
        self, cliente_ids: list[int]
    ) -> set[int]:
        """Devuelve el subconjunto de clientes que ya tienen recomendación ACTIVA."""
        if not cliente_ids:
            return set()
        rows = (
            self._db.query(ClientRecommendation.cliente_id)
            .filter(
                ClientRecommendation.cliente_id.in_(cliente_ids),
                ClientRecommendation.estado == ClientRecommendationStatus.ACTIVA,
            )
            .all()
        )
        return {int(r.cliente_id) for r in rows}

    # ══════════════════════════════════════════════════════════════════════════
    #  BLOQUES DE AFLUENCIA — apoyo desde el análisis global
    # ══════════════════════════════════════════════════════════════════════════

    def list_low_affluence_blocks(
        self, limit: int | None = None
    ) -> list[ScheduleRecommendation]:
        """
        Lista bloques de baja concurrencia (es_recomendado=True), del más vacío
        al menos vacío. Si aún no hay bloques marcados como recomendados, cae a
        los bloques con menor promedio disponibles.
        """
        base = self._db.query(ScheduleRecommendation).order_by(
            ScheduleRecommendation.cantidad_promedio.asc(),
            ScheduleRecommendation.dia_semana.asc(),
            ScheduleRecommendation.hora_inicio.asc(),
        )

        recomendados = base.filter(
            ScheduleRecommendation.es_recomendado.is_(True)
        )
        query = recomendados if recomendados.count() > 0 else base

        if limit:
            query = query.limit(limit)
        return query.all()

    def get_block(
        self, dia_semana: WeekDay, hora_inicio
    ) -> ScheduleRecommendation | None:
        """Busca el bloque de afluencia que coincide con día y hora de inicio."""
        return (
            self._db.query(ScheduleRecommendation)
            .filter(
                ScheduleRecommendation.dia_semana == dia_semana,
                ScheduleRecommendation.hora_inicio == hora_inicio,
            )
            .first()
        )

    def get_blocks_by_hour(self, hora: int) -> list[ScheduleRecommendation]:
        """Lista los bloques (de cualquier día) que empiezan a una hora dada."""
        from datetime import time as _time

        return (
            self._db.query(ScheduleRecommendation)
            .filter(ScheduleRecommendation.hora_inicio == _time(hour=hora, minute=0))
            .all()
        )

    # ══════════════════════════════════════════════════════════════════════════
    #  CRUD — recomendaciones a clientes
    # ══════════════════════════════════════════════════════════════════════════

    def get_client(self, cliente_id: int) -> Client | None:
        return self._db.query(Client).filter(Client.id == cliente_id).first()

    def get_by_id(self, rec_id: int) -> ClientRecommendation | None:
        return (
            self._db.query(ClientRecommendation)
            .filter(ClientRecommendation.id == rec_id)
            .first()
        )

    def get_active_for_client(self, cliente_id: int) -> ClientRecommendation | None:
        return (
            self._db.query(ClientRecommendation)
            .filter(
                ClientRecommendation.cliente_id == cliente_id,
                ClientRecommendation.estado == ClientRecommendationStatus.ACTIVA,
            )
            .order_by(ClientRecommendation.created_at.desc())
            .first()
        )

    def discard_active_for_client(self, cliente_id: int) -> None:
        """Marca como DESCARTADA cualquier recomendación activa previa del cliente."""
        (
            self._db.query(ClientRecommendation)
            .filter(
                ClientRecommendation.cliente_id == cliente_id,
                ClientRecommendation.estado == ClientRecommendationStatus.ACTIVA,
            )
            .update(
                {ClientRecommendation.estado: ClientRecommendationStatus.DESCARTADA},
                synchronize_session=False,
            )
        )
        self._db.flush()

    def create(self, data: dict) -> ClientRecommendation:
        """Persiste una nueva recomendación (reemplazando la activa previa)."""
        self.discard_active_for_client(data["cliente_id"])
        obj = ClientRecommendation(**data)
        self._db.add(obj)
        self._db.commit()
        self._db.refresh(obj)
        return obj

    def list_filtered(
        self,
        page: int,
        per_page: int,
        cliente_id: int | None = None,
        estado: ClientRecommendationStatus | None = None,
    ) -> tuple[list[ClientRecommendation], int]:
        """Lista recomendaciones asignadas con filtros y paginación."""
        query = self._db.query(ClientRecommendation)

        if cliente_id is not None:
            query = query.filter(ClientRecommendation.cliente_id == cliente_id)
        if estado is not None:
            query = query.filter(ClientRecommendation.estado == estado)

        total = query.count()
        items = (
            query.order_by(ClientRecommendation.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return items, total

    def discard(self, rec: ClientRecommendation) -> None:
        """Marca una recomendación como DESCARTADA."""
        rec.estado = ClientRecommendationStatus.DESCARTADA
        self._db.commit()
