"""
Constantes globales de la aplicación.
Centraliza valores fijos para evitar strings mágicos dispersos.
"""
from enum import Enum


class UserRole(str, Enum):
    """Roles permitidos en el sistema."""
    ADMINISTRADOR = "administrador"
    CLIENTE = "cliente"


class UserStatus(str, Enum):
    """Estados posibles de un usuario."""
    ACTIVO = "activo"
    INACTIVO = "inactivo"


# ── Seed defaults ──────────────────────────────────────────────────────────────
ADMIN_DEFAULT_NOMBRES: str = "Admin"
ADMIN_DEFAULT_APELLIDOS: str = "Sistema"
ADMIN_DEFAULT_DNI: str = "00000000"
ADMIN_DEFAULT_EMAIL: str = "admin@gym.com"
ADMIN_DEFAULT_PASSWORD: str = "Admin123"

# ── Token ──────────────────────────────────────────────────────────────────────
TOKEN_TYPE: str = "bearer"


# ── Módulo Clientes ────────────────────────────────────────────────────────────

class ClientStatus(str, Enum):
    """Estados posibles de un cliente."""
    ACTIVO = "activo"
    INACTIVO = "inactivo"


class ClientSex(str, Enum):
    """Sexo biológico/identidad declarada del cliente."""
    MASCULINO = "masculino"
    FEMENINO = "femenino"
    OTRO = "otro"


class AgeGroup(str, Enum):
    """Clasificación demográfica por edad."""
    JOVEN = "joven"    # < 30 años
    ADULTO = "adulto"  # >= 30 años


# Edad mínima para registrar un cliente (años cumplidos)
CLIENT_MIN_AGE: int = 14

# Contraseña temporal asignada al crear el acceso del cliente
TEMP_PASSWORD_DEFAULT: str = "Gym12345"

# Longitud del sufijo numérico del username generado automáticamente
USERNAME_SUFFIX_LENGTH: int = 3


# ── Módulo Membresías ──────────────────────────────────────────────────────────

class MembershipType(str, Enum):
    """Tipos de membresía disponibles."""
    MENSUAL = "mensual"   # 30 días
    ANUAL = "anual"       # 365 días
    DIARIO = "diario"     # 1 día


class MembershipStatus(str, Enum):
    """Estados posibles de una membresía."""
    ACTIVA = "activa"
    VENCIDA = "vencida"
    PENDIENTE = "pendiente"


class CardStatus(str, Enum):
    """Estados posibles de una tarjeta física."""
    ACTIVA = "activa"
    INACTIVA = "inactiva"


# Duración en días por tipo de membresía (única fuente de verdad)
MEMBERSHIP_DURATION_DAYS: dict = {
    "mensual": 30,
    "anual": 365,
    "diario": 1,
}

# Prefijo del código de tarjeta (GYM-00001)
CARD_CODE_PREFIX: str = "GYM"

# Tipos de membresía elegibles para recibir tarjeta física
CARD_ELIGIBLE_TYPES: frozenset = frozenset({"mensual", "anual"})


# ── Módulo Pagos ───────────────────────────────────────────────────────────────

class PaymentStatus(str, Enum):
    """Estados posibles de un pago."""
    PAGADO   = "pagado"     # monto_pagado == monto_total
    PENDIENTE = "pendiente" # monto_pagado < monto_total
    VENCIDO  = "vencido"    # pendiente + membresía vencida


class PaymentMethod(str, Enum):
    """Métodos de pago aceptados."""
    EFECTIVO     = "efectivo"
    TRANSFERENCIA = "transferencia"
    YAPE         = "yape"
    PLIN         = "plin"


# ── Módulo Asistencias ─────────────────────────────────────────────────────────

class AttendanceStatus(str, Enum):
    """Resultado del intento de ingreso al gimnasio."""
    INGRESO_APROBADO = "ingreso_aprobado"
    INGRESO_DENEGADO = "ingreso_denegado"


class DenialReason(str, Enum):
    """Motivos estandarizados de denegación de ingreso."""
    TARJETA_INVALIDA     = "tarjeta_invalida"
    TARJETA_INACTIVA     = "tarjeta_inactiva"
    CLIENTE_INACTIVO     = "cliente_inactivo"
    MEMBRESIA_INEXISTENTE = "membresia_inexistente"
    MEMBRESIA_VENCIDA    = "membresia_vencida"
    DEUDA_VENCIDA        = "deuda_vencida"


# ── Módulo Clientes Diarios (Fase 6) ───────────────────────────────────────────

class DailyClientStatus(str, Enum):
    """Estados posibles de un cliente diario."""
    ACTIVO   = "activo"
    INACTIVO = "inactivo"


class DailyIngresoStatus(str, Enum):
    """Resultado del intento de ingreso de un cliente diario."""
    APROBADO = "aprobado"
    DENEGADO = "denegado"


# Motivos de denegación para ingresos diarios
class DailyDenialReason(str, Enum):
    """Motivos estandarizados para denegación de ingreso diario."""
    CLIENTE_INACTIVO  = "cliente_inactivo"
    SIN_PAGO_DEL_DIA  = "sin_pago_del_dia"
    INGRESO_DUPLICADO = "ingreso_duplicado"


# ── Módulo Segmentación (Fase 7) ───────────────────────────────────────────────

class ActivitySegment(str, Enum):
    """Segmento de actividad calculado por frecuencia de asistencia mensual."""
    ACTIVO       = "activo"        # >= ACTIVITY_ACTIVE_THRESHOLD asistencias/mes
    POCO_ACTIVO  = "poco_activo"   # 1 a ACTIVITY_ACTIVE_THRESHOLD-1 asistencias/mes
    INACTIVO     = "inactivo"      # 0 asistencias en el mes en curso


class FinancialSegment(str, Enum):
    """Segmento financiero calculado a partir del estado de pagos."""
    SIN_DEUDA = "sin_deuda"   # sin pagos pendientes ni vencidos
    CON_DEUDA = "con_deuda"   # tiene al menos un pago pendiente o vencido


# Umbral mínimo de asistencias en el mes actual para ser considerado "activo"
ACTIVITY_ACTIVE_THRESHOLD: int = 8   # >= 8 visitas/mes → activo
ACTIVITY_LOW_THRESHOLD: int    = 1   # 1-7 visitas/mes → poco activo
                                     # 0 visitas/mes   → inactivo

# Edad límite para clasificar como "joven" (inclusive)
AGE_YOUNG_MAX: int = 25   # 14-25 → joven | 26+ → adulto


# ── Módulo Recomendación de Horarios (Fase 10) ─────────────────────────────────

class AffluenceLevel(str, Enum):
    """Nivel de afluencia de un bloque horario según ingresos registrados."""
    BAJA  = "BAJA"   # 0-20 personas
    MEDIA = "MEDIA"  # 21-45 personas
    ALTA  = "ALTA"   # 46+ personas


class WeekDay(str, Enum):
    """Días de operación del gimnasio (lunes a sábado)."""
    LUNES     = "lunes"
    MARTES    = "martes"
    MIERCOLES = "miercoles"
    JUEVES    = "jueves"
    VIERNES   = "viernes"
    SABADO    = "sabado"


# Horario de operación del gimnasio
GYM_OPEN_HOUR: int  = 7    # 07:00 AM
GYM_CLOSE_HOUR: int = 22   # 10:00 PM

# Umbrales de clasificación de afluencia (cantidad promedio de personas por bloque)
AFFLUENCE_LOW_MAX: int  = 20   # 0-20  → BAJA
AFFLUENCE_MED_MAX: int  = 45   # 21-45 → MEDIA
                               # 46+   → ALTA

# Mapeo de weekday() de Python (lunes=0) al enum de día
PYTHON_WEEKDAY_TO_ENUM: dict = {
    0: "lunes",
    1: "martes",
    2: "miercoles",
    3: "jueves",
    4: "viernes",
    5: "sabado",
    # 6 (domingo) se excluye: el gimnasio no opera
}
