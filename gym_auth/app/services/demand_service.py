"""
Servicio de Gestión de Demanda (analítica predictiva para el administrador).

Entrega:
  - Dashboard de demanda prevista (por máquina, hora y zona) para una fecha.
  - Vista del entrenador: quiénes planificaron y quiénes no.
  - Índice de Demanda histórico + recomendación de inversión.
  - Precisión de la predicción (planificado vs asistido).
"""
from __future__ import annotations

from datetime import date

from app.core.constants import (
    DEMAND_INDEX_INVEST_THRESHOLD,
    GYM_CLOSE_HOUR,
    GYM_OPEN_HOUR,
    PYTHON_WEEKDAY_TO_ENUM,
    WeekDay,
)
from app.repositories.demand_repository import DemandRepository
from app.repositories.machine_repository import MachineRepository
from app.repositories.training_plan_repository import TrainingPlanRepository
from app.schemas.demand_schema import (
    HourAffluenceItemSchema,
    HourDemandItemSchema,
    InvestmentReportSchema,
    MachineDemandIndexSchema,
    MachineDemandItemSchema,
    PrecisionStatsSchema,
    PredictedAffluenceSchema,
    TodayDemandDashboardSchema,
    TrainerClientItemSchema,
    TrainerTodayViewSchema,
    ZoneDistributionItemSchema,
)
from app.utils.demand_utils import classify_demand_level, hour_block_label
from app.utils.recommendation_utils import classify_affluence


class DemandService:
    """Analítica de demanda para el administrador."""

    def __init__(
        self,
        demand_repo: DemandRepository,
        machine_repo: MachineRepository,
        plan_repo: TrainingPlanRepository,
    ) -> None:
        self._demand = demand_repo
        self._machines = machine_repo
        self._plans = plan_repo

    # ══════════════════════════════════════════════════════════════════════════
    #  DASHBOARD DE DEMANDA PREVISTA
    # ══════════════════════════════════════════════════════════════════════════

    def today_dashboard(self, fecha: date | None = None) -> TodayDemandDashboardSchema:
        objetivo = fecha or date.today()

        total = self._demand.count_plans(objetivo)
        por_maquina = self._demand.demand_by_machine(objetivo)
        por_maquina_hora = self._demand.demand_by_machine_hour(objetivo)
        por_hora = self._demand.demand_by_hour(objetivo)
        por_zona = self._demand.zone_distribution(objetivo)

        # ── Demanda por máquina + saturación ───────────────────────────────────
        machines = {m.id: m for m in self._machines.get_many_by_ids(list(por_maquina.keys()))}
        items_maquina: list[MachineDemandItemSchema] = []
        saturadas: list[str] = []
        for mid, clientes in por_maquina.items():
            m = machines.get(mid)
            if m is None:
                continue
            # Saturada si la demanda concurrente en algún bloque supera las unidades
            pico = max(
                (c for (mm, _h), c in por_maquina_hora.items() if mm == mid),
                default=0,
            )
            saturada = pico > m.cantidad
            if saturada:
                saturadas.append(m.nombre)
            items_maquina.append(MachineDemandItemSchema(
                maquina_id=mid,
                nombre=m.nombre,
                zona=m.zona,
                clientes=clientes,
                cantidad=m.cantidad,
                saturada=saturada,
            ))
        items_maquina.sort(key=lambda x: x.clientes, reverse=True)

        # ── Demanda por hora ────────────────────────────────────────────────────
        items_hora = [
            HourDemandItemSchema(
                horario=hour_block_label(h),
                clientes=c,
                nivel=classify_demand_level(c),
            )
            for h, c in sorted(por_hora.items())
        ]

        # ── Distribución por zonas ──────────────────────────────────────────────
        total_zona = sum(por_zona.values()) or 0
        items_zona = [
            ZoneDistributionItemSchema(
                zona=z,
                clientes=c,
                porcentaje=round((c / total_zona) * 100, 2) if total_zona else 0.0,
            )
            for z, c in sorted(por_zona.items(), key=lambda kv: kv[1], reverse=True)
        ]

        mensaje = (
            f"{total} clientes han planificado entrenar el {objetivo.isoformat()}."
            if total else f"Aún no hay planificaciones para el {objetivo.isoformat()}."
        )

        return TodayDemandDashboardSchema(
            fecha=objetivo,
            total_planes=total,
            demanda_por_maquina=items_maquina,
            demanda_por_hora=items_hora,
            distribucion_zonas=items_zona,
            maquinas_saturadas=saturadas,
            mensaje=mensaje,
        )

    # ══════════════════════════════════════════════════════════════════════════
    #  AFLUENCIA PREVISTA POR HORA (declarado + histórico)
    # ══════════════════════════════════════════════════════════════════════════

    def predicted_affluence(self, fecha: date | None = None) -> PredictedAffluenceSchema:
        """
        Combina las horas declaradas por los clientes (check-in / plan) con el
        promedio histórico de asistencia, para anticipar las horas pico del día.
        """
        objetivo = fecha or date.today()
        dia_str = PYTHON_WEEKDAY_TO_ENUM.get(objetivo.weekday())

        declared = self._demand.demand_by_hour(objetivo)
        historical = (
            self._demand.historical_affluence_by_hour(WeekDay(dia_str)) if dia_str else {}
        )
        total_declarados = sum(declared.values())

        por_hora: list[HourAffluenceItemSchema] = []
        for h in range(GYM_OPEN_HOUR, GYM_CLOSE_HOUR):
            d = declared.get(h, 0)
            hist = round(historical.get(h, 0.0))
            total = d + hist
            por_hora.append(HourAffluenceItemSchema(
                hora=h,
                horario=hour_block_label(h),
                declarados=d,
                historico=hist,
                total_estimado=total,
                nivel=classify_affluence(total),
            ))

        pico = max(por_hora, key=lambda x: x.total_estimado, default=None)
        hora_pico = pico.horario if pico and pico.total_estimado > 0 else None

        if dia_str is None:
            mensaje = "El gimnasio no opera los domingos."
        elif total_declarados == 0 and not historical:
            mensaje = f"Aún sin datos de afluencia para el {objetivo.isoformat()}."
        else:
            mensaje = (
                f"{total_declarados} cliente(s) declararon su hora para el "
                f"{objetivo.isoformat()}."
                + (f" Hora pico prevista: {hora_pico}." if hora_pico else "")
            )

        return PredictedAffluenceSchema(
            fecha=objetivo,
            dia_semana=dia_str,
            total_declarados=total_declarados,
            hora_pico_prevista=hora_pico,
            por_hora=por_hora,
            mensaje=mensaje,
        )

    # ══════════════════════════════════════════════════════════════════════════
    #  VISTA DEL ENTRENADOR
    # ══════════════════════════════════════════════════════════════════════════

    def trainer_today_view(self, fecha: date | None = None) -> TrainerTodayViewSchema:
        objetivo = fecha or date.today()

        planes = self._plans.list_for_date(objetivo)
        planes_por_cliente = {p.cliente_id: p for p in planes}

        con_plan: list[TrainerClientItemSchema] = []
        sin_plan: list[TrainerClientItemSchema] = []

        for cliente in self._demand.list_active_clients():
            plan = planes_por_cliente.get(cliente.id)
            nombre = f"{cliente.nombres} {cliente.apellidos}"
            if plan is not None:
                zonas = list(dict.fromkeys(
                    pm.maquina.zona for pm in plan.maquinas if pm.maquina is not None
                ))
                con_plan.append(TrainerClientItemSchema(
                    cliente_id=cliente.id,
                    nombre=nombre,
                    zonas=zonas,
                    estado=plan.estado,
                    planifico=True,
                ))
            else:
                sin_plan.append(TrainerClientItemSchema(
                    cliente_id=cliente.id,
                    nombre=nombre,
                    zonas=[],
                    estado=None,
                    planifico=False,
                ))

        return TrainerTodayViewSchema(
            fecha=objetivo,
            total_clientes=len(con_plan) + len(sin_plan),
            total_planifico=len(con_plan),
            total_sin_confirmar=len(sin_plan),
            con_plan=con_plan,
            sin_plan=sin_plan,
        )

    # ══════════════════════════════════════════════════════════════════════════
    #  ÍNDICE DE DEMANDA / INVERSIÓN
    # ══════════════════════════════════════════════════════════════════════════

    def demand_index_report(self) -> InvestmentReportSchema:
        machines, _ = self._machines.list_all(page=1, per_page=1000)
        plan_count = self._demand.plan_count_per_machine()
        usage = self._demand.real_usage_proxy_per_machine()

        items: list[MachineDemandIndexSchema] = []
        recomendaciones: list[str] = []

        for m in machines:
            planificaciones = plan_count.get(m.id, 0)
            usos = usage.get(m.id, 0)
            espera = 0.0  # tiempo de espera real aún no se registra
            cantidad = max(m.cantidad, 1)
            indice = round((planificaciones + usos + espera) / cantidad, 2)
            recomienda = indice >= DEMAND_INDEX_INVEST_THRESHOLD

            if recomienda:
                texto = (
                    f"Alta demanda sostenida en '{m.nombre}'. Se recomienda evaluar la "
                    f"adquisición de una unidad adicional."
                )
                recomendaciones.append(texto)
            else:
                texto = "Demanda dentro de la capacidad actual."

            items.append(MachineDemandIndexSchema(
                maquina_id=m.id,
                nombre=m.nombre,
                zona=m.zona,
                cantidad=m.cantidad,
                planificaciones=planificaciones,
                usos_reales_proxy=usos,
                tiempo_espera_promedio=espera,
                indice_demanda=indice,
                recomienda_invertir=recomienda,
                recomendacion=texto,
            ))

        items.sort(key=lambda x: x.indice_demanda, reverse=True)
        return InvestmentReportSchema(
            generado_para=date.today(),
            items=items,
            recomendaciones=recomendaciones,
        )

    # ══════════════════════════════════════════════════════════════════════════
    #  PRECISIÓN DE PREDICCIÓN
    # ══════════════════════════════════════════════════════════════════════════

    def precision_stats(self, desde: date, hasta: date) -> PrecisionStatsSchema:
        total, cumplidos = self._demand.precision_counts(desde, hasta)
        precision = round((cumplidos / total) * 100, 2) if total else 0.0
        mensaje = (
            f"De {total} planificaciones, {cumplidos} se cumplieron con asistencia real "
            f"({precision}% de precisión)."
            if total else "No hay planificaciones en el rango indicado."
        )
        return PrecisionStatsSchema(
            desde=desde,
            hasta=hasta,
            total_planes=total,
            planes_cumplidos=cumplidos,
            precision_porcentaje=precision,
            mensaje=mensaje,
        )
