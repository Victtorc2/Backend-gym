"""
Schemas Pydantic para el Portal del Cliente (Fase 10 — Módulos Cliente).
Todas las respuestas están filtradas por el cliente autenticado vía JWT.
El cliente nunca envía su propio ID: siempre lo provee el token.
"""
from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel

from app.core.constants import (
    AffluenceLevel,
    AgeGroup,
    AttendanceStatus,
    ClientSex,
    ClientStatus,
    DenialReason,
    MembershipStatus,
    MembershipType,
    PaymentMethod,
    PaymentStatus,
    WeekDay,
)


# ══════════════════════════════════════════════════════════════════════════════
#  MÓDULO 1 — MI MEMBRESÍA
# ══════════════════════════════════════════════════════════════════════════════

class MiMembresiaSchema(BaseModel):
    """Estado de la membresía activa del cliente."""
    id: int
    tipo: MembershipType
    precio: Decimal
    fecha_inicio: date
    fecha_fin: date
    dias_restantes: int
    estado: MembershipStatus
    vigente: bool


class SinMembresiaSchema(BaseModel):
    """Respuesta controlada cuando el cliente no tiene membresía activa."""
    tiene_membresia: bool = False
    mensaje: str = "No tienes una membresía activa en este momento"


# ══════════════════════════════════════════════════════════════════════════════
#  MÓDULO 2 — MIS PAGOS
# ══════════════════════════════════════════════════════════════════════════════

class MiPagoSchema(BaseModel):
    """Registro individual de pago del cliente."""
    id: int
    monto_total: Decimal
    monto_pagado: Decimal
    saldo_pendiente: Decimal
    metodo_pago: PaymentMethod
    fecha_pago: date
    estado: PaymentStatus

    model_config = {"from_attributes": True}


class MisPagosSchema(BaseModel):
    """Resumen de pagos del cliente."""
    total_pagos: int
    total_pagado: Decimal
    deuda_pendiente: Decimal
    pagos: list[MiPagoSchema]


class MiHistorialPagosSchema(BaseModel):
    """Historial cronológico completo de pagos."""
    total_registros: int
    historial: list[MiPagoSchema]


class MiDeudaSchema(BaseModel):
    """Estado de deuda consolidado del cliente."""
    tiene_deuda: bool
    monto_total_deuda: Decimal
    pagos_pendientes: int
    pagos_vencidos: int
    mensaje: str


# ══════════════════════════════════════════════════════════════════════════════
#  MÓDULO 3 — MI ASISTENCIA
# ══════════════════════════════════════════════════════════════════════════════

class MiAsistenciaItemSchema(BaseModel):
    """Registro individual de asistencia del cliente."""
    id: int
    fecha: date
    hora: str
    estado: AttendanceStatus
    motivo_denegacion: DenialReason | None

    model_config = {"from_attributes": True}


class MiAsistenciaSchema(BaseModel):
    """Historial de asistencia del cliente."""
    total_asistencias: int
    total_aprobados: int
    total_denegados: int
    historial: list[MiAsistenciaItemSchema]


class MiFrecuenciaSchema(BaseModel):
    """Estadísticas de frecuencia de asistencia del cliente."""
    total_ingresos: int
    asistencias_mes_actual: int
    frecuencia_semanal: float          # promedio de visitas por semana
    primer_ingreso: date | None
    ultimo_ingreso: date | None


# ══════════════════════════════════════════════════════════════════════════════
#  MÓDULO 4 — MI PERFIL
# ══════════════════════════════════════════════════════════════════════════════

class MiPerfilSchema(BaseModel):
    """Datos personales del cliente autenticado."""
    id: int
    nombres: str
    apellidos: str
    dni: str
    correo: str
    telefono: str
    sexo: ClientSex
    edad: int
    grupo_edad: AgeGroup
    ocupacion: str | None
    direccion: str | None
    estado: ClientStatus
    miembro_desde: datetime

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════════════════
#  MÓDULO 5 — MI HORARIO RECOMENDADO
# ══════════════════════════════════════════════════════════════════════════════

class BloqueHorarioSchema(BaseModel):
    """Bloque horario con su nivel de afluencia."""
    dia_semana: WeekDay
    horario: str                       # ej. "08:00-09:00"
    promedio_personas: float
    nivel_afluencia: AffluenceLevel


class RecomendacionPersonalSchema(BaseModel):
    """Recomendación de horario que el administrador asignó a este cliente."""
    dia_semana: WeekDay
    horario: str                       # ej. "08:00-09:00"
    nivel_afluencia: AffluenceLevel | None
    mensaje: str | None                # nota del administrador
    asignada_el: datetime


class MiHorarioRecomendadoSchema(BaseModel):
    """Recomendación de horarios personalizada según el día actual."""
    dia_actual: WeekDay
    recomendacion_personal: RecomendacionPersonalSchema | None  # asignada por el admin
    horario_recomendado: BloqueHorarioSchema | None
    horario_a_evitar: BloqueHorarioSchema | None
    horarios_libres_hoy: list[BloqueHorarioSchema]
    horas_pico_hoy: list[BloqueHorarioSchema]
    mensaje: str


# ══════════════════════════════════════════════════════════════════════════════
#  MÓDULO 6 — LOGOUT
# ══════════════════════════════════════════════════════════════════════════════

class LogoutResponseSchema(BaseModel):
    """Confirmación de cierre de sesión."""
    sesion_cerrada: bool = True
    mensaje: str = "Sesión cerrada correctamente"
