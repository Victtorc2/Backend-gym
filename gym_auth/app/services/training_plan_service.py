"""
Servicio de Planificación de Entrenamiento del cliente.

Resuelve las máquinas a partir de las zonas y/o la rutina elegida, registra la
intención de uso (no es reserva) y devuelve el valor agregado: avisos de
demanda por zona en su horario y una sugerencia de orden para evitar colas.
"""
from __future__ import annotations

from datetime import date

from app.core.constants import (
    ClientStatus,
    DemandLevel,
    MuscleZone,
    TrainingPlanStatus,
)
from app.core.exceptions import (
    InactiveUserException,
    RoutineNotFoundException,
    TrainingPlanInvalidException,
    TrainingPlanNotFoundException,
)
from app.models.client import Client
from app.repositories.demand_repository import DemandRepository
from app.repositories.machine_repository import MachineRepository
from app.repositories.routine_repository import RoutineRepository
from app.repositories.training_plan_repository import TrainingPlanRepository
from app.schemas.training_plan_schema import (
    DemandHintSchema,
    PlanMachineItemSchema,
    TrainingPlanCreateSchema,
    TrainingPlanResponseSchema,
    TrainingPlanStatusUpdateSchema,
)
from app.utils.demand_utils import classify_demand_level, hour_block_label

# Niveles que disparan un aviso de alta demanda al cliente
_HIGH_LEVELS = {DemandLevel.ALTO, DemandLevel.MUY_ALTO}


class TrainingPlanService:
    """Planificación del cliente + valor agregado de demanda."""

    def __init__(
        self,
        repo: TrainingPlanRepository,
        machine_repo: MachineRepository,
        routine_repo: RoutineRepository,
        demand_repo: DemandRepository,
    ) -> None:
        self._repo = repo
        self._machines = machine_repo
        self._routines = routine_repo
        self._demand = demand_repo

    @staticmethod
    def _assert_active(client: Client) -> None:
        if client.estado != ClientStatus.ACTIVO:
            raise InactiveUserException()

    # ── Crear / actualizar plan ─────────────────────────────────────────────────

    def plan_day(
        self, client: Client, data: TrainingPlanCreateSchema
    ) -> TrainingPlanResponseSchema:
        """Registra (o reemplaza) la planificación del cliente para una fecha."""
        self._assert_active(client)

        if not data.zonas and data.rutina_id is None:
            raise TrainingPlanInvalidException(
                "Debes indicar al menos una zona muscular o una rutina"
            )

        # Resolver máquinas desde zonas y/o rutina
        maquina_ids: list[int] = []
        if data.zonas:
            maquina_ids += [m.id for m in self._machines.list_active_by_zones(data.zonas)]

        if data.rutina_id is not None:
            routine = self._routines.get_by_id(data.rutina_id)
            if routine is None:
                raise RoutineNotFoundException()
            maquina_ids += [rm.maquina_id for rm in routine.maquinas]

        maquina_ids = list(dict.fromkeys(maquina_ids))  # únicos
        if not maquina_ids:
            raise TrainingPlanInvalidException(
                "No hay máquinas asociadas a las zonas o rutina seleccionadas"
            )

        plan = self._repo.upsert(
            cliente_id=client.id,
            fecha=data.fecha,
            hora_inicio=data.hora_inicio,
            estado=data.estado,
            rutina_id=data.rutina_id,
            maquina_ids=maquina_ids,
        )
        return self._build_response(plan, con_valor_agregado=True)

    def checkin(
        self, client: Client, hora_inicio, fecha: date | None = None
    ) -> TrainingPlanResponseSchema:
        """
        Declaración rápida de asistencia: el cliente indica a qué hora irá.
        Crea/actualiza el plan del día como CONFIRMADO. Conserva las máquinas
        y rutina si ya había planificado; si no, queda solo la intención de hora.
        """
        self._assert_active(client)
        objetivo = fecha or date.today()

        existing = self._repo.get_for_client_date(client.id, objetivo)
        maquina_ids = [pm.maquina_id for pm in existing.maquinas] if existing else []
        rutina_id = existing.rutina_id if existing else None

        plan = self._repo.upsert(
            cliente_id=client.id,
            fecha=objetivo,
            hora_inicio=hora_inicio,
            estado=TrainingPlanStatus.CONFIRMADO,
            rutina_id=rutina_id,
            maquina_ids=maquina_ids,
        )
        return self._build_response(plan, con_valor_agregado=True)

    def update_status(
        self, client: Client, data: TrainingPlanStatusUpdateSchema, fecha: date | None = None
    ) -> TrainingPlanResponseSchema:
        """Cambia el nivel de compromiso (confirmar / en camino / cancelar)."""
        self._assert_active(client)
        objetivo = fecha or date.today()
        plan = self._repo.get_for_client_date(client.id, objetivo)
        if plan is None:
            raise TrainingPlanNotFoundException("No tienes un plan para esa fecha")
        plan = self._repo.update_status(plan, data.estado)
        return self._build_response(plan, con_valor_agregado=False)

    # ── Consultas del cliente ───────────────────────────────────────────────────

    def get_today(self, client: Client) -> TrainingPlanResponseSchema | None:
        self._assert_active(client)
        plan = self._repo.get_for_client_date(client.id, date.today())
        if plan is None:
            return None
        return self._build_response(plan, con_valor_agregado=True)

    def list_mine(self, client: Client) -> list[TrainingPlanResponseSchema]:
        self._assert_active(client)
        return [
            self._build_response(p, con_valor_agregado=False)
            for p in self._repo.list_for_client(client.id)
        ]

    def cancel_today(self, client: Client) -> None:
        self._assert_active(client)
        plan = self._repo.get_for_client_date(client.id, date.today())
        if plan is None:
            raise TrainingPlanNotFoundException("No tienes un plan para hoy")
        self._repo.delete(plan)

    # ── Construcción de respuesta + valor agregado ──────────────────────────────

    def _build_response(
        self, plan, con_valor_agregado: bool
    ) -> TrainingPlanResponseSchema:
        maquinas = [
            PlanMachineItemSchema(
                maquina_id=pm.maquina.id, nombre=pm.maquina.nombre, zona=pm.maquina.zona
            )
            for pm in plan.maquinas
            if pm.maquina is not None
        ]
        zonas: list[MuscleZone] = list(dict.fromkeys(m.zona for m in maquinas))

        avisos: list[DemandHintSchema] = []
        sugerencia_orden: str | None = None

        if con_valor_agregado and zonas:
            hora = plan.hora_inicio.hour
            demanda_zonas = self._demand.zone_distribution(plan.fecha, hora=hora)

            # Avisos por zona con alta demanda en el horario
            for zona in zonas:
                clientes = demanda_zonas.get(zona, 0)
                nivel = classify_demand_level(clientes)
                if nivel in _HIGH_LEVELS:
                    avisos.append(DemandHintSchema(
                        zona=zona,
                        nivel=nivel,
                        clientes_previstos=clientes,
                        mensaje=(
                            f"Entre las {hour_block_label(hora)} la zona de "
                            f"{zona.value} tendrá demanda {nivel.value.replace('_', ' ')}."
                        ),
                    ))

            # Sugerencia de orden: empezar por la zona menos congestionada
            if len(zonas) >= 2:
                ordenadas = sorted(zonas, key=lambda z: demanda_zonas.get(z, 0))
                menos, mas = ordenadas[0], ordenadas[-1]
                if demanda_zonas.get(mas, 0) > demanda_zonas.get(menos, 0):
                    sugerencia_orden = (
                        f"Para reducir el tiempo de espera, empieza por los ejercicios de "
                        f"{menos.value} y deja {mas.value} para el final. No cambies tu "
                        f"rutina, solo el orden."
                    )

        mensaje = self._mensaje_estado(plan.estado)
        return TrainingPlanResponseSchema(
            id=plan.id,
            cliente_id=plan.cliente_id,
            fecha=plan.fecha,
            hora_inicio=plan.hora_inicio.strftime("%H:%M"),
            estado=plan.estado,
            rutina_id=plan.rutina_id,
            maquinas=maquinas,
            zonas=zonas,
            avisos_demanda=avisos,
            sugerencia_orden=sugerencia_orden,
            mensaje=mensaje,
            created_at=plan.created_at,
        )

    @staticmethod
    def _mensaje_estado(estado: TrainingPlanStatus) -> str:
        return {
            TrainingPlanStatus.PLANEADO: "Plan registrado. Confírmalo cuando estés seguro de asistir.",
            TrainingPlanStatus.CONFIRMADO: "¡Asistencia confirmada! Te esperamos.",
            TrainingPlanStatus.EN_CAMINO: "En camino registrado. Tu entrenamiento está activo.",
            TrainingPlanStatus.CANCELADO: "Tu plan fue cancelado.",
        }.get(estado, "Plan actualizado.")
