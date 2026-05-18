"""
Utilidades de cálculo para el módulo de Membresías.
Lógica completamente desacoplada: sin dependencias de ORM ni HTTP.

Centraliza:
- Cálculo de fechas de inicio y fin.
- Resolución del estado de vigencia.
- Generación de códigos de tarjeta.
"""
from datetime import date, timedelta

from app.core.constants import (
    CARD_CODE_PREFIX,
    CARD_ELIGIBLE_TYPES,
    MEMBERSHIP_DURATION_DAYS,
    MembershipStatus,
    MembershipType,
)


def resolve_membership_dates(tipo: MembershipType) -> tuple[date, date, int]:
    """
    Calcula fecha_inicio, fecha_fin y duracion_dias para un tipo de membresía.

    La fecha de inicio siempre es hoy (el sistema la asigna, no el usuario).

    Args:
        tipo: Tipo de membresía (mensual, anual, diario).

    Returns:
        Tupla (fecha_inicio, fecha_fin, duracion_dias).

    Example:
        Hoy 2026-05-20, tipo mensual → (2026-05-20, 2026-06-19, 30)
    """
    duracion: int = MEMBERSHIP_DURATION_DAYS[tipo.value]
    inicio: date = date.today()
    fin: date = inicio + timedelta(days=duracion - 1)   # día N incluido
    return inicio, fin, duracion


def compute_membership_status(fecha_fin: date) -> MembershipStatus:
    """
    Determina el estado de vigencia comparando fecha_fin con hoy.

    Regla:
        fecha_actual > fecha_fin → VENCIDA
        fecha_actual <= fecha_fin → ACTIVA

    Args:
        fecha_fin: Fecha de vencimiento de la membresía.

    Returns:
        MembershipStatus correspondiente.
    """
    return (
        MembershipStatus.VENCIDA
        if date.today() > fecha_fin
        else MembershipStatus.ACTIVA
    )


def is_card_eligible(tipo: MembershipType) -> bool:
    """
    Verifica si el tipo de membresía otorga derecho a tarjeta física.

    Solo membresías mensuales y anuales son elegibles.

    Args:
        tipo: Tipo de membresía.

    Returns:
        True si es elegible para tarjeta.
    """
    return tipo.value in CARD_ELIGIBLE_TYPES


def generate_card_code(sequence: int) -> str:
    """
    Genera el código único de tarjeta con formato GYM-NNNNN.

    Args:
        sequence: Número secuencial (se usará el total de tarjetas + 1).

    Returns:
        Código formateado, ej. "GYM-00001".
    """
    return f"{CARD_CODE_PREFIX}-{sequence:05d}"
