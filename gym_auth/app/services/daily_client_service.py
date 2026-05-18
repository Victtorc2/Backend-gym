"""
Servicio de Clientes Diarios (Fase 6).
Centraliza toda la lógica de negocio del módulo.
Los routes solo coordinan: no toman decisiones de negocio.

Reglas de negocio implementadas:
  - Solo clientes activos pueden operar
  - No pagos duplicados el mismo día
  - Ingreso requiere pago del día
  - No ingreso duplicado (aprobado) el mismo día
  - Motivo requerido si el ingreso es denegado
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.core.constants import DailyClientStatus, DailyIngresoStatus
from app.core.exceptions import (
    DailyClientAlreadyExistsException,
    DailyClientInactiveException,
    DailyClientNotFoundException,
    DailyIngresoAlreadyExistsException,
    DailyIngresoNotFoundException,
    DailyPaymentAlreadyExistsException,
    DailyPaymentInvalidException,
)
from app.models.daily_client import DailyClient, DailyIngreso, DailyPayment
from app.repositories.daily_client_repository import (
    DailyClientRepository,
    DailyIngresoRepository,
    DailyPaymentRepository,
)
from app.schemas.daily_client_schema import (
    DailyClientCreate,
    DailyClientDetailResponse,
    DailyClientResponse,
    DailyClientUpdate,
    DailyFrecuenciaResponse,
    DailyIngresoDetailResponse,
    DailyIngresoListResponse,
    DailyPaymentListResponse,
    DailyPaymentResponse,
)


def _today() -> date:
    """Devuelve la fecha actual (UTC). Centralizado para facilitar tests."""
    return datetime.now(timezone.utc).date()


def _now_time():
    """Devuelve la hora actual (UTC)."""
    return datetime.now(timezone.utc).time().replace(microsecond=0)


def _to_client_response(client: DailyClient) -> DailyClientResponse:
    return DailyClientResponse(
        id=client.id,
        nombre=client.nombre,
        documento=client.documento,
        estado=client.estado,
        created_at=client.created_at,
    )


def _to_ingreso_detail(ingreso: DailyIngreso) -> DailyIngresoDetailResponse:
    return DailyIngresoDetailResponse(
        id=ingreso.id,
        cliente_id=ingreso.cliente_id,
        fecha=ingreso.fecha,
        hora=ingreso.hora,
        estado=ingreso.estado,
        motivo=ingreso.motivo,
        created_at=ingreso.created_at,
        cliente_nombre=ingreso.cliente.nombre if ingreso.cliente else "",
        cliente_documento=ingreso.cliente.documento if ingreso.cliente else None,
    )


# ══════════════════════════════════════════════════════════════════════════════
# SERVICE: CLIENTES DIARIOS
# ══════════════════════════════════════════════════════════════════════════════

class DailyClientService:
    """
    Lógica de negocio para la gestión de clientes diarios.
    Orquesta repositorios y aplica reglas del dominio.
    """

    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = DailyClientRepository(db)
        self._payment_repo = DailyPaymentRepository(db)
        self._ingreso_repo = DailyIngresoRepository(db)

    # ── Registro de cliente ────────────────────────────────────────────────────

    def registrar_cliente(self, payload: DailyClientCreate) -> DailyClientResponse:
        """
        Registra un nuevo cliente diario.

        Validaciones:
          - Si se provee documento, no debe existir otro cliente con el mismo.
        """
        if payload.documento:
            existing = self._repo.get_by_documento(payload.documento)
            if existing:
                raise DailyClientAlreadyExistsException(
                    f"Ya existe un cliente diario con el documento '{payload.documento}'"
                )

        client = self._repo.create(
            nombre=payload.nombre,
            documento=payload.documento,
        )
        return _to_client_response(client)

    # ── Listado de clientes ────────────────────────────────────────────────────

    def listar_clientes(
        self,
        estado: DailyClientStatus | None = None,
        nombre_contains: str | None = None,
    ) -> list[DailyClientDetailResponse]:
        """
        Lista todos los clientes diarios.
        Incluye contadores de actividad (total_pagos, total_ingresos).
        """
        clients = self._repo.list_all(
            estado=estado, nombre_contains=nombre_contains
        )
        result = []
        for c in clients:
            total_pagos = self._payment_repo.count_by_cliente(c.id)
            total_ingresos = self._ingreso_repo.count_aprobados_by_cliente(c.id)
            result.append(
                DailyClientDetailResponse(
                    id=c.id,
                    nombre=c.nombre,
                    documento=c.documento,
                    estado=c.estado,
                    created_at=c.created_at,
                    total_pagos=total_pagos,
                    total_ingresos=total_ingresos,
                )
            )
        return result

    # ── Actualización de cliente ───────────────────────────────────────────────

    def actualizar_cliente(
        self, client_id: int, payload: DailyClientUpdate
    ) -> DailyClientResponse:
        """
        Actualiza un cliente diario (PATCH semántico).

        Validaciones:
          - El cliente debe existir.
          - Si se cambia documento, no debe existir otro con ese documento.
        """
        client = self._get_client_or_404(client_id)

        if payload.documento and payload.documento != client.documento:
            existing = self._repo.get_by_documento(payload.documento)
            if existing and existing.id != client_id:
                raise DailyClientAlreadyExistsException(
                    f"Ya existe otro cliente con el documento '{payload.documento}'"
                )

        updates: dict = {}
        if payload.nombre is not None:
            updates["nombre"] = payload.nombre
        if payload.documento is not None:
            updates["documento"] = payload.documento
        if payload.estado is not None:
            updates["estado"] = payload.estado

        if not updates:
            return _to_client_response(client)

        updated = self._repo.update(client, **updates)
        return _to_client_response(updated)

    # ── Helpers internos ───────────────────────────────────────────────────────

    def _get_client_or_404(self, client_id: int) -> DailyClient:
        client = self._repo.get_by_id(client_id)
        if not client:
            raise DailyClientNotFoundException(
                f"No se encontró el cliente diario con id={client_id}"
            )
        return client

    def _require_active(self, client: DailyClient) -> None:
        if client.estado != DailyClientStatus.ACTIVO:
            raise DailyClientInactiveException(
                f"El cliente '{client.nombre}' está inactivo y no puede operar"
            )


# ══════════════════════════════════════════════════════════════════════════════
# SERVICE: PAGOS DIARIOS
# ══════════════════════════════════════════════════════════════════════════════

class DailyPaymentService:
    """
    Lógica de negocio para pagos diarios.

    Reglas:
      - Cliente debe existir y estar activo.
      - No se permiten pagos duplicados en la misma fecha para el mismo cliente.
      - El monto debe ser mayor a 0.
    """

    def __init__(self, db: Session) -> None:
        self._db = db
        self._client_repo = DailyClientRepository(db)
        self._payment_repo = DailyPaymentRepository(db)

    def registrar_pago(
        self, client_id: int, monto: float, fecha_pago: date | None
    ) -> DailyPaymentResponse:
        """
        Registra un pago diario para el cliente especificado.

        Args:
            client_id: ID del cliente diario.
            monto: Monto del pago (> 0).
            fecha_pago: Fecha del pago (None = hoy).

        Raises:
            DailyClientNotFoundException: Si el cliente no existe.
            DailyClientInactiveException: Si el cliente está inactivo.
            DailyPaymentAlreadyExistsException: Si ya existe un pago ese día.
            DailyPaymentInvalidException: Si el monto no es válido.
        """
        client = self._client_repo.get_by_id(client_id)
        if not client:
            raise DailyClientNotFoundException(
                f"No se encontró el cliente diario con id={client_id}"
            )
        if client.estado != DailyClientStatus.ACTIVO:
            raise DailyClientInactiveException(
                f"El cliente '{client.nombre}' está inactivo"
            )
        if monto <= 0:
            raise DailyPaymentInvalidException("El monto debe ser mayor a 0")

        fecha = fecha_pago or _today()

        # Verificar pago duplicado
        existing = self._payment_repo.get_by_cliente_and_fecha(client_id, fecha)
        if existing:
            raise DailyPaymentAlreadyExistsException(
                f"Ya existe un pago registrado para el cliente '{client.nombre}' "
                f"en la fecha {fecha.isoformat()}"
            )

        payment = self._payment_repo.create(
            cliente_id=client_id,
            monto=monto,
            fecha_pago=fecha,
        )
        return DailyPaymentResponse(
            id=payment.id,
            cliente_id=payment.cliente_id,
            monto=float(payment.monto),
            fecha_pago=payment.fecha_pago,
            created_at=payment.created_at,
        )

    def historial_pagos(self, client_id: int) -> DailyPaymentListResponse:
        """
        Devuelve el historial completo de pagos de un cliente diario.

        Raises:
            DailyClientNotFoundException: Si el cliente no existe.
        """
        client = self._client_repo.get_by_id(client_id)
        if not client:
            raise DailyClientNotFoundException(
                f"No se encontró el cliente diario con id={client_id}"
            )

        pagos = self._payment_repo.list_by_cliente(client_id)
        pagos_response = [
            DailyPaymentResponse(
                id=p.id,
                cliente_id=p.cliente_id,
                monto=float(p.monto),
                fecha_pago=p.fecha_pago,
                created_at=p.created_at,
            )
            for p in pagos
        ]
        return DailyPaymentListResponse(
            cliente_id=client_id,
            cliente_nombre=client.nombre,
            total_pagos=len(pagos_response),
            pagos=pagos_response,
        )


# ══════════════════════════════════════════════════════════════════════════════
# SERVICE: INGRESOS DIARIOS
# ══════════════════════════════════════════════════════════════════════════════

class DailyIngresoService:
    """
    Lógica de negocio para ingresos diarios.

    Flujo de validación para ingreso aprobado:
      1. Cliente existe
      2. Cliente activo
      3. Pago del día registrado
      4. No existe ingreso aprobado ese día (evitar duplicado)

    Si cualquier condición falla → ingreso DENEGADO con motivo,
    o excepción según la naturaleza del error.
    """

    def __init__(self, db: Session) -> None:
        self._db = db
        self._client_repo = DailyClientRepository(db)
        self._payment_repo = DailyPaymentRepository(db)
        self._ingreso_repo = DailyIngresoRepository(db)

    def registrar_ingreso(
        self, client_id: int, fecha: date | None, motivo_manual: str | None
    ) -> DailyIngresoDetailResponse:
        """
        Registra un intento de ingreso para el cliente.

        El sistema determina automáticamente si el ingreso es APROBADO o DENEGADO
        basándose en las reglas de negocio. Si motivo_manual se provee, se
        registra como denegado con ese motivo (denegación administrativa).

        Args:
            client_id: ID del cliente diario.
            fecha: Fecha del ingreso (None = hoy).
            motivo_manual: Motivo de denegación manual (None = flujo automático).

        Returns:
            DailyIngresoDetailResponse con estado y motivo.
        """
        fecha_ingreso = fecha or _today()
        hora_ingreso = _now_time()

        # 1. Verificar que el cliente existe
        client = self._client_repo.get_by_id(client_id)
        if not client:
            raise DailyClientNotFoundException(
                f"No se encontró el cliente diario con id={client_id}"
            )

        # 2. Verificar cliente activo
        if client.estado != DailyClientStatus.ACTIVO:
            ingreso = self._ingreso_repo.create(
                cliente_id=client_id,
                fecha=fecha_ingreso,
                hora=hora_ingreso,
                estado=DailyIngresoStatus.DENEGADO,
                motivo=f"Cliente inactivo: {client.nombre}",
            )
            return _to_ingreso_detail(ingreso)

        # 3. Si hay motivo manual → denegación administrativa
        if motivo_manual:
            ingreso = self._ingreso_repo.create(
                cliente_id=client_id,
                fecha=fecha_ingreso,
                hora=hora_ingreso,
                estado=DailyIngresoStatus.DENEGADO,
                motivo=motivo_manual,
            )
            return _to_ingreso_detail(ingreso)

        # 4. Verificar ingreso duplicado (aprobado) ese día
        ingreso_existente = self._ingreso_repo.get_aprobado_by_cliente_and_fecha(
            client_id, fecha_ingreso
        )
        if ingreso_existente:
            raise DailyIngresoAlreadyExistsException(
                f"El cliente '{client.nombre}' ya registró un ingreso aprobado "
                f"el {fecha_ingreso.isoformat()}"
            )

        # 5. Verificar pago del día
        pago_del_dia = self._payment_repo.get_by_cliente_and_fecha(
            client_id, fecha_ingreso
        )
        if not pago_del_dia:
            ingreso = self._ingreso_repo.create(
                cliente_id=client_id,
                fecha=fecha_ingreso,
                hora=hora_ingreso,
                estado=DailyIngresoStatus.DENEGADO,
                motivo=f"Sin pago registrado para el día {fecha_ingreso.isoformat()}",
            )
            return _to_ingreso_detail(ingreso)

        # 6. Todas las validaciones pasaron → APROBADO
        ingreso = self._ingreso_repo.create(
            cliente_id=client_id,
            fecha=fecha_ingreso,
            hora=hora_ingreso,
            estado=DailyIngresoStatus.APROBADO,
            motivo=None,
        )
        return _to_ingreso_detail(ingreso)

    def listar_ingresos(
        self,
        page: int,
        per_page: int,
        cliente_id: int | None = None,
        estado: DailyIngresoStatus | None = None,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
    ) -> DailyIngresoListResponse:
        """Lista ingresos diarios con filtros opcionales y paginación."""
        items, total = self._ingreso_repo.list_all_paginated(
            page=page,
            per_page=per_page,
            cliente_id=cliente_id,
            estado=estado,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
        )
        return DailyIngresoListResponse(
            total=total,
            page=page,
            per_page=per_page,
            items=[_to_ingreso_detail(i) for i in items],
        )

    def obtener_ingreso(self, ingreso_id: int) -> DailyIngresoDetailResponse:
        """
        Obtiene un ingreso diario por su ID.

        Raises:
            DailyIngresoNotFoundException: Si no existe.
        """
        ingreso = self._ingreso_repo.get_by_id(ingreso_id)
        if not ingreso:
            raise DailyIngresoNotFoundException(
                f"No se encontró el ingreso diario con id={ingreso_id}"
            )
        return _to_ingreso_detail(ingreso)

    def ingresos_por_cliente(self, client_id: int) -> DailyIngresoListResponse:
        """
        Lista todos los ingresos de un cliente diario.

        Raises:
            DailyClientNotFoundException: Si el cliente no existe.
        """
        client = self._client_repo.get_by_id(client_id)
        if not client:
            raise DailyClientNotFoundException(
                f"No se encontró el cliente diario con id={client_id}"
            )

        items, total = self._ingreso_repo.list_all_paginated(
            page=1, per_page=10_000, cliente_id=client_id
        )
        return DailyIngresoListResponse(
            total=total,
            page=1,
            per_page=total or 0,
            items=[_to_ingreso_detail(i) for i in items],
        )

    def calcular_frecuencia(self, client_id: int) -> DailyFrecuenciaResponse:
        """
        Calcula la frecuencia de asistencia de un cliente diario.
        Incluye:
          - Total de ingresos aprobados y denegados
          - Primer y último ingreso aprobado
          - Ingresos del mes actual
          - Historial mensual agrupado

        Raises:
            DailyClientNotFoundException: Si el cliente no existe.
        """
        client = self._client_repo.get_by_id(client_id)
        if not client:
            raise DailyClientNotFoundException(
                f"No se encontró el cliente diario con id={client_id}"
            )

        total_aprobados = self._ingreso_repo.count_aprobados_by_cliente(client_id)
        total_denegados = self._ingreso_repo.count_denegados_by_cliente(client_id)
        primer_ingreso = self._ingreso_repo.get_primer_ingreso(client_id)
        ultimo_ingreso = self._ingreso_repo.get_ultimo_ingreso(client_id)
        dias_mes_actual = self._ingreso_repo.count_aprobados_mes_actual(client_id)
        historial_mensual = self._ingreso_repo.get_frecuencia_mensual(client_id)

        return DailyFrecuenciaResponse(
            cliente_id=client_id,
            cliente_nombre=client.nombre,
            total_ingresos_aprobados=total_aprobados,
            total_ingresos_denegados=total_denegados,
            primer_ingreso=primer_ingreso,
            ultimo_ingreso=ultimo_ingreso,
            dias_mes_actual=dias_mes_actual,
            historial_mensual=historial_mensual,
        )
