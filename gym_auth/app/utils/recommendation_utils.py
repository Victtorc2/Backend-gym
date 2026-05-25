"""
Utilidades de análisis de afluencia (Fase 10).
Lógica completamente desacoplada: sin dependencias de ORM ni HTTP.

Centraliza:
- Clasificación de nivel de afluencia.
- Conversión de día MySQL (DAYOFWEEK) al enum interno.
- Construcción de etiquetas de bloque horario legibles.
"""
from __future__ import annotations

from datetime import time

from app.core.constants import (
    AFFLUENCE_LOW_MAX,
    AFFLUENCE_MED_MAX,
    AffluenceLevel,
    WeekDay,
)

# DAYOFWEEK de MySQL: 1=domingo, 2=lunes, ..., 7=sábado
_MYSQL_DOW_TO_WEEKDAY: dict[int, WeekDay | None] = {
    1: None,            # domingo → gimnasio cerrado, se excluye
    2: WeekDay.LUNES,
    3: WeekDay.MARTES,
    4: WeekDay.MIERCOLES,
    5: WeekDay.JUEVES,
    6: WeekDay.VIERNES,
    7: WeekDay.SABADO,
}


def classify_affluence(cantidad_promedio: float) -> AffluenceLevel:
    """
    Clasifica el nivel de afluencia según la cantidad promedio de personas.

    Reglas:
        0-20  → BAJA
        21-45 → MEDIA
        46+   → ALTA

    Args:
        cantidad_promedio: Promedio de ingresos en el bloque.

    Returns:
        AffluenceLevel correspondiente.
    """
    if cantidad_promedio <= AFFLUENCE_LOW_MAX:
        return AffluenceLevel.BAJA
    if cantidad_promedio <= AFFLUENCE_MED_MAX:
        return AffluenceLevel.MEDIA
    return AffluenceLevel.ALTA


def mysql_dow_to_weekday(dow_mysql: int) -> WeekDay | None:
    """
    Convierte el valor DAYOFWEEK de MySQL al enum WeekDay interno.

    Args:
        dow_mysql: 1 (domingo) a 7 (sábado).

    Returns:
        WeekDay correspondiente, o None si es domingo (cerrado).
    """
    return _MYSQL_DOW_TO_WEEKDAY.get(dow_mysql)


def build_block_times(hora_bloque: int) -> tuple[time, time]:
    """
    Construye las horas de inicio y fin de un bloque de una hora.

    Args:
        hora_bloque: Hora entera (0-23).

    Returns:
        Tupla (hora_inicio, hora_fin). Ej. 18 → (18:00, 19:00).
    """
    inicio = time(hour=hora_bloque, minute=0)
    fin_hour = (hora_bloque + 1) % 24
    fin = time(hour=fin_hour, minute=0)
    return inicio, fin


def format_block_label(dia: WeekDay, hora_inicio: time, hora_fin: time) -> str:
    """Genera una etiqueta legible del bloque. Ej. 'viernes 19:00-20:00'."""
    return f"{dia.value} {hora_inicio.strftime('%H:%M')}-{hora_fin.strftime('%H:%M')}"


def format_hour_range(hora_inicio: time, hora_fin: time) -> str:
    """Genera el rango horario legible. Ej. '18:00-19:00'."""
    return f"{hora_inicio.strftime('%H:%M')}-{hora_fin.strftime('%H:%M')}"
