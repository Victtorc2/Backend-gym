"""
Servicio de Segmentación y Seguimiento (Fase 7).

Centraliza toda la lógica de clasificación de clientes en tres dimensiones:
  1. Demográfica  → sexo + grupo de edad (calculado desde fecha_nacimiento)
  2. Actividad    → activo / poco_activo / inactivo (asistencias mes actual)
  3. Financiera   → sin_deuda / con_deuda (pagos pendientes/vencidos)

La segmentación es DINÁMICA: se recalcula en cada consulta usando los datos
actuales de clientes, pagos y asistencias. No persiste en BD (no hay tabla
de segmentación): es una vista calculada sobre datos existentes.

Principios aplicados:
  - Toda la lógica de negocio está aquí, cero lógica en los routes.
  - Las queries masivas (bulk) se ejecutan una sola vez para evitar N+1.
  - Los umbrales de clasificación están en constants.py como única fuente.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.constants import (
    ACTIVITY_ACTIVE_THRESHOLD,
    ACTIVITY_LOW_THRESHOLD,
    AGE_YOUNG_MAX,
    ActivitySegment,
    AgeGroup,
    ClientStatus,
    FinancialSegment,
)
from app.core.exceptions import ClientNotFoundException
from app.models.client import Client
from app.repositories.segmentation_repository import SegmentationRepository
from app.schemas.segmentation_schema import (
    ActivityBreakdown,
    ClientSegmentationResponse,
    DemographicBreakdown,
    FinancialBreakdown,
    SegmentationFilter,
    SegmentationSummaryResponse,
)


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE CLASIFICACIÓN PURAS (sin dependencias externas)
# ══════════════════════════════════════════════════════════════════════════════

def _calculate_age(fecha_nacimiento: date) -> int:
    """
    Calcula la edad en años cumplidos respecto a la fecha actual (UTC).
    """
    today = datetime.now(timezone.utc).date()
    age = today.year - fecha_nacimiento.year
    # Ajuste si aún no ha llegado el cumpleaños este año
    if (today.month, today.day) < (fecha_nacimiento.month, fecha_nacimiento.day):
        age -= 1
    return max(age, 0)


def _classify_age_group(age: int) -> AgeGroup:
    """
    Clasifica al cliente en grupo de edad según el umbral configurado.
    - joven:  14 – AGE_YOUNG_MAX (25)
    - adulto: AGE_YOUNG_MAX+1 (26) en adelante
    """
    return AgeGroup.JOVEN if age <= AGE_YOUNG_MAX else AgeGroup.ADULTO


def _classify_activity(asistencias_mes: int) -> ActivitySegment:
    """
    Clasifica la actividad del cliente en base a sus asistencias del mes actual.
    Umbrales definidos en constants.py (única fuente de verdad):
      - activo:      >= ACTIVITY_ACTIVE_THRESHOLD (8)
      - poco_activo: ACTIVITY_LOW_THRESHOLD (1) a ACTIVITY_ACTIVE_THRESHOLD-1 (7)
      - inactivo:    0 asistencias
    """
    if asistencias_mes >= ACTIVITY_ACTIVE_THRESHOLD:
        return ActivitySegment.ACTIVO
    if asistencias_mes >= ACTIVITY_LOW_THRESHOLD:
        return ActivitySegment.POCO_ACTIVO
    return ActivitySegment.INACTIVO


def _classify_financial(pagos_pendientes: int) -> FinancialSegment:
    """
    Clasifica al cliente financieramente.
    Cualquier pago en estado PENDIENTE o VENCIDO implica deuda.
    """
    return FinancialSegment.CON_DEUDA if pagos_pendientes > 0 else FinancialSegment.SIN_DEUDA


def _build_segmentation(
    client: Client,
    asistencias_mes: int,
    ultimo_ingreso: date | None,
    pagos_pendientes: int,
    deuda_total: Decimal,
) -> ClientSegmentationResponse:
    """
    Construye el objeto de respuesta completo para un cliente dado sus métricas.
    Función pura: no hace IO, no accede a BD.
    """
    age = _calculate_age(client.fecha_nacimiento)
    return ClientSegmentationResponse(
        cliente_id=client.id,
        nombres=client.nombres,
        apellidos=client.apellidos,
        dni=client.dni,
        estado=client.estado,
        # Demográfico
        sexo=client.sexo,
        edad=age,
        grupo_edad=_classify_age_group(age),
        # Actividad
        asistencias_mes_actual=asistencias_mes,
        ultimo_ingreso=ultimo_ingreso,
        segmento_actividad=_classify_activity(asistencias_mes),
        # Financiero
        pagos_pendientes=pagos_pendientes,
        deuda_total=float(deuda_total),
        segmento_financiero=_classify_financial(pagos_pendientes),
    )


def _apply_filters(
    results: list[ClientSegmentationResponse],
    filters: SegmentationFilter,
) -> list[ClientSegmentationResponse]:
    """
    Aplica los filtros de la query sobre la lista ya calculada.
    Se hace en Python (no en SQL) porque la segmentación es calculada,
    no persistida; los filtros son AND entre sí.
    """
    out = results

    if filters.sexo is not None:
        out = [r for r in out if r.sexo == filters.sexo]

    if filters.grupo_edad is not None:
        out = [r for r in out if r.grupo_edad == filters.grupo_edad]

    if filters.segmento_actividad is not None:
        out = [r for r in out if r.segmento_actividad == filters.segmento_actividad]

    if filters.segmento_financiero is not None:
        out = [r for r in out if r.segmento_financiero == filters.segmento_financiero]

    if filters.edad_min is not None:
        out = [r for r in out if r.edad >= filters.edad_min]

    if filters.edad_max is not None:
        out = [r for r in out if r.edad <= filters.edad_max]

    return out


# ══════════════════════════════════════════════════════════════════════════════
# SERVICIO PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

class SegmentationService:
    """
    Orquesta repositorios y funciones de clasificación para generar
    la segmentación completa de clientes.

    Patrón bulk:
      El listado de todos los clientes ejecuta 3 queries agregadas (una por
      dimensión) y luego construye los objetos en Python — evita N+1.
    """

    def __init__(self, db: Session) -> None:
        self._repo = SegmentationRepository(db)

    # ── Segmentación individual ────────────────────────────────────────────────

    def get_client_segmentation(self, client_id: int) -> ClientSegmentationResponse:
        """
        Calcula la segmentación completa de un cliente específico.

        Raises:
            ClientNotFoundException: Si el cliente no existe.
        """
        client = self._repo.get_client_by_id(client_id)
        if client is None:
            raise ClientNotFoundException(
                f"No se encontró el cliente con id={client_id}"
            )

        asistencias_mes = self._repo.count_approved_attendances_current_month(client_id)
        ultimo_ingreso  = self._repo.get_last_approved_attendance_date(client_id)
        pagos_pendientes = self._repo.count_pending_payments(client_id)
        deuda_total      = self._repo.sum_pending_balance(client_id)

        return _build_segmentation(
            client=client,
            asistencias_mes=asistencias_mes,
            ultimo_ingreso=ultimo_ingreso,
            pagos_pendientes=pagos_pendientes,
            deuda_total=deuda_total,
        )

    # ── Segmentación masiva (listado) ──────────────────────────────────────────

    def list_clients_segmentation(
        self,
        filters: SegmentationFilter,
        only_active: bool = True,
    ) -> list[ClientSegmentationResponse]:
        """
        Calcula y retorna la segmentación de todos los clientes.
        Usa queries bulk para evitar N+1 en listas grandes.

        Args:
            filters: Filtros de segmentación a aplicar.
            only_active: Si True (defecto), solo incluye clientes activos.

        Returns:
            Lista de segmentaciones filtradas y ordenadas por apellido.
        """
        clients = (
            self._repo.list_active_clients()
            if only_active
            else self._repo.list_all_clients()
        )

        if not clients:
            return []

        # Queries bulk: una sola consulta por dimensión para todos los clientes
        bulk_asistencias = self._repo.bulk_count_approved_current_month()
        bulk_ultimo      = self._repo.bulk_last_attendance_date()
        bulk_pagos       = self._repo.bulk_pending_payments()

        results: list[ClientSegmentationResponse] = []
        for client in clients:
            asistencias_mes  = bulk_asistencias.get(client.id, 0)
            ultimo_ingreso   = bulk_ultimo.get(client.id)
            pend_data        = bulk_pagos.get(client.id, (0, Decimal("0.00")))
            pagos_pendientes = pend_data[0]
            deuda_total      = pend_data[1]

            seg = _build_segmentation(
                client=client,
                asistencias_mes=asistencias_mes,
                ultimo_ingreso=ultimo_ingreso,
                pagos_pendientes=pagos_pendientes,
                deuda_total=deuda_total,
            )
            results.append(seg)

        return _apply_filters(results, filters)

    # ── Resumen estadístico ────────────────────────────────────────────────────

    def get_segmentation_summary(self) -> SegmentationSummaryResponse:
        """
        Genera estadísticas agregadas de segmentación para todos los clientes activos.

        Calcula distribuciones por:
          - Sexo y grupo de edad (demográfico)
          - Segmento de actividad
          - Segmento financiero
          - Deuda total del sistema

        Returns:
            SegmentationSummaryResponse con los contadores agregados.
        """
        # Reutiliza list_clients_segmentation (ya tiene el patrón bulk)
        all_segs = self.list_clients_segmentation(
            filters=SegmentationFilter(), only_active=True
        )

        # ── Demográfico ────────────────────────────────────────────────────────
        masculino = sum(1 for s in all_segs if s.sexo.value == "masculino")
        femenino  = sum(1 for s in all_segs if s.sexo.value == "femenino")
        otro      = sum(1 for s in all_segs if s.sexo.value == "otro")
        joven     = sum(1 for s in all_segs if s.grupo_edad == AgeGroup.JOVEN)
        adulto    = sum(1 for s in all_segs if s.grupo_edad == AgeGroup.ADULTO)

        # ── Actividad ──────────────────────────────────────────────────────────
        activos      = sum(1 for s in all_segs if s.segmento_actividad == ActivitySegment.ACTIVO)
        poco_activos = sum(1 for s in all_segs if s.segmento_actividad == ActivitySegment.POCO_ACTIVO)
        inactivos    = sum(1 for s in all_segs if s.segmento_actividad == ActivitySegment.INACTIVO)

        # ── Financiero ─────────────────────────────────────────────────────────
        sin_deuda      = sum(1 for s in all_segs if s.segmento_financiero == FinancialSegment.SIN_DEUDA)
        con_deuda      = sum(1 for s in all_segs if s.segmento_financiero == FinancialSegment.CON_DEUDA)
        deuda_sistema  = self._repo.sum_total_pending_balance_system()

        total = len(all_segs)

        return SegmentationSummaryResponse(
            total_clientes_activos=total,
            demografico=DemographicBreakdown(
                masculino=masculino,
                femenino=femenino,
                otro=otro,
                joven=joven,
                adulto=adulto,
                total=total,
            ),
            actividad=ActivityBreakdown(
                activo=activos,
                poco_activo=poco_activos,
                inactivo=inactivos,
                total=total,
            ),
            financiero=FinancialBreakdown(
                sin_deuda=sin_deuda,
                con_deuda=con_deuda,
                total=total,
                deuda_total_sistema=float(deuda_sistema),
            ),
        )
