"""
Servicio de Tarjetas.
Gestiona consultas y cambios de estado de tarjetas físicas.
La emisión de tarjetas es responsabilidad de MembershipService.
"""
from __future__ import annotations

from app.core.exceptions import CardNotFoundException, ClientNotFoundException
from app.repositories.card_repository import CardRepository
from app.repositories.client_repository import ClientRepository
from app.schemas.card_schema import CardResponseSchema, CardStatusUpdateSchema


class CardService:
    """Gestiona operaciones de consulta y estado de tarjetas."""

    def __init__(
        self,
        card_repo: CardRepository,
        client_repo: ClientRepository,
    ) -> None:
        self._cards = card_repo
        self._clients = client_repo

    # ── Consultas ──────────────────────────────────────────────────────────────

    def get_card(self, card_id: int) -> CardResponseSchema:
        """
        Obtiene una tarjeta por ID.

        Raises:
            CardNotFoundException: Si el ID no existe.
        """
        card = self._cards.get_by_id(card_id)
        if card is None:
            raise CardNotFoundException()
        return CardResponseSchema.model_validate(card)

    def list_cards(self, estado=None) -> list[CardResponseSchema]:
        """Lista todas las tarjetas con filtro opcional de estado."""
        cards = self._cards.list_all(estado=estado)
        return [CardResponseSchema.model_validate(c) for c in cards]

    def get_by_cliente(self, cliente_id: int) -> list[CardResponseSchema]:
        """
        Lista todas las tarjetas de un cliente.

        Raises:
            ClientNotFoundException: Si el cliente no existe.
        """
        if self._clients.get_by_id(cliente_id) is None:
            raise ClientNotFoundException()
        cards = self._cards.get_by_cliente(cliente_id)
        return [CardResponseSchema.model_validate(c) for c in cards]

    # ── Estado ─────────────────────────────────────────────────────────────────

    def toggle_card_status(
        self, card_id: int, data: CardStatusUpdateSchema
    ) -> CardResponseSchema:
        """
        Activa o desactiva una tarjeta.

        Raises:
            CardNotFoundException: Si la tarjeta no existe.
        """
        card = self._cards.get_by_id(card_id)
        if card is None:
            raise CardNotFoundException()

        try:
            updated = self._cards.update_status(card, data.estado)
            self._cards.commit()
        except Exception:
            self._cards.rollback()
            raise

        return CardResponseSchema.model_validate(updated)
