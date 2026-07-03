"""
Servicio de Pagos y Deudas.
Orquesta toda la lógica financiera del módulo:
  - Registro de pagos completos y parciales.
  - Cálculo automático de saldo pendiente y estado.
  - Consulta de clientes con deuda.
  - Sincronización batch de estados vencidos.
  - Historial por cliente.
  - Paginación y filtros.
"""
from __future__ import annotations

import math
from datetime import date
from decimal import Decimal

from app.core.constants import ClientStatus, MembershipStatus, PaymentStatus
from app.core.exceptions import (
    ClientNotFoundException,
    MembershipInactiveException,
    MembershipNotFoundException,
    PaymentInvalidException,
    PaymentNotFoundException,
)
from app.repositories.client_repository import ClientRepository
from app.repositories.membership_repository import MembershipRepository
from app.repositories.payment_repository import PaymentRepository
from app.schemas.payment_schema import (
    ClientDebtSummarySchema,
    PaginatedPaymentSchema,
    PaymentCreateSchema,
    PaymentFilterSchema,
    PaymentResponseSchema,
    PaymentSettleSchema,
)
from app.utils.payment_utils import compute_payment_state, resolve_overdue_status


class PaymentService:
    """Gestiona todas las operaciones de negocio del módulo de pagos."""

    def __init__(
        self,
        payment_repo: PaymentRepository,
        client_repo: ClientRepository,
        membership_repo: MembershipRepository,
    ) -> None:
        self._payments = payment_repo
        self._clients = client_repo
        self._memberships = membership_repo

    # ── Registro ───────────────────────────────────────────────────────────────

    def register_payment(self, data: PaymentCreateSchema) -> PaymentResponseSchema:
        """
        Registra un pago completo o parcial para una membresía de cliente.

        Flujo:
            1. Validar existencia y estado activo del cliente.
            2. Validar existencia y vigencia de la membresía.
            3. Confirmar que la membresía pertenece al cliente.
            4. Calcular saldo_pendiente y estado automáticamente.
            5. Persistir y confirmar.

        Raises:
            ClientNotFoundException:    Cliente inexistente.
            PaymentInvalidException:    Cliente inactivo o monto inválido.
            MembershipNotFoundException: Membresía inexistente.
            MembershipInactiveException: Membresía vencida o no activa.
        """
        # ── Validar cliente ────────────────────────────────────────────────────
        client = self._clients.get_by_id(data.cliente_id)
        if client is None:
            raise ClientNotFoundException()
        if client.estado != ClientStatus.ACTIVO:
            raise PaymentInvalidException(
                "No se puede registrar pago para un cliente inactivo"
            )

        # ── Validar membresía ──────────────────────────────────────────────────
        membership = self._memberships.get_by_id(data.membresia_id)
        if membership is None:
            raise MembershipNotFoundException()
        if membership.cliente_id != data.cliente_id:
            raise PaymentInvalidException(
                "La membresía no pertenece al cliente indicado"
            )
        if membership.estado == MembershipStatus.VENCIDA:
            raise MembershipInactiveException(
                "No se puede registrar pago sobre una membresía vencida"
            )

        # ── Calcular saldo y estado ────────────────────────────────────────────
        saldo_pendiente, estado = compute_payment_state(
            monto_total=data.monto_total,
            monto_pagado=data.monto_pagado,
            fecha_fin_membresia=membership.fecha_fin,
        )

        try:
            payment = self._payments.create(
                cliente_id=data.cliente_id,
                membresia_id=data.membresia_id,
                monto_total=data.monto_total,
                monto_pagado=data.monto_pagado,
                saldo_pendiente=saldo_pendiente,
                metodo_pago=data.metodo_pago,
                fecha_pago=date.today(),
                estado=estado,
            )
            self._payments.commit()
        except Exception:
            self._payments.rollback()
            raise

        return PaymentResponseSchema.model_validate(payment)

    def settle_payment(
        self, payment_id: int, data: PaymentSettleSchema
    ) -> PaymentResponseSchema:
        """
        Abona un monto a un pago parcial existente, completándolo total o
        parcialmente. Al saldar por completo, el pago pasa a PAGADO y deja de
        contar como deuda (sin crear un pago nuevo).

        Raises:
            PaymentNotFoundException: Pago inexistente.
            PaymentInvalidException:  Ya pagado o abono mayor al saldo.
        """
        payment = self._payments.get_by_id(payment_id)
        if payment is None:
            raise PaymentNotFoundException()
        if payment.estado == PaymentStatus.PAGADO:
            raise PaymentInvalidException("Este pago ya está saldado")
        if data.monto > payment.saldo_pendiente:
            raise PaymentInvalidException(
                f"El abono ({data.monto}) supera el saldo pendiente ({payment.saldo_pendiente})"
            )

        membership = self._memberships.get_by_id(payment.membresia_id)
        fecha_fin = membership.fecha_fin if membership else date.today()

        nuevo_pagado = payment.monto_pagado + data.monto
        saldo, estado = compute_payment_state(payment.monto_total, nuevo_pagado, fecha_fin)

        try:
            self._payments.apply_settlement(
                payment,
                monto_pagado=nuevo_pagado,
                saldo_pendiente=saldo,
                estado=estado,
                metodo_pago=data.metodo_pago or payment.metodo_pago,
            )
            self._payments.commit()
        except Exception:
            self._payments.rollback()
            raise

        return PaymentResponseSchema.model_validate(payment)

    # ── Consultas ──────────────────────────────────────────────────────────────

    def get_payment(self, payment_id: int) -> PaymentResponseSchema:
        """
        Obtiene un pago por ID.

        Raises:
            PaymentNotFoundException: Si el ID no existe.
        """
        payment = self._payments.get_by_id(payment_id)
        if payment is None:
            raise PaymentNotFoundException()
        return PaymentResponseSchema.model_validate(payment)

    def list_payments(self, filters: PaymentFilterSchema) -> PaginatedPaymentSchema:
        """
        Lista pagos con filtros opcionales y paginación.

        Soporta filtros por: cliente, estado, método, rango de fechas.
        """
        items, total = self._payments.list_paginated(
            page=filters.page,
            per_page=filters.per_page,
            cliente_id=filters.cliente_id,
            estado=filters.estado,
            metodo_pago=filters.metodo_pago,
            fecha_desde=filters.fecha_desde,
            fecha_hasta=filters.fecha_hasta,
        )
        total_pages = math.ceil(total / filters.per_page) if total > 0 else 1

        return PaginatedPaymentSchema(
            items=[PaymentResponseSchema.model_validate(p) for p in items],
            total=total,
            page=filters.page,
            per_page=filters.per_page,
            total_pages=total_pages,
        )

    def get_client_history(self, cliente_id: int) -> list[PaymentResponseSchema]:
        """
        Lista el historial completo de pagos de un cliente.

        Raises:
            ClientNotFoundException: Si el cliente no existe.
        """
        if self._clients.get_by_id(cliente_id) is None:
            raise ClientNotFoundException()
        payments = self._payments.get_by_cliente(cliente_id)
        return [PaymentResponseSchema.model_validate(p) for p in payments]

    def list_pending_payments(self) -> list[PaymentResponseSchema]:
        """Lista todos los pagos en estado PENDIENTE, ordenados por fecha asc."""
        payments = self._payments.list_pending()
        return [PaymentResponseSchema.model_validate(p) for p in payments]

    def get_clients_with_debt(self) -> list[ClientDebtSummarySchema]:
        """
        Devuelve resumen de deuda consolidada por cliente.

        Solo incluye clientes con saldo_pendiente > 0.
        Agrupa por cliente sumando todos sus saldos pendientes.
        """
        rows = self._payments.get_clients_with_debt()
        return [
            ClientDebtSummarySchema(
                cliente_id=r["cliente_id"],
                nombre_cliente=r["nombre_cliente"],
                total_deuda=r["total_deuda"],
                pagos_pendientes=r["pagos_pendientes"],
                ultimo_pago=r["ultimo_pago"],
            )
            for r in rows
        ]

    # ── Mantenimiento ──────────────────────────────────────────────────────────

    def sync_overdue_payments(self) -> int:
        """
        Actualiza a VENCIDO todos los pagos pendientes cuya membresía ya venció.

        Diseñado para ejecutarse como tarea periódica (cron / scheduler).
        No lanza excepciones; retorna el número de registros actualizados.

        Returns:
            Cantidad de pagos actualizados.
        """
        candidates = self._payments.find_overdue_candidates()
        for payment in candidates:
            self._payments.update_status(payment, PaymentStatus.VENCIDO)
        if candidates:
            self._payments.commit()
        return len(candidates)
