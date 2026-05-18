"""
Repositorio de Clientes Diarios (Fase 6).
Única capa autorizada para interactuar con las tablas:
  - clientes_diarios
  - pagos_diarios
  - ingresos_diarios

Principios:
  - Sin lógica de negocio (solo queries y persistencia)
  - Append-only para pagos e ingresos (nunca se eliminan)
  - Repository Pattern estricto
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.constants import DailyClientStatus, DailyIngresoStatus
from app.models.daily_client import DailyClient, DailyIngreso, DailyPayment


# ══════════════════════════════════════════════════════════════════════════════
# REPOSITORIO: CLIENTES DIARIOS
# ══════════════════════════════════════════════════════════════════════════════

class DailyClientRepository:
    """Gestiona la persistencia de clientes diarios."""

    def __init__(self, db: Session) -> None:
        self._db = db

    # ── Consultas ──────────────────────────────────────────────────────────────

    def get_by_id(self, client_id: int) -> DailyClient | None:
        """Busca un cliente diario por su ID."""
        return (
            self._db.query(DailyClient)
            .filter(DailyClient.id == client_id)
            .first()
        )

    def get_by_documento(self, documento: str) -> DailyClient | None:
        """Busca un cliente diario por número de documento (único)."""
        return (
            self._db.query(DailyClient)
            .filter(DailyClient.documento == documento)
            .first()
        )

    def list_all(
        self,
        estado: DailyClientStatus | None = None,
        nombre_contains: str | None = None,
    ) -> list[DailyClient]:
        """
        Lista todos los clientes diarios con filtros opcionales.

        Args:
            estado: filtrar por activo / inactivo
            nombre_contains: búsqueda parcial por nombre (LIKE)
        """
        query = self._db.query(DailyClient)

        if estado is not None:
            query = query.filter(DailyClient.estado == estado)
        if nombre_contains:
            query = query.filter(
                DailyClient.nombre.ilike(f"%{nombre_contains}%")
            )

        return query.order_by(DailyClient.created_at.desc()).all()

    # ── Escritura ──────────────────────────────────────────────────────────────

    def create(self, *, nombre: str, documento: str | None) -> DailyClient:
        """Registra un nuevo cliente diario. Estado inicial: activo."""
        client = DailyClient(
            nombre=nombre,
            documento=documento,
            estado=DailyClientStatus.ACTIVO,
        )
        self._db.add(client)
        self._db.commit()
        self._db.refresh(client)
        return client

    def update(self, client: DailyClient, **fields) -> DailyClient:
        """
        Actualiza campos de un cliente diario.
        Solo modifica los campos proporcionados (PATCH semántico).
        """
        for field, value in fields.items():
            if value is not None:
                setattr(client, field, value)
        self._db.commit()
        self._db.refresh(client)
        return client


# ══════════════════════════════════════════════════════════════════════════════
# REPOSITORIO: PAGOS DIARIOS
# ══════════════════════════════════════════════════════════════════════════════

class DailyPaymentRepository:
    """Gestiona la persistencia de pagos diarios."""

    def __init__(self, db: Session) -> None:
        self._db = db

    # ── Consultas ──────────────────────────────────────────────────────────────

    def get_by_id(self, payment_id: int) -> DailyPayment | None:
        """Busca un pago diario por ID."""
        return (
            self._db.query(DailyPayment)
            .filter(DailyPayment.id == payment_id)
            .first()
        )

    def get_by_cliente_and_fecha(
        self, cliente_id: int, fecha: date
    ) -> DailyPayment | None:
        """
        Busca el pago de un cliente para una fecha específica.
        Usado para verificar si ya existe pago del día (evitar duplicados).
        """
        return (
            self._db.query(DailyPayment)
            .filter(
                DailyPayment.cliente_id == cliente_id,
                DailyPayment.fecha_pago == fecha,
            )
            .first()
        )

    def list_by_cliente(self, cliente_id: int) -> list[DailyPayment]:
        """Lista todos los pagos de un cliente, del más reciente al más antiguo."""
        return (
            self._db.query(DailyPayment)
            .filter(DailyPayment.cliente_id == cliente_id)
            .order_by(DailyPayment.fecha_pago.desc())
            .all()
        )

    def count_by_cliente(self, cliente_id: int) -> int:
        """Cuenta el total de pagos de un cliente diario."""
        return (
            self._db.query(func.count(DailyPayment.id))
            .filter(DailyPayment.cliente_id == cliente_id)
            .scalar() or 0
        )

    # ── Escritura ──────────────────────────────────────────────────────────────

    def create(
        self, *, cliente_id: int, monto: float, fecha_pago: date
    ) -> DailyPayment:
        """Registra un nuevo pago diario (append-only)."""
        payment = DailyPayment(
            cliente_id=cliente_id,
            monto=monto,
            fecha_pago=fecha_pago,
        )
        self._db.add(payment)
        self._db.commit()
        self._db.refresh(payment)
        return payment


# ══════════════════════════════════════════════════════════════════════════════
# REPOSITORIO: INGRESOS DIARIOS
# ══════════════════════════════════════════════════════════════════════════════

class DailyIngresoRepository:
    """Gestiona la persistencia de ingresos diarios."""

    def __init__(self, db: Session) -> None:
        self._db = db

    # ── Consultas individuales ─────────────────────────────────────────────────

    def get_by_id(self, ingreso_id: int) -> DailyIngreso | None:
        """Busca un ingreso por ID, cargando relación con el cliente."""
        return (
            self._db.query(DailyIngreso)
            .options(joinedload(DailyIngreso.cliente))
            .filter(DailyIngreso.id == ingreso_id)
            .first()
        )

    def get_aprobado_by_cliente_and_fecha(
        self, cliente_id: int, fecha: date
    ) -> DailyIngreso | None:
        """
        Verifica si ya existe un ingreso APROBADO para el cliente en la fecha dada.
        Usado para evitar doble ingreso en el mismo día.
        """
        return (
            self._db.query(DailyIngreso)
            .filter(
                DailyIngreso.cliente_id == cliente_id,
                DailyIngreso.fecha == fecha,
                DailyIngreso.estado == DailyIngresoStatus.APROBADO,
            )
            .first()
        )

    def list_all_paginated(
        self,
        page: int,
        per_page: int,
        cliente_id: int | None = None,
        estado: DailyIngresoStatus | None = None,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
    ) -> tuple[list[DailyIngreso], int]:
        """
        Lista ingresos con filtros opcionales y paginación.

        Returns:
            Tupla (lista de la página, total de registros).
        """
        query = (
            self._db.query(DailyIngreso)
            .options(joinedload(DailyIngreso.cliente))
        )

        if cliente_id is not None:
            query = query.filter(DailyIngreso.cliente_id == cliente_id)
        if estado is not None:
            query = query.filter(DailyIngreso.estado == estado)
        if fecha_desde is not None:
            query = query.filter(DailyIngreso.fecha >= fecha_desde)
        if fecha_hasta is not None:
            query = query.filter(DailyIngreso.fecha <= fecha_hasta)

        total = query.count()
        offset = (page - 1) * per_page
        items = (
            query
            .order_by(DailyIngreso.fecha.desc(), DailyIngreso.hora.desc())
            .offset(offset)
            .limit(per_page)
            .all()
        )
        return items, total

    def list_by_cliente(self, cliente_id: int) -> list[DailyIngreso]:
        """Lista todos los ingresos de un cliente diario."""
        return (
            self._db.query(DailyIngreso)
            .filter(DailyIngreso.cliente_id == cliente_id)
            .order_by(DailyIngreso.fecha.desc(), DailyIngreso.hora.desc())
            .all()
        )

    # ── Consultas agregadas (frecuencia) ───────────────────────────────────────

    def count_aprobados_by_cliente(self, cliente_id: int) -> int:
        """Cuenta el total de ingresos aprobados de un cliente."""
        return (
            self._db.query(func.count(DailyIngreso.id))
            .filter(
                DailyIngreso.cliente_id == cliente_id,
                DailyIngreso.estado == DailyIngresoStatus.APROBADO,
            )
            .scalar() or 0
        )

    def count_denegados_by_cliente(self, cliente_id: int) -> int:
        """Cuenta el total de ingresos denegados de un cliente."""
        return (
            self._db.query(func.count(DailyIngreso.id))
            .filter(
                DailyIngreso.cliente_id == cliente_id,
                DailyIngreso.estado == DailyIngresoStatus.DENEGADO,
            )
            .scalar() or 0
        )

    def get_primer_ingreso(self, cliente_id: int) -> date | None:
        """Obtiene la fecha del primer ingreso aprobado de un cliente."""
        return (
            self._db.query(func.min(DailyIngreso.fecha))
            .filter(
                DailyIngreso.cliente_id == cliente_id,
                DailyIngreso.estado == DailyIngresoStatus.APROBADO,
            )
            .scalar()
        )

    def get_ultimo_ingreso(self, cliente_id: int) -> date | None:
        """Obtiene la fecha del último ingreso aprobado de un cliente."""
        return (
            self._db.query(func.max(DailyIngreso.fecha))
            .filter(
                DailyIngreso.cliente_id == cliente_id,
                DailyIngreso.estado == DailyIngresoStatus.APROBADO,
            )
            .scalar()
        )

    def count_aprobados_mes_actual(self, cliente_id: int) -> int:
        """Cuenta los ingresos aprobados del mes en curso."""
        today = date.today()
        return (
            self._db.query(func.count(DailyIngreso.id))
            .filter(
                DailyIngreso.cliente_id == cliente_id,
                DailyIngreso.estado == DailyIngresoStatus.APROBADO,
                func.month(DailyIngreso.fecha) == today.month,
                func.year(DailyIngreso.fecha) == today.year,
            )
            .scalar() or 0
        )

    def get_frecuencia_mensual(self, cliente_id: int) -> list[dict]:
        """
        Calcula la frecuencia de ingresos aprobados agrupada por mes y año.

        Returns:
            Lista de dicts con: anio, mes, total_ingresos
            ordenada de más reciente a más antiguo.
        """
        rows = (
            self._db.query(
                func.year(DailyIngreso.fecha).label("anio"),
                func.month(DailyIngreso.fecha).label("mes"),
                func.count(DailyIngreso.id).label("total_ingresos"),
            )
            .filter(
                DailyIngreso.cliente_id == cliente_id,
                DailyIngreso.estado == DailyIngresoStatus.APROBADO,
            )
            .group_by(
                func.year(DailyIngreso.fecha),
                func.month(DailyIngreso.fecha),
            )
            .order_by(
                func.year(DailyIngreso.fecha).desc(),
                func.month(DailyIngreso.fecha).desc(),
            )
            .all()
        )
        return [
            {"anio": row.anio, "mes": row.mes, "total_ingresos": row.total_ingresos}
            for row in rows
        ]

    def count_by_cliente(self, cliente_id: int) -> int:
        """Cuenta el total de registros de ingreso (todos los estados) de un cliente."""
        return (
            self._db.query(func.count(DailyIngreso.id))
            .filter(DailyIngreso.cliente_id == cliente_id)
            .scalar() or 0
        )

    # ── Escritura ──────────────────────────────────────────────────────────────

    def create(
        self,
        *,
        cliente_id: int,
        fecha: date,
        hora,
        estado: DailyIngresoStatus,
        motivo: str | None,
    ) -> DailyIngreso:
        """Registra un nuevo intento de ingreso (append-only)."""
        ingreso = DailyIngreso(
            cliente_id=cliente_id,
            fecha=fecha,
            hora=hora,
            estado=estado,
            motivo=motivo,
        )
        self._db.add(ingreso)
        self._db.commit()
        self._db.refresh(ingreso)
        return ingreso
