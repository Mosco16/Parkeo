# Backend de Parkeo

API REST de **Parkeo** desarrollada con FastAPI, SQLAlchemy 2, Pydantic v2, bcrypt y PyJWT,
con persistencia en PostgreSQL y gestión de migraciones mediante Alembic.

## Estructura y regla de capas

```
backend/
  app/
    main.py            FastAPI app y endpoint /health
    config.py          Carga de backend/.env (DB, JWT y SMTP)
    database.py        Motor SQLAlchemy y sesiones bajo demanda
    security.py        Bcrypt y codificación/decodificación de tokens JWT HS256
    dependencies.py    Guards FastAPI: usuario_actual y requiere_administrador
    models.py          Modelos: Vehiculo, Celda, Usuario, Estancia, CambioCelda, Pago, Aviso
    schemas/           Validación y contratos Pydantic por recurso
    routers/           Rutas: auth, vehiculos, celdas, usuarios, estancias, pagos
    services/          Lógica de negocio, validaciones y transacciones
  migrations/versions/ Revisiones Alembic 0001 a 0009
  scripts/             Carga de datos demo y job de avisos por correo
  tests/               Suites unitarias y de integración
```

**Regla de capas:** Los routers reciben la petición, aplican dependencias de autenticación/rol, delegan en `app/services/` y retornan la respuesta. Los routers nunca ejecutan consultas directas a la base ni gestionan transacciones.

## Configuración y ejecución

```powershell
Set-Location -LiteralPath 'backend'
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe check_db.py
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- Swagger UI: <http://127.0.0.1:8000/docs>
- Health check: <http://127.0.0.1:8000/health>

## Migraciones de base de datos (Alembic)

| Revisión | Contenido |
| --- | --- |
| `0001_modelos_iniciales` | Tablas iniciales `vehiculo`, `celda`, `operador` |
| `0002_estancia` | Tabla `estancia` con índices parciales de exclusión |
| `0003_mensualidad_y_tipo_celda` | Restricción NOT NULL en vencimiento y tipos `AUTO`/`MOTO` |
| `0004_telefono_operador_opcional` | Teléfono de operador opcional |
| `0005_usuarios_y_autenticacion` | Renombra operador a usuario, añade rol, usuario, contraseña bcrypt |
| `0006_celda_activa` | Campo booleano `activa` en celda para mantenimiento |
| `0007_historial_cambios_celda` | Tabla append-only `cambio_celda` para auditoría |
| `0008_pago` | Tabla `pago`, índice único parcial de referencia activa y relación con `vehiculo` |
| `0009_aviso_correo` | Tabla `aviso`, correo y autorización en `vehiculo`, índice parcial de aviso enviado; elimina `vehiculo.fecha_vencimiento` |

El vencimiento ya no se almacena en `vehiculo`: se deriva de
`max(pago.vencimiento_ciclo)` entre los pagos activos. `vehiculo.dia_corte` también
se deriva del último pago activo, porque el anclaje del día 31 no se reconstruye
desde la fecha.

Para aplicar:

```powershell
.\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
```

## Recursos y endpoints

### Autenticación (`/auth`)
- `POST /auth/login`: Autentica credenciales y genera token JWT Bearer.
- `GET /auth/me`: Retorna los datos del usuario autenticado.

### Usuarios (`/usuarios`) — Exclusivo Administrador
- `POST /usuarios`: Crea una cuenta interna con contraseña inicial.
- `GET /usuarios`: Lista paginada de usuarios con estado.
- `GET /usuarios/{id}`: Detalle de usuario.
- `PATCH /usuarios/{id}`: Actualización de datos (documento, nombre, teléfono, correo, dirección).
- `PATCH /usuarios/{id}/estado`: Activa o desactiva la cuenta.
- `POST /usuarios/{id}/restablecer-password`: Establece una nueva contraseña.

### Celdas (`/celdas`)
- `GET /celdas/disponibilidad`: Retorna el estado en tiempo real de todas las celdas (`DISPONIBLE`, `OCUPADA`, `MANTENIMIENTO`), la placa en celdas ocupadas y el cupo por tipo.
- `PATCH /celdas/{id}/estado`: Habilita o pone en mantenimiento una celda (Solo Administrador; rechaza celdas con estancias abiertas).

### Estancias (`/estancias`)
- `POST /estancias/entrada`: Registra ingreso vehicular. Asigna celda automáticamente y valida mensualidad.
- `POST /estancias/salida`: Registra salida y cierra estancia activa en hora del servidor.
- `POST /estancias/cambiar-celda`: Reubica un vehículo a otra celda libre y registra en `cambio_celda`.
- `GET /estancias/historial-cambios`: Listado paginado del historial de cambios de celda ordenado cronológicamente descendente.
- `GET /estancias/vehiculo/{placa}`: Consulta estado de ingreso, estancia activa y mensualidad.

### Vehículos (`/vehiculos`)
- CRUD completo de vehículos con validación de tipo y correo opcional. La respuesta
  expone `fecha_vencimiento`, `mensualidad` y `avisos_autorizados` como datos
  derivados de solo lectura; el cliente ya no digita el vencimiento.

### Pagos (`/pagos`)
- `POST /pagos`: registra la mensualidad con placa y referencia. El servidor calcula
  valor, día de corte, inicio y vencimiento del ciclo (RN-PAG-05). Opcionalmente
  actualiza correo y autorización de avisos. Conflicto `409` si la referencia ya
  está activa o si el vencimiento supera el tope de un ciclo por adelantado.
- `POST /pagos/{id}/anular`: anula solo el último pago activo con un motivo del
  catálogo fijo; el vencimiento se recalcula con los pagos activos restantes.
- `GET /pagos?placa=...&pagina=1&tamano=20`: historial paginado con estado
  (`ACTIVO`/`ANULADO`), motivo y usuario responsable.

### Avisos por correo
- `scripts/enviar_avisos.py`: job idempotente que envía el aviso dos días antes del
  vencimiento y registra `ENVIADO` o `FALLIDO` en `aviso`. Soporta `--dry-run` y
  `--fecha AAAA-MM-DD`. Requiere las variables `SMTP_*` en `backend/.env`.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```
