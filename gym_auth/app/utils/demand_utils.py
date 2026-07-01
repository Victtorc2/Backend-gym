"""
Utilidades de la Gestión de Demanda. Sin dependencias de ORM ni HTTP.
"""
from __future__ import annotations

from app.core.constants import (
    DEMAND_HIGH_MAX,
    DEMAND_LOW_MAX,
    DEMAND_MED_MAX,
    DemandLevel,
)


def classify_demand_level(clientes: int) -> DemandLevel:
    """Clasifica el nivel de demanda de un bloque según el nº de clientes previstos."""
    if clientes <= DEMAND_LOW_MAX:
        return DemandLevel.BAJO
    if clientes <= DEMAND_MED_MAX:
        return DemandLevel.MEDIO
    if clientes <= DEMAND_HIGH_MAX:
        return DemandLevel.ALTO
    return DemandLevel.MUY_ALTO


def hour_block_label(hora: int) -> str:
    """Etiqueta legible de un bloque de una hora. Ej. 18 → '18:00-19:00'."""
    fin = (hora + 1) % 24
    return f"{hora:02d}:00-{fin:02d}:00"
