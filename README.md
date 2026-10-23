# Autos Colombia

Aplicación de ejemplo para administrar el parqueadero de una empresa: vehículos
y mensualidad, operadores, celdas y el control diario de entradas, salidas y
cambios de celda.

- **Backend:** FastAPI, SQLAlchemy y PostgreSQL, con migraciones Alembic.
- **Frontend:** Angular 22 con componentes standalone, formularios reactivos y
  CSS propio (sin Angular Material).

El historial detallado de cada etapa del proyecto quedó en
[docs/historial.md](docs/historial.md).

## Qué permite hacer

- Gestionar vehículos con placa, marca, modelo, color, tipo y fecha de
  vencimiento de la mensualidad.
- Gestionar operadores y celdas; el tipo de celda solo puede ser `AUTO` o `MOTO`.
- Iniciar turno con un operador y trabajar desde el tablero de celdas.
- Registrar la entrada de un vehículo sin elegir celda: el sistema asigna la
  primera celda libre del tipo que corresponde.
- Registrar la salida y cambiar una estancia abierta a otra celda libre del
  mismo tipo.
- Consultar por placa si el vehículo está `DENTRO` o `FUERA` y si la mensualidad
  está `VIGENTE` o `VENCIDA`.
- Corregir una entrada duplicada cerrando la estancia anterior con una salida
  normal y registrando una entrada nueva; el historial no se borra ni se edita.

## Requisitos

- Windows con PowerShell.
- Python 3.13 (probado con 3.13.16).
- Node.js 24 (mínimo 24.15.0) y npm 11.
- PostgreSQL local con una base de datos y un usuario. El proyecto no instala
  PostgreSQL ni crea la base.

## Instalación

### Backend

```powershell
Set-Location -LiteralPath 'C:\ruta\a\AutosColombia\backend'
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path -LiteralPath .env)) { Copy-Item -LiteralPath .env.example -Destination .env }
```

Edita `backend/.env` con los datos de tu PostgreSQL (`DB_HOST`, `DB_PORT`,
`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_CONNECT_TIMEOUT`). No versiones `.env`
ni compartas sus valores. Comprueba la conexión:

```powershell
.\.venv\Scripts\python.exe .\check_db.py
```

### Frontend

```powershell
Set-Location -LiteralPath 'C:\ruta\a\AutosColombia\frontend'
npm.cmd ci
```

## Ejecución en Windows

Terminal 1 (backend):

```powershell
Set-Location -LiteralPath 'C:\ruta\a\AutosColombia\backend'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2 (frontend):

```powershell
Set-Location -LiteralPath 'C:\ruta\a\AutosColombia\frontend'
npm.cmd start -- --host 127.0.0.1 --port 4200
```

Abre <http://127.0.0.1:4200>. La API queda en <http://127.0.0.1:8000> y su
documentación interactiva en <http://127.0.0.1:8000/docs>. El proxy de
desarrollo (`frontend/proxy.conf.json`) dirige `/health`, `/vehiculos`,
`/celdas`, `/operadores` y `/estancias` al backend local.

## Base de datos y migraciones

Las tablas se crean solo cuando ejecutas Alembic de forma explícita:

```powershell
Set-Location -LiteralPath 'C:\ruta\a\AutosColombia\backend'
.\.venv\Scripts\python.exe -m alembic -c .\alembic.ini upgrade head
.\.venv\Scripts\python.exe -m alembic -c .\alembic.ini current
```

Para revisar el SQL sin aplicarlo usa `upgrade head --sql`. No apliques
migraciones a una base con datos que no controlas sin revisar antes ese SQL.
El detalle de las revisiones `0001` a `0004` está en
[backend/README.md](backend/README.md).

## Datos de demostración

`backend/scripts/cargar_datos_demo.py` carga 80 celdas (A1–A70 `AUTO`, M1–M10
`MOTO`), operadores de ejemplo y vehículos con vencimientos relativos a hoy en
America/Bogota. Es idempotente y no es una migración. Ejecútalo solo en una base
de demostración:

```powershell
Set-Location -LiteralPath 'C:\ruta\a\AutosColombia\backend'
.\.venv\Scripts\python.exe scripts\cargar_datos_demo.py
```

## Pruebas

Backend:

```powershell
Set-Location -LiteralPath 'C:\ruta\a\AutosColombia\backend'
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
```

Las pruebas de integración contra PostgreSQL se habilitan con
`$env:RUN_POSTGRES_TESTS = '1'` y requieren las migraciones aplicadas. Usan
transacciones revertidas: no borran ni crean datos permanentes.

Frontend:

```powershell
Set-Location -LiteralPath 'C:\ruta\a\AutosColombia\frontend'
npm.cmd run build
npm.cmd test -- --watch=false
```

## Documentación

- [backend/README.md](backend/README.md): API, migraciones, modelos y mensajes de error.
- [frontend/README.md](frontend/README.md): pantallas, rutas y verificación.
- [AGENTS.md](AGENTS.md): convenciones de trabajo del repositorio.
- [docs/historial.md](docs/historial.md): historial completo de las etapas anteriores.
