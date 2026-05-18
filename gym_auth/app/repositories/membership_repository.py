"""
Repositorio de Membresías.
Única capa autorizada para interactuar con la tabla 'membresias'.
Sin lógica de negocio: solo operaciones CRUD y consultas.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session, joinedload

from app.core.constants import MembershipStatus, MembershipType
from app.models.membership import Membership


class MembershipRepository:
    """Gestiona todas las operaciones de persistencia del modelo Membership."""

    def __init__(self, db: Session) -> None:
        self._db = db

    # ── Consultas ──────────────────────────────────────────────────────────────

    def get_by_id(self, membership_id: int) -> Membership | None:
        """Busca una membresía por ID, cargando el cliente asociado."""
        return (
            self._db.query(Membership)
            .options(joinedload(Membership.cliente))
            .filter(Membership.id == membership_id)
            .first()
        )

    def get_by_cliente(self, cliente_id: int) -> list[Membership]:
        """Lista todas las membresías de un cliente, ordenadas por fecha desc."""
        return (
            self._db.query(Membership)
            .filter(Membership.cliente_id == cliente_id)
            .order_by(Membership.created_at.desc())
            .all()
        )

    def get_active_by_cliente(self, cliente_id: int) -> Membership | None:
        """Retorna la membresía activa de un cliente, si existe."""
        return (
            self._db.query(Membership)
            .filter(
                Membership.cliente_id == cliente_id,
                Membership.estado == MembershipStatus.ACTIVA,
            )
            .first()
        )

    def list_all(
        self,
        estado: MembershipStatus | None = None,
        tipo: MembershipType | None = None,
    ) -> list[Membership]:
        """Lista todas las membresías con filtros opcionales."""
        query = self._db.query(Membership).options(joinedload(Membership.cliente))
        if estado:
            query = query.filter(Membership.estado == estado)
        if tipo:
            query = query.filter(Membership.tipo == tipo)
        return query.order_by(Membership.created_at.desc()).all()

    def find_expired(self) -> list[Membership]:
        """
        Retorna membresías que siguen marcadas como activas pero ya vencieron.
        Útil para tareas de sincronización de estado en background.
        """
        return (
            self._db.query(Membership)
            .filter(
                Membership.estado == MembershipStatus.ACTIVA,
                Membership.fecha_fin < date.today(),
            )
            .all()
        )

    # ── Escritura ──────────────────────────────────────────────────────────────

    def create(
        self,
        *,
        cliente_id: int,
        tipo: MembershipType,
        precio: Decimal,
        duracion_dias: int,
        fecha_inicio: date,
        fecha_fin: date,
        estado: MembershipStatus,
    ) -> Membership:
        """Persiste una nueva membresía. Usa flush para participar en transacciones."""
        membership = Membership(
            cliente_id=cliente_id,
            tipo=tipo,
            precio=precio,
            duracion_dias=duracion_dias,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            estado=estado,
        )
        self._db.add(membership)
        self._db.flush()
        self._db.refresh(membership)
        return membership

    def update(self, membership: Membership, updates: dict) -> Membership:
        """Aplica un dict de cambios sobre una membresía (partial update)."""
        for field, value in updates.items():
            setattr(membership, field, value)
        self._db.flush()
        self._db.refresh(membership)
        return membership

    def commit(self) -> None:
        """Confirma la transacción activa."""
        self._db.commit()

    def rollback(self) -> None:
        """Revierte la transacción activa."""
        self._db.rollback()
