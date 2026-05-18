# 🏋️ Gym CRM — Módulo de Autenticación y Acceso

Backend REST API construido con **FastAPI + Clean Architecture** para gestión de autenticación de un sistema CRM de gimnasio.

---

## 🛠️ Tecnologías

| Capa | Tecnología |
|---|---|
| Framework | FastAPI |
| ORM | SQLAlchemy 2.x |
| Base de datos | MySQL |
| Migraciones | Alembic |
| Autenticación | JWT (python-jose) |
| Hashing | Passlib + bcrypt |
| Validación | Pydantic v2 |
| Config | pydantic-settings + .env |

---

## 📁 Estructura del proyecto

```
app/
├── core/           # config, seguridad, excepciones, constantes
├── database/       # conexión SQLAlchemy, sesión, Base declarativa
├── models/         # modelos ORM (tabla usuarios)
├── schemas/        # contratos Pydantic (entrada/salida)
├── repositories/   # acceso a BD (Repository Pattern)
├── services/       # lógica de negocio (Service Layer)
├── dependencies/   # inyección de dependencias FastAPI
├── middleware/      # CORS, logging de requests
├── routes/         # endpoints REST
├── seed/           # datos iniciales (admin por defecto)
├── utils/          # respuestas HTTP uniformes
└── main.py         # entry point, handlers globales
alembic/            # migraciones de BD
```

---

## 🚀 Instalación y ejecución

### 1. Clonar y crear entorno virtual

```bash
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

```bash
cp .env.example .env   # o editar .env directamente
```

Editar `.env`:

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=tu_contraseña
DB_NAME=gym_crm

SECRET_KEY=cambia_esto_en_produccion
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

### 4. Crear la base de datos en MySQL

```sql
CREATE DATABASE gym_crm CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 5. Ejecutar migraciones con Alembic

```bash
alembic revision --autogenerate -m "crear tabla usuarios"
alembic upgrade head
```

> **Alternativa rápida (desarrollo):** La aplicación crea las tablas automáticamente al arrancar via `Base.metadata.create_all()`.

### 6. Iniciar el servidor

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 📋 Endpoints disponibles

| Método | Ruta | Descripción | Auth |
|---|---|---|---|
| `POST` | `/api/auth/login` | Iniciar sesión | ❌ Público |
| `GET` | `/api/auth/me` | Datos del usuario autenticado | ✅ JWT |
| `GET` | `/health` | Estado del servidor | ❌ Público |
| `GET` | `/docs` | Swagger UI interactivo | ❌ Público |
| `GET` | `/redoc` | Documentación ReDoc | ❌ Público |

---

## 🔑 Credenciales del administrador por defecto

Se crean automáticamente al arrancar si no existe ningún admin:

```
Email:    admin@gym.com
Password: Admin123
```

---

## 📦 Ejemplos de uso

### Login

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@gym.com", "password": "Admin123"}'
```

**Respuesta:**
```json
{
  "success": true,
  "message": "Login exitoso",
  "data": {
    "access_token": "eyJ...",
    "token_type": "bearer",
    "rol": "administrador",
    "nombre": "Admin Sistema"
  }
}
```

### Usuario autenticado

```bash
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer eyJ..."
```

**Respuesta:**
```json
{
  "success": true,
  "message": "Usuario autenticado",
  "data": {
    "id": 1,
    "nombre": "Admin Sistema",
    "email": "admin@gym.com",
    "rol": "administrador"
  }
}
```

---

## 🔒 Proteger rutas futuras

```python
from app.dependencies.auth_dependencies import require_admin, require_cliente

# Solo administradores
@router.get("/admin-only", dependencies=[Depends(require_admin)])
def admin_route(): ...

# Solo clientes
@router.get("/client-only", dependencies=[Depends(require_cliente)])
def client_route(): ...

# Cualquier usuario autenticado
@router.get("/protected")
def protected(user: User = Depends(get_current_user)): ...
```

---

## 🏗️ Arquitectura

```
HTTP Request
    │
    ▼
[Router]          ← Solo define rutas, delega todo
    │
    ▼
[Service]         ← Lógica de negocio pura
    │
    ▼
[Repository]      ← Acceso a BD (SQLAlchemy)
    │
    ▼
[Database]        ← MySQL via connection pool
```

**Dependencias entre capas (siempre hacia adentro):**

```
Routes → Services → Repositories → Models
           ↓
        Schemas (contratos Pydantic)
           ↓
        Core (config, security, exceptions)
```

---

## 🔮 Módulos futuros previstos

Este backend está preparado para integrar sin modificaciones:

- `app/models/membresia.py` — Membresías
- `app/models/pago.py` — Pagos
- `app/models/asistencia.py` — Asistencia
- `app/routes/clientes_router.py` — CRUD de clientes
- Proteger rutas con `Depends(require_admin)` / `Depends(require_cliente)`
