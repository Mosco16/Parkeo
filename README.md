<p align="center">
  <img src="frontend/public/parkeo-logo.jpeg" alt="Parkeo — Encuentra tu espacio" width="460">
</p>

# Parkeo

Sistema de gestión y control de parqueaderos para **Autos Colombia**: gestión de vehículos
con mensualidades, cuentas internas con control de acceso por roles (`ADMINISTRADOR` y `OPERADOR`),
mantenimiento de celdas con estados calculados (`DISPONIBLE`, `OCUPADA`, `MANTENIMIENTO`),
control diario de entradas y salidas con asignación automática de celda, cambios de celda
con historial auditable y panel general de ocupación en tiempo real.

- **Backend:** FastAPI, SQLAlchemy 2, Pydantic v2, bcrypt y PyJWT, con PostgreSQL y migraciones Alembic.
- **Frontend:** Angular 22 con componentes standalone, señales (`Signals`), formularios reactivos y CSS propio (sin dependencias de librerías de UI externas).

El historial detallado de cada entrega está en [docs/historial.md](docs/historial.md).

---

## Características principales

- **Autenticación y roles:** Inicio de sesión con JWT HS256 y contraseñas hasheadas con bcrypt (costo 12). Cuentas diferenciadas por rol (`ADMINISTRADOR` para gestión de usuarios y mantenimiento de celdas; `OPERADOR` para la operación diaria).
- **Panel de resumen (Dashboard):** KPIs de ocupación en tiempo real (celdas ocupadas, disponibles, en mantenimiento y total), porcentaje de ocupación, mapa interactivo agrupado por tipo de vehículo (`AUTOMOVIL` y `MOTO`) con visualización de placas en celdas ocupadas, accesos directos rápidos y monitoreo de salud de la API.
- **Gestión de vehículos:** Registro y consulta de vehículos con placa, marca, modelo, color, tipo (`AUTOMOVIL`, `CAMIONETA`, `MOTO`) y fecha de vencimiento de la mensualidad.
- **Control de accesos (Entrada):** Consulta de estado por placa y confirmación de entrada. El sistema asigna automáticamente la primera celda libre del tipo correspondiente; no permite ingresar vehículos con mensualidad vencida ni duplicar estancias abiertas.
- **Salida vehicular:** Consulta y registro de salida con cierre de estancia en la hora exacta del servidor.
- **Cambio de celda con historial auditable:** Reubicación de estancias activas hacia celdas libres del mismo tipo. Cada movimiento se registra de forma inmutable en la tabla `cambio_celda` guardando fecha/hora (hora de Bogotá), placa, celda origen, celda destino y usuario responsable.
- **Consulta de historial:** Pantalla dedicada `/historial` con paginación de los movimientos de celda ordenados del más reciente al más antiguo.
- **Administración de celdas:** Vista exclusiva para administradores donde se pueden habilitar o poner en mantenimiento celdas sin estancias activas.
- **Administración de usuarios:** CRUD de cuentas de operador, activación/desactivación lógica y restablecimiento seguro de contraseñas.

---

## Requisitos del sistema

- Sistema operativo Windows con **PowerShell**.
- **Python 3.13** (probado con 3.13.16).
- **Node.js 24** (mínimo 24.15.0) y **npm 11**.
- **PostgreSQL 17** con una base de datos creada (por defecto `autos_colombia`).

---

## Instalación y configuración

### 1. Clonar el repositorio

```powershell
git clone https://github.com/Mosco16/Parkeo.git
Set-Location -LiteralPath 'Parkeo'
```

### 2. Backend

```powershell
Set-Location -LiteralPath 'backend'
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path -LiteralPath .env)) { Copy-Item -LiteralPath .env.example -Destination .env }
```

Edita `backend/.env` con las credenciales de tu PostgreSQL local (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`). Comprueba la conexión:

```powershell
.\.venv\Scripts\python.exe .\check_db.py
```

### 3. Frontend

```powershell
Set-Location -LiteralPath '..\frontend'
npm.cmd ci
```

---

## Base de datos y migraciones

Aplica las migraciones de Alembic (`0001` a `0007`) para crear y estructurar las tablas:

```powershell
Set-Location -LiteralPath '..\backend'
.\.venv\Scripts\python.exe -m alembic -c .\alembic.ini upgrade head
```

### Cargar datos de demostración

El script `cargar_datos_demo.py` es idempotente y carga 80 celdas (A1–A70 `AUTO`, M1–M10 `MOTO`), 4 cuentas de usuario demostrativas y 5 vehículos con vencimientos relativos a hoy:

```powershell
.\.venv\Scripts\python.exe scripts\cargar_datos_demo.py
```

### Credenciales de demostración

| Usuario | Contraseña | Rol | Descripción |
|---|---|---|---|
| `admin` | `Parkeo2026*` | `ADMINISTRADOR` | Administrador general con acceso a usuarios y celdas |
| `ana.gomez` | `Parkeo2026*` | `OPERADOR` | Operador para registro de entradas, salidas y reubicaciones |
| `carlos.perez` | `Parkeo2026*` | `OPERADOR` | Operador de turno |
| `laura.rios` | `Parkeo2026*` | `OPERADOR` | Operadora de turno |

---

## Ejecución del proyecto

### Terminal 1 — Backend (FastAPI)

```powershell
Set-Location -LiteralPath 'backend'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- API Base: <http://127.0.0.1:8000>
- Documentación interactiva Swagger: <http://127.0.0.1:8000/docs>
- Estado de salud: <http://127.0.0.1:8000/health>

### Terminal 2 — Frontend (Angular)

```powershell
Set-Location -LiteralPath 'frontend'
npm.cmd start -- --host 127.0.0.1 --port 4200
```

Accede a la aplicación en <http://127.0.0.1:4200>.

---

## Ejecución de pruebas

### Backend (pytest)

```powershell
Set-Location -LiteralPath 'backend'
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
```

Para ejecutar las pruebas de integración directa contra la base PostgreSQL:

```powershell
$env:RUN_POSTGRES_TESTS = '1'
try {
    .\.venv\Scripts\python.exe -m pytest -q
} finally {
    Remove-Item Env:RUN_POSTGRES_TESTS -ErrorAction SilentlyContinue
}
```

### Frontend (Vitest)

```powershell
Set-Location -LiteralPath 'frontend'
npm.cmd run build
npm.cmd test -- --watch=false
```

---

## Documentación adicional

- [backend/README.md](backend/README.md): especificación de endpoints, schemas y lógica de capas.
- [frontend/README.md](frontend/README.md): rutas, guards de navegación y componentes.
- [AGENTS.md](AGENTS.md): lineamientos y convenciones de desarrollo.
- [docs/historial.md](docs/historial.md): registro histórico de iteraciones.
