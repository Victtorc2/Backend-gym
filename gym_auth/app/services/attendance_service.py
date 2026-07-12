"""
Servicio de Asistencias.
Implementa el flujo completo de validación de ingreso al gimnasio:

    Tarjeta → Cliente → Membresía → Pagos → Registrar resultado

Siempre registra el intento (aprobado o denegado) para trazabilidad completa.
"""
from __future__ import annotations

import math
from datetime import date, datetime

from app.core.constants import (
    LIMA_TZ,
    AttendanceStatus,
    CardStatus,
    ClientStatus,
    DenialReason,
    MembershipStatus,
    PaymentStatus,
)
from app.core.exceptions import ClientNotFoundException
from app.repositories.attendance_repository import AttendanceRepository
from app.repositories.card_repository import CardRepository
from app.repositories.client_repository import ClientRepository
from app.repositories.membership_repository import MembershipRepository
from app.repositories.payment_repository import PaymentRepository
from app.schemas.attendance_schema import (
    AttendanceCheckInSchema,
    AttendanceFilterSchema,
    AttendanceFrequencySchema,
    AttendanceResponseSchema,
    CheckInResultSchema,
    PaginatedAttendanceSchema,
)


class AttendanceService:
    """Gestiona el control de acceso y el historial de asistencias."""

    def __init__(
        self,
        attendance_repo: AttendanceRepository,
        card_repo: CardRepository,
        client_repo: ClientRepository,
        membership_repo: MembershipRepository,
        payment_repo: PaymentRepository,
    ) -> None:
        self._attendances = attendance_repo
        self._cards = card_repo
        self._clients = client_repo
        self._memberships = membership_repo
        self._payments = payment_repo

    # ── Validar ingreso ────────────────────────────────────────────────────────

    def validate_check_in(self, data: AttendanceCheckInSchema) -> CheckInResultSchema:
        """
        Valida el acceso de un cliente mediante su código de tarjeta.

        Cadena de validaciones (se detiene en el primer fallo):
            1. Tarjeta existe.
            2. Tarjeta activa.
            3. Cliente existe y está activo.
            4. Membresía activa y vigente (fecha_fin >= hoy).
            5. Sin deuda vencida en pagos.

        Siempre registra el intento en la tabla asistencias con su resultado
        y motivo, independientemente del resultado.

        Returns:
            CheckInResultSchema con el registro creado y el veredicto.
        """
        now = datetime.now(LIMA_TZ)
        today = now.date()
        hora_actual = now.time()

        # ── 1. Tarjeta existe ──────────────────────────────────────────────────
        tarjeta = self._cards.get_by_codigo(data.codigo_tarjeta.upper().strip())
        if tarjeta is None:
            # Sin tarjeta no tenemos cliente_id → no podemos registrar asistencia
            # Se lanza excepción; el handler global la convierte en 404 uniforme
            from app.core.exceptions import CardNotFoundException
            raise CardNotFoundException("Tarjeta no encontrada: " + data.codigo_tarjeta)

        cliente_id = tarjeta.cliente_id

        # ── 2. Tarjeta activa ──────────────────────────────────────────────────
        if tarjeta.estado != CardStatus.ACTIVA:
            return self._register_and_build(
                cliente_id=cliente_id,
                tarjeta_id=tarjeta.id,
                fecha=today,
                hora=hora_actual,
                estado=AttendanceStatus.INGRESO_DENEGADO,
                motivo=DenialReason.TARJETA_INACTIVA,
                nombre_cliente=self._safe_nombre(cliente_id),
            )

        # ── 3. Cliente activo ──────────────────────────────────────────────────
        cliente = self._clients.get_by_id(cliente_id)
        if cliente is None or cliente.estado != ClientStatus.ACTIVO:
            return self._register_and_build(
                cliente_id=cliente_id,
                tarjeta_id=tarjeta.id,
                fecha=today,
                hora=hora_actual,
                estado=AttendanceStatus.INGRESO_DENEGADO,
                motivo=DenialReason.CLIENTE_INACTIVO,
                nombre_cliente=self._safe_nombre(cliente_id),
            )

        nombre_cliente = f"{cliente.nombres} {cliente.apellidos}"

        # ── 4. Membresía activa y vigente ──────────────────────────────────────
        membresia = self._memberships.get_active_by_cliente(cliente_id)

        if membresia is None:
            return self._register_and_build(
                cliente_id=cliente_id,
                tarjeta_id=tarjeta.id,
                fecha=today,
                hora=hora_actual,
                estado=AttendanceStatus.INGRESO_DENEGADO,
                motivo=DenialReason.MEMBRESIA_INEXISTENTE,
                nombre_cliente=nombre_cliente,
            )

        if membresia.estado == MembershipStatus.VENCIDA or today > membresia.fecha_fin:
            return self._register_and_build(
                cliente_id=cliente_id,
                tarjeta_id=tarjeta.id,
                fecha=today,
                hora=hora_actual,
                estado=AttendanceStatus.INGRESO_DENEGADO,
                motivo=DenialReason.MEMBRESIA_VENCIDA,
                nombre_cliente=nombre_cliente,
            )

        # ── 5. Sin deuda vencida ───────────────────────────────────────────────
        if self._has_overdue_debt(cliente_id):
            return self._register_and_build(
                cliente_id=cliente_id,
                tarjeta_id=tarjeta.id,
                fecha=today,
                hora=hora_actual,
                estado=AttendanceStatus.INGRESO_DENEGADO,
                motivo=DenialReason.DEUDA_VENCIDA,
                nombre_cliente=nombre_cliente,
            )

        # ── Todas las validaciones pasaron: ingreso aprobado ───────────────────
        return self._register_and_build(
            cliente_id=cliente_id,
            tarjeta_id=tarjeta.id,
            fecha=today,
            hora=hora_actual,
            estado=AttendanceStatus.INGRESO_APROBADO,
            motivo=None,
            nombre_cliente=nombre_cliente,
        )

    # ── Consultas ──────────────────────────────────────────────────────────────

    def get_attendance(self, attendance_id: int) -> AttendanceResponseSchema:
        """Obtiene un registro por ID."""
        from app.core.exceptions import AttendanceNotFoundException
        record = self._attendances.get_by_id(attendance_id)
        if record is None:
            raise AttendanceNotFoundException()
        return self._to_response(record)

    def list_attendances(self, filters: AttendanceFilterSchema) -> PaginatedAttendanceSchema:
        """Lista asistencias con filtros y paginación."""
        items, total = self._attendances.list_paginated(
            page=filters.page,
            per_page=filters.per_page,
            cliente_id=filters.cliente_id,
            estado=filters.estado,
            fecha_desde=filters.fecha_desde,
            fecha_hasta=filters.fecha_hasta,
        )
        total_pages = math.ceil(total / filters.per_page) if total > 0 else 1
        return PaginatedAttendanceSchema(
            items=[self._to_response(a) for a in items],
            total=total,
            page=filters.page,
            per_page=filters.per_page,
            total_pages=total_pages,
        )

    def get_client_history(self, cliente_id: int) -> list[AttendanceResponseSchema]:
        """Lista el historial completo de asistencias de un cliente."""
        if self._clients.get_by_id(cliente_id) is None:
            raise ClientNotFoundException()
        records = self._attendances.get_by_cliente(cliente_id)
        return [self._to_response(a) for a in records]

    def get_frequency(self, cliente_id: int) -> AttendanceFrequencySchema:
        """
        Calcula estadísticas de frecuencia de asistencia de un cliente.

        Raises:
            ClientNotFoundException: Si el cliente no existe.
        """
        cliente = self._clients.get_by_id(cliente_id)
        if cliente is None:
            raise ClientNotFoundException()

        stats = self._attendances.get_frequency_stats(cliente_id)
        return AttendanceFrequencySchema(
            cliente_id=cliente_id,
            nombre_cliente=f"{cliente.nombres} {cliente.apellidos}",
            **stats,
        )

    # ── Helpers privados ───────────────────────────────────────────────────────

    @staticmethod
    def _to_response(record) -> AttendanceResponseSchema:
        """
        Construye el schema de respuesta e incluye el nombre completo del cliente
        cuando la relación está disponible (para mostrarlo en los listados).
        """
        schema = AttendanceResponseSchema.model_validate(record)
        cliente = getattr(record, "cliente", None)
        if cliente is not None:
            schema.nombre_cliente = f"{cliente.nombres} {cliente.apellidos}"
        return schema

    def _register_and_build(
        self,
        *,
        cliente_id: int,
        tarjeta_id: int,
        fecha: date,
        hora,
        estado: AttendanceStatus,
        motivo: DenialReason | None,
        nombre_cliente: str,
    ) -> CheckInResultSchema:
        """
        Persiste el registro de asistencia y construye la respuesta uniforme.
        Separa la responsabilidad de persistir de la de construir el resultado.
        """
        record = self._attendances.create(
            cliente_id=cliente_id,
            tarjeta_id=tarjeta_id,
            fecha=fecha,
            hora=hora,
            estado=estado,
            motivo_denegacion=motivo,
        )

        # Mensajes legibles para el operador de recepción
        _mensajes: dict[DenialReason | None, str] = {
            None: "Acceso permitido",
            DenialReason.TARJETA_INACTIVA: "Tarjeta desactivada",
            DenialReason.CLIENTE_INACTIVO: "Cliente inactivo",
            DenialReason.MEMBRESIA_INEXISTENTE: "Sin membresía activa",
            DenialReason.MEMBRESIA_VENCIDA: "Membresía vencida",
            DenialReason.DEUDA_VENCIDA: "Deuda vencida pendiente de pago",
        }

        return CheckInResultSchema(
            asistencia=AttendanceResponseSchema.model_validate(record),
            nombre_cliente=nombre_cliente,
            acceso_permitido=(estado == AttendanceStatus.INGRESO_APROBADO),
            motivo=_mensajes.get(motivo),
        )

    def _has_overdue_debt(self, cliente_id: int) -> bool:
        """
        Verifica si el cliente tiene al menos un pago en estado VENCIDO
        con saldo pendiente mayor a cero.
        """
        from decimal import Decimal
        payments = self._payments.get_by_cliente(cliente_id)
        return any(
            p.estado == PaymentStatus.VENCIDO and p.saldo_pendiente > Decimal("0")
            for p in payments
        )

    def _safe_nombre(self, cliente_id: int) -> str:
        """Retorna nombre del cliente o 'Desconocido' si no se puede recuperar."""
        c = self._clients.get_by_id(cliente_id)
        return f"{c.nombres} {c.apellidos}" if c else "Desconocido"
