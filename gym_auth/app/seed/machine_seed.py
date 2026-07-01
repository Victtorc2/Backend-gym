"""
Seed del catálogo de máquinas de ejemplo.
Se ejecuta al arrancar. Solo inserta si la tabla 'maquinas' está vacía;
nunca duplica ni sobrescribe un catálogo ya cargado por el administrador.
"""
import logging

from sqlalchemy.orm import Session

from app.core.constants import MuscleZone
from app.models.machine import Machine
from app.repositories.machine_repository import MachineRepository

logger = logging.getLogger(__name__)

# Catálogo de ejemplo: (nombre, zona, unidades disponibles)
_DEFAULT_MACHINES: list[tuple[str, MuscleZone, int]] = [
    ("Press banca", MuscleZone.PECHO, 1),
    ("Peck Deck", MuscleZone.PECHO, 1),
    ("Press inclinado", MuscleZone.PECHO, 1),
    ("Polea Alta", MuscleZone.ESPALDA, 1),
    ("Remo sentado", MuscleZone.ESPALDA, 1),
    ("Jalón unilateral", MuscleZone.ESPALDA, 1),
    ("Prensa", MuscleZone.PIERNAS, 1),
    ("Smith", MuscleZone.PIERNAS, 1),
    ("Extensión de cuádriceps", MuscleZone.PIERNAS, 1),
    ("Curl femoral", MuscleZone.PIERNAS, 1),
    ("Hip thrust", MuscleZone.GLUTEOS, 1),
    ("Curl Scott", MuscleZone.BICEPS, 1),
    ("Curl con barra", MuscleZone.BICEPS, 1),
    ("Extensión de tríceps polea", MuscleZone.TRICEPS, 1),
    ("Press militar", MuscleZone.HOMBROS, 1),
    ("Elevaciones laterales", MuscleZone.HOMBROS, 1),
    ("Máquina abdominal", MuscleZone.ABDOMEN, 1),
    ("Cinta de correr", MuscleZone.CARDIO, 3),
    ("Bicicleta estática", MuscleZone.CARDIO, 3),
    ("Elíptica", MuscleZone.CARDIO, 2),
]


def run_machine_seed(db: Session) -> None:
    """Carga el catálogo de máquinas de ejemplo si aún no hay ninguna."""
    repo = MachineRepository(db)

    if repo.count() > 0:
        logger.info("Seed: ya existen máquinas, se omite la carga del catálogo.")
        return

    objetos = [
        Machine(nombre=nombre, zona=zona, cantidad=cantidad, activa=True)
        for nombre, zona, cantidad in _DEFAULT_MACHINES
    ]
    db.add_all(objetos)
    db.commit()
    logger.info("Seed: catálogo de máquinas cargado (%d máquinas).", len(objetos))
