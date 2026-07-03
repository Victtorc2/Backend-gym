"""
Servicio del Portal de Cliente (Fase 10 — Módulos Cliente).
Orquesta la lógica de consulta para el cliente autenticado.

Principios de seguridad:
- El objeto `Client` siempre llega ya resuelto desde el JWT.
- Nunca se exponen datos de otros clientes.
- Solo lectura: no modifica ningún dato del sistema.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from app.core.constants import (
    LIMA_TZ,
    AffluenceLevel,
    ClientStatus,
    PYTHON_WEEKDAY_TO_ENUM,
    PaymentStatus,
    WeekDay,
)
from app.core.exceptions import InactiveUserException
from app.models.client import Client
from app.repositories.client_dashboard_repository import ClientDashboardRepository
from app.schemas.client_dashboard_schema import (
    BloqueHorarioSchema,
    LogoutResponseSchema,
    MiAsistenciaItemSchema,
    MiAsistenciaSchema,
    MiDeudaSchema,
    MiFrecuenciaSchema,
    MiHistorialPagosSchema,
    MiHorarioRecomendadoSchema,
    MiMembresiaSchema,
    MiPagoSchema,
    MiPerfilSchema,
    MisPagosSchema,
    RecomendacionPersonalSchema,
    SinMembresiaSchema,
)
from app.utils.recommendation_utils import format_hour_range


class ClientDashboardService:
    """Servicio de solo lectura del portal del cliente autenticado."""

    def __init__(self, repo: ClientDashboardRepository) -> None:
        self._repo = repo

    # ── Guardia de estado ──────────────────────────────────────────────────────

    @staticmethod
    def _assert_active(client: Client) -> None:
        """Verifica que el cliente esté activo antes de exponer información operativa."""
        if client.estado != ClientStatus.ACTIVO:
            raise InactiveUserException()

    @staticmethod
    def _calcular_edad(fecha_nacimiento: date) -> int:
        """Calcula la edad en años cumplidos."""
        hoy = date.today()
        return (
            hoy.year - fecha_nacimiento.year
            - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))
        )

    # ══════════════════════════════════════════════════════════════════════════
    #  MÓDULO 1 — MI MEMBRESÍA
    # ══════════════════════════════════════════════════════════════════════════

    def get_mi_membresia(self, client: Client) -> MiMembresiaSchema | SinMembresiaSchema:
        """Devuelve la membresía activa del cliente con días restantes calculados."""
        self._assert_active(client)

        membresia = self._repo.get_active_membership(client.id)
        today = date.today()

        if membresia is None or today > membresia.fecha_fin:
            return SinMembresiaSchema()

        return MiMembresiaSchema(
            id=membresia.id,
            tipo=membresia.tipo,
            precio=membresia.precio,
            fecha_inicio=membresia.fecha_inicio,
            fecha_fin=membresia.fecha_fin,
            dias_restantes=max(0, (membresia.fecha_fin - today).days),
            estado=membresia.estado,
            vigente=True,
        )

    # ══════════════════════════════════════════════════════════════════════════
    #  MÓDULO 2 — MIS PAGOS
    # ══════════════════════════════════════════════════════════════════════════

    def get_mis_pagos(self, client: Client) -> MisPagosSchema:
        """Devuelve el resumen de pagos del cliente con totales."""
        self._assert_active(client)

        pagos = self._repo.get_payments(client.id)
        total_pagado = sum((p.monto_pagado for p in pagos), Decimal("0"))
        deuda = sum(
            (p.saldo_pendiente for p in pagos
             if p.estado in (PaymentStatus.PENDIENTE, PaymentStatus.VENCIDO)),
            Decimal("0"),
        )

        return MisPagosSchema(
            total_pagos=len(pagos),
            total_pagado=total_pagado,
            deuda_pendiente=deuda,
            pagos=[MiPagoSchema.model_validate(p) for p in pagos],
        )

    def get_historial_pagos(self, client: Client) -> MiHistorialPagosSchema:
        """Devuelve el historial cronológico completo de pagos."""
        self._assert_active(client)
        pagos = self._repo.get_payments(client.id)
        return MiHistorialPagosSchema(
            total_registros=len(pagos),
            historial=[MiPagoSchema.model_validate(p) for p in pagos],
        )

    def get_mi_deuda(self, client: Client) -> MiDeudaSchema:
        """Devuelve el estado de deuda consolidado del cliente."""
        self._assert_active(client)

        agg = self._repo.get_debt_aggregates(client.id)
        total = Decimal(str(agg["total_deuda"]))
        tiene_deuda = total > Decimal("0")

        return MiDeudaSchema(
            tiene_deuda=tiene_deuda,
            monto_total_deuda=total,
            pagos_pendientes=agg["pagos_pendientes"],
            pagos_vencidos=agg["pagos_vencidos"],
            mensaje=(
                f"Tienes una deuda pendiente de {total}"
                if tiene_deuda else "No tienes deudas pendientes"
            ),
        )

    # ══════════════════════════════════════════════════════════════════════════
    #  MÓDULO 3 — MI ASISTENCIA
    # ══════════════════════════════════════════════════════════════════════════

    def get_mi_asistencia(self, client: Client) -> MiAsistenciaSchema:
        """Devuelve el historial completo de asistencia del cliente."""
        self._assert_active(client)

        records = self._repo.get_attendances(client.id)
        from app.core.constants import AttendanceStatus

        aprobados = sum(1 for a in records if a.estado == AttendanceStatus.INGRESO_APROBADO)
        denegados = sum(1 for a in records if a.estado == AttendanceStatus.INGRESO_DENEGADO)

        historial = [
            MiAsistenciaItemSchema(
                id=a.id,
                fecha=a.fecha,
                hora=a.hora.strftime("%H:%M") if a.hora else "00:00",
                estado=a.estado,
                motivo_denegacion=a.motivo_denegacion,
            )
            for a in records
        ]

        return MiAsistenciaSchema(
            total_asistencias=len(records),
            total_aprobados=aprobados,
            total_denegados=denegados,
            historial=historial,
        )

    def get_mi_frecuencia(self, client: Client) -> MiFrecuenciaSchema:
        """Devuelve estadísticas de frecuencia con cálculo de visitas semanales."""
        self._assert_active(client)

        stats = self._repo.get_attendance_frequency(client.id)
        frecuencia_semanal = self._calc_frecuencia_semanal(
            stats["total_ingresos"],
            stats["primer_ingreso"],
            stats["ultimo_ingreso"],
        )

        return MiFrecuenciaSchema(
            total_ingresos=stats["total_ingresos"],
            asistencias_mes_actual=stats["asistencias_mes_actual"],
            frecuencia_semanal=frecuencia_semanal,
            primer_ingreso=stats["primer_ingreso"],
            ultimo_ingreso=stats["ultimo_ingreso"],
        )

    # ══════════════════════════════════════════════════════════════════════════
    #  MÓDULO 4 — MI PERFIL
    # ══════════════════════════════════════════════════════════════════════════

    def get_mi_perfil(self, client: Client) -> MiPerfilSchema:
        """Devuelve los datos personales del cliente (visible aunque esté inactivo)."""
        return MiPerfilSchema(
            id=client.id,
            nombres=client.nombres,
            apellidos=client.apellidos,
            dni=client.dni,
            correo=client.correo,
            telefono=client.telefono,
            sexo=client.sexo,
            edad=self._calcular_edad(client.fecha_nacimiento),
            grupo_edad=client.grupo_edad,
            ocupacion=client.ocupacion,
            direccion=client.direccion,
            estado=client.estado,
            miembro_desde=client.created_at,
        )

    # ══════════════════════════════════════════════════════════════════════════
    #  MÓDULO 5 — MI HORARIO RECOMENDADO
    # ══════════════════════════════════════════════════════════════════════════

    def get_mi_horario_recomendado(self, client: Client) -> MiHorarioRecomendadoSchema:
        """
        Devuelve los horarios recomendados para el día actual,
        integrando con el módulo de Recomendación Inteligente de Horarios.
        """
        self._assert_active(client)

        # Recomendación personalizada asignada por el admin (si existe)
        personal = self._get_recomendacion_personal(client.id)

        # Afluencia YA declarada por otros clientes para hoy (check-in / plan)
        hoy = datetime.now(LIMA_TZ).date()
        confirmados = self._repo.count_declared_plans(hoy)
        declarados_hora = self._repo.declared_plans_by_hour(hoy)

        # Determinar el día actual (hora de Lima)
        dia_enum_str = PYTHON_WEEKDAY_TO_ENUM.get(hoy.weekday())

        # Si hoy es domingo (gimnasio cerrado), no hay recomendaciones
        if dia_enum_str is None:
            return MiHorarioRecomendadoSchema(
                dia_actual=WeekDay.LUNES,
                recomendacion_personal=personal,
                horario_recomendado=None,
                horario_a_evitar=None,
                horarios_libres_hoy=[],
                horas_pico_hoy=[],
                confirmados_hoy=confirmados,
                mensaje="El gimnasio no opera los domingos. Vuelve el lunes.",
            )

        dia_actual = WeekDay(dia_enum_str)
        bloques = self._repo.get_recommendations_by_day(dia_actual)

        if not bloques:
            return MiHorarioRecomendadoSchema(
                dia_actual=dia_actual,
                recomendacion_personal=personal,
                horario_recomendado=None,
                horario_a_evitar=None,
                horarios_libres_hoy=[],
                horas_pico_hoy=[],
                confirmados_hoy=confirmados,
                mensaje="Aún no hay recomendaciones generadas para hoy",
            )

        def to_bloque(b) -> BloqueHorarioSchema:
            return BloqueHorarioSchema(
                dia_semana=b.dia_semana,
                horario=format_hour_range(b.hora_inicio, b.hora_fin),
                promedio_personas=float(b.cantidad_promedio),
                nivel_afluencia=b.nivel_afluencia,
            )

        # Carga combinada = promedio histórico + clientes que ya declararon esa hora hoy
        def carga_combinada(b) -> float:
            return float(b.cantidad_promedio) + declarados_hora.get(b.hora_inicio.hour, 0)

        recomendado = min(bloques, key=carga_combinada)
        a_evitar = max(bloques, key=carga_combinada)
        libres = [to_bloque(b) for b in bloques if b.es_recomendado]
        picos = [to_bloque(b) for b in bloques if b.evitar]

        # Si el admin le asignó una recomendación personal, se destaca primero
        if personal is not None:
            mensaje = (
                f"Tu entrenador te recomienda venir el {personal.dia_semana.value} "
                f"de {personal.horario} (menos gente)."
            )
        else:
            extra = f" · {confirmados} personas ya confirmaron para hoy" if confirmados else ""
            mensaje = (
                f"Hoy {dia_actual.value}, el mejor horario es "
                f"{format_hour_range(recomendado.hora_inicio, recomendado.hora_fin)} "
                f"(~{carga_combinada(recomendado):.0f} personas estimadas){extra}"
            )

        return MiHorarioRecomendadoSchema(
            dia_actual=dia_actual,
            recomendacion_personal=personal,
            horario_recomendado=to_bloque(recomendado),
            horario_a_evitar=to_bloque(a_evitar),
            horarios_libres_hoy=libres,
            horas_pico_hoy=picos,
            confirmados_hoy=confirmados,
            mensaje=mensaje,
        )

    def _get_recomendacion_personal(
        self, cliente_id: int
    ) -> RecomendacionPersonalSchema | None:
        """Construye la recomendación personal activa del cliente, si existe."""
        rec = self._repo.get_active_personal_recommendation(cliente_id)
        if rec is None:
            return None
        return RecomendacionPersonalSchema(
            dia_semana=rec.dia_semana,
            horario=format_hour_range(rec.hora_inicio, rec.hora_fin),
            nivel_afluencia=rec.nivel_afluencia,
            mensaje=rec.mensaje,
            asignada_el=rec.created_at,
        )

    # ══════════════════════════════════════════════════════════════════════════
    #  MÓDULO 6 — LOGOUT
    # ══════════════════════════════════════════════════════════════════════════

    def logout(self, client: Client) -> LogoutResponseSchema:
        """
        Cierra la sesión del cliente.

        Con JWT stateless, la invalidación efectiva ocurre en el cliente
        (descartando el token). La estructura queda preparada para una
        blacklist futura de tokens si se requiere invalidación server-side.
        """
        # Punto de extensión: aquí se registraría el token en una blacklist.
        return LogoutResponseSchema(
            sesion_cerrada=True,
            mensaje="Sesión cerrada correctamente. Elimina el token del cliente.",
        )

    # ── Helpers privados ───────────────────────────────────────────────────────

    @staticmethod
    def _calc_frecuencia_semanal(
        total_ingresos: int,
        primer_ingreso: date | None,
        ultimo_ingreso: date | None,
    ) -> float:
        """
        Calcula el promedio de visitas por semana.

        Usa el rango entre el primer y último ingreso para estimar
        la cantidad de semanas activas del cliente.
        """
        if not primer_ingreso or total_ingresos == 0:
            return 0.0

        fin = ultimo_ingreso or date.today()
        dias_activo = max(1, (fin - primer_ingreso).days + 1)
        semanas = max(1, dias_activo / 7)
        return round(total_ingresos / semanas, 2)
