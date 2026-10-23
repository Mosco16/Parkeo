# Frontend de Autos Colombia

Angular 22 con componentes standalone, TypeScript estricto, formularios reactivos
y CSS propio (sin Angular Material). Las dependencias son locales; conserva
`package-lock.json` y usa `npm.cmd ci` al reinstalar.

## Iniciar en Windows (PowerShell)

Mantén el backend activo en otra terminal, como se explica en el
[README principal](../README.md#ejecución-en-windows).

```powershell
Set-Location -LiteralPath 'C:\ruta\a\AutosColombia\frontend'
npm.cmd ci
npm.cmd start -- --host 127.0.0.1 --port 4200
```

Abre <http://127.0.0.1:4200>.

## Pantallas y rutas

| Ruta | Pantalla | Qué hace |
| --- | --- | --- |
| `/` | Inicio | Bienvenida y estado de `/health`. |
| `/operador` | Iniciar turno | Elige el operador activo y lo guarda en `sessionStorage`. |
| `/tablero` | Tablero | Cuadrícula de celdas `LIBRE`/`OCUPADA`, cupo por tipo y consulta por placa. |
| `/control-acceso` | Registrar entrada | Consulta la placa, muestra la celda sugerida y registra la entrada. |
| `/salida` | Registrar salida | Cierra la estancia abierta; si no hay ninguna, ofrece ir a la entrada. |
| `/cambiar-celda` | Cambiar celda | Mueve una estancia abierta a otra celda libre del mismo tipo. |
| `/gestion/vehiculos` | Vehículos | CRUD con fecha de vencimiento de la mensualidad. |
| `/gestion/celdas` | Celdas | CRUD; el tipo es `AUTO` o `MOTO`. |
| `/gestion/operadores` | Operadores | CRUD con teléfono opcional. |

Las rutas de operación (`/tablero`, `/control-acceso`, `/salida`,
`/cambiar-celda`) están protegidas por el guard `operadorActivo`: si no hay turno
iniciado, redirigen a `/operador`. La navegación superior cambia a **Turno: nombre**
con la opción **Cambiar operador** cuando hay una sesión activa.

## Proxy de desarrollo

`proxy.conf.json` conecta con FastAPI en `127.0.0.1:8000`:

- `/health`
- `/vehiculos` y `/vehiculos/**`
- `/celdas` y `/celdas/**`
- `/operadores` y `/operadores/**`
- `/estancias/**`

Reinicia el servidor de Angular si cambias ese archivo. En producción configura
estas rutas en el servidor web; `ng build` no incluye un proxy.

## Recorrido de demostración

1. Carga los datos de ejemplo con `backend/scripts/cargar_datos_demo.py` (ver el
   [README principal](../README.md#datos-de-demostración)).
2. Abre `/operador`, elige un operador y pulsa **Iniciar turno**. Irás al tablero.
3. En `/tablero` revisa el cupo por tipo y consulta la placa `ABC123`.
4. En `/control-acceso` registra la entrada de `ABC123`: no se elige celda, el
   sistema asigna la primera libre del tipo.
5. Repite con `DEF456` para ver el bloqueo por mensualidad vencida.
6. En `/cambiar-celda` mueve `ABC123` a otra celda libre del mismo tipo.
7. En `/salida` cierra la estancia y comprueba que el vehículo queda `FUERA`.

Las pantallas de operación muestran los textos del backend tal cual. Los fallos
de red y de validación usan los mensajes compartidos de `src/app/utils/mensajes.ts`.

## Compilar y probar

```powershell
Set-Location -LiteralPath 'C:\ruta\a\AutosColombia\frontend'
npm.cmd run build
npm.cmd test -- --watch=false
```

`npm.cmd test` usa Vitest con jsdom y compila todo el programa: un error de
plantilla o de tipos aparece aunque la prueba no toque ese componente.

## Estructura

- `src/app/services/`: `ApiService`, `CeldasService`, `OperadoresService`,
  `EstanciasService` y `SesionOperador`.
- `src/app/models/`: contratos de vehículos, celdas, operadores y estancias.
- `src/app/guards/operador.guard.ts`: exige turno activo.
- `src/app/utils/`: `fechas.ts` (America/Bogota) y `mensajes.ts`.
- `src/app/<pantalla>/`: componente standalone con su plantilla, CSS y spec.
- `src/styles.css`: estilos globales.
