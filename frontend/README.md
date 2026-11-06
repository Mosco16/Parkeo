# Frontend de Parkeo

Aplicación cliente de **Parkeo** desarrollada en Angular 22 con componentes standalone,
TypeScript estricto, gestión de estado reactivo mediante Signals, formularios reactivos
y estilos propios en CSS sin librerías de UI externas.

## Requisitos y ejecución

Requiere Node.js 24 (mínimo 24.15.0) y npm 11. Mantén la API corriendo en el puerto 8000.

```powershell
Set-Location -LiteralPath 'frontend'
npm.cmd ci
npm.cmd start -- --host 127.0.0.1 --port 4200
```

Acceso: <http://127.0.0.1:4200>.

## Pantallas y rutas

| Ruta | Pantalla | Acceso | Propósito |
|---|---|---|---|
| `/login` | Iniciar sesión | Público | Autenticación mediante usuario y contraseña con JWT |
| `/` | Panel de resumen | Autenticado | KPIs de ocupación, mapa de celdas por tipo con placa, accesos directos y salud de la API |
| `/tablero` | Tablero | Autenticado | Visualización del estado de celdas (`DISPONIBLE`, `OCUPADA`, `MANTENIMIENTO`) y consulta por placa |
| `/control-acceso` | Entrada | Autenticado | Consulta de vehículos y confirmación de ingreso con asignación automática de celda |
| `/salida` | Salida | Autenticado | Cierre de estancias abiertas en hora del servidor |
| `/cambiar-celda` | Cambiar celda | Autenticado | Reubicación de estancias activas a celdas disponibles del mismo tipo |
| `/historial` | Historial | Autenticado | Consulta paginada y auditable de los movimientos de cambio de celda |
| `/gestion/vehiculos` | Vehículos | Autenticado | CRUD de vehículos con control de mensualidad |
| `/gestion/celdas` | Celdas | Solo Administrador | Mantenimiento de celdas (activación y puesta en mantenimiento) |
| `/gestion/usuarios` | Usuarios | Solo Administrador | Administración de cuentas de operador, estados y reseteo de contraseñas |

## Seguridad y Guards

- `sesionActiva`: Bloquea el acceso a todas las rutas internas si no existe un token JWT válido en `sessionStorage` (`parkeo.sesion`).
- `soloAdministrador`: Restringe `/gestion/usuarios` y `/gestion/celdas` exclusivamente a usuarios con rol `ADMINISTRADOR`.
- `authInterceptor`: Adjunta la cabecera `Authorization: Bearer <token>` a cada petición HTTP y redirige a `/login` ante respuestas HTTP 401.

## Proxy de desarrollo

El archivo `proxy.conf.json` redirige las peticiones locales a la API de FastAPI en `http://127.0.0.1:8000`:
- `/auth/**`
- `/estancias/**`
- `/usuarios/**`
- `/celdas/**`
- `/vehiculos/**`
- `/health`

## Compilación y pruebas

```powershell
npm.cmd run build
npm.cmd test -- --watch=false
```
