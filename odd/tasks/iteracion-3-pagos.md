# Iteración 3 — Pagos y avisos (Parkeo)

**Objetivo:** registrar la mensualidad de un vehículo, derivar su fecha de vencimiento
desde los pagos, anular pagos con motivo, consultar el historial y avisar por correo
dos días antes del vencimiento, sin romper las iteraciones 1 y 2.

**Rama:** `iteracion-3-pagos` desde `iteracion-2-parkeo` (`6974b55`).
**Fuente de reglas:** `Entregable 3/Reglas de negocio - ultima versión.docx`.
**Estrategia:** commits por unidad de trabajo; push y PR solo con autorización.
**Runners:** `backend/.venv/Scripts/python.exe -m pytest`; `npm.cmd run build` y
`npm.cmd test -- --watch=false`.

---

## Specs

**S1 · Esquema.** Migración `0008_pago` crea `pago`; migración `0009_aviso_correo`
agrega `vehiculo.correo`, `vehiculo.avisos_autorizados`,
`vehiculo.autorizacion_usuario_id`, `vehiculo.autorizacion_fecha_hora`, crea `aviso`
y elimina `vehiculo.fecha_vencimiento`. No se editan las migraciones `0001` a `0007`.
`pago` guarda `vehiculo_id`, `valor`, `referencia`, `fecha_hora`, `usuario_id`,
`dia_corte`, `inicio_ciclo`, `vencimiento_ciclo` y los campos de anulación
(`anulacion_fecha_hora`, `anulacion_usuario_id`, `anulacion_motivo`).
`dia_corte` se guarda porque el anclaje no se puede reconstruir desde la fecha:
primer pago el 31 de enero vence el 28 de febrero, y el ciclo siguiente vence el
31 de marzo (RN-VIG-02).

**S2 · Cálculo del ciclo (RN-VIG-02).** Función pura, sin base de datos.
- Primer pago: `dia_corte = día de hoy (Bogotá)`, `inicio_ciclo = hoy`,
  `vencimiento_ciclo = hoy + 1 mes anclado a dia_corte`.
- Pago a tiempo (hoy <= vencimiento vigente, incluido el mismo día):
  `inicio_ciclo = vencimiento vigente`, `dia_corte` no cambia,
  `vencimiento_ciclo = inicio_ciclo + 1 mes anclado a dia_corte`.
- Pago vencido (hoy > vencimiento vigente): `dia_corte = día de hoy`,
  `inicio_ciclo = hoy`, `vencimiento_ciclo = hoy + 1 mes anclado a dia_corte`.
- Anclaje: si el día de corte no existe en el mes destino, vence el último día del
  mes, pero el día de corte se conserva para el ciclo siguiente.
Casos: E-16, E-17, E-19, E-20, E-27.

**S3 · Vigencia (RN-VIG-03, RN-VIG-05).** `VIGENTE` si `hoy_bogota() < vencimiento`;
si el vencimiento es hoy, ya es `VENCIDA`. La comparación usa `America/Bogota`,
nunca UTC. Un vehículo sin pagos activos no tiene vencimiento y figura `VENCIDA`.
El vencimiento vigente es `max(vencimiento_ciclo)` de los pagos activos.

**S4 · Tarifas (RN-VIG-04).** `$250.000` para `AUTOMOVIL` y `CAMIONETA`;
`$100.000` para `MOTO`. El operador no digita el valor (RN-PAG-04).

**S5 · Registro de pago (RN-PAG-01…12).** `POST /pagos` recibe placa, referencia,
correo opcional y autorización opcional. Valida, en este orden:
placa existente (si no: `404 "Vehículo no encontrado"`), referencia no vacía y sin
espacios en los extremos (`422`), referencia no repetida entre pagos activos
(`409 "La referencia del recibo ya está registrada en un pago activo."`),
tope de un ciclo por adelantado (`409 "Solo se puede pagar un ciclo por adelantado."`).
Valor, día de corte, fechas y usuario salen del servidor (RN-PAG-05).
Registran pagos `OPERADOR` y `ADMINISTRADOR` (RN-PAG-07); se puede pagar con el
vehículo dentro o fuera y con la mensualidad vigente o vencida (RN-PAG-08).

**S6 · Referencia única entre pagos activos (RN-PAG-06).** Se garantiza con un
índice único parcial `uq_pago_referencia_activa` sobre `referencia`
`WHERE anulacion_fecha_hora IS NULL`. La base es la autoridad; el servicio traduce
la violación a `409`. No hay verificación previa como única defensa.

**S7 · Tope por adelantado (RN-PAG-09).** Se rechaza si el vencimiento vigente es
posterior a `hoy + 1 mes` (anclado al día de hoy). El ciclo pagado por adelantado
cuenta desde el día de corte, no desde el día del pago.

**S8 · Anulación (RN-ANU-01…04).** `POST /pagos/{id}/anular` con `motivo` del
catálogo fijo: `Error de digitación`, `Valor incorrecto`, `Pago duplicado`,
`Recibo no válido`, `Otro`. Solo se anula el último pago no anulado del vehículo
(si no: `409 "Solo se puede anular el último pago activo del vehículo."`).
El pago no se borra ni se edita: se marcan fecha, hora, usuario y motivo. El
vencimiento se recalcula con los pagos activos restantes. Las estancias no cambian.

**S9 · Historial (RN-HIS-01).** `GET /pagos?placa=...&pagina=1&tamano=20` devuelve
los pagos activos y anulados del más reciente al más antiguo, con fecha, valor,
referencia, usuario, estado (`ACTIVO`/`ANULADO`) y motivo cuando aplica.

**S10 · Aviso de vencimiento (RN-AVI-01…06).** Un correo real, HTML con el logo
`parkeo-logo.jpeg` incrustado por CID a 200 px y versión en texto plano, enviado
dos días antes del vencimiento vigente, una vez al día en horario de Bogotá.
Se envía un solo aviso por ciclo: único `(vehiculo_id, fecha_vencimiento)` en
`aviso`. Cada envío se registra con vehículo, correo, fecha, hora y resultado
(`ENVIADO`/`FALLIDO`). Si el vehículo no tiene correo o no autorizó los avisos no
se envía nada y nada más se afecta. El servicio de correo queda detrás de una
interfaz, con implementación SMTP, doble para pruebas y `--dry-run`.

**S11 · Entrada (RN-ENT-03).** La entrada se bloquea con
`409 "Pago pendiente: la mensualidad está vencida."` cuando la mensualidad
derivada es `VENCIDA`. El mensaje y el código actuales se conservan.

**S12 · Contrato de vehículos.** `POST` y `PATCH /vehiculos` dejan de aceptar
`fecha_vencimiento`; la respuesta la expone como derivada y de solo lectura, junto
con `correo`, `avisos_autorizados` y `mensualidad`. El frontend quita el campo
manual del formulario y muestra el vencimiento calculado.

**S13 · Pruebas.** Unitarias del cálculo del ciclo (31 de enero, bisiesto, mismo
día del vencimiento, pago vencido, tope por adelantado), del servicio de pagos con
base simulada, de la API con `TestClient` (códigos y mensajes), e integración con
PostgreSQL para el índice parcial y la anulación (`RUN_POSTGRES_TESTS=1`).
Frontend: specs de las pantallas nuevas y de las modificadas.

**S14 · Datos y documentación.** `scripts/cargar_datos_demo.py` sigue siendo
idempotente y suma pagos de ejemplo: ABC123 vigente y DEF456 por vencer a dos días.
`README.md` y `AGENTS.md` describen las tablas, reglas y variables SMTP nuevas.

---

## Tasks

| ID | Tarea | Specs | Ruta | Estado |
|---|---|---|---|---|
| T1 | Migraciones `0008` y `0009` + modelos + `Configuración SMTP` | S1 | inline | hecho `a47afaf` |
| T2 | Módulo de ciclo y vigencia + pruebas unitarias | S2, S3, S4 | inline | hecho `855fc8b` |
| T3 | Servicio de pagos (registro, anulación, historial) + pruebas | S5, S6, S7, S8, S9 | inline | hecho `6c017a4` |
| T4 | Schemas y router `/pagos` + pruebas de API | S5, S9 | inline | hecho |
| T5 | Ajuste de entrada y contrato de vehículos | S11, S12 | inline | hecho |
| T6 | Correo con logo, job de avisos y registro | S10 | inline | pendiente |
| T7 | Frontend: registrar pago, anular, historial | S12 | delegated | pendiente |
| T8 | Frontend: integración en entrada y vehículos | S12 | delegated | pendiente |
| T9 | Datos demo, documentación y evidencias | S14 | inline | pendiente |

---

## Log

**L1 (18/11/2026).** «vale, hazlo con el de 200 px, y arranca, la idea es poder
hacer cada paso sin tener que repetir varias etapas por errores, y quemar asi muchos
tokens, asi que hazlo con cuidado, y siguiendo el plan, y los commits.»

**L2 (18/11/2026).** «eliminalo» — se elimina `vehiculo.fecha_vencimiento` manual;
el vencimiento se deriva siempre de `pago`.

**L3 (18/11/2026).** Cuenta emisora `parkeo.alertas@gmail.com` con contraseña de
aplicación, cargada solo en `backend/.env` (ignorado por git). Logo del correo:
`frontend/public/parkeo-logo.jpeg`, 200 px, incrustado por CID.

**L4 (18/11/2026).** Baseline verde antes de empezar: backend `205 passed,
26 skipped`; frontend `79 passed` y build correcto. Rama `iteracion-3-pagos`
creada desde `6974b55`.

**L5 (18/11/2026).** T1–T4 completas: `a47afaf` (modelos y migraciones),
`855fc8b` (ciclo y vigencia), `6c017a4` (servicio de pagos) y T4 (router y
pruebas de API). Backend en `258 passed, 26 skipped`.

**L6 (18/11/2026).** PostgreSQL no está instalado en esta máquina: no hay
servicio, binarios ni puerto 5432 escuchando. `alembic upgrade head` y
`check_db.py` fallan por conexión, así que `0008`/`0009` quedan sin aplicar y las
26 pruebas de integración siguen saltadas. Las migraciones se validaron en modo
SQL offline (`0007:0008` y `0008:0009`). Para validar en PostgreSQL real se
necesita la base en otra máquina o instalar PostgreSQL localmente.

**L7 (18/11/2026).** T5 completa: `VehiculoRespuesta` expone `mensualidad`
derivada, la entrada se bloquea con la mensualidad vencida (pruebas nuevas sin
base) y el formulario de vehículos pierde el campo manual de vencimiento y gana
`correo`. Backend `266 passed, 26 skipped`; frontend `79 passed` y build
correcto.
