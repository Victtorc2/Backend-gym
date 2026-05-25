"""
Servicio de Recomendación de Horarios (Fase 10).
Motor de análisis de afluencia del gimnasio.

Proceso completo:
    1. Obtener historial de asistencia agregado.
    2. Agrupar por día y hora.
    3. Calcular promedio por bloque.
    4. Clasificar afluencia (BAJA/MEDIA/ALTA).
    5. Detectar horarios libres (recomendados) y horas pico (a evitar).
    6. Almacenar resultados.

Solo consume la tabla 'asistencias'; nunca la modifica.
"""
from __future__ import annotations

import math
from decimal import Decimal

from app.core.constants import AffluenceLevel, WeekDay
from app.core.exceptions import (
    InsufficientHistoryException,
    RecommendationNotFoundException,
)
from app.models.recommendation import ScheduleRecommendation
from app.repositories.recommendation_repository import RecommendationRepository
from app.schemas.recommendation_schema import (
    DayScheduleSchema,
    DayStatsSchema,
    GeneralStatsSchema,
    GenerationResultSchema,
    PaginatedRecommendationSchema,
    RecommendationFilterSchema,
    RecommendationResponseSchema,
)
from app.utils.recommendation_utils import (
    build_block_times,
    classify_affluence,
    format_block_label,
    format_hour_range,
    mysql_dow_to_weekday,
)


class RecommendationService:
    """Genera y consulta recomendaciones de horarios basadas en afluencia."""

    def __init__(self, repo: RecommendationRepository) -> None:
        self._repo = repo

    # ══════════════════════════════════════════════════════════════════════════
    #  GENERACIÓN
    # ══════════════════════════════════════════════════════════════════════════

    def generate_recommendations(self) -> GenerationResultSchema:
        """
        Ejecuta el análisis completo y regenera las recomendaciones.

        Raises:
            InsufficientHistoryException: Si no hay asistencias aprobadas.
        """
        total_asistencias = self._repo.count_approved_attendances()
        if total_asistencias == 0:
            raise InsufficientHistoryException()

        aggregates = self._repo.get_attendance_aggregates()
        if not aggregates:
            raise InsufficientHistoryException()

        # ── Construir bloques con promedio y clasificación ─────────────────────
        blocks: list[dict] = []
        for agg in aggregates:
            dia = mysql_dow_to_weekday(agg["dow_mysql"])
            if dia is None:
                continue  # domingo → excluido

            # Promedio = total de ingresos / número de fechas distintas observadas
            promedio = agg["total_ingresos"] / agg["dias_distintos"]
            nivel = classify_affluence(promedio)
            hora_inicio, hora_fin = build_block_times(agg["hora_bloque"])

            blocks.append({
                "dia_semana": dia,
                "hora_inicio": hora_inicio,
                "hora_fin": hora_fin,
                "cantidad_promedio": round(promedio, 2),
                "nivel_afluencia": nivel,
                "es_recomendado": nivel == AffluenceLevel.BAJA,
                "evitar": nivel == AffluenceLevel.ALTA,
            })

        if not blocks:
            raise InsufficientHistoryException(
                "No hay asistencias en días de operación (lunes a sábado)"
            )

        # ── Persistir: borrar previo + insertar nuevo ──────────────────────────
        self._repo.delete_all()
        self._repo.bulk_create(blocks)

        recomendados = sum(1 for b in blocks if b["es_recomendado"])
        a_evitar = sum(1 for b in blocks if b["evitar"])

        return GenerationResultSchema(
            bloques_analizados=len(blocks),
            bloques_recomendados=recomendados,
            bloques_a_evitar=a_evitar,
            total_asistencias_procesadas=total_asistencias,
            mensaje=f"Se analizaron {len(blocks)} bloques horarios correctamente",
        )

    # ══════════════════════════════════════════════════════════════════════════
    #  CONSULTAS
    # ══════════════════════════════════════════════════════════════════════════

    def list_recommendations(
        self, filters: RecommendationFilterSchema
    ) -> PaginatedRecommendationSchema:
        """Lista recomendaciones con filtros, orden y paginación."""
        items, total = self._repo.list_filtered(
            page=filters.page,
            per_page=filters.per_page,
            dia_semana=filters.dia_semana,
            nivel_afluencia=filters.nivel_afluencia,
            es_recomendado=filters.es_recomendado,
            evitar=filters.evitar,
            orden=filters.orden,
        )
        total_pages = math.ceil(total / filters.per_page) if total > 0 else 1
        return PaginatedRecommendationSchema(
            items=[RecommendationResponseSchema.model_validate(i) for i in items],
            total=total,
            page=filters.page,
            per_page=filters.per_page,
            total_pages=total_pages,
        )

    def get_day_schedule(self, dia: WeekDay) -> DayScheduleSchema:
        """
        Devuelve los bloques de un día con su horario recomendado y hora pico.

        Raises:
            RecommendationNotFoundException: Si no hay datos para ese día.
        """
        blocks = self._repo.list_by_day(dia)
        if not blocks:
            raise RecommendationNotFoundException(
                f"No hay recomendaciones generadas para {dia.value}"
            )

        # El bloque con menor promedio es el recomendado; el mayor, la hora pico
        recomendado = min(blocks, key=lambda b: b.cantidad_promedio)
        pico = max(blocks, key=lambda b: b.cantidad_promedio)

        return DayScheduleSchema(
            dia_semana=dia,
            bloques=[RecommendationResponseSchema.model_validate(b) for b in blocks],
            horario_recomendado=RecommendationResponseSchema.model_validate(recomendado),
            horario_pico=RecommendationResponseSchema.model_validate(pico),
        )

    def get_peak_hours(self) -> list[RecommendationResponseSchema]:
        """Lista los bloques marcados como hora pico (a evitar)."""
        blocks = self._repo.list_by_recommendation_flag(recomendado=False)
        if not blocks:
            raise RecommendationNotFoundException("No hay horas pico identificadas")
        return [RecommendationResponseSchema.model_validate(b) for b in blocks]

    def get_free_hours(self) -> list[RecommendationResponseSchema]:
        """Lista los bloques recomendados (afluencia baja)."""
        blocks = self._repo.list_by_recommendation_flag(recomendado=True)
        if not blocks:
            raise RecommendationNotFoundException("No hay horarios libres identificados")
        return [RecommendationResponseSchema.model_validate(b) for b in blocks]

    # ══════════════════════════════════════════════════════════════════════════
    #  ESTADÍSTICAS
    # ══════════════════════════════════════════════════════════════════════════

    def get_statistics(self) -> GeneralStatsSchema:
        """
        Genera estadísticas generales de afluencia a partir de las
        recomendaciones almacenadas.

        Raises:
            RecommendationNotFoundException: Si no se han generado recomendaciones.
        """
        all_blocks = self._repo.list_all()
        if not all_blocks:
            raise RecommendationNotFoundException(
                "No se han generado recomendaciones aún. Use POST /api/recomendaciones/generar"
            )

        total_semanal = sum(float(b.cantidad_promedio) for b in all_blocks)

        # Bloque más y menos concurrido a nivel global
        mas = max(all_blocks, key=lambda b: b.cantidad_promedio)
        menos = min(all_blocks, key=lambda b: b.cantidad_promedio)
        pico_global = float(mas.cantidad_promedio)

        # Estadísticas por día
        por_dia: list[DayStatsSchema] = []
        dias_presentes = {b.dia_semana for b in all_blocks}

        for dia in dias_presentes:
            bloques_dia = [b for b in all_blocks if b.dia_semana == dia]
            total_dia = sum(float(b.cantidad_promedio) for b in bloques_dia)
            promedio_hora = total_dia / len(bloques_dia) if bloques_dia else 0

            pico_dia = max(bloques_dia, key=lambda b: b.cantidad_promedio)
            libre_dia = min(bloques_dia, key=lambda b: b.cantidad_promedio)

            por_dia.append(DayStatsSchema(
                dia_semana=dia,
                promedio_por_hora=round(promedio_hora, 2),
                total_ingresos=int(total_dia),
                hora_pico=format_hour_range(pico_dia.hora_inicio, pico_dia.hora_fin),
                hora_libre=format_hour_range(libre_dia.hora_inicio, libre_dia.hora_fin),
            ))

        # Ordenar días estadísticos por el orden natural de la semana
        orden_dias = list(WeekDay)
        por_dia.sort(key=lambda d: orden_dias.index(d.dia_semana))

        promedio_por_dia = total_semanal / len(dias_presentes) if dias_presentes else 0
        promedio_por_hora = total_semanal / len(all_blocks) if all_blocks else 0

        # Porcentaje de ocupación: promedio global respecto al pico observado
        porcentaje = (
            round((promedio_por_hora / pico_global) * 100, 2)
            if pico_global > 0 else 0.0
        )

        return GeneralStatsSchema(
            total_semanal=int(total_semanal),
            promedio_por_dia=round(promedio_por_dia, 2),
            promedio_por_hora=round(promedio_por_hora, 2),
            horario_mas_concurrido=format_block_label(mas.dia_semana, mas.hora_inicio, mas.hora_fin),
            horario_menos_concurrido=format_block_label(menos.dia_semana, menos.hora_inicio, menos.hora_fin),
            porcentaje_ocupacion=porcentaje,
            por_dia=por_dia,
        )
