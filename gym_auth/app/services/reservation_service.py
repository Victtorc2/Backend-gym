"""
Servicio de Reservas de Máquina.
El cliente reserva una máquina en una franja; el sistema valida el horario de
operación y la disponibilidad (según las unidades de la máquina), y los demás
clientes ven las franjas ocupadas para elegir una libre.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

from app.core.constants import (
    GYM_CLOSE_HOUR,
    GYM_OPEN_HOUR,
    RESERVATION_DURATION_STEP,
    ClientStatus,
    MuscleZone,
    ReservationStatus,
)
from app.core.exceptions import (
    InactiveUserException,
    MachineNotFoundException,
    ReservationAccessDeniedException,
    ReservationConflictException,
    ReservationInvalidException,
    ReservationNotFoundException,
)
from app.models.client import Client
from app.repositories.machine_repository import MachineRepository
from app.repositories.reservation_repository import ReservationRepository
from app.schemas.reservation_schema import (
    MachineAvailabilitySchema,
    MachineSlotOccupancySchema,
    ReservationCreateSchema,
    ReservationResponseSchema,
)


class ReservationService:
    """Gestiona la reserva de máquinas por franja horaria."""

    def __init__(self, repo: ReservationRepository, machine_repo: MachineRepository) -> None:
        self._repo = repo
        self._machines = machine_repo

    @staticmethod
    def _assert_active(client: Client) -> None:
        if client.estado != ClientStatus.ACTIVO:
            raise InactiveUserException()

    @staticmethod
    def _add_minutes(t: time, minutes: int) -> time:
        return (datetime.combine(date.today(), t) + timedelta(minutes=minutes)).time()

    # ── Crear ───────────────────────────────────────────────────────────────────

    def create_reservation(
        self, client: Client, data: ReservationCreateSchema
    ) -> ReservationResponseSchema:
        self._assert_active(client)

        machine = self._machines.get_by_id(data.maquina_id)
        if machine is None:
            raise MachineNotFoundException()
        if not machine.activa:
            raise ReservationInvalidException("La máquina está en mantenimiento")
        if data.duracion_min % RESERVATION_DURATION_STEP != 0:
            raise ReservationInvalidException("La duración debe ser múltiplo de 15 minutos")

        hora_fin = self._add_minutes(data.hora_inicio, data.duracion_min)
        if hora_fin <= data.hora_inicio:
            raise ReservationInvalidException("La franja no puede cruzar la medianoche")
        if data.hora_inicio.hour < GYM_OPEN_HOUR or hora_fin > time(hour=GYM_CLOSE_HOUR):
            raise ReservationInvalidException(
                f"El gimnasio opera de {GYM_OPEN_HOUR:02d}:00 a {GYM_CLOSE_HOUR:02d}:00"
            )

        ocupadas = self._repo.overlapping_count(machine.id, data.fecha, data.hora_inicio, hora_fin)
        if ocupadas >= machine.cantidad:
            raise ReservationConflictException(
                f"'{machine.nombre}' ya está ocupada en esa franja. Elige otra hora."
            )

        reserva = self._repo.create({
            "cliente_id": client.id,
            "maquina_id": machine.id,
            "fecha": data.fecha,
            "hora_inicio": data.hora_inicio,
            "hora_fin": hora_fin,
            "duracion_min": data.duracion_min,
            "estado": ReservationStatus.ACTIVA,
        })
        return self._to_response(reserva, machine)

    # ── Disponibilidad ──────────────────────────────────────────────────────────

    def machines_availability(
        self, client: Client, fecha: date, zonas: list[MuscleZone] | None = None
    ) -> list[MachineAvailabilitySchema]:
        machines = (
            self._machines.list_active_by_zones(zonas)
            if zonas else self._machines.list_active_catalog()
        )
        ids = [m.id for m in machines]
        reservas = self._repo.list_for_machines_date(ids, fecha)

        por_maquina: dict[int, list] = {}
        for r in reservas:
            por_maquina.setdefault(r.maquina_id, []).append(r)

        result: list[MachineAvailabilitySchema] = []
        for m in machines:
            tramos = self._capacity_segments(
                por_maquina.get(m.id, []), m.cantidad, client.id
            )
            result.append(MachineAvailabilitySchema(
                maquina_id=m.id, nombre=m.nombre, zona=m.zona,
                cantidad=m.cantidad, foto_url=m.foto_url, tramos=tramos,
            ))
        return result

    @staticmethod
    def _capacity_segments(
        reservas: list, cantidad: int, mi_id: int
    ) -> list[MachineSlotOccupancySchema]:
        """
        Calcula la ocupación por tramo mediante barrido de intervalos.

        Toma todas las reservas activas de una máquina en una fecha y las parte
        en tramos según los límites (inicios y fines). En cada tramo cuenta las
        reservas que lo cubren = unidades ocupadas; el resto son unidades libres.
        Tramos contiguos con la misma ocupación se fusionan para no fragmentar.

        Solo devuelve tramos con al menos una unidad ocupada; el tiempo restante
        se entiende como totalmente libre.
        """
        if not reservas:
            return []

        # Puntos de corte: cada inicio y fin de reserva define una frontera.
        puntos = sorted({r.hora_inicio for r in reservas} | {r.hora_fin for r in reservas})

        segmentos: list[MachineSlotOccupancySchema] = []
        for inicio, fin in zip(puntos, puntos[1:]):
            # Reservas que cubren por completo el tramo [inicio, fin).
            cubren = [r for r in reservas if r.hora_inicio <= inicio and r.hora_fin >= fin]
            ocupadas = len(cubren)
            if ocupadas == 0:
                continue

            es_mia = any(r.cliente_id == mi_id for r in cubren)
            ocupadas = min(ocupadas, cantidad)   # nunca más ocupadas que la capacidad
            nuevo = MachineSlotOccupancySchema(
                hora_inicio=inicio.strftime("%H:%M"),
                hora_fin=fin.strftime("%H:%M"),
                ocupadas=ocupadas,
                libres=max(cantidad - ocupadas, 0),
                es_mia=es_mia,
            )

            # Fusiona con el tramo previo si es contiguo y tiene la misma ocupación.
            if (
                segmentos
                and segmentos[-1].hora_fin == nuevo.hora_inicio
                and segmentos[-1].ocupadas == nuevo.ocupadas
                and segmentos[-1].es_mia == nuevo.es_mia
            ):
                segmentos[-1].hora_fin = nuevo.hora_fin
            else:
                segmentos.append(nuevo)

        return segmentos

    # ── Mis reservas ────────────────────────────────────────────────────────────

    def list_my_reservations(
        self, client: Client, fecha: date | None = None
    ) -> list[ReservationResponseSchema]:
        return [self._to_response(r) for r in self._repo.list_for_client(client.id, fecha)]

    def cancel_reservation(self, client: Client, rid: int) -> None:
        reserva = self._repo.get_by_id(rid)
        if reserva is None:
            raise ReservationNotFoundException()
        if reserva.cliente_id != client.id:
            raise ReservationAccessDeniedException()
        self._repo.cancel(reserva)

    # ── Helpers ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _to_response(reserva, machine=None) -> ReservationResponseSchema:
        m = machine or reserva.maquina
        return ReservationResponseSchema(
            id=reserva.id,
            maquina_id=reserva.maquina_id,
            maquina_nombre=m.nombre if m else "—",
            zona=m.zona if m else None,
            fecha=reserva.fecha,
            hora_inicio=reserva.hora_inicio.strftime("%H:%M"),
            hora_fin=reserva.hora_fin.strftime("%H:%M"),
            duracion_min=reserva.duracion_min,
            estado=reserva.estado,
        )
