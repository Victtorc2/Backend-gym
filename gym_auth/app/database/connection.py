"""
Configuración de la conexión a la base de datos.
Provee el engine, la sesión y la base declarativa de SQLAlchemy.
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


# ── Engine ─────────────────────────────────────────────────────────────────────
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,       # Verifica la conexión antes de usarla
    pool_recycle=3600,        # Recicla conexiones cada hora
    echo=settings.APP_ENV == "development",  # Log SQL solo en desarrollo
)

# ── Session factory ────────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


# ── Base declarativa ───────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """Clase base para todos los modelos SQLAlchemy."""
    pass


# ── Dependency ─────────────────────────────────────────────────────────────────
def get_db() -> Generator[Session, None, None]:
    """
    Dependency de FastAPI que provee una sesión de BD por request.
    Garantiza el cierre de la sesión al finalizar.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
