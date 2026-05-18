"""
Punto de entrada de la aplicación FastAPI.
Configura middlewares, manejadores de excepciones, rutas y el seed inicial.
"""
import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.database.connection import Base, SessionLocal, engine
from app.middleware.role_middleware import RequestLoggingMiddleware, register_cors
from app.routes.auth_router import router as auth_router
from app.routes.client_router import router as client_router
from app.routes.membership_router import membership_router, card_router
from app.routes.payment_router import router as payment_router
from app.routes.attendance_router import router as attendance_router
from app.routes.daily_client_router import daily_client_router, daily_ingreso_router
from app.routes.segmentation_router import router as segmentation_router
from app.routes.report_router import router as report_router
from app.seed.admin_seed import run_admin_seed
import app.models.user       # noqa: F401
import app.models.client     # noqa: F401
import app.models.membership # noqa: F401
import app.models.card       # noqa: F401
import app.models.payment    # noqa: F401
import app.models.attendance # noqa: F401
import app.models.daily_client  # noqa: F401

# ── Logging básico ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ── Inicialización de la app ───────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    description="Backend para el Sistema de Gimnasio.",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middlewares ────────────────────────────────────────────────────────────────
register_cors(app)
app.add_middleware(RequestLoggingMiddleware)


# ── Manejadores globales de excepciones ───────────────────────────────────────

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Convierte HTTPException al formato de respuesta uniforme."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Convierte errores de validación Pydantic al formato uniforme (422)."""
    errors = [
        {"campo": " → ".join(str(loc) for loc in err["loc"]), "mensaje": err["msg"]}
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "Error de validación en los datos enviados",
            "details": errors,
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Captura excepciones no controladas y evita exponer trazas al cliente."""
    logger.exception("Error no controlado en %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"success": False, "message": "Error interno del servidor"},
    )


# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(client_router)
app.include_router(membership_router)
app.include_router(card_router)
app.include_router(payment_router)
app.include_router(attendance_router)
app.include_router(daily_client_router)
app.include_router(daily_ingreso_router)
app.include_router(segmentation_router)
app.include_router(report_router)


# ── Eventos de ciclo de vida ───────────────────────────────────────────────────

@app.on_event("startup")
def on_startup() -> None:
    """
    Tareas al iniciar la aplicación:
    1. Crear tablas si no existen (desarrollo/testing).
    2. Ejecutar el seed del administrador.
    """
    logger.info("Iniciando aplicación: %s v%s", settings.APP_TITLE, settings.APP_VERSION)

    # Crea las tablas definidas en los modelos (no reemplaza Alembic en producción)
    Base.metadata.create_all(bind=engine)
    logger.info("Tablas verificadas / creadas en la base de datos.")

    # Seed del administrador inicial
    with SessionLocal() as db:
        run_admin_seed(db)

    logger.info("Aplicación lista.")


# ── Health check ───────────────────────────────────────────────────────────────

@app.get("/health", tags=["Sistema"], summary="Estado del servidor")
def health_check():
    """Endpoint de verificación de disponibilidad."""
    return {"success": True, "message": "Servidor operativo", "version": settings.APP_VERSION}
