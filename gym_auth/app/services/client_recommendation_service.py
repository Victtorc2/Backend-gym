"""
Servicio de Recomendación Personalizada a Clientes.

Flujo asistido:
    1. El sistema calcula los bloques de BAJA concurrencia (horas con poca
       gente) a partir del análisis de afluencia ya existente.
    2. El admin ve a los clientes (con su hora habitual) y elige la mejor
       hora vacía para recomendársela.
    3. La recomendación queda asignada al cliente, que la ve en su panel.

Se apoya en 'recomendaciones_horario' y 'asistencias' (solo lectura) y
escribe únicamente en 'recomendaciones_cliente'.
"""
from __future__ import annotations

import math

from app.core.constants import (
    AffluenceLevel,
    ClientRecommendationOrigin,
    ClientRecommendationStatus,
    DEFAULT_SUGGESTED_BLOCKS,
)
from app.core.exceptions import (
    ClientNotFoundException,
    ClientRecommendationInvalidException,
    ClientRecommendationNotFoundException,
)
from app.repositories.client_recommendation_repository import (
    ClientRecommendationRepository,
)
from app.schemas.client_recommendation_schema import (
    CandidateFilterSchema,
    ClientCandidateSchema,
    ClientRecommendationResponseSchema,
    CreateClientRecommendationSchema,
    PaginatedCandidatesSchema,
    PaginatedClientRecommendationSchema,
    SuggestedBlockSchema,
)
from app.utils.recommendation_utils import format_hour_range

# Orden de severidad de afluencia (para comparar niveles)
_AFFLUENCE_ORDER = {
    AffluenceLevel.BAJA: 0,
    AffluenceLevel.MEDIA: 1,
    AffluenceLevel.ALTA: 2,
}


class ClientRecommendationService:
    """Genera candidatos/sugerencias y gestiona recomendaciones a clientes."""

    def __init__(self, repo: ClientRecommendationRepository) -> None:
        self._repo = repo

    # ══════════════════════════════════════════════════════════════════════════
    #  BLOQUES SUGERIDOS (horas con poca gente)
    # ══════════════════════════════════════════════════════════════════════════

    def get_suggested_blocks(
        self, limit: int = DEFAULT_SUGGESTED_BLOCKS
    ) -> list[SuggestedBlockSchema]:
        """Devuelve las horas de baja concurrencia, de la más vacía a la menos."""
        blocks = self._repo.list_low_affluence_blocks(limit=limit)
        return [self._to_suggested(b) for b in blocks]

    @staticmethod
    def _to_suggested(block) -> SuggestedBlockSchema:
        return SuggestedBlockSchema(
            dia_semana=block.dia_semana,
            hora_inicio=block.hora_inicio,
            hora_fin=block.hora_fin,
            horario=format_hour_range(block.hora_inicio, block.hora_fin),
            cantidad_promedio=block.cantidad_promedio,
            nivel_afluencia=block.nivel_afluencia,
        )

    # ══════════════════════════════════════════════════════════════════════════
    #  CANDIDATOS
    # ══════════════════════════════════════════════════════════════════════════

    def list_candidates(
        self, filters: CandidateFilterSchema
    ) -> PaginatedCandidatesSchema:
        """
        Lista clientes con su hora habitual y si vienen en hora pico, más la
        mejor sugerencia global de horario vacío.
        """
        clients, total = self._repo.list_clients(
            page=filters.page,
            per_page=filters.per_page,
            buscar=filters.buscar,
            estado=filters.estado,
        )

        cliente_ids = [c.id for c in clients]
        horas_habituales = self._repo.get_habitual_hours(cliente_ids)
        con_reco = self._repo.get_client_ids_with_active_recommendation(cliente_ids)

        # Cache de nivel por hora para no repetir consultas
        nivel_cache: dict[int, AffluenceLevel | None] = {}

        items: list[ClientCandidateSchema] = []
        for c in clients:
            hora = horas_habituales.get(c.id)
            nivel = None
            horario_txt = None
            es_pico = False

            if hora is not None:
                if hora not in nivel_cache:
                    nivel_cache[hora] = self._nivel_de_hora(hora)
                nivel = nivel_cache[hora]
                horario_txt = f"{hora:02d}:00-{(hora + 1) % 24:02d}:00"
                es_pico = nivel == AffluenceLevel.ALTA

            items.append(
                ClientCandidateSchema(
                    cliente_id=c.id,
                    nombres=c.nombres,
                    apellidos=c.apellidos,
                    dni=c.dni,
                    estado=c.estado,
                    hora_habitual=horario_txt,
                    nivel_hora_habitual=nivel,
                    viene_en_hora_pico=es_pico,
                    tiene_recomendacion_activa=c.id in con_reco,
                )
            )

        # Filtro opcional: solo quienes vienen en hora pico
        if filters.solo_hora_pico:
            items = [i for i in items if i.viene_en_hora_pico]

        # Mejor sugerencia global (el bloque más vacío disponible)
        sugeridos = self._repo.list_low_affluence_blocks(limit=1)
        mejor = self._to_suggested(sugeridos[0]) if sugeridos else None

        total_pages = math.ceil(total / filters.per_page) if total > 0 else 1
        return PaginatedCandidatesSchema(
            items=items,
            total=total,
            page=filters.page,
            per_page=filters.per_page,
            total_pages=total_pages,
            mejor_sugerencia=mejor,
        )

    def _nivel_de_hora(self, hora: int) -> AffluenceLevel | None:
        """
        Nivel de afluencia representativo de una hora (a través de los días):
        el más alto observado en esa franja. None si no hay análisis.
        """
        blocks = self._repo.get_blocks_by_hour(hora)
        if not blocks:
            return None
        return max(
            (b.nivel_afluencia for b in blocks),
            key=lambda n: _AFFLUENCE_ORDER[n],
        )

    # ══════════════════════════════════════════════════════════════════════════
    #  ASIGNACIÓN
    # ══════════════════════════════════════════════════════════════════════════

    def create_recommendation(
        self, admin_user_id: int, data: CreateClientRecommendationSchema
    ) -> ClientRecommendationResponseSchema:
        """
        Asigna (o reemplaza) la recomendación de horario de un cliente.

        Si el bloque coincide con el análisis de afluencia, se toma su nivel y
        promedio como snapshot y el origen es ASISTIDA; en caso contrario el
        origen es MANUAL.

        Raises:
            ClientNotFoundException: Si el cliente no existe.
            ClientRecommendationInvalidException: Si el horario es inválido.
        """
        if data.hora_inicio >= data.hora_fin:
            raise ClientRecommendationInvalidException(
                "La hora de inicio debe ser anterior a la hora de fin"
            )

        cliente = self._repo.get_client(data.cliente_id)
        if cliente is None:
            raise ClientNotFoundException()

        # Snapshot desde el análisis de afluencia, si el bloque existe
        block = self._repo.get_block(data.dia_semana, data.hora_inicio)
        if block is not None:
            promedio = block.cantidad_promedio
            nivel = block.nivel_afluencia
            origen = (
                ClientRecommendationOrigin.ASISTIDA
                if block.es_recomendado
                else ClientRecommendationOrigin.MANUAL
            )
        else:
            promedio = None
            nivel = None
            origen = ClientRecommendationOrigin.MANUAL

        rec = self._repo.create({
            "cliente_id": data.cliente_id,
            "dia_semana": data.dia_semana,
            "hora_inicio": data.hora_inicio,
            "hora_fin": data.hora_fin,
            "cantidad_promedio_estimada": promedio,
            "nivel_afluencia": nivel,
            "mensaje": data.mensaje,
            "origen": origen,
            "estado": ClientRecommendationStatus.ACTIVA,
            "creado_por": admin_user_id,
        })

        return self._to_response(rec, cliente_nombre=f"{cliente.nombres} {cliente.apellidos}")

    # ══════════════════════════════════════════════════════════════════════════
    #  CONSULTA / GESTIÓN
    # ══════════════════════════════════════════════════════════════════════════

    def list_recommendations(
        self,
        page: int,
        per_page: int,
        cliente_id: int | None = None,
        estado: ClientRecommendationStatus | None = None,
    ) -> PaginatedClientRecommendationSchema:
        """Lista las recomendaciones asignadas con filtros y paginación."""
        items, total = self._repo.list_filtered(
            page=page, per_page=per_page, cliente_id=cliente_id, estado=estado
        )
        total_pages = math.ceil(total / per_page) if total > 0 else 1
        return PaginatedClientRecommendationSchema(
            items=[self._to_response(r) for r in items],
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
        )

    def discard_recommendation(self, rec_id: int) -> None:
        """Da de baja (descarta) una recomendación asignada."""
        rec = self._repo.get_by_id(rec_id)
        if rec is None:
            raise ClientRecommendationNotFoundException()
        self._repo.discard(rec)

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _to_response(
        rec, cliente_nombre: str | None = None
    ) -> ClientRecommendationResponseSchema:
        if cliente_nombre is None:
            cliente = rec.cliente
            cliente_nombre = (
                f"{cliente.nombres} {cliente.apellidos}" if cliente else "—"
            )
        return ClientRecommendationResponseSchema(
            id=rec.id,
            cliente_id=rec.cliente_id,
            cliente_nombre=cliente_nombre,
            dia_semana=rec.dia_semana,
            horario=format_hour_range(rec.hora_inicio, rec.hora_fin),
            cantidad_promedio_estimada=rec.cantidad_promedio_estimada,
            nivel_afluencia=rec.nivel_afluencia,
            mensaje=rec.mensaje,
            origen=rec.origen,
            estado=rec.estado,
            created_at=rec.created_at,
        )
