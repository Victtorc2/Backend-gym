"""
Excepciones personalizadas del dominio de la aplicación.
Centraliza todos los errores para evitar lógica repetida en las capas superiores.
"""
from fastapi import HTTPException, status


class InvalidCredentialsException(HTTPException):
    """401 – Email o contraseña incorrectos."""

    def __init__(self, message: str = "Credenciales inválidas") -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=message,
            headers={"WWW-Authenticate": "Bearer"},
        )


class TokenExpiredException(HTTPException):
    """401 – El token JWT ha expirado."""

    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token ha expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )


class AccessDeniedException(HTTPException):
    """403 – El usuario no tiene permisos suficientes."""

    def __init__(self, message: str = "Acceso denegado") -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=message,
        )


class UserNotFoundException(HTTPException):
    """404 – Usuario no encontrado en la base de datos."""

    def __init__(self, message: str = "Usuario no encontrado") -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        )


class InactiveUserException(HTTPException):
    """401 – La cuenta del usuario está desactivada."""

    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La cuenta de usuario está inactiva",
            headers={"WWW-Authenticate": "Bearer"},
        )


class InternalServerException(HTTPException):
    """500 – Error interno no controlado."""

    def __init__(self, message: str = "Error interno del servidor") -> None:
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message,
        )


# ── Excepciones del módulo Clientes ───────────────────────────────────────────

class ClientNotFoundException(HTTPException):
    """404 – Cliente no encontrado."""

    def __init__(self, message: str = "Cliente no encontrado") -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        )


class ClientAlreadyExistsException(HTTPException):
    """409 – Ya existe un cliente con ese DNI o correo."""

    def __init__(self, field: str = "dni") -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un cliente registrado con ese {field}",
        )


class ClientInvalidDataException(HTTPException):
    """400 – Datos del cliente inválidos (ej. edad mínima no cumplida)."""

    def __init__(self, message: str = "Datos del cliente inválidos") -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )


# ── Excepciones del módulo Membresías / Tarjetas ───────────────────────────────

class MembershipNotFoundException(HTTPException):
    """404 – Membresía no encontrada."""
    def __init__(self, message: str = "Membresía no encontrada") -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=message)


class MembershipAlreadyExistsException(HTTPException):
    """409 – El cliente ya tiene una membresía activa del mismo tipo."""
    def __init__(self, message: str = "El cliente ya posee una membresía activa") -> None:
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=message)


class MembershipInvalidException(HTTPException):
    """400 – Datos de membresía inválidos (cliente inactivo, tipo inválido, etc.)."""
    def __init__(self, message: str = "Datos de membresía inválidos") -> None:
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


class CardNotFoundException(HTTPException):
    """404 – Tarjeta no encontrada."""
    def __init__(self, message: str = "Tarjeta no encontrada") -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=message)


class CardAlreadyExistsException(HTTPException):
    """409 – El cliente ya tiene una tarjeta activa."""
    def __init__(self, message: str = "El cliente ya posee una tarjeta activa") -> None:
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=message)


class CardNotEligibleException(HTTPException):
    """400 – El tipo de membresía no es elegible para emitir tarjeta."""
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo membresías mensuales o anuales son elegibles para tarjeta",
        )


# ── Excepciones del módulo Pagos ───────────────────────────────────────────────

class PaymentNotFoundException(HTTPException):
    """404 – Pago no encontrado."""
    def __init__(self, message: str = "Pago no encontrado") -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=message)


class PaymentInvalidException(HTTPException):
    """400 – Datos del pago inválidos (monto incorrecto, cliente inactivo, etc.)."""
    def __init__(self, message: str = "Datos del pago inválidos") -> None:
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


class MembershipInactiveException(HTTPException):
    """400 – La membresía no está activa o vigente."""
    def __init__(self, message: str = "La membresía no está activa") -> None:
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


class AttendanceNotFoundException(HTTPException):
    """404 – Registro de asistencia no encontrado."""
    def __init__(self, message: str = "Registro de asistencia no encontrado") -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=message)


# ── Excepciones del módulo Clientes Diarios (Fase 6) ──────────────────────────

class DailyClientNotFoundException(HTTPException):
    """404 – Cliente diario no encontrado."""

    def __init__(self, message: str = "Cliente diario no encontrado") -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=message)


class DailyClientAlreadyExistsException(HTTPException):
    """409 – Ya existe un cliente diario con ese documento."""

    def __init__(self, message: str = "Ya existe un cliente diario con ese documento") -> None:
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=message)


class DailyClientInactiveException(HTTPException):
    """400 – El cliente diario está inactivo."""

    def __init__(self, message: str = "El cliente diario está inactivo") -> None:
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


class DailyPaymentAlreadyExistsException(HTTPException):
    """409 – Ya existe un pago diario para ese cliente en esa fecha."""

    def __init__(self, message: str = "Ya existe un pago registrado para este cliente en esa fecha") -> None:
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=message)


class DailyPaymentInvalidException(HTTPException):
    """400 – Datos del pago diario inválidos (monto <= 0, etc.)."""

    def __init__(self, message: str = "Datos del pago diario inválidos") -> None:
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


class DailyIngresoAlreadyExistsException(HTTPException):
    """409 – El cliente diario ya registró un ingreso aprobado ese día."""

    def __init__(self, message: str = "El cliente ya registró un ingreso aprobado en esta fecha") -> None:
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=message)


class DailyIngresoNotFoundException(HTTPException):
    """404 – Registro de ingreso diario no encontrado."""

    def __init__(self, message: str = "Ingreso diario no encontrado") -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=message)


# ── Excepciones del módulo Recomendación de Horarios ───────────────────────────

class RecommendationNotFoundException(HTTPException):
    """404 – Recomendación de horario no encontrada."""
    def __init__(self, message: str = "Recomendación de horario no encontrada") -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=message)


class InsufficientHistoryException(HTTPException):
    """404 – No existe historial de asistencia suficiente para generar recomendaciones."""
    def __init__(self, message: str = "No existe historial de asistencia suficiente") -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=message)


class InvalidWeekDayException(HTTPException):
    """400 – Día de la semana inválido (solo lunes a sábado)."""
    def __init__(self, message: str = "Día inválido: el gimnasio opera de lunes a sábado") -> None:
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


# ── Excepciones del módulo Recomendación Personalizada a Clientes ──────────────

class ClientRecommendationNotFoundException(HTTPException):
    """404 – Recomendación personalizada no encontrada."""
    def __init__(self, message: str = "Recomendación no encontrada") -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=message)


class ClientRecommendationInvalidException(HTTPException):
    """400 – Datos inválidos para la recomendación (horario mal formado, etc.)."""
    def __init__(self, message: str = "Datos de la recomendación inválidos") -> None:
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


# ── Excepciones del módulo Planificación Inteligente / Gestión de Demanda ──────

class MachineNotFoundException(HTTPException):
    """404 – Máquina no encontrada."""
    def __init__(self, message: str = "Máquina no encontrada") -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=message)


class MachineAlreadyExistsException(HTTPException):
    """409 – Ya existe una máquina con ese nombre."""
    def __init__(self, message: str = "Ya existe una máquina con ese nombre") -> None:
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=message)


class RoutineNotFoundException(HTTPException):
    """404 – Rutina no encontrada."""
    def __init__(self, message: str = "Rutina no encontrada") -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=message)


class RoutineInvalidException(HTTPException):
    """400 – Datos de rutina inválidos (sin máquinas, máquinas inexistentes...)."""
    def __init__(self, message: str = "Datos de la rutina inválidos") -> None:
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


class TrainingPlanNotFoundException(HTTPException):
    """404 – Planificación de entrenamiento no encontrada."""
    def __init__(self, message: str = "Planificación no encontrada") -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=message)


class TrainingPlanInvalidException(HTTPException):
    """400 – Datos de planificación inválidos (sin zonas ni rutina, etc.)."""
    def __init__(self, message: str = "Datos de la planificación inválidos") -> None:
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


# ── Excepciones del módulo Comentarios / Sugerencias ──────────────────────────

class FeedbackNotFoundException(HTTPException):
    """404 – Comentario/sugerencia no encontrado."""
    def __init__(self, message: str = "Mensaje no encontrado") -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=message)


class FeedbackAccessDeniedException(HTTPException):
    """403 – El cliente intenta acceder a un mensaje que no es suyo."""
    def __init__(self, message: str = "No puedes acceder a este mensaje") -> None:
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=message)
