# Iteración 2 — Parkeo (EA2)

**Objetivo:** convertir Autos Colombia en **Parkeo**, agregando autenticación con roles,
gestión de cuentas de operador, mantenimiento de celdas, historial de cambios de celda,
panel de resumen y la identidad visual aprobada, sin romper las funciones de la iteración 1.

**Rama:** `iteracion-2-parkeo` desde `main` (`5b9a16f`).
**Entrega:** domingo 15 de noviembre de 2026.
**Estrategia de entrega:** commits por unidad de trabajo en la rama; push/PR solo con autorización.
**Runners:** backend `backend/.venv/Scripts/python.exe -m pytest`; frontend `npm.cmd run build` y `npm.cmd test -- --watch=false`.

---

## 1. Alcance confirmado (fuente: `Entregable 2/Documentos Guías`)

### 1.1 Cambiar en lo existente

| Área | Cambio |
|---|---|
| Identidad visual | Nombre visible **Parkeo**, logo y paleta azul oscuro, amarillo y blanco. |
| Inicio de sesión | Reemplazar el selector de operador por acceso con usuario y contraseña. El sistema identifica si inicia sesión un administrador o un operador. |
| Permisos | Las acciones disponibles dependen del rol. El administrador también puede operar; el operador no puede gestionar cuentas ni activar o desactivar celdas. |
| Entradas y salidas de EA1 | Conservarlas y relacionarlas con el usuario que inició sesión y con el estado de las celdas. |
| Disponibilidad de celdas | Excluir del conteo de disponibles las celdas ocupadas y las inactivas por mantenimiento. |

### 1.2 Agregar para EA2

| Área | Función nueva |
|---|---|
| Cuentas internas | El administrador crea, consulta, edita, activa e inactiva cuentas de operadores. No puede crear otros administradores. |
| Datos de cuenta | Exigir documento, nombre, teléfono, usuario y contraseña. Correo y dirección son opcionales. Validar que documento y usuario no estén repetidos. |
| Restablecer contraseña | Acción del administrador para restablecer la contraseña de un operador. |
| Gestión de celdas | Consultar las 80 celdas y activar o desactivar una por mantenimiento. No agregar opciones para crear, eliminar ni cambiar el código o tipo de una celda. |
| Validación de mantenimiento | Impedir desactivar por mantenimiento una celda que tenga un vehículo en una estancia activa. |
| Cambio de celda | Permitir que un operador o administrador cambie un vehículo a otra celda activa, disponible y compatible con su tipo. |
| Historial de cambios | Guardar en cada cambio la celda anterior, la nueva celda, la fecha y hora, y el usuario que realizó la operación. |
| Vistas por rol | Mostrar al operador sus opciones de consulta y operación; al administrador, además, cuentas y mantenimiento. |

### 1.3 Diagramas de secuencia incluidos

1. Iniciar sesión y mostrar opciones según el rol.
2. Registrar entrada de vehículo.
3. Registrar salida de vehículo.
4. Consultar disponibilidad de celdas.
5. Cambiar un vehículo de celda y guardar el historial.
6. Gestionar cuentas de operadores.
7. Gestionar el estado de una celda.

**Fuera de alcance:** módulo de **Pagos** (aparece en el mockup, pero no está en las funciones de EA2),
diagramas de componentes y cualquier función de la tercera entrega.

---

## 2. Estado actual medido (5 nov 2026)

- `main` limpio en `5b9a16f`; solo hay `?? .atl/` y `?? .engram/`.
- Backend: **107 pruebas aprobadas, 25 omitidas** (las de PostgreSQL se omiten sin `RUN_POSTGRES_TESTS=1`).
- Frontend: **build OK**, **64 pruebas aprobadas en 12 archivos**.
- Docker Desktop está apagado; PostgreSQL no está disponible en este momento.
- No existe autenticación, rol, contraseña ni sesión: el operador se elige de una lista y se guarda en `sessionStorage`.
- `Celda` no tiene estado persistido: la disponibilidad se calcula como `LIBRE/OCUPADA`.
- `Estancia.celda_id` se sobrescribe al cambiar de celda; no hay historial.
- No hay dependencias de hash de contraseña ni de JWT.

---

## 3. Decisiones de diseño

### D1. Un solo modelo `Usuario` con rol (reemplaza a `Operador`)
La tabla `operador` pasa a `usuario`; las FKs de `estancia` pasan a `usuario_entrada_id` y
`usuario_salida_id`. `rol` es `ADMINISTRADOR` o `OPERADOR`. El administrador también puede
registrar entradas, salidas y cambios de celda. Las cuentas de operador son las únicas que se
crean desde la aplicación; el administrador se siembra con el script de datos de demostración.

**Por qué:** las cuentas internas con roles son el concepto central de EA2; mantener
`Operador` para representar también al administrador deja un modelo confuso y arrastra el
error al diagrama de clases de la siguiente entrega.

### D2. Autenticación con JWT y contraseñas con bcrypt
- `POST /auth/login` recibe `{usuario, password}` y responde `200` con token y datos del usuario.
- Token JWT HS256, expiración de 8 horas, claims `sub`, `rol`, `usuario`, `nombre`.
- Contraseñas con `bcrypt` (costo 12), nunca en texto plano ni en respuestas.
- `JWT_SECRET` se lee del entorno; si no existe, se genera uno efímero con advertencia para
  desarrollo. En `.env` local se define uno estable.
- El frontend guarda `{token, usuario}` en `sessionStorage` (clave `parkeo.sesion`) y envía
  `Authorization: Bearer` mediante un interceptor.
- Toda ruta, salvo `/health` y `/auth/login`, exige token. El backend vuelve a verificar que la
  cuenta siga activa en cada petición.

**Códigos:** `401` credenciales inválidas o token ausente; `403` cuenta inactiva o rol sin permiso;
`409` duplicados y conflictos de mantenimiento.

### D3. Estado de celda persistido
`Celda.activa: bool` (por defecto `true`). La disponibilidad queda en tres estados:
`DISPONIBLE` (activa y sin estancia abierta), `OCUPADA` (con estancia abierta) y
`MANTENIMIENTO` (inactiva). El resumen cuenta las 80 celdas: total, disponibles, ocupadas y
mantenimiento. Desactivar una celda ocupada responde `409`.

### D4. Historial append-only
Nueva tabla `cambio_celda` con `estancia_id`, `celda_anterior_id`, `celda_nueva_id`,
`usuario_id` y `fecha_hora`. Se escribe en la misma transacción que actualiza la estancia; si el
cambio falla, no queda historial. Se consulta con paginación, orden descendente.

### D5. Rebranding y renombre del repositorio
El producto y el repositorio pasan a llamarse **Parkeo**; la carpeta local también. El logo
aprobado (`logo.jpeg` de Documentos Guías) se versiona en `frontend/public/parkeo-logo.jpeg` y
se usa en README y login. "Autos Colombia" permanece solo como organización/sede en el
breadcrumb, igual que en el mockup. Se actualizan títulos, paleta, README y el nombre de la API.

---

## 4. Specs

### S1 — Identidad Parkeo
- Nombre visible "Parkeo" en login, shell, títulos de pestaña, README y API.
- Paleta: azul oscuro (`#0E2A47`), amarillo (`#F5C242`), blanco y gris claro.
- Logo oficial `frontend/public/parkeo-logo.jpeg` visible en el README y en el login; el shell usa la marca "P".
- Breadcrumb "Autos Colombia · Sede principal" en el shell.
- Repositorio, carpeta local y remoto `origin` renombrados a Parkeo.
- **Verificación:** build del frontend, revisión visual y búsqueda de textos "Autos Colombia" en la UI.

### S2 — Inicio de sesión
- `/login` con usuario y contraseña; sin selector de operador.
- `POST /auth/login`: `200` con token y rol; `401` con mensaje genérico; `403` si la cuenta está inactiva.
- Sesión restaurada al recargar; `GET /auth/me` valida el token.
- Cerrar sesión limpia la sesión y vuelve a `/login`.
- **Verificación:** pruebas de auth (éxito, contraseña incorrecta, cuenta inactiva, token inválido)
  y prueba del componente de login.

### S3 — Permisos por rol
- Operador: inicio, operación (entrada, salida, cambio de celda), consulta, historial y vehículos.
- Administrador: todo lo anterior + usuarios + mantenimiento de celdas.
- El backend rechaza con `403` lo que el rol no permite; el frontend oculta las opciones.
- **Verificación:** pruebas de endpoint con token de operador y de administrador.

### S4 — Cuentas de operador
- `GET /usuarios` paginado (solo operadores), `POST /usuarios`, `PATCH /usuarios/{id}`,
  `PATCH /usuarios/{id}/estado`, `POST /usuarios/{id}/restablecer-password`.
- Campos obligatorios: documento, nombre, teléfono, usuario, contraseña.
- Opcionales: correo, dirección.
- Documento y usuario únicos (`409` con mensaje específico); usuario normalizado a minúsculas.
- `rol` siempre `OPERADOR` al crear; no se puede cambiar a administrador.
- Sin borrado físico: se desactiva.
- **Verificación:** pruebas de creación, duplicados, edición, activación/desactivación,
  restablecimiento y login con la nueva contraseña.

### S5 — Mantenimiento de celdas
- `GET /celdas` y `GET /celdas/disponibilidad` con `activa` y los tres estados.
- `PATCH /celdas/{id}/estado` con `{activa: bool}` (solo administrador).
- `409` si se intenta desactivar una celda con estancia abierta.
- La UI de celdas solo lista y cambia estado; no crea, elimina ni edita código/tipo.
- **Verificación:** pruebas de disponibilidad, conteo y conflicto de mantenimiento.

### S6 — Cambio de celda con historial
- `POST /estancias/cambiar-celda` valida que la celda destino esté activa, libre y sea del tipo
  del vehículo; rechaza la misma celda.
- Registra `cambio_celda` con celda anterior, nueva, fecha/hora y usuario autenticado.
- `GET /estancias/historial-cambios` paginado con placa, códigos y nombre del usuario.
- **Verificación:** prueba de cambio exitoso + historial; cambio inválido no escribe historial.

### S7 — Entradas y salidas de EA1
- Se conservan las reglas de mensualidad, tipo de celda, una estancia abierta por vehículo y por celda.
- `operador_id` desaparece de los cuerpos; el usuario sale del token.
- La UI muestra el usuario de la sesión y ya no pide operador.
- **Verificación:** suite de estancias actualizada y verde.

### S8 — Panel de resumen
- KPIs: ocupadas, disponibles, mantenimiento y total.
- Mapa de celdas agrupado por AUTO/MOTO, con colores y detalle de placa en ocupadas.
- Accesos rápidos: registrar ingreso, registrar salida, cambiar celda y crear cuenta (solo admin).
- Tarjetas de perfiles del sistema.
- **Verificación:** pruebas del componente con datos simulados y comparación con la API.

### S9 — Historial visible
- `/historial` con tabla paginada: fecha/hora, placa, celda anterior, celda nueva, usuario.
- **Verificación:** prueba del componente y del servicio.

### S10 — Calidad y documentación
- `pip check`, `pytest`, `npm run build`, `npm test` en verde.
- Migraciones revisadas con `alembic upgrade head --sql` antes de aplicarlas.
- README actualizado con Parkeo, credenciales de demostración, roles y endpoints nuevos.
- `AGENTS.md` actualizado con la nueva estructura.

### S11 — Fuera de alcance
- Pagos, facturación y cualquier módulo de EA3.
- Cambio de código/tipo/creación/eliminación de celdas desde la UI.
- Creación de administradores desde la aplicación.

---

## 5. Plan de datos y migraciones

| Revisión | Contenido |
|---|---|
| `0005_usuarios_y_autenticacion` | Renombra `operador`→`usuario`, FKs de `estancia`, agrega `documento`, `usuario`, `password_hash`, `rol`, `activo`, `correo`, `direccion`, `creado_en`, `actualizado_en`; únicos de documento y usuario; backfill de cuentas existentes con contraseña temporal documentada. |
| `0006_celda_activa` | Agrega `celda.activa` (`NOT NULL DEFAULT true`). |
| `0007_historial_cambios_celda` | Crea `cambio_celda` con FKs, índice por fecha y check de celdas distintas. |

Todas con `downgrade` implementado. **No se aplican a la base local sin autorización expresa.**

Credenciales de demostración (solo desarrollo, documentadas en README):
- Administrador: `admin` / `Parkeo2026*`.
- Operadores sembrados por `scripts/cargar_datos_demo.py` con usuarios conocidos.
- El script siembra 2 celdas en mantenimiento para evidenciar el estado.

---

## 6. Tareas y commits

| # | Tarea | Specs | Commit |
|---|---|---|---|
| T1 | Renombrar carpeta/repositorio a Parkeo, copiar logo, crear rama y este plan | S1 | ✅ `4ab7065` `docs: renombra el proyecto a Parkeo y agrega el logo` |
| T2 | Seguridad: bcrypt, JWT, dependencias, configuración | S2 | ✅ `dc28db4` `feat(backend): agrega utilidades de seguridad y configuracion de sesion` |
| T3 | Migración 0005, modelo `Usuario`, backfill y script de admin | S2, S4 | ✅ `401d1ce` `feat(backend): migra operadores a usuarios con rol y credenciales` |
| T4 | `/auth/login`, `/auth/me`, dependencias de rol, proteger routers | S2, S3 | ✅ `f3a07d3` `feat(backend): implementa inicio de sesion y proteccion por rol` |
| T5 | Entrada/salida con usuario autenticado; pruebas actualizadas | S7 | ✅ `a64933b` `refactor(backend): relaciona entradas y salidas con el usuario de la sesion` |
| T6 | CRUD de cuentas de operador, estado y restablecimiento | S4 | ✅ `4b91d46` `test(backend): cubre la gestion de cuentas de operador` |
| T7 | Migración 0006, `activa`, disponibilidad de 3 estados, toggle | S5 | ✅ `10b589f` `feat(backend): agrega mantenimiento de celdas y disponibilidad por estado` |
| T8 | Migración 0007, historial en cambio de celda, endpoint | S6 | ✅ `124ff7f` `feat(backend): registra el historial de cambios de celda` |
| T9 | Frontend auth: servicio, interceptor, guards, login, quitar selector | S2, S3 | `feat(frontend): agrega inicio de sesion y rutas protegidas` |
| T10 | Shell, sidebar, topbar, tema y rebranding | S1, S3 | `feat(frontend): aplica la identidad visual y el menu por rol` |
| T11 | Dashboard con KPIs, mapa, accesos rápidos y perfiles | S8 | `feat(frontend): agrega el panel de resumen del parqueadero` |
| T12 | Gestión de usuarios (listar, crear, editar, estado, reset) | S4 | `feat(frontend): administra cuentas de operador` |
| T13 | Gestión de celdas (mapa + mantenimiento) | S5 | `feat(frontend): administra el mantenimiento de celdas` |
| T14 | Historial de cambios | S6, S9 | `feat(frontend): consulta el historial de cambios de celda` |
| T15 | Adaptar entrada, salida y cambio de celda a la sesión | S7 | `refactor(frontend): adapta la operacion a la sesion autenticada` |
| T16 | Datos demo, README, AGENTS y verificación final | S10 | `chore: actualiza datos de demostracion y documentacion de Parkeo` |

Cada commit debe dejar build y pruebas en verde. El último incluye la corrida completa con
PostgreSQL habilitado.

---

## 7. Riesgos

1. **Base de datos apagada:** Docker Desktop no está corriendo; las pruebas de integración quedan
   omitidas hasta levantarlo. Requiere autorización para iniciar Docker y aplicar migraciones.
2. **Renombre `operador`→`usuario`:** toca modelos, esquemas, servicios, routers, pruebas y
   frontend. Se mitiga con commits incrementales y la suite completa en cada uno.
3. **Dependencias nuevas (`bcrypt`, `PyJWT`) en Python 3.13:** verificar instalación con el
   `.venv` del proyecto y `pip check`; no instalar globalmente.
4. **Reestructura del frontend (shell + login):** puede romper rutas y pruebas existentes; se
   reemplazan los specs del selector de operador por los de auth.
5. **Alcance:** Pagos no entra en EA2; si se implementa, se desvía la entrega del 15 de noviembre.
6. **Credenciales demo:** son solo para desarrollo y deben quedar marcadas como tales; no se
   reutilizan en producción.

---

## 8. Log

### L1 — Pedido original del usuario (5 nov 2026)
> ahora seguimos con la iteracion 2, tenemos que seguir con el siguiente paso para autoscolombia, que ahora lleva por nombre parkeo, adicionar las funciones nuevas, mirar errores, realizar commits, y que todo quede totalemnte funcional, lo primero que debemos hacer es aramar bien primero el plan, tipo /init, y mirar los caminos. En esta ruta:C:\Users\Control\Desktop\IUD\5° SEMESTRE\Ingeniería de software\Entregable 2\Documentos Guías. enconmtraras las dos imagenes (las de whatssap) que dicen que es lo nuevo, y lo que debe agregarse en esta iteración 2, tambien los diagramas de secuencias, y aca te dejo un muckup de diseño para el frontend, de como debe verse la app al final :https://www.figma.com/make/G88D9wv4nYbqIBGnvSm2FC/Mockups-de-Autos-Colombia?p=f.

### L2 — Evidencia revisada
- 9 imágenes de `Entregable 2/Documentos Guías`: 7 diagramas de secuencia + tabla "Cambiar en lo existente" + tabla "Agregar para EA2".
- Mockup: dashboard Parkeo con sidebar (Inicio, Operación, Usuarios, Celdas, Pagos, Historial), KPIs, mapa de 80 celdas, accesos rápidos y perfiles.
- Transcripción del encuentro sincrónico: login con 200/401, rol en la respuesta, diagramas por caso de uso y plan de pruebas.

### L3 — Baseline
- Backend: 107 passed, 25 skipped (4.02 s).
- Frontend: build OK; 64 tests passed en 12 archivos (8.48 s).

### L4 — Decisiones tomadas
- `Usuario` único con rol; renombre de tabla y FKs.
- JWT + bcrypt; sesión en `sessionStorage`.
- `Celda.activa` persistido; tres estados de disponibilidad.
- Historial `cambio_celda` append-only en la misma transacción.
- Pagos fuera de alcance.
- Repositorio (`Mosco16/Parkeo`), carpeta local y remoto `origin` renombrados; logo oficial versionado.

### L5 — Pendiente de confirmación
- Autorización expresa para aplicar las migraciones `0005`–`0007` a la base local (Docker ya está arriba).
- Decisión de push a `origin` al terminar (los commits se hacen igual en local).

### L6 — Avance backend (5 nov 2026)

**T3 (`401d1ce`, 25 archivos, +1153/−589).**
- Migración `0005_usuarios_y_autenticacion`: renombra `operador`→`usuario` y las FKs de
  `estancia` con `ALTER TABLE ... RENAME` (sin recrear tablas ni perder datos); agrega
  `documento`, `usuario`, `password_hash`, `rol`, `activo`, `correo`, `direccion`,
  `creado_en`, `actualizado_en`; backfill de cuentas existentes con rol `OPERADOR` y hash
  temporal de `Parkeo2026*`; únicos y checks de normalización.
- Modelo `Usuario` (`es_administrador()`), esquemas, servicio y router `/usuarios`, y
  `scripts/cargar_datos_demo.py` siembra la cuenta `admin`.
- `tests/test_migracion_0005.py` valida el SQL offline de upgrade y downgrade sin abrir
  conexión ni tocar datos.
- Evidencia: `pip check` OK; **136 passed / 25 skipped**.

**T4 (`f3a07d3`, 22 archivos, +595/−29).**
- `POST /auth/login` (JWT HS256, 8 h) devuelve `access_token`, `token_type` y el usuario con
  su rol; `GET /auth/me` revalida la cuenta en cada petición.
- Contraseña incorrecta y usuario inexistente comparten `401` genérico y costo bcrypt
  equivalente (`_hash_ficticio`); la verificación de contraseña ocurre antes del estado de
  la cuenta, así una cuenta inactiva con clave errónea no revela que existe.
- `app/dependencies.py`: `usuario_actual`, `requiere_administrador` y los alias
  `UsuarioAutenticado`/`Administrador`; todos los routers quedan protegidos salvo `/health`
  y `/auth/login`. Escrituras de celdas y `/usuarios` exigen administrador.
- `tests/conftest.py` centraliza `usuario_de_prueba`, `token_para` y `encabezado`.
- Evidencia: `pip check` OK; `test_security.py` + `test_auth.py` 41 passed; **173 passed /
  25 skipped**.

**T5 (`a64933b`, 9 archivos, +43/−54).**
- `EntradaCrear` y `SalidaCrear` dejan de aceptar `usuario_id`; `entrada(data, usuario)` y
  `salida(data, usuario)` reciben el `Usuario` de la sesión y lo escriben en
  `usuario_entrada_id` / `usuario_salida_id`. Un cuerpo manipulado ya no puede atribuir un
  movimiento a otra cuenta.
- Pruebas de API, escenarios, disponibilidad, concurrencia y PostgreSQL actualizadas. Se
  retiraron 4 casos parametrizados que ya no aplican (`usuario_id` inválido en el cuerpo) y
  el caso de salida con usuario inexistente; el resto de rechazos se conserva.
- Evidencia: `pip check` OK; **169 passed / 25 skipped**.

**Notas de proceso.**
- Los mensajes de commit se escriben con `UTF8Encoding($false)`: `Out-File -Encoding utf8` de
  PowerShell 5.1 agrega BOM al asunto (se corrigió con `--amend` una vez).
- `.atl/` y `.engram/` siguen sin versionar a propósito.

### L7 — Backend de la iteración 2 cerrado (5 nov 2026)

**T6 (`4b91d46`, 2 archivos, +102/−4).**
- Pruebas de restablecimiento de contraseña (hash bcrypt, clave inválida `422`), cambio de
  estado, `404` de cuentas inexistentes, ausencia de borrado físico y filtro del listado por
  rol `OPERADOR`.
- En la integración, la clave restablecida inicia sesión, la anterior deja de servir y una
  cuenta desactivada responde `403`. El teléfono sigue opcional por la decisión 9 de EA1
  (migración `0004`).
- Evidencia: **182 passed / 25 skipped**.

**T7 (`10b589f`, 11 archivos, +318/−16).**
- Migración `0006` agrega `celda.activa` (`NOT NULL DEFAULT true`) sin recrear la tabla.
- `PATCH /celdas/{id}/estado` (solo administrador) enciende o apaga una celda; apagar una
  celda con estancia abierta responde `409`.
- La disponibilidad calcula `DISPONIBLE` / `OCUPADA` / `MANTENIMIENTO` e incluye `activa`.
  Solo las celdas activas cuentan como libres, se ofrecen en la entrada y se aceptan como
  destino de un cambio de celda.
- Evidencia: SQL offline de `0005:0006` y su downgrade revisado; **192 passed / 26 skipped**.

**T8 (`124ff7f`, 9 archivos, +465/−10).**
- Migración `0007` crea `cambio_celda` append-only con FKs `RESTRICT`, check de celdas
  distintas e índice por `fecha_hora`; el downgrade elimina índice y tabla.
- `POST /estancias/cambiar-celda` recibe el usuario autenticado, rechaza la misma celda y
  escribe el historial en la misma transacción. Un cambio inválido no deja registro.
- `GET /estancias/historial-cambios` pagina con `offset`/`limit` y devuelve placa, códigos
  anterior/nuevo y nombre del usuario, ordenado por `fecha_hora DESC, id DESC`.
- Evidencia: SQL offline de `0007` y su downgrade revisado; **204 passed / 26 skipped**.

**Siguiente.** T9–T15 (frontend: autenticación, shell por rol, panel, usuarios, celdas,
historial y adaptación de las pantallas de operación) y T16 (datos demo y documentación).
Sigue pendiente la autorización expresa para aplicar `0005`–`0007` a la base local y correr
las pruebas de PostgreSQL con `RUN_POSTGRES_TESTS=1`.
