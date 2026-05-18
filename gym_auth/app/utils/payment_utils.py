"""
Utilidades de cálculo para el módulo de Pagos.
Lógica financiera completamente desacoplada: sin dependencias de ORM ni HTTP.

Centraliza:
- Cálculo de saldo pendiente y estado del pago.
- Determinación de vencimiento por cruce de fechas.
- Clasificación de deuda por cliente.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.core.constants import PaymentStatus


def compute_payment_state(
    monto_total: Decimal,
    monto_pagado: Decimal,
    fecha_fin_membresia: date,
) -> tuple[Decimal, PaymentStatus]:
    """
    Calcula el saldo pendiente y el estado resultante de un pago.

    Reglas:
        - monto_pagado == monto_total → saldo=0, estado=PAGADO
        - monto_pagado <  monto_total y membresía vigente → saldo>0, estado=PENDIENTE
        - monto_pagado <  monto_total y membresía vencida → saldo>0, estado=VENCIDO

    Args:
        monto_total:          Importe total de la membresía.
        monto_pagado:         Importe abonado en este pago.
        fecha_fin_membresia:  Fecha de vencimiento de la membresía asociada.

    Returns:
        Tupla (saldo_pendiente, PaymentStatus).
    """
    saldo = monto_total - monto_pagado

    if saldo <= Decimal("0"):
        return Decimal("0"), PaymentStatus.PAGADO

    membresia_vencida = date.today() > fecha_fin_membresia
    estado = PaymentStatus.VENCIDO if membresia_vencida else PaymentStatus.PENDIENTE
    return saldo, estado


def resolve_overdue_status(
    saldo_pendiente: Decimal,
    fecha_fin_membresia: date,
    estado_actual: PaymentStatus,
) -> PaymentStatus:
    """
    Re-evalúa si un pago pendiente debe marcarse como vencido.

    Útil para tareas batch de sincronización de estados.

    Args:
        saldo_pendiente:      Saldo actual del pago.
        fecha_fin_membresia:  Fecha fin de la membresía.
        estado_actual:        Estado almacenado en BD.

    Returns:
        PaymentStatus actualizado (o el mismo si no cambia).
    """
    if estado_actual == PaymentStatus.PAGADO:
        return estado_actual   # pagado no cambia

    if saldo_pendiente > Decimal("0") and date.today() > fecha_fin_membresia:
        return PaymentStatus.VENCIDO

    return estado_actual


def has_debt(saldo_pendiente: Decimal) -> bool:
    """Determina si el pago representa una deuda activa."""
    return saldo_pendiente > Decimal("0")
