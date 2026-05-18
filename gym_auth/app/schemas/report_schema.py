"""
Schemas Pydantic para el Módulo de Reportes (Fase 8).
Define los contratos de respuesta para cada reporte.
Solo lectura: no existen schemas de entrada de escritura.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.core.constants import (
    AgeGroup,
    ClientSex,
    ClientStatus,
    MembershipStatus,
    MembershipType,
    PaymentMethod,
    PaymentStatus,
)


# ══════════════════════════════════════════════════════════════════════════════
#  PARÁMETROS DE FILTRO GLOBALES
# ══════════════════════════════════════════════════════════════════════════════

class ReportDateFilter(BaseModel):
    """Filtros de fecha aplicables a todos los reportes que los soporten."""
    fecha_desde: date | None = Field(default=None, description="Fecha de inicio del rango")
    fecha_hasta: date | None = Field(default=None, description="Fecha de fin del rango")
    cliente_id: int | None = Field(default=None, description="Filtrar por cliente específico")


# ══════════════════════════════════════════════════════════════════════════════
#  REPORTE: CLIENTES ACTIVOS
# ══════════════════════════════════════════════════════════════════════════════

class ClienteActivoSchema(BaseModel):
    """Datos de un cliente activo para el reporte."""
    id: int
    nombres: str
    apellidos: str
    correo: str
    dni: str
    telefono: str
    sexo: ClientSex
    grupo_edad: AgeGroup
    created_at: datetime

    model_config = {"from_attributes": True}


class ReporteClientesActivosSchema(BaseModel):
    """Reporte completo de clientes activos."""
    total_activos: int
    total_inactivos: int
    total_general: int
    porcentaje_activos: float
    clientes: list[ClienteActivoSchema]


# ══════════════════════════════════════════════════════════════════════════════
#  REPORTE: CLIENTES CON DEUDA
# ══════════════════════════════════════════════════════════════════════════════

class ClienteConDeudaSchema(BaseModel):
    """Resumen de deuda de un cliente para el reporte."""
    cliente_id: int
    nombres: str
    apellidos: str
    correo: str
    total_deuda: Decimal
    pagos_pendientes: int
    pagos_vencidos: int
    ultimo_pago: date | None


class ReporteDeudaSchema(BaseModel):
    """Reporte completo de clientes con deuda."""
    total_clientes_con_deuda: int
    monto_total_deuda: Decimal
    clientes: list[ClienteConDeudaSchema]


# ══════════════════════════════════════════════════════════════════════════════
#  REPORTE: MEMBRESÍAS VIGENTES
# ══════════════════════════════════════════════════════════════════════════════

class MembresiaVigenteSchema(BaseModel):
    """Membresía activa y vigente con datos del cliente."""
    id: int
    cliente_id: int
    nombre_cliente: str
    correo_cliente: str
    tipo: MembershipType
    precio: Decimal
    fecha_inicio: date
    fecha_fin: date
    dias_restantes: int
    estado: MembershipStatus

    model_config = {"from_attributes": True}


class ReporteMembresíasSchema(BaseModel):
    """Reporte completo de membresías vigentes."""
    total_activas: int
    total_vencidas: int
    total_pendientes: int
    ingresos_proyectados: Decimal        # suma de precios de membresías activas
    por_tipo: dict[str, int]             # {"mensual": 5, "anual": 3, "diario": 2}
    membresias: list[MembresiaVigenteSchema]


# ══════════════════════════════════════════════════════════════════════════════
#  REPORTE: PAGOS
# ══════════════════════════════════════════════════════════════════════════════

class PagoReporteSchema(BaseModel):
    """Datos de un pago para el reporte."""
    id: int
    cliente_id: int
    nombre_cliente: str
    membresia_id: int
    monto_total: Decimal
    monto_pagado: Decimal
    saldo_pendiente: Decimal
    metodo_pago: PaymentMethod
    fecha_pago: date
    estado: PaymentStatus

    model_config = {"from_attributes": True}


class ResumenPagosSchema(BaseModel):
    """Resumen financiero de pagos para el reporte."""
    total_pagos: int
    total_ingresos: Decimal              # suma de monto_pagado de todos los pagos
    total_deuda_pendiente: Decimal       # suma de saldo_pendiente
    pagos_completados: int               # estado = pagado
    pagos_pendientes: int                # estado = pendiente
    pagos_vencidos: int                  # estado = vencido
    por_metodo: dict[str, Decimal]       # {"efectivo": 500.00, "yape": 300.00, ...}
    fecha_desde: date | None
    fecha_hasta: date | None


class ReportePagosSchema(BaseModel):
    """Reporte completo de pagos con lista y resumen."""
    resumen: ResumenPagosSchema
    pagos: list[PagoReporteSchema]


# ══════════════════════════════════════════════════════════════════════════════
#  REPORTE: ASISTENCIA
# ══════════════════════════════════════════════════════════════════════════════

class AsistenciaReporteSchema(BaseModel):
    """Datos de un registro de asistencia para el reporte."""
    id: int
    cliente_id: int
    nombre_cliente: str
    fecha: date
    hora: str                            # formateado HH:MM para mejor lectura
    estado: str
    motivo_denegacion: str | None

    model_config = {"from_attributes": True}


class FrecuenciaClienteSchema(BaseModel):
    """Frecuencia de asistencia de un cliente."""
    cliente_id: int
    nombre_cliente: str
    total_aprobados: int
    total_denegados: int
    asistencias_mes_actual: int
    primer_ingreso: date | None
    ultimo_ingreso: date | None
    promedio_mensual: float              # ingresos aprobados / meses activo


class ReporteAsistenciaSchema(BaseModel):
    """Reporte completo de asistencias."""
    total_registros: int
    total_aprobados: int
    total_denegados: int
    porcentaje_aprobacion: float
    fecha_desde: date | None
    fecha_hasta: date | None
    asistencias: list[AsistenciaReporteSchema]


class ReporteFrecuenciaSchema(BaseModel):
    """Reporte de frecuencia de asistencia por cliente."""
    total_clientes: int
    fecha_desde: date | None
    fecha_hasta: date | None
    frecuencias: list[FrecuenciaClienteSchema]
