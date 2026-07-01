"""
Repositorio de Comentarios / Sugerencias del Cliente.
"""
from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.constants import FeedbackStatus, FeedbackType
from app.models.feedback import Feedback


class FeedbackRepository:
    """Acceso a datos de los mensajes de clientes."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, data: dict) -> Feedback:
        obj = Feedback(**data)
        self._db.add(obj)
        self._db.commit()
        self._db.refresh(obj)
        return obj

    def get_by_id(self, feedback_id: int) -> Feedback | None:
        return self._db.query(Feedback).filter(Feedback.id == feedback_id).first()

    def list_for_client(self, cliente_id: int) -> list[Feedback]:
        return (
            self._db.query(Feedback)
            .filter(Feedback.cliente_id == cliente_id)
            .order_by(Feedback.created_at.desc())
            .all()
        )

    def list_filtered(
        self,
        page: int,
        per_page: int,
        tipo: FeedbackType | None = None,
        estado: FeedbackStatus | None = None,
        cliente_id: int | None = None,
    ) -> tuple[list[Feedback], int]:
        query = self._db.query(Feedback)
        if tipo is not None:
            query = query.filter(Feedback.tipo == tipo)
        if estado is not None:
            query = query.filter(Feedback.estado == estado)
        if cliente_id is not None:
            query = query.filter(Feedback.cliente_id == cliente_id)

        total = query.count()
        items = (
            query.order_by(Feedback.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return items, total

    def count_new(self) -> int:
        return (
            self._db.query(func.count(Feedback.id))
            .filter(Feedback.estado == FeedbackStatus.NUEVO)
            .scalar()
        ) or 0

    def update_status(self, feedback: Feedback, estado: FeedbackStatus) -> Feedback:
        feedback.estado = estado
        self._db.commit()
        self._db.refresh(feedback)
        return feedback

    def delete(self, feedback: Feedback) -> None:
        self._db.delete(feedback)
        self._db.commit()
