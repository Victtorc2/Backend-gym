"""
Middleware de la aplicación.
Actualmente gestiona CORS y logging básico de requests.
Preparado para extenderse con auditoría y trazabilidad.
"""
import logging
import time

from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware de logging por request.

    Registra método, ruta, código de respuesta y tiempo de ejecución.
    Base para futura auditoría de acciones sensibles.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()

        response = await call_next(request)

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "%s %s → %d [%.1fms]",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )

        return response


def register_cors(app) -> None:
    """
    Registra el middleware CORS en la aplicación FastAPI.
    Configurado para desarrollo; ajustar allow_origins en producción.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],          # ← En prod: especificar el dominio del frontend
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
