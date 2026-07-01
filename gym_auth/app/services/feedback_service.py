"""
Servicio de Comentarios / Sugerencias del Cliente.
El cliente envía mensajes y consulta los suyos; el administrador los visualiza
y gestiona su estado.
"""
from __future__ import annotations

import math

from app.core.constants import ClientStatus, FeedbackStatus, FeedbackType
from app.core.exceptions import (
    FeedbackAccessDeniedException,
    FeedbackNotFoundException,
    InactiveUserException,
)
from app.models.client import Client
from app.repositories.feedback_repository import FeedbackRepository
from app.schemas.feedback_schema import (
    FeedbackAdminItemSchema,
    FeedbackCreateSchema,
    FeedbackResponseSchema,
    PaginatedFeedbackSchema,
)


class FeedbackService:
    """Gestiona los mensajes enviados por los clientes."""

    def __init__(self, repo: FeedbackRepository) -> None:
        self._repo = repo

    # ── Cliente ─────────────────────────────────────────────────────────────────

    def create(self, client: Client, data: FeedbackCreateSchema) -> FeedbackResponseSchema:
        if client.estado != ClientStatus.ACTIVO:
            raise InactiveUserException()
        feedback = self._repo.create({
            "cliente_id": client.id,
            "tipo": data.tipo,
            "asunto": data.asunto,
            "mensaje": data.mensaje,
            "estado": FeedbackStatus.NUEVO,
        })
        return FeedbackResponseSchema.model_validate(feedback)

    def list_mine(self, client: Client) -> list[FeedbackResponseSchema]:
        return [
            FeedbackResponseSchema.model_validate(f)
            for f in self._repo.list_for_client(client.id)
        ]

    def delete_mine(self, client: Client, feedback_id: int) -> None:
        feedback = self._repo.get_by_id(feedback_id)
        if feedback is None:
            raise FeedbackNotFoundException()
        if feedback.cliente_id != client.id:
            raise FeedbackAccessDeniedException()
        self._repo.delete(feedback)

    # ── Administrador ───────────────────────────────────────────────────────────

    def list_admin(
        self,
        page: int,
        per_page: int,
        tipo: FeedbackType | None,
        estado: FeedbackStatus | None,
        cliente_id: int | None,
    ) -> PaginatedFeedbackSchema:
        items, total = self._repo.list_filtered(
            page=page, per_page=per_page, tipo=tipo, estado=estado, cliente_id=cliente_id
        )
        total_pages = math.ceil(total / per_page) if total > 0 else 1
        return PaginatedFeedbackSchema(
            items=[self._to_admin_item(f) for f in items],
            total=total,
            nuevos=self._repo.count_new(),
            page=page,
            per_page=per_page,
            total_pages=total_pages,
        )

    def get_admin(self, feedback_id: int, marcar_leido: bool = True) -> FeedbackAdminItemSchema:
        feedback = self._repo.get_by_id(feedback_id)
        if feedback is None:
            raise FeedbackNotFoundException()
        # Al abrirlo, si estaba nuevo se marca como leído automáticamente
        if marcar_leido and feedback.estado == FeedbackStatus.NUEVO:
            feedback = self._repo.update_status(feedback, FeedbackStatus.LEIDO)
        return self._to_admin_item(feedback)

    def update_status(self, feedback_id: int, estado: FeedbackStatus) -> FeedbackAdminItemSchema:
        feedback = self._repo.get_by_id(feedback_id)
        if feedback is None:
            raise FeedbackNotFoundException()
        feedback = self._repo.update_status(feedback, estado)
        return self._to_admin_item(feedback)

    def delete_admin(self, feedback_id: int) -> None:
        feedback = self._repo.get_by_id(feedback_id)
        if feedback is None:
            raise FeedbackNotFoundException()
        self._repo.delete(feedback)

    # ── Helpers ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _to_admin_item(feedback) -> FeedbackAdminItemSchema:
        cliente = feedback.cliente
        nombre = f"{cliente.nombres} {cliente.apellidos}" if cliente else "—"
        return FeedbackAdminItemSchema(
            id=feedback.id,
            cliente_id=feedback.cliente_id,
            cliente_nombre=nombre,
            tipo=feedback.tipo,
            asunto=feedback.asunto,
            mensaje=feedback.mensaje,
            estado=feedback.estado,
            created_at=feedback.created_at,
        )
