"""
Repositorio de Pagos Diarios.
Única capa autorizada para interactuar con la tabla 'pagos_diarios'.
Los pagos son inmutables tras su creación (append-only).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.daily_payment import DailyPayment


class DailyPaymentRepository:
    """Gestiona todas las operaciones de persistencia del modelo DailyPayment."""

    def __init__(self, db: Session) -> None:
        self._db = db

    # ── Consultas ──────────────────────────────────────────────────────────────

    def get_by_id(self, payment_id: int) -> DailyPayment | None:
        return self._db.query(DailyPayment).filter(DailyPayment.id == payment_id).first()

    def get_by_cliente(self, cliente_id: int) -> list[DailyPayment]:
        """Lista todos los pagos de un cliente, del más reciente al más antiguo."""
        return (
            self._db.query(DailyPayment)
            .filter(DailyPayment.cliente_id == cliente_id)
            .order_by(DailyPayment.fecha_pago.desc())
            .all()
        )

    def get_by_cliente_and_date(self, cliente_id: int, fecha: date) -> DailyPayment | None:
        """
        Busca el pago de un cliente para una fecha específica.
        Usado para verificar si ya pagó hoy antes de registrar ingreso.
        """
        return (
            self._db.query(DailyPayment)
            .filter(
                DailyPayment.cliente_id == cliente_id,
                DailyPayment.fecha_pago == fecha,
            )
            .first()
        )

    def paid_today(self, cliente_id: int) -> bool:
        """Verifica si el cliente ya tiene pago registrado para hoy."""
        return self.get_by_cliente_and_date(cliente_id, date.today()) is not None

    # ── Escritura ──────────────────────────────────────────────────────────────

    def create(self, cliente_id: int, monto: Decimal) -> DailyPayment:
        """
        Registra el pago del día actual para un cliente diario.
        La fecha se asigna automáticamente como hoy.
        """
        payment = DailyPayment(
            cliente_id=cliente_id,
            monto=monto,
            fecha_pago=date.today(),
        )
        self._db.add(payment)
        self._db.commit()
        self._db.refresh(payment)
        return payment
