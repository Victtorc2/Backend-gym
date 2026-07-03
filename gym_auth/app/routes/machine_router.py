"""
Router del catálogo de Máquinas.
- Administrador: CRUD, subida de foto y gestión de estado (activa/mantenimiento).
- Cualquier usuario autenticado: catálogo de máquinas activas (con foto).
"""
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.constants import MuscleZone
from app.database.connection import get_db
from app.dependencies.auth_dependencies import get_current_user, require_admin
from app.repositories.machine_repository import MachineRepository
from app.schemas.machine_schema import MachineCreateSchema, MachineUpdateSchema
from app.services.machine_service import MachineService
from app.utils.responses import success_response

router = APIRouter(prefix="/api/maquinas", tags=["Máquinas"])

# ── Almacenamiento de fotos ──────────────────────────────────────────────────
STATIC_ROOT = Path(__file__).resolve().parents[2] / "static"
MAQUINAS_DIR = STATIC_ROOT / "maquinas"
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_PHOTO_BYTES = 5 * 1024 * 1024  # 5 MB


def _get_service(db: Annotated[Session, Depends(get_db)]) -> MachineService:
    return MachineService(MachineRepository(db))


@router.post("", status_code=201, summary="Registrar máquina", dependencies=[Depends(require_admin)])
def crear(
    payload: MachineCreateSchema,
    service: Annotated[MachineService, Depends(_get_service)],
):
    """Registra una máquina en el catálogo. **Solo administradores.**"""
    result = service.create(payload)
    return success_response(result.model_dump(), "Máquina registrada", status_code=201)


@router.get("", summary="Listar máquinas", dependencies=[Depends(require_admin)])
def listar(
    service: Annotated[MachineService, Depends(_get_service)],
    buscar: str | None = Query(default=None),
    zona: MuscleZone | None = Query(default=None),
    solo_activas: bool = Query(default=False),
    activa: bool | None = Query(default=None, description="Filtra por estado: true=operativas, false=mantenimiento"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
):
    """Lista el catálogo de máquinas con filtros. **Solo administradores.**"""
    result = service.list(page, per_page, buscar, zona, solo_activas, activa)
    return success_response(result, "Listado de máquinas")


@router.get("/catalogo", summary="Catálogo de máquinas activas (con foto)")
def catalogo(
    service: Annotated[MachineService, Depends(_get_service)],
    _user=Depends(get_current_user),
):
    """
    Catálogo de máquinas operativas con su foto. Accesible para cualquier
    usuario autenticado (el cliente lo usa para ver las máquinas del gimnasio).
    """
    return success_response(service.list_catalog(), "Catálogo de máquinas")


@router.post("/{machine_id}/foto", summary="Subir foto de la máquina", dependencies=[Depends(require_admin)])
async def subir_foto(
    machine_id: int,
    service: Annotated[MachineService, Depends(_get_service)],
    file: UploadFile = File(...),
):
    """Sube (o reemplaza) la foto de una máquina. **Solo administradores.**"""
    # Verifica que la máquina exista antes de guardar el archivo
    service.get(machine_id)

    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato no permitido. Usa: {', '.join(sorted(ALLOWED_EXT))}",
        )
    contents = await file.read()
    if len(contents) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La imagen supera los 5 MB")

    MAQUINAS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{machine_id}_{uuid.uuid4().hex[:8]}{ext}"
    (MAQUINAS_DIR / filename).write_bytes(contents)

    foto_url = f"/static/maquinas/{filename}"
    result = service.set_photo(machine_id, foto_url)
    return success_response(result.model_dump(), "Foto actualizada")


@router.get("/{machine_id}", summary="Detalle de máquina", dependencies=[Depends(require_admin)])
def detalle(
    machine_id: int,
    service: Annotated[MachineService, Depends(_get_service)],
):
    """Devuelve una máquina por su ID. **Solo administradores.**"""
    return success_response(service.get(machine_id).model_dump(), "Máquina encontrada")


@router.put("/{machine_id}", summary="Actualizar máquina", dependencies=[Depends(require_admin)])
def actualizar(
    machine_id: int,
    payload: MachineUpdateSchema,
    service: Annotated[MachineService, Depends(_get_service)],
):
    """Actualiza una máquina (incluye activar / enviar a mantenimiento). **Solo administradores.**"""
    return success_response(service.update(machine_id, payload).model_dump(), "Máquina actualizada")


@router.delete("/{machine_id}", summary="Eliminar máquina", dependencies=[Depends(require_admin)])
def eliminar(
    machine_id: int,
    service: Annotated[MachineService, Depends(_get_service)],
):
    """Elimina una máquina del catálogo (acción independiente del mantenimiento). **Solo administradores.**"""
    service.delete(machine_id)
    return success_response(message="Máquina eliminada")
