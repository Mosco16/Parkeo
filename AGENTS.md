# Guía de trabajo de Parkeo

Estas instrucciones se aplican a todo el repositorio. La documentación para
instalar y ejecutar los proyectos en Windows está en `README.md`.

## Estructura

- `backend/app/main.py`: aplicación FastAPI (`Parkeo API`); `GET /health` devuelve
  HTTP 200 y `{"status": "ok"}`.
- `backend/tests/`: pruebas con pytest y `TestClient`.
- `backend/app/config.py`: carga `backend/.env` por ruta absoluta; incluye
  configuración de base de datos (`load_database_settings`) y seguridad JWT
  (`load_security_settings`).
- `backend/app/database.py`: motor SQLAlchemy y sesiones bajo demanda con psycopg.
- `backend/check_db.py`: comprobación explícita mediante `SELECT 1`, sin DDL.
- `backend/app/models.py`: Base, Vehiculo, Celda, Usuario, Estancia y CambioCelda;
  tablas en singular y minúsculas.
- `backend/app/security.py`: hashing de contraseñas con bcrypt (costo 12) y
  generación/verificación de tokens JWT HS256.
- `backend/app/dependencies.py`: dependencias FastAPI para autenticación:
  `usuario_actual` (cualquier usuario activo) y `requiere_administrador`
  (exige rol `ADMINISTRADOR`).
- `backend/app/schemas/`: contratos Pydantic por recurso (`vehiculo.py`,
  `celda.py`, `usuario.py`, `estancia.py`, `auth.py`).
- `backend/app/routers/`: routers FastAPI (`auth.py`, `vehiculos.py`, `celdas.py`,
  `usuarios.py`, `estancias.py`). Todos los endpoints de operación y gestión
  exigen autenticación previa.
- `backend/app/services/`: lógica de negocio, transacciones y errores públicos
  (`auth.py`, `vehiculo.py`, `celda.py`, `usuario.py`, `estancia.py`).
- **Regla de capas:** los routers solo reciben la petición, delegan en un servicio
  de `app/services/` y devuelven la respuesta. Las consultas a la base, los
  `commit`/`rollback` y la traducción de errores no van en los routers.
- `backend/scripts/cargar_datos_demo.py`: datos de demostración idempotentes (80
  celdas, 4 cuentas demo y 5 vehículos); no es una migración y solo debe
  ejecutarse en una base de demostración.
- `backend/migrations/`: revisiones Alembic `0001` a `0007`; `backend/alembic.ini`
  reutiliza la configuración privada.
- `backend/.env.example`: plantilla pública; conservar cualquier `.env` existente y privado.
- `backend/requirements.txt`: dependencias de ejecución y pruebas con versiones
  exactas, incluidas las transitivas.
- `backend/.venv/`: entorno virtual local, excluido de Git.
- `frontend/src/app/`: componentes standalone, configuración y rutas Angular.
- `frontend/src/app/panel/`: panel de resumen del parqueadero (ruta raíz `/`),
  con KPIs, mapa de celdas agrupado por tipo con estados, placa en celdas
  ocupadas, accesos rápidos y estado del servicio.
- `frontend/src/app/login/`: inicio de sesión con usuario y contraseña.
- `frontend/src/app/guards/sesion.guard.ts`: `sesionActiva` protege las rutas
  internas; `soloAdministrador` protege `/gestion/usuarios` y `/gestion/celdas`.
- `frontend/src/app/tablero/`: cuadrícula de celdas con 3 estados (`DISPONIBLE`,
  `OCUPADA`, `MANTENIMIENTO`), cupo por tipo y consulta por placa.
- `frontend/src/app/control-acceso/`: registrar entrada (la celda la asigna el
  servidor) y corregir una entrada duplicada.
- `frontend/src/app/registrar-salida/`: registrar salida y volver a la entrada si
  el vehículo no tiene estancia abierta.
- `frontend/src/app/cambiar-celda/`: mover una estancia abierta a otra celda libre
  del mismo tipo; registra el movimiento en el historial.
- `frontend/src/app/historial/`: consulta paginada de cambios de celda con fecha/hora
  (Bogotá), placa, celda anterior, celda nueva y usuario.
- `frontend/src/app/vehiculos/`: formulario reactivo y listado paginado de vehículos.
- `frontend/src/app/celdas/`: mantenimiento de celdas (habilitar / poner en
  mantenimiento); solo administradores.
- `frontend/src/app/usuarios/`: administración de cuentas de operador (crear,
  editar, activar/desactivar, restablecer contraseña); solo administradores.
- `frontend/src/app/services/`: `ApiService`, `AuthService`, `CeldasService`,
  `EstanciasService`, `SesionUsuario` y `UsuariosService`.
- `frontend/src/app/interceptors/auth.interceptor.ts`: inyecta el token JWT
  `Bearer` en cada petición saliente y limpia la sesión ante HTTP 401.
- `frontend/src/app/utils/`: `fechas.ts` (hora de Bogotá) y `mensajes.ts`
  (mensajes de error compartidos de las pantallas de operación).
- `frontend/src/styles.css`: variables CSS globales `--parkeo-*` y estilos base.
- `frontend/public/`: recursos estáticos (`parkeo-logo.jpeg`).
- `frontend/package.json` y `frontend/package-lock.json`: scripts, dependencias
  y versiones resueltas. Ambos se versionan.

## Herramientas y dependencias

- Entorno verificado: Python 3.13.16, Node.js 24.22.0 y npm 11.7.0.
- Mantener Node.js en la rama 24 con versión mínima 24.15.0 para Angular 22.
- Usar exclusivamente `backend/.venv` para instalar paquetes y ejecutar Python
  del proyecto. No instalar dependencias del backend globalmente.
- Usar Angular CLI 22 y TypeScript como dependencias locales. No actualizar sus
  instalaciones globales.
- Usar `npm.cmd ci` para reproducir la instalación existente.
- No usar librerías de UI externas (sin Angular Material); estilos propios en CSS.
- Al cambiar dependencias Python, actualizar las versiones fijadas en
  `requirements.txt` desde un entorno del proyecto limpio y verificar `pip check`.
- No editar manualmente `.venv`, `node_modules`, `dist` ni otros archivos generados.

## Convenciones

- Mantener cambios limitados al objetivo solicitado y respetar el trabajo existente.
- Documentar en español los comandos y las decisiones que afecten al desarrollo.
- Python: cuatro espacios, nombres `snake_case` para funciones y variables,
  `PascalCase` para clases y anotaciones de tipos en las funciones nuevas.
- Angular/TypeScript: respetar `frontend/.editorconfig` y `.prettierrc`, usar dos
  espacios, componentes standalone, CSS y el enrutamiento existente.
- Mantener `strict` y `strictTemplates` activados; no desactivar comprobaciones
  para ocultar errores de tipos o de plantillas.
- Añadir o ajustar pruebas cuando cambie el comportamiento. Los endpoints nuevos
  deben probar su estado HTTP y su respuesta esperada.
- Conservar el contrato de `/health` (`{"status": "ok"}`).
- Mantener restricciones de integridad en modelos y migraciones. Nunca aplicar
  migraciones a la base del usuario sin autorización; para revisión usar
  `python -m alembic -c alembic.ini upgrade head --sql` con el intérprete de `.venv`.
- Mantener `/health` independiente de PostgreSQL. No conectar ni crear tablas al
  importar módulos. No registrar credenciales, URL de conexión ni errores crudos.
- El proxy de desarrollo en `frontend/proxy.conf.json` dirige `/auth`, `/health`,
  `/vehiculos`, `/celdas`, `/usuarios` y `/estancias` a `127.0.0.1:8000`.
- Las pantallas internas están protegidas por `sesionActiva`; la sesión guarda
  token y usuario en `sessionStorage` (`parkeo.sesion`).
- El presupuesto de estilos por componente (`anyComponentStyle`) en Angular es
  de 4 kB máximo de advertencia.

## Secretos y archivos excluidos

- Nunca incluir credenciales, tokens, contraseñas ni claves privadas en código,
  pruebas, documentación o commits.
- Las contraseñas demo documentadas (`Parkeo2026*`) son exclusivas para entornos
  locales de desarrollo y pruebas.
- Usar variables de entorno para configuración privada (`.env`).
- No colocar secretos en el frontend: su código compilado es público.

## Comandos de verificación (PowerShell)

### Backend

```powershell
Push-Location backend
try {
    .\.venv\Scripts\python.exe -m pip check
    if ($LASTEXITCODE -ne 0) { throw 'Dependencias del backend inconsistentes.' }
    .\.venv\Scripts\python.exe -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw 'Fallaron las pruebas del backend.' }
} finally {
    Pop-Location
}
```

Las pruebas de integración con PostgreSQL se habilitan con `RUN_POSTGRES_TESTS=1`
y requieren la base con migraciones aplicadas hasta la `0007`.

### Frontend

```powershell
Push-Location frontend
try {
    npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'Falló la compilación del frontend.' }
    npm.cmd test -- --watch=false
    if ($LASTEXITCODE -ne 0) { throw 'Fallaron las pruebas del frontend.' }
} finally {
    Pop-Location
}
```
