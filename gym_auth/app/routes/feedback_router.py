"""
Routers de Comentarios / Sugerencias.
  - client_feedback_router: el cliente envía y consulta sus mensajes.
  - admin_feedback_router: el administrador visualiza y gestiona todos los mensajes.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.constants import FeedbackStatus, FeedbackType
from app.database.connection import get_db
from app.dependencies.auth_dependencies import get_current_client, require_admin
from app.models.client import Client
from app.repositories.feedback_repository import FeedbackRepository
from app.schemas.feedback_schema import (
    FeedbackCreateSchema,
    FeedbackStatusUpdateSchema,
)
from app.services.feedback_service import FeedbackService
from app.utils.responses import success_response


def _get_service(db: Annotated[Session, Depends(get_db)]) -> FeedbackService:
    return FeedbackService(FeedbackRepository(db))


# ══════════════════════════════════════════════════════════════════════════════
#  CLIENTE
# ══════════════════════════════════════════════════════════════════════════════

client_feedback_router = APIRouter(
    prefix="/api/mis-comentarios", tags=["Portal Cliente - Comentarios"]
)


@client_feedback_router.post("", status_code=201, summary="Enviar un comentario o sugerencia")
def enviar(
    payload: FeedbackCreateSchema,
    client: Annotated[Client, Depends(get_current_client)],
    service: Annotated[FeedbackService, Depends(_get_service)],
):
    """
    Envía un comentario, sugerencia, recomendación o queja al gimnasio.
    **Rol: cliente.**
    """
    result = service.create(client, payload)
    return success_response(result.model_dump(), "Mensaje enviado. ¡Gracias por tu opinión!", status_code=201)


@client_feedback_router.get("", summary="Ver mis comentarios enviados")
def mis_comentarios(
    client: Annotated[Client, Depends(get_current_client)],
    service: Annotated[FeedbackService, Depends(_get_service)],
):
    """Lista los mensajes que el cliente ha enviado. **Rol: cliente.**"""
    result = service.list_mine(client)
    return success_response([r.model_dump() for r in result], "Mis comentarios")


@client_feedback_router.delete("/{feedback_id}", summary="Eliminar un comentario mío")
def eliminar_mio(
    feedback_id: int,
    client: Annotated[Client, Depends(get_current_client)],
    service: Annotated[FeedbackService, Depends(_get_service)],
):
    """Elimina un mensaje propio del cliente. **Rol: cliente.**"""
    service.delete_mine(client, feedback_id)
    return success_response(message="Comentario eliminado")


# ══════════════════════════════════════════════════════════════════════════════
#  ADMINISTRADOR
# ══════════════════════════════════════════════════════════════════════════════

admin_feedback_router = APIRouter(prefix="/api/comentarios", tags=["Comentarios (Admin)"])


@admin_feedback_router.get("", summary="Listar comentarios de clientes", dependencies=[Depends(require_admin)])
def listar(
    service: Annotated[FeedbackService, Depends(_get_service)],
    tipo: FeedbackType | None = Query(default=None, description="Filtra por tipo"),
    estado: FeedbackStatus | None = Query(default=None, description="Filtra por estado"),
    cliente_id: int | None = Query(default=None, ge=1),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
):
    """
    Lista los mensajes de los clientes con filtros y el conteo de nuevos.
    **Solo administradores.**
    """
    result = service.list_admin(page, per_page, tipo, estado, cliente_id)
    return success_response(result.model_dump(), "Listado de comentarios")


@admin_feedback_router.get("/{feedback_id}", summary="Ver un comentario", dependencies=[Depends(require_admin)])
def detalle(
    feedback_id: int,
    service: Annotated[FeedbackService, Depends(_get_service)],
):
    """
    Devuelve un mensaje. Si estaba 'nuevo', se marca como 'leído'.
    **Solo administradores.**
    """
    return success_response(service.get_admin(feedback_id).model_dump(), "Comentario")


@admin_feedback_router.patch("/{feedback_id}/estado", summary="Cambiar estado", dependencies=[Depends(require_admin)])
def cambiar_estado(
    feedback_id: int,
    payload: FeedbackStatusUpdateSchema,
    service: Annotated[FeedbackService, Depends(_get_service)],
):
    """Marca un mensaje como nuevo / leído / archivado. **Solo administradores.**"""
    result = service.update_status(feedback_id, payload.estado)
    return success_response(result.model_dump(), "Estado actualizado")


@admin_feedback_router.delete("/{feedback_id}", summary="Eliminar comentario", dependencies=[Depends(require_admin)])
def eliminar(
    feedback_id: int,
    service: Annotated[FeedbackService, Depends(_get_service)],
):
    """Elimina un mensaje. **Solo administradores.**"""
    service.delete_admin(feedback_id)
    return success_response(message="Comentario eliminado")
