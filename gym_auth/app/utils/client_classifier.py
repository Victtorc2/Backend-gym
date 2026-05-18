"""
Utilidades de clasificación automática de clientes.
Lógica completamente desacoplada: no depende de modelos ni de BD.

Clasificaciones implementadas:
- Demográfica: grupo de edad (joven / adulto) y sexo
- Socioeconómica: categoría por ocupación
"""
from datetime import date

from app.core.constants import AgeGroup


def calculate_age(birth_date: date) -> int:
    """
    Calcula la edad exacta en años cumplidos.

    Args:
        birth_date: Fecha de nacimiento.

    Returns:
        Edad en años completos.
    """
    today = date.today()
    return (
        today.year - birth_date.year
        - ((today.month, today.day) < (birth_date.month, birth_date.day))
    )


def classify_age_group(birth_date: date) -> AgeGroup:
    """
    Clasifica el cliente en un grupo etario.

    Regla:
        edad < 30  → AgeGroup.JOVEN
        edad >= 30 → AgeGroup.ADULTO

    Args:
        birth_date: Fecha de nacimiento del cliente.

    Returns:
        AgeGroup correspondiente.
    """
    age = calculate_age(birth_date)
    return AgeGroup.JOVEN if age < 30 else AgeGroup.ADULTO


def generate_username(nombres: str, apellidos: str, suffix: int) -> str:
    """
    Genera un nombre de usuario a partir del primer nombre y primer apellido.

    Formato: <primer_nombre><primer_apellido><sufijo_3_digitos>
    Ejemplo: "Víctor Chipana", sufijo=1 → "vchipana001"

    Args:
        nombres:   Nombres del cliente (puede contener varios).
        apellidos: Apellidos del cliente (puede contener varios).
        suffix:    Número entero para garantizar unicidad.

    Returns:
        Username normalizado en minúsculas sin tildes.
    """
    import unicodedata

    def normalize(text: str) -> str:
        """Elimina tildes y caracteres especiales."""
        nfkd = unicodedata.normalize("NFKD", text)
        return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()

    first_name = normalize(nombres.strip().split()[0])
    first_lastname = normalize(apellidos.strip().split()[0])
    return f"{first_name}{first_lastname}{suffix:03d}"
