"""
Servicio de Reportes (Fase 8).
Orquesta la generación de todos los reportes del sistema.

Principios:
- Solo lectura: nunca modifica datos.
- Toda la lógica de cálculo vive aquí, no en las rutas.
- Delega queries optimizadas al ReportRepository.
- Calcula métricas derivadas (porcentajes, días restantes, promedios)
  a partir de los datos brutos del repositorio.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from app.repositories.report_repository import ReportRepository
from app.schemas.report_schema import (
    AsistenciaReporteSchema,
    ClienteActivoSchema,
    ClienteConDeudaSchema,
    FrecuenciaClienteSchema,
    MembresiaVigenteSchema,
    PagoReporteSchema,
    ReporteAsistenciaSchema,
    ReporteClientesActivosSchema,
    ReporteDeudaSchema,
    ReporteFrecuenciaSchema,
    ReporteMembresíasSchema,
    ReportePagosSchema,
    ResumenPagosSchema,
)


class ReportService:
    """Genera reportes de lectura para apoyo a decisiones administrativas."""

    def __init__(self, repo: ReportRepository) -> None:
        self._repo = repo

    # ══════════════════════════════════════════════════════════════════════════
    #  CLIENTES ACTIVOS
    # ══════════════════════════════════════════════════════════════════════════

    def get_clientes_activos(self) -> ReporteClientesActivosSchema:
        """
        Genera reporte de clientes activos con estadísticas de distribución.

        Incluye:
        - Total activos / inactivos / general.
        - Porcentaje de clientes activos.
        - Listado completo de clientes activos.
        """
        counts = self._repo.count_clients_by_status()
        activos = counts["activos"]
        inactivos = counts["inactivos"]
        total = activos + inactivos

        porcentaje = (
            round((activos / total) * 100, 2) if total > 0 else 0.0
        )

        clientes = self._repo.get_active_clients()

        return ReporteClientesActivosSchema(
            total_activos=activos,
            total_inactivos=inactivos,
            total_general=total,
            porcentaje_activos=porcentaje,
            clientes=[ClienteActivoSchema.model_validate(c) for c in clientes],
        )

    # ══════════════════════════════════════════════════════════════════════════
    #  DEUDA
    # ══════════════════════════════════════════════════════════════════════════

    def get_reporte_deuda(self) -> ReporteDeudaSchema:
        """
        Genera reporte de clientes con deuda pendiente o vencida.

        Incluye:
        - Total de clientes con deuda.
        - Monto total acumulado de deuda.
        - Listado detallado por cliente.
        """
        rows = self._repo.get_debt_summary_by_client()
        total_deuda = self._repo.get_total_debt_amount()

        clientes = [
            ClienteConDeudaSchema(
                cliente_id=r["cliente_id"],
                nombres=r["nombres"],
                apellidos=r["apellidos"],
                correo=r["correo"],
                total_deuda=r["total_deuda"],
                pagos_pendientes=r["pagos_pendientes"],
                pagos_vencidos=r["pagos_vencidos"],
                ultimo_pago=r["ultimo_pago"],
            )
            for r in rows
        ]

        return ReporteDeudaSchema(
            total_clientes_con_deuda=len(clientes),
            monto_total_deuda=total_deuda,
            clientes=clientes,
        )

    # ══════════════════════════════════════════════════════════════════════════
    #  MEMBRESÍAS VIGENTES
    # ══════════════════════════════════════════════════════════════════════════

    def get_reporte_membresias(self) -> ReporteMembresíasSchema:
        """
        Genera reporte de membresías vigentes con distribución por tipo.

        Incluye:
        - Conteos por estado (activa, vencida, pendiente).
        - Ingresos proyectados de membresías activas.
        - Distribución por tipo.
        - Listado con días restantes calculados.
        """
        by_status = self._repo.count_memberships_by_status()
        by_type = self._repo.count_memberships_by_type()
        ingresos_proyectados = self._repo.get_projected_income()
        membresias = self._repo.get_memberships_with_client(solo_vigentes=True)
        today = date.today()

        items = [
            MembresiaVigenteSchema(
                id=m.id,
                cliente_id=m.cliente_id,
                nombre_cliente=f"{m.cliente.nombres} {m.cliente.apellidos}",
                correo_cliente=m.cliente.correo,
                tipo=m.tipo,
                precio=m.precio,
                fecha_inicio=m.fecha_inicio,
                fecha_fin=m.fecha_fin,
                dias_restantes=max(0, (m.fecha_fin - today).days),
                estado=m.estado,
            )
            for m in membresias
        ]

        return ReporteMembresíasSchema(
            total_activas=by_status.get("activa", 0),
            total_vencidas=by_status.get("vencida", 0),
            total_pendientes=by_status.get("pendiente", 0),
            ingresos_proyectados=ingresos_proyectados,
            por_tipo=by_type,
            membresias=items,
        )

    # ══════════════════════════════════════════════════════════════════════════
    #  PAGOS
    # ══════════════════════════════════════════════════════════════════════════

    def get_reporte_pagos(
        self,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
        cliente_id: int | None = None,
    ) -> ReportePagosSchema:
        """
        Genera reporte de pagos con resumen financiero y listado detallado.

        Soporta filtros por rango de fechas y cliente específico.
        """
        summary_data = self._repo.get_payment_summary(fecha_desde, fecha_hasta)
        payments = self._repo.get_payments_with_client(fecha_desde, fecha_hasta, cliente_id)

        resumen = ResumenPagosSchema(
            **summary_data,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
        )

        pagos = [
            PagoReporteSchema(
                id=p.id,
                cliente_id=p.cliente_id,
                nombre_cliente=f"{p.cliente.nombres} {p.cliente.apellidos}",
                membresia_id=p.membresia_id,
                monto_total=p.monto_total,
                monto_pagado=p.monto_pagado,
                saldo_pendiente=p.saldo_pendiente,
                metodo_pago=p.metodo_pago,
                fecha_pago=p.fecha_pago,
                estado=p.estado,
            )
            for p in payments
        ]

        return ReportePagosSchema(resumen=resumen, pagos=pagos)

    def get_resumen_pagos(
        self,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
    ) -> ResumenPagosSchema:
        """
        Devuelve solo el resumen financiero sin el listado detallado.
        Más eficiente cuando el frontend solo necesita los KPIs.
        """
        data = self._repo.get_payment_summary(fecha_desde, fecha_hasta)
        return ResumenPagosSchema(
            **data,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
        )

    # ══════════════════════════════════════════════════════════════════════════
    #  ASISTENCIA
    # ══════════════════════════════════════════════════════════════════════════

    def get_reporte_asistencia(
        self,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
        cliente_id: int | None = None,
    ) -> ReporteAsistenciaSchema:
        """
        Genera reporte de asistencias con métricas de aprobación.

        Incluye porcentaje de aprobación y listado legible con hora formateada.
        """
        counts = self._repo.get_attendance_counts(fecha_desde, fecha_hasta)
        records = self._repo.get_attendances_with_client(fecha_desde, fecha_hasta, cliente_id)

        total = counts["total"]
        aprobados = counts["aprobados"]
        porcentaje = round((aprobados / total) * 100, 2) if total > 0 else 0.0

        items = [
            AsistenciaReporteSchema(
                id=a.id,
                cliente_id=a.cliente_id,
                nombre_cliente=f"{a.cliente.nombres} {a.cliente.apellidos}",
                fecha=a.fecha,
                hora=a.hora.strftime("%H:%M") if a.hora else "",
                estado=a.estado.value,
                motivo_denegacion=a.motivo_denegacion.value if a.motivo_denegacion else None,
            )
            for a in records
        ]

        return ReporteAsistenciaSchema(
            total_registros=total,
            total_aprobados=aprobados,
            total_denegados=counts["denegados"],
            porcentaje_aprobacion=porcentaje,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            asistencias=items,
        )

    def get_reporte_frecuencia(
        self,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
    ) -> ReporteFrecuenciaSchema:
        """
        Genera reporte de frecuencia de asistencia por cliente.

        Calcula promedio mensual como ingresos_aprobados / meses activo.
        """
        rows = self._repo.get_frequency_by_client(fecha_desde, fecha_hasta)

        frecuencias = [
            FrecuenciaClienteSchema(
                cliente_id=r["cliente_id"],
                nombre_cliente=r["nombre_cliente"],
                total_aprobados=r["total_aprobados"],
                total_denegados=r["total_denegados"],
                asistencias_mes_actual=r["asistencias_mes_actual"],
                primer_ingreso=r["primer_ingreso"],
                ultimo_ingreso=r["ultimo_ingreso"],
                promedio_mensual=self._calc_monthly_avg(
                    r["total_aprobados"],
                    r["primer_ingreso"],
                    r["ultimo_ingreso"],
                ),
            )
            for r in rows
        ]

        return ReporteFrecuenciaSchema(
            total_clientes=len(frecuencias),
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            frecuencias=frecuencias,
        )

    # ── Helpers privados ───────────────────────────────────────────────────────

    @staticmethod
    def _calc_monthly_avg(
        total_aprobados: int,
        primer_ingreso: date | None,
        ultimo_ingreso: date | None,
    ) -> float:
        """
        Calcula el promedio mensual de asistencias aprobadas.

        Si solo hay datos de un mes, retorna el total como promedio.
        """
        if not primer_ingreso or total_aprobados == 0:
            return 0.0

        end = ultimo_ingreso or date.today()
        months = max(
            1,
            (end.year - primer_ingreso.year) * 12
            + (end.month - primer_ingreso.month)
            + 1,
        )
        return round(total_aprobados / months, 2)
