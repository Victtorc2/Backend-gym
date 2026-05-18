"""
Repositorio de Clientes.
Única capa autorizada para interactuar con la tabla 'clientes'.
Nunca contiene lógica de negocio; solo operaciones de persistencia.
"""
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.core.constants import ClientStatus
from app.models.client import Client


class ClientRepository:
    """Gestiona todas las operaciones de persistencia del modelo Client."""

    def __init__(self, db: Session) -> None:
        self._db = db

    # ── Consultas ──────────────────────────────────────────────────────────────

    def get_by_id(self, client_id: int) -> Client | None:
        """Busca un cliente por su ID, cargando el usuario asociado."""
        return (
            self._db.query(Client)
            .options(joinedload(Client.usuario))
            .filter(Client.id == client_id)
            .first()
        )

    def get_by_dni(self, dni: str) -> Client | None:
        """Busca un cliente por DNI."""
        return self._db.query(Client).filter(Client.dni == dni).first()

    def get_by_correo(self, correo: str) -> Client | None:
        """Busca un cliente por correo electrónico (case-insensitive)."""
        return (
            self._db.query(Client)
            .filter(Client.correo == correo.lower().strip())
            .first()
        )

    def get_by_user_id(self, user_id: int) -> Client | None:
        """Busca el cliente vinculado a un user_id."""
        return self._db.query(Client).filter(Client.user_id == user_id).first()

    def list_paginated(
        self,
        page: int,
        per_page: int,
        nombre: str | None = None,
        dni: str | None = None,
        estado: ClientStatus | None = None,
    ) -> tuple[list[Client], int]:
        """
        Lista clientes con filtros opcionales y paginación.

        Returns:
            Tupla (lista de clientes de la página, total de registros).
        """
        query = self._db.query(Client).options(joinedload(Client.usuario))

        # ── Filtros ────────────────────────────────────────────────────────────
        if nombre:
            term = f"%{nombre.strip()}%"
            query = query.filter(
                or_(
                    Client.nombres.ilike(term),
                    Client.apellidos.ilike(term),
                )
            )

        if dni:
            query = query.filter(Client.dni == dni.strip())

        if estado:
            query = query.filter(Client.estado == estado)

        # ── Conteo total ───────────────────────────────────────────────────────
        total = query.count()

        # ── Paginación ─────────────────────────────────────────────────────────
        offset = (page - 1) * per_page
        items = (
            query
            .order_by(Client.created_at.desc())
            .offset(offset)
            .limit(per_page)
            .all()
        )

        return items, total

    def count_by_username_prefix(self, prefix: str) -> int:
        """
        Cuenta cuántos usuarios tienen un username que empieza con el prefijo dado.
        Usado para generar sufijos únicos en usernames.
        """
        from app.models.user import User
        return (
            self._db.query(User)
            .filter(User.email.like(f"{prefix}%"))
            .count()
        )

    # ── Escritura ──────────────────────────────────────────────────────────────

    def create(
        self,
        *,
        nombres: str,
        apellidos: str,
        dni: str,
        telefono: str,
        correo: str,
        sexo,
        fecha_nacimiento,
        ocupacion: str | None,
        direccion: str | None,
        grupo_edad,
        estado,
        user_id: int,
    ) -> Client:
        """
        Persiste un nuevo cliente en la base de datos.
        Recibe parámetros explícitos para mantener el contrato de la capa clara.
        """
        client = Client(
            nombres=nombres.strip(),
            apellidos=apellidos.strip(),
            dni=dni.strip(),
            telefono=telefono.strip(),
            correo=correo.lower().strip(),
            sexo=sexo,
            fecha_nacimiento=fecha_nacimiento,
            ocupacion=ocupacion.strip() if ocupacion else None,
            direccion=direccion.strip() if direccion else None,
            grupo_edad=grupo_edad,
            estado=estado,
            user_id=user_id,
        )
        self._db.add(client)
        self._db.flush()   # Obtiene el ID sin cerrar la transacción
        self._db.refresh(client)
        return client

    def update(self, client: Client, updates: dict) -> Client:
        """
        Aplica un diccionario de cambios sobre un cliente existente.
        Solo modifica campos presentes en el dict (partial update).
        """
        for field, value in updates.items():
            setattr(client, field, value)
        self._db.flush()
        self._db.refresh(client)
        return client

    def commit(self) -> None:
        """Confirma la transacción activa."""
        self._db.commit()

    def rollback(self) -> None:
        """Revierte la transacción activa."""
        self._db.rollback()
