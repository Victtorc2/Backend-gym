"""
Servicio de Membresías.
Orquesta toda la lógica de negocio del módulo:
  - Registro y cálculo automático de fechas/vigencia.
  - Validaciones de cliente activo y duplicidad.
  - Emisión automática de tarjeta al registrar membresía mensual/anual.
  - Actualización y consulta con estado de vigencia en tiempo real.
  - Sincronización de estados vencidos.
"""
from __future__ import annotations

from datetime import date

from app.core.constants import (
    CARD_ELIGIBLE_TYPES,
    CardStatus,
    ClientStatus,
    MembershipStatus,
    MembershipType,
)
from app.core.exceptions import (
    CardAlreadyExistsException,
    ClientNotFoundException,
    MembershipInvalidException,
    MembershipNotFoundException,
)
from app.models.membership import Membership
from app.repositories.card_repository import CardRepository
from app.repositories.client_repository import ClientRepository
from app.repositories.membership_repository import MembershipRepository
from app.schemas.membership_schema import (
    MembershipCreateSchema,
    MembershipResponseSchema,
    MembershipUpdateSchema,
    MembershipWithStatusSchema,
)
from app.schemas.card_schema import CardResponseSchema
from app.utils.membership_utils import (
    compute_membership_status,
    generate_card_code,
    is_card_eligible,
    resolve_membership_dates,
)


class MembershipService:
    """Gestiona todas las operaciones de negocio del módulo de membresías."""

    def __init__(
        self,
        membership_repo: MembershipRepository,
        card_repo: CardRepository,
        client_repo: ClientRepository,
    ) -> None:
        self._memberships = membership_repo
        self._cards = card_repo
        self._clients = client_repo

    # ── Registro ───────────────────────────────────────────────────────────────

    def register_membership(
        self, data: MembershipCreateSchema
    ) -> dict:
        """
        Registra una membresía y emite tarjeta si corresponde.

        Flujo:
            1. Validar que el cliente exista y esté activo.
            2. Validar que no tenga una membresía activa del mismo tipo.
            3. Calcular fecha_inicio, fecha_fin y duracion_dias automáticamente.
            4. Persistir la membresía.
            5. Si el tipo es mensual o anual → emitir tarjeta automáticamente.
            6. Confirmar transacción única.

        Returns:
            Dict con la membresía y, opcionalmente, la tarjeta emitida.

        Raises:
            ClientNotFoundException: Si el cliente no existe.
            MembershipInvalidException: Si el cliente está inactivo o tiene membresía activa.
        """
        client = self._clients.get_by_id(data.cliente_id)
        if client is None:
            raise ClientNotFoundException()

        if client.estado != ClientStatus.ACTIVO:
            raise MembershipInvalidException(
                "No se puede asignar membresía a un cliente inactivo"
            )

        # Validar que no tenga ya una membresía activa vigente
        existing = self._memberships.get_active_by_cliente(data.cliente_id)
        if existing and self._is_still_active(existing):
            raise MembershipInvalidException(
                f"El cliente ya tiene una membresía {existing.tipo.value} activa "
                f"hasta el {existing.fecha_fin}"
            )

        # Calcular fechas automáticamente (regla de negocio central)
        fecha_inicio, fecha_fin, duracion_dias = resolve_membership_dates(data.tipo)

        try:
            # Persistir membresía
            membership = self._memberships.create(
                cliente_id=data.cliente_id,
                tipo=data.tipo,
                precio=data.precio,
                duracion_dias=duracion_dias,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                estado=MembershipStatus.ACTIVA,
            )

            # Emitir tarjeta automáticamente si el tipo es elegible
            card = None
            if is_card_eligible(data.tipo):
                card = self._emit_card_for_client(data.cliente_id)

            self._memberships.commit()

        except (CardAlreadyExistsException, MembershipInvalidException):
            self._memberships.rollback()
            raise
        except Exception:
            self._memberships.rollback()
            raise

        result: dict = {
            "membresia": MembershipResponseSchema.model_validate(membership).model_dump()
        }
        if card:
            result["tarjeta"] = CardResponseSchema.model_validate(card).model_dump()

        return result

    # ── Consultas ──────────────────────────────────────────────────────────────

    def get_membership(self, membership_id: int) -> MembershipWithStatusSchema:
        """
        Obtiene una membresía por ID con estado de vigencia recalculado.

        Raises:
            MembershipNotFoundException: Si el ID no existe.
        """
        membership = self._memberships.get_by_id(membership_id)
        if membership is None:
            raise MembershipNotFoundException()
        return self._to_status_schema(membership)

    def list_memberships(
        self,
        estado: MembershipStatus | None = None,
        tipo: MembershipType | None = None,
    ) -> list[MembershipWithStatusSchema]:
        """Lista todas las membresías con estado recalculado en tiempo real."""
        memberships = self._memberships.list_all(estado=estado, tipo=tipo)
        return [self._to_status_schema(m) for m in memberships]

    def get_by_cliente(self, cliente_id: int) -> list[MembershipWithStatusSchema]:
        """
        Lista todas las membresías de un cliente con vigencia recalculada.

        Raises:
            ClientNotFoundException: Si el cliente no existe.
        """
        if self._clients.get_by_id(cliente_id) is None:
            raise ClientNotFoundException()
        memberships = self._memberships.get_by_cliente(cliente_id)
        return [self._to_status_schema(m) for m in memberships]

    # ── Actualización ──────────────────────────────────────────────────────────

    def update_membership(
        self, membership_id: int, data: MembershipUpdateSchema
    ) -> MembershipResponseSchema:
        """
        Actualiza precio y/o estado de una membresía (partial update).

        Raises:
            MembershipNotFoundException: Si la membresía no existe.
        """
        membership = self._memberships.get_by_id(membership_id)
        if membership is None:
            raise MembershipNotFoundException()

        updates = data.model_dump(exclude_none=True)
        if not updates:
            return MembershipResponseSchema.model_validate(membership)

        try:
            updated = self._memberships.update(membership, updates)
            self._memberships.commit()
        except Exception:
            self._memberships.rollback()
            raise

        return MembershipResponseSchema.model_validate(updated)

    def sync_expired_statuses(self) -> int:
        """
        Actualiza a 'vencida' todas las membresías activas ya caducadas.
        Pensado para ejecutarse como tarea periódica (cron/scheduler).

        Returns:
            Número de membresías actualizadas.
        """
        expired = self._memberships.find_expired()
        for m in expired:
            self._memberships.update(m, {"estado": MembershipStatus.VENCIDA})
        if expired:
            self._memberships.commit()
        return len(expired)

    # ── Helpers privados ───────────────────────────────────────────────────────

    def _emit_card_for_client(self, cliente_id: int):
        """
        Emite una tarjeta activa para el cliente si no tiene una ya.

        Si ya tiene tarjeta activa, no emite una nueva (idempotente).
        Usa flush para participar en la transacción del registro de membresía.

        Returns:
            Card recién creada, o None si ya tenía tarjeta activa.
        """
        existing_card = self._cards.get_active_by_cliente(cliente_id)
        if existing_card:
            return existing_card  # ya tiene tarjeta, no duplicar

        # Generar código único con reintentos ante colisión
        sequence = self._cards.count_total() + 1
        codigo = generate_card_code(sequence)
        while self._cards.codigo_exists(codigo):
            sequence += 1
            codigo = generate_card_code(sequence)

        return self._cards.create(
            codigo=codigo,
            cliente_id=cliente_id,
            fecha_emision=date.today(),
            estado=CardStatus.ACTIVA,
        )

    @staticmethod
    def _is_still_active(membership: Membership) -> bool:
        """Verifica si una membresía sigue vigente según la fecha de hoy."""
        return date.today() <= membership.fecha_fin

    @staticmethod
    def _to_status_schema(membership: Membership) -> MembershipWithStatusSchema:
        """Construye el schema de respuesta con vigencia recalculada en tiempo real."""
        data = MembershipResponseSchema.model_validate(membership).model_dump()
        data["vigente"] = date.today() <= membership.fecha_fin
        return MembershipWithStatusSchema(**data)
