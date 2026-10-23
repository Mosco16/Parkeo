# Backend de Autos Colombia

API del parqueadero: vehículos y mensualidad, operadores, celdas y estancias
(entrada, salida y cambio de celda).

- FastAPI para las rutas y la documentación interactiva.
- SQLAlchemy 2 para los modelos y las sesiones.
- PostgreSQL como base de datos.
- Alembic para las migraciones.
- pytest con `TestClient` para las pruebas.

La documentación general del proyecto está en el [README principal](../README.md)
y el historial de etapas en [docs/historial.md](../docs/historial.md).

## Estructura y regla de capas

```
backend/
  app/
    main.py            aplicación FastAPI y /health
    config.py          lectura de backend/.env
    database.py        get_engine() y get_session()
    models.py          Vehiculo, Celda, Operador, Estancia
    schemas/           contratos Pydantic por recurso
    routers/           vehículos, operadores, celdas, estancias
    services/          reglas de negocio y transacciones
  migrations/versions/ revisiones Alembic 0001 a 0004
  scripts/             datos de demostración
  tests/               pruebas unitarias y de integración
```

**Regla de capas:** los routers solo reciben la petición, delegan en un servicio
y devuelven la respuesta. Las reglas de negocio, las validaciones contra la base,
los `commit`/`rollback` y la traducción de errores viven en `app/services/`.
Los routers no consultan la base ni capturan excepciones de SQLAlchemy.

## Requisitos y entorno

Entorno verificado: Python 3.13.16 en Windows.

```powershell
Set-Location -LiteralPath 'C:\ruta\a\AutosColombia\backend'
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

`requirements.txt` fija todas las dependencias, incluidas las transitivas. No es
necesario activar el entorno virtual. Usa siempre `backend/.venv`; no instales
paquetes del backend de forma global.

## Configuración de PostgreSQL

1. Prepara una base y un usuario en tu PostgreSQL local. El proyecto no crea la base.
2. Si no existe `.env`, copia la plantilla sin sobrescribir un archivo existente:

   ```powershell
   if (-not (Test-Path -LiteralPath .env)) {
       Copy-Item -LiteralPath .env.example -Destination .env
   }
   ```

3. Edita `.env` con `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` y
   `DB_CONNECT_TIMEOUT` (entero entre 1 y 60). Los valores `CAMBIAR_...` son
   marcadores y bloquean la conexión.
4. Comprueba la conexión con `SELECT 1`, sin DDL:

   ```powershell
   .\.venv\Scripts\python.exe .\check_db.py
   $LASTEXITCODE
   ```

`.env` está excluido de Git. `.env.example` se versiona solo con valores ficticios.
Ni la API ni `check_db.py` imprimen credenciales, la URL de conexión o errores
crudos del controlador.

## Ejecutar la API

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- `GET /health` → `200 {"status": "ok"}`, independiente de PostgreSQL.
- Documentación interactiva: <http://127.0.0.1:8000/docs>.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Las pruebas de integración usan PostgreSQL real y se omiten por defecto. Se
habilitan con `RUN_POSTGRES_TESTS=1`:

```powershell
$env:RUN_POSTGRES_TESTS = '1'
try {
    .\.venv\Scripts\python.exe -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw 'Fallaron las pruebas.' }
} finally {
    Remove-Item Env:RUN_POSTGRES_TESTS -ErrorAction SilentlyContinue
}
```

Requieren las migraciones aplicadas. Cada prueba corre dentro de una transacción
exterior con savepoints que se revierte al terminar: no crean tablas, no borran
datos existentes y no modifican el esquema. Las secuencias de ids pueden avanzar.

## Modelos y migraciones

| Revisión | Contenido |
| --- | --- |
| `0001_modelos_iniciales` | `vehiculo`, `celda` y `operador` |
| `0002_estancia` | `estancia`, con una sola estancia abierta por vehículo y por celda |
| `0003_mensualidad_y_tipo_celda` | `vehiculo.fecha_vencimiento` (NOT NULL) y `celda.tipo` restringido a `AUTO` o `MOTO` |
| `0004_telefono_operador_opcional` | `operador.telefono` pasa a ser opcional |

En `0003`, los vehículos que ya existían recibieron `CURRENT_DATE + 30` días como
fecha de vencimiento para no romper la restricción `NOT NULL`.

Comandos útiles:

```powershell
.\.venv\Scripts\python.exe -m alembic -c .\alembic.ini current
.\.venv\Scripts\python.exe -m alembic -c .\alembic.ini heads
.\.venv\Scripts\python.exe -m alembic -c .\alembic.ini history
# Revisar el SQL sin conectarse ni aplicar cambios:
.\.venv\Scripts\python.exe -m alembic -c .\alembic.ini upgrade head --sql
# Aplicar (sí modifica el esquema):
.\.venv\Scripts\python.exe -m alembic -c .\alembic.ini upgrade head
```

No uses `stamp` para dar por aplicada una migración que no se ejecutó.

Detalles de los modelos:

- `id` es `BIGINT GENERATED ALWAYS AS IDENTITY`; se omite al insertar.
- El ORM recorta los textos, convierte `placa` y `codigo` a mayúsculas y rechaza
  valores vacíos o formados solo por espacios.
- `modelo` es un año entero entre 1 y 9999.
- `vehiculo.tipo` admite `MOTO`, `AUTOMOVIL` y `CAMIONETA`.
- `celda.tipo` admite únicamente `AUTO` o `MOTO`.
- `estancia` guarda entrada y salida con zona horaria y los operadores que
  registraron cada movimiento. Una estancia abierta es la que tiene `salida IS NULL`.

## API por recurso

### Vehículos — `/vehiculos`

| Método y ruta | Resultado |
| --- | --- |
| `POST /vehiculos` | 201 con el vehículo creado |
| `GET /vehiculos?offset=0&limit=20` | 200 con `items`, `total`, `offset` y `limit` |
| `GET /vehiculos/{id}` | 200 o 404 |
| `PATCH /vehiculos/{id}` | 200; solo campos enviados, sin nulos ni `id` |
| `DELETE /vehiculos/{id}` | 204, 404 o 409 si tiene estancias |

Al crear se requieren `placa`, `color`, `modelo`, `marca`, `tipo` y
`fecha_vencimiento`. La fecha se envía como texto `AAAA-MM-DD`; es obligatoria y
se escribe a mano al registrar o editar. La placa es texto libre: no se valida el
formato colombiano, solo se recorta y se pasa a mayúsculas.

```json
{
  "placa": "ABC123",
  "color": "Blanco",
  "modelo": 2021,
  "marca": "Renault",
  "tipo": "AUTOMOVIL",
  "fecha_vencimiento": "2027-01-31"
}
```

### Operadores — `/operadores`

CRUD completo (`POST`, `GET` paginado, `GET /{id}`, `PATCH`, `DELETE`). `nombre`
es obligatorio; `telefono` es opcional y, si se envía, no puede estar vacío.
Borrar un operador con estancias asociadas devuelve 409.

### Celdas — `/celdas`

| Método y ruta | Resultado |
| --- | --- |
| `POST /celdas` | 201 con la celda creada |
| `GET /celdas?offset=0&limit=20` | 200 paginado |
| `GET /celdas/{id}` | 200 o 404 |
| `PATCH /celdas/{id}` | 200; solo campos enviados |
| `DELETE /celdas/{id}` | 204, 404 o 409 si tiene estancias |
| `GET /celdas/disponibilidad` | 200 con todas las celdas y su estado |

`codigo` se recorta y se pasa a mayúsculas. `tipo` ya **no es texto libre**: es
obligatorio y solo acepta `AUTO` o `MOTO`; cualquier otro valor devuelve 422.

```json
{ "codigo": "A-01", "tipo": "AUTO" }
```

`GET /celdas/disponibilidad` devuelve cada celda con `estado` (`LIBRE` u
`OCUPADA`, según si tiene una estancia abierta) y el cupo por tipo:

```json
{
  "celdas": [
    { "id": 1, "codigo": "A1", "tipo": "AUTO", "estado": "OCUPADA" },
    { "id": 2, "codigo": "A2", "tipo": "AUTO", "estado": "LIBRE" }
  ],
  "cupo": {
    "AUTO": { "total": 70, "libres": 69 },
    "MOTO": { "total": 10, "libres": 10 }
  }
}
```

### Estancias — `/estancias`

| Método y ruta | Resultado |
| --- | --- |
| `POST /estancias/entrada` | 201 con la estancia abierta y su celda |
| `POST /estancias/salida` | 200 con la estancia cerrada |
| `POST /estancias/cambiar-celda` | 200 con la estancia abierta y la celda nueva |
| `GET /estancias/vehiculo/{placa}` | 200 con el estado del vehículo |

**Entrada.** Solo lleva `placa` y `operador_id`; **no se envía `celda_id`**. El
servidor elige la primera celda libre del tipo que corresponde al vehículo
(`AUTOMOVIL` y `CAMIONETA` usan `AUTO`; `MOTO` usa `MOTO`) y bloquea la fila para
evitar que dos operadores tomen la misma celda. El contrato rechaza campos
desconocidos: mandar `celda_id` devuelve 422.

```json
{ "placa": "ABC123", "operador_id": 1 }
```

Respuesta:

```json
{
  "id": 10,
  "vehiculo_id": 3,
  "celda_id": 7,
  "entrada": "2026-10-23T15:04:05Z",
  "salida": null,
  "operador_entrada_id": 1,
  "operador_salida_id": null,
  "celda": { "id": 7, "codigo": "A7", "tipo": "AUTO" }
}
```

Reglas de la entrada:

- La mensualidad debe estar vigente. `VIGENTE` solo si hoy en America/Bogota es
  anterior a `fecha_vencimiento`; si vence hoy, ya está `VENCIDA`.
- Un vehículo no puede tener dos estancias abiertas.
- Si no hay celdas libres del tipo, devuelve 409.

**Salida.** Lleva `placa` y `operador_id`. Cierra la estancia abierta con la fecha
y hora del servidor. La mensualidad vencida **no** impide registrar la salida.

**Cambio de celda.** Lleva `placa` y `celda_id`; la celda destino debe estar
`LIBRE` y ser del mismo tipo que el vehículo. Se registra sobre la misma estancia
abierta: no se borra ni se edita el historial.

```json
{ "placa": "ABC123", "celda_id": 12 }
```

**Consulta por placa.** Devuelve si el vehículo está dentro, la estancia abierta
con su celda, la mensualidad calculada y la celda que se le asignaría si entrara:

```json
{
  "vehiculo": {
    "id": 3,
    "placa": "ABC123",
    "color": "Blanco",
    "modelo": 2021,
    "marca": "Renault",
    "tipo": "AUTOMOVIL",
    "fecha_vencimiento": "2027-01-31"
  },
  "esta_dentro": false,
  "estancia": null,
  "mensualidad": "VIGENTE",
  "celda_sugerida": { "id": 2, "codigo": "A2", "tipo": "AUTO" }
}
```

`celda_sugerida` es `null` cuando no hay celdas libres del tipo. La consulta no
bloquea la celda; la asignación definitiva ocurre al registrar la entrada.

## Mensajes de error

Los errores de negocio usan `{"detail": "..."}` con un texto ya en español, que
el frontend muestra tal cual.

| Estado | Mensaje |
| --- | --- |
| 404 | `Vehículo no encontrado.` |
| 404 | `Operador no encontrado.` |
| 404 | `Celda no encontrada.` |
| 409 | `Pago pendiente: la mensualidad está vencida.` |
| 409 | `Este vehículo ya figura dentro.` |
| 409 | `No hay celdas libres para este tipo de vehículo.` |
| 409 | `El vehículo no tiene una entrada abierta.` |
| 409 | `La celda no está disponible o es de otro tipo.` |
| 409 | `Ya existe un vehículo con esa placa.` |
| 409 | `Ya existe una celda con ese código.` |
| 409 | `El vehículo tiene registros relacionados y no se puede eliminar.` |
| 422 | Datos inválidos, con el detalle de Pydantic en `detail`. |
| 503 | `No se pudo completar la operación con la base de datos.` |

Los conflictos hacen `rollback` y no dejan escrituras parciales.

## Datos de demostración

`scripts/cargar_datos_demo.py` **no es una migración**: carga datos de ejemplo en
una base que ya tiene las tablas. Es idempotente (usa `codigo` de celdas, `placa`
de vehículos y nombre + teléfono de operadores) y recalcula los vencimientos
respecto a hoy en America/Bogota.

Carga 80 celdas (A1–A70 `AUTO`, M1–M10 `MOTO`), tres operadores y cinco vehículos:
`ABC123` vigente, `DEF456` vencida, `GHI12J` que vence hoy, `DEMO01` que vence
mañana y `DEMO02` vigente con holgura. Se niega a ejecutarse si la base conectada
no se llama como `DB_NAME` en `.env`.

```powershell
Set-Location -LiteralPath 'C:\ruta\a\AutosColombia\backend'
.\.venv\Scripts\python.exe scripts\cargar_datos_demo.py
```

Úsalo solo en una base de demostración.

## Probar desde /docs

Inicia el servidor, abre <http://127.0.0.1:8000/docs> y usa **Try it out** en
cada sección. Un recorrido útil:

1. Crea un operador y un par de celdas (`AUTO` y `MOTO`).
2. Crea un vehículo con `fecha_vencimiento` futura.
3. `GET /estancias/vehiculo/{placa}` para ver la celda sugerida.
4. `POST /estancias/entrada` con placa y operador.
5. `GET /celdas/disponibilidad` para comprobar el estado de las celdas.
6. `POST /estancias/cambiar-celda` a otra celda libre del mismo tipo.
7. `POST /estancias/salida` para cerrar la estancia.

Estas acciones desde `/docs` sí guardan cambios en tu base.
