"""
Repositorio de Tarjetas.
Única capa autorizada para interactuar con la tabla 'tarjetas'.
Sin lógica de negocio: solo operaciones CRUD y consultas.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session, joinedload

from app.core.constants import CardStatus
from app.models.card import Card


class CardRepository:
    """Gestiona todas las operaciones de persistencia del modelo Card."""

    def __init__(self, db: Session) -> None:
        self._db = db

    # ── Consultas ──────────────────────────────────────────────────────────────

    def get_by_id(self, card_id: int) -> Card | None:
        """Busca una tarjeta por ID, cargando el cliente asociado."""
        return (
            self._db.query(Card)
            .options(joinedload(Card.cliente))
            .filter(Card.id == card_id)
            .first()
        )

    def get_by_codigo(self, codigo: str) -> Card | None:
        """Busca una tarjeta por su código único."""
        return self._db.query(Card).filter(Card.codigo == codigo).first()

    def get_by_cliente(self, cliente_id: int) -> list[Card]:
        """Lista todas las tarjetas de un cliente."""
        return (
            self._db.query(Card)
            .filter(Card.cliente_id == cliente_id)
            .order_by(Card.created_at.desc())
            .all()
        )

    def get_active_by_cliente(self, cliente_id: int) -> Card | None:
        """Retorna la tarjeta activa de un cliente, si existe."""
        return (
            self._db.query(Card)
            .filter(
                Card.cliente_id == cliente_id,
                Card.estado == CardStatus.ACTIVA,
            )
            .first()
        )

    def list_all(self, estado: CardStatus | None = None) -> list[Card]:
        """Lista todas las tarjetas con filtro opcional de estado."""
        query = self._db.query(Card).options(joinedload(Card.cliente))
        if estado:
            query = query.filter(Card.estado == estado)
        return query.order_by(Card.created_at.desc()).all()

    def count_total(self) -> int:
        """Cuenta el total de tarjetas (para generar el siguiente código secuencial)."""
        return self._db.query(Card).count()

    def codigo_exists(self, codigo: str) -> bool:
        """Verifica si un código de tarjeta ya está en uso."""
        return self._db.query(Card).filter(Card.codigo == codigo).count() > 0

    # ── Escritura ──────────────────────────────────────────────────────────────

    def create(
        self,
        *,
        codigo: str,
        cliente_id: int,
        fecha_emision: date,
        estado: CardStatus,
    ) -> Card:
        """Persiste una nueva tarjeta. Usa flush para participar en transacciones."""
        card = Card(
            codigo=codigo,
            cliente_id=cliente_id,
            fecha_emision=fecha_emision,
            estado=estado,
        )
        self._db.add(card)
        self._db.flush()
        self._db.refresh(card)
        return card

    def update_status(self, card: Card, estado: CardStatus) -> Card:
        """Actualiza el estado de una tarjeta existente."""
        card.estado = estado
        self._db.flush()
        self._db.refresh(card)
        return card

    def commit(self) -> None:
        """Confirma la transacción activa."""
        self._db.commit()

    def rollback(self) -> None:
        """Revierte la transacción activa."""
        self._db.rollback()
