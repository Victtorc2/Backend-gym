"""
Utilidades para respuestas HTTP uniformes.
Garantiza un contrato consistente para el frontend React.

Usa jsonable_encoder de FastAPI para serializar correctamente:
  - date / datetime → strings ISO 8601
  - Decimal → compatible con JSON
  - Enums → sus valores string
  - Objetos Pydantic / SQLAlchemy
"""
from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def success_response(
    data: Any = None,
    message: str = "Operación exitosa",
    status_code: int = 200,
) -> JSONResponse:
    """
    Respuesta estándar de éxito con serialización segura.

    Formato:
        {
            "success": true,
            "message": "...",
            "data": { ... }
        }
    """
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder({
            "success": True,
            "message": message,
            "data": data,
        }),
    )


def error_response(
    message: str = "Ha ocurrido un error",
    status_code: int = 400,
    details: Any = None,
) -> JSONResponse:
    """
    Respuesta estándar de error con serialización segura.

    Formato:
        {
            "success": false,
            "message": "...",
            "details": null  (opcional)
        }
    """
    body: dict[str, Any] = {
        "success": False,
        "message": message,
    }
    if details is not None:
        body["details"] = details

    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(body),
    )
