"""
Repositorio de Pagos.
Única capa autorizada para interactuar con la tabla 'pagos'.
Sin lógica de negocio: solo persistencia y consultas.
Los pagos nunca se eliminan (append-only / trazabilidad).
"""
from __future__ import annotations

import math
from datetime import date
from decimal import Decimal

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload

from app.core.constants import PaymentMethod, PaymentStatus
from app.models.payment import Payment


class PaymentRepository:
    """Gestiona todas las operaciones de persistencia del modelo Payment."""

    def __init__(self, db: Session) -> None:
        self._db = db

    # ── Consultas individuales ─────────────────────────────────────────────────

    def get_by_id(self, payment_id: int) -> Payment | None:
        """Busca un pago por ID cargando cliente y membresía."""
        return (
            self._db.query(Payment)
            .options(
                joinedload(Payment.cliente),
                joinedload(Payment.membresia),
            )
            .filter(Payment.id == payment_id)
            .first()
        )

    def get_by_cliente(self, cliente_id: int) -> list[Payment]:
        """Lista todos los pagos de un cliente, del más reciente al más antiguo."""
        return (
            self._db.query(Payment)
            .filter(Payment.cliente_id == cliente_id)
            .order_by(Payment.fecha_pago.desc())
            .all()
        )

    def get_by_membresia(self, membresia_id: int) -> list[Payment]:
        """Lista todos los pagos asociados a una membresía."""
        return (
            self._db.query(Payment)
            .filter(Payment.membresia_id == membresia_id)
            .order_by(Payment.fecha_pago.desc())
            .all()
        )

    # ── Consultas agregadas ────────────────────────────────────────────────────

    def list_paginated(
        self,
        page: int,
        per_page: int,
        cliente_id: int | None = None,
        estado: PaymentStatus | None = None,
        metodo_pago: PaymentMethod | None = None,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
    ) -> tuple[list[Payment], int]:
        """
        Lista pagos con filtros opcionales y paginación.

        Returns:
            Tupla (lista de pagos de la página, total de registros).
        """
        query = self._db.query(Payment).options(
            joinedload(Payment.cliente),
            joinedload(Payment.membresia),
        )

        if cliente_id:
            query = query.filter(Payment.cliente_id == cliente_id)
        if estado:
            query = query.filter(Payment.estado == estado)
        if metodo_pago:
            query = query.filter(Payment.metodo_pago == metodo_pago)
        if fecha_desde:
            query = query.filter(Payment.fecha_pago >= fecha_desde)
        if fecha_hasta:
            query = query.filter(Payment.fecha_pago <= fecha_hasta)

        total = query.count()
        offset = (page - 1) * per_page
        items = (
            query
            .order_by(Payment.fecha_pago.desc())
            .offset(offset)
            .limit(per_page)
            .all()
        )
        return items, total

    def list_pending(self) -> list[Payment]:
        """Retorna todos los pagos en estado pendiente."""
        return (
            self._db.query(Payment)
            .filter(Payment.estado == PaymentStatus.PENDIENTE)
            .order_by(Payment.fecha_pago.asc())
            .all()
        )

    def get_clients_with_debt(self) -> list[dict]:
        """
        Retorna un resumen agrupado de clientes con saldo pendiente > 0.

        Returns:
            Lista de dicts con cliente_id, total_deuda, pagos_pendientes, ultimo_pago.
        """
        from app.models.client import Client

        rows = (
            self._db.query(
                Payment.cliente_id,
                func.sum(Payment.saldo_pendiente).label("total_deuda"),
                func.count(Payment.id).label("pagos_pendientes"),
                func.max(Payment.fecha_pago).label("ultimo_pago"),
                (Client.nombres + " " + Client.apellidos).label("nombre_cliente"),
            )
            .join(Client, Payment.cliente_id == Client.id)
            .filter(Payment.saldo_pendiente > Decimal("0"))
            .group_by(Payment.cliente_id, Client.nombres, Client.apellidos)
            .all()
        )
        return [
            {
                "cliente_id": r.cliente_id,
                "nombre_cliente": r.nombre_cliente,
                "total_deuda": r.total_deuda,
                "pagos_pendientes": r.pagos_pendientes,
                "ultimo_pago": r.ultimo_pago,
            }
            for r in rows
        ]

    def find_overdue_candidates(self) -> list[Payment]:
        """
        Retorna pagos pendientes cuya membresía ya venció.
        Usado para la tarea batch de actualización de estados a VENCIDO.
        """
        from app.models.membership import Membership

        return (
            self._db.query(Payment)
            .join(Membership, Payment.membresia_id == Membership.id)
            .filter(
                Payment.estado == PaymentStatus.PENDIENTE,
                Payment.saldo_pendiente > Decimal("0"),
                Membership.fecha_fin < date.today(),
            )
            .all()
        )

    # ── Escritura ──────────────────────────────────────────────────────────────

    def create(
        self,
        *,
        cliente_id: int,
        membresia_id: int,
        monto_total: Decimal,
        monto_pagado: Decimal,
        saldo_pendiente: Decimal,
        metodo_pago: PaymentMethod,
        fecha_pago: date,
        estado: PaymentStatus,
    ) -> Payment:
        """
        Persiste un nuevo pago usando flush (transacción coordinada).
        Los pagos son inmutables tras su creación.
        """
        payment = Payment(
            cliente_id=cliente_id,
            membresia_id=membresia_id,
            monto_total=monto_total,
            monto_pagado=monto_pagado,
            saldo_pendiente=saldo_pendiente,
            metodo_pago=metodo_pago,
            fecha_pago=fecha_pago,
            estado=estado,
        )
        self._db.add(payment)
        self._db.flush()
        self._db.refresh(payment)
        return payment

    def update_status(self, payment: Payment, estado: PaymentStatus) -> Payment:
        """Actualiza únicamente el estado de un pago existente."""
        payment.estado = estado
        self._db.flush()
        self._db.refresh(payment)
        return payment

    def apply_settlement(
        self,
        payment: Payment,
        *,
        monto_pagado: Decimal,
        saldo_pendiente: Decimal,
        estado: PaymentStatus,
        metodo_pago: PaymentMethod,
    ) -> Payment:
        """Aplica un abono: actualiza monto pagado, saldo, estado y método."""
        payment.monto_pagado = monto_pagado
        payment.saldo_pendiente = saldo_pendiente
        payment.estado = estado
        payment.metodo_pago = metodo_pago
        self._db.flush()
        self._db.refresh(payment)
        return payment

    def commit(self) -> None:
        """Confirma la transacción activa."""
        self._db.commit()

    def rollback(self) -> None:
        """Revierte la transacción activa."""
        self._db.rollback()
