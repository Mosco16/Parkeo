# Evidencias de pruebas manuales — Parkeo (Iteración 2)

Carpeta de evidencias del plan de pruebas manuales de la entrega EA2.

El requisito del curso es que las evidencias estén **hospedadas en un repositorio o carpeta accesible para la revisión**, y que la plantilla de pruebas lleve el **enlace** a cada una. Por eso la evidencia vive acá y el Excel solo la referencia.

- Plan de pruebas: `Entregable 2/Plan_Pruebas_Usuarios_Celdas_Autos_Colombia.xlsx`
- Documentación del sistema: `Entregable 2/Parkeo - Documentación del sistema - Iteración 2.docx`
- Casos: 33 (13 US, 5 PE, 15 CE)
- Enlace público de esta carpeta:
  `https://github.com/Mosco16/Parkeo/tree/iteracion-2-parkeo/evidencias`

## Convención de nombres

Un archivo por caso, con esta forma:

```
<ID>_<slug>.png
```

- `<ID>` es el identificador del caso en el Excel: `US-01`, `PE-01`, `CE-01`.
- `<slug>` es un resumen corto en minúsculas con guiones, sin acentos ni espacios.
- Si un caso necesita más de una captura, se numera al final: `CE-07_entrada-celda-asignada-1.png`, `-2.png`.
- Formato **PNG**. No usar JPEG: el texto de los mensajes de error se degrada y deja de ser legible.

El prefijo `ID_` no es decorativo: permite ordenar la carpeta alfabéticamente y que cada archivo quede alineado con su fila del Excel sin abrir ninguno.

## Archivos por caso

| ID | Nombre del archivo | Qué debe mostrar |
|---|---|---|
| US-01 | `US-01_login-administrador.png` | Panel de resumen con el menú de administración visible. |
| US-02 | `US-02_login-operador.png` | Panel de resumen sin el grupo Administración. |
| US-03 | `US-03_credenciales-incorrectas.png` | Mensaje «Usuario o contraseña incorrectos.» sobre el formulario. |
| US-04 | `US-04_login-campos-obligatorios.png` | Validación de campos vacíos en `/login`. |
| US-05 | `US-05_cuenta-inactiva.png` | Mensaje «La cuenta está inactiva. Contacta al administrador.» |
| US-06 | `US-06_token-invalido-expirado.png` | Redirección a `/login` tras el 401. |
| US-07 | `US-07_crear-operador.png` | Cuenta nueva en el listado de usuarios. |
| US-08 | `US-08_no-crear-administrador.png` | Formulario sin selector de rol y cuenta creada como OPERADOR. |
| US-09 | `US-09_documento-usuario-duplicado.png` | Mensaje de duplicado del backend. |
| US-10 | `US-10_validaciones-cuenta-nueva.png` | Errores de validación del formulario. |
| US-11 | `US-11_editar-operador.png` | Datos editados guardados en el listado. |
| US-12 | `US-12_activar-desactivar-operador.png` | Cambio de estado reflejado y bloqueo sobre la cuenta administradora. |
| US-13 | `US-13_restablecer-password.png` | Confirmación del restablecimiento. |
| PE-01 | `PE-01_sin-token-401.png` | Salida de terminal con `401` y «Falta el token de sesión.» |
| PE-02 | `PE-02_operador-no-gestiona-cuentas-403.png` | Salida de terminal con `403` al llamar `/usuarios` con token de operador. |
| PE-03 | `PE-03_operador-no-cambia-estado-403.png` | Salida de terminal con `403` al cambiar estado de celda como operador. |
| PE-04 | `PE-04_admin-tambien-opera.png` | Entrada registrada por la cuenta administradora. |
| PE-05 | `PE-05_rutas-por-rol.png` | Navegación a `/gestion/usuarios` como operador devolviendo a `/tablero`. |
| CE-01 | `CE-01_listar-80-celdas.png` | Listado con las 80 celdas y su tipo. |
| CE-02 | `CE-02_disponibilidad-cupo.png` | Cupo por tipo («Autos: N libres de 70»). |
| CE-03 | `CE-03_disponibilidad-excluye-no-disponibles.png` | Celda ocupada o en mantenimiento ausente del cupo libre. |
| CE-04 | `CE-04_celda-mantenimiento.png` | Celda en MANTENIMIENTO en la cuadrícula. |
| CE-05 | `CE-05_habilitar-celda.png` | Celda de vuelta en DISPONIBLE. |
| CE-06 | `CE-06_no-desactivar-celda-ocupada-409.png` | Mensaje «La celda tiene una estancia abierta y no se puede desactivar.» |
| CE-07 | `CE-07_entrada-celda-asignada.png` | Entrada registrada con la celda asignada por el servidor. |
| CE-08 | `CE-08_entrada-ya-dentro-409.png` | Mensaje «Este vehículo ya figura dentro.» |
| CE-09 | `CE-09_entrada-mensualidad-vencida-409.png` | Mensaje «Pago pendiente: la mensualidad está vencida.» |
| CE-10 | `CE-10_entrada-sin-cupo-409.png` | Mensaje «No hay celdas libres para este tipo de vehículo.» |
| CE-11 | `CE-11_salida-libera-celda.png` | Estancia cerrada y celda liberada en el tablero. |
| CE-12 | `CE-12_salida-sin-estancia-409.png` | Mensaje «El vehículo no tiene una entrada abierta.» |
| CE-13 | `CE-13_cambiar-celda.png` | Celda anterior, celda nueva y registro en el historial. |
| CE-14 | `CE-14_cambio-celda-invalido-409.png` | Mensaje «La celda no está disponible o es de otro tipo.» |
| CE-15 | `CE-15_historial-cambios.png` | Tabla paginada con placa, celdas y usuario. |

## Cómo capturar

Windows: `Win + Shift + S` recorta la región y copia al portapapeles; se pega en Paint y se guarda como PNG. Alternativa: `Win + PrtScn` guarda el escritorio completo, pero después hay que recortarlo.

Reglas de la captura:

1. **Dos capturas como máximo por caso**: una del punto de acción (formulario lleno o comando ejecutado) y una del resultado. Más de dos no agregan información y hacen la revisión más lenta.
2. **Dejar visible la barra de direcciones** con la ruta (`http://127.0.0.1:4200/...`). Sin eso, la captura no prueba en qué pantalla se hizo la prueba.
3. **Dejar visible la barra superior** con el usuario y el rol. En un solo plano queda registrado con qué cuenta se probó, que es justo lo que distingue un caso de permisos de otro.
4. Recortar al área relevante; no capturar el escritorio entero con otras ventanas.

## Qué no debe aparecer en una captura

- Contraseñas en texto claro, tokens JWT completos ni hashes.
- Datos personales reales de terceros.
- Archivos `.env` ni cadenas de conexión.

Los campos de contraseña ya vienen enmascarados por el propio formulario. Si un caso necesita mostrar el token —por ejemplo `US-06`—, se muestra solo el resultado (`401` y mensaje), no el valor del token.

## Casos de API y permisos

Los casos `PE-01` a `PE-03` no se documentan con captura del navegador: una pantalla en blanco no prueba nada. Se documentan con la salida de la terminal, que muestra código y mensaje exactos.

PowerShell:

```powershell
curl.exe -i http://127.0.0.1:8000/usuarios
```

Sin token la respuesta esperada es:

```
HTTP/1.1 401 Unauthorized
{"detail":"Falta el token de sesión."}
```

Para los casos con sesión de operador, primero se obtiene el token y se usa en el encabezado:

```powershell
$cuerpo = '{"usuario":"ana.gomez","password":"<contraseña-de-demostración>"}'
$token = (curl.exe -s -X POST http://127.0.0.1:8000/auth/login `
  -H 'Content-Type: application/json' -d $cuerpo | ConvertFrom-Json).access_token
curl.exe -i http://127.0.0.1:8000/usuarios -H "Authorization: Bearer $token"
```

En la captura, tapar el valor de `$token`. La contraseña de demostración no se escribe en el README ni en las evidencias.

## Cómo enlazar desde el Excel

En la hoja `Casos`, columna **J — Evidencia: enlace o archivo**, cada fila lleva la ruta relativa dentro del repositorio:

```
evidencias/CE-07_entrada-celda-asignada.png
```

Para los casos con dos capturas, se enlaza la carpeta del caso por prefijo o se listan las dos rutas separadas por coma. Y en la columna **K — Incidencia / bloqueo** se describe qué pasó cuando el resultado no coincide con el esperado; si no hubo incidencia, se deja vacía.

Las columnas **H a M** se llenan en el momento de la ejecución, no después: estado, resultado real, evidencia, incidencia, fecha y responsable.

## Antes de cerrar la entrega

- Los 33 casos tienen archivo de evidencia existente en esta carpeta.
- Cada fila de la hoja `Casos` tiene las columnas H a M completas.
- Los casos de error muestran el mensaje exacto que aparece en el documento del sistema, §7.4 Mensajes de error.
- La hoja `Plan` refleja el avance real (aprobados, fallidos, pendientes y porcentaje).
- No hay contraseñas, tokens ni hashes visibles en ninguna captura.
