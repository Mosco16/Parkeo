import { HttpErrorResponse } from '@angular/common/http';

/** Mensajes compartidos por las pantallas de operación (D10). */
export const SERVICIO_NO_DISPONIBLE = 'El servicio no está disponible. Intente de nuevo.';
export const DATOS_INVALIDOS = 'Datos inválidos. Revisa los campos e intenta de nuevo.';
export const VEHICULO_NO_ENCONTRADO = 'Vehículo no encontrado.';

/**
 * Traduce una respuesta HTTP a un mensaje para el operador.
 * - 404 y 409 con `detail` de texto: se muestra tal cual (viene en español del backend).
 * - 422: mensaje de validación genérico.
 * - 404 sin detalle al consultar una placa: vehículo no encontrado.
 * - Cualquier otro fallo (red, 500): servicio no disponible.
 */
export function mensajeApi(error: HttpErrorResponse): string {
  const detail = error.error?.detail;
  if (
    (error.status === 404 || error.status === 409) &&
    typeof detail === 'string' &&
    detail.trim()
  )
    return detail;
  if (error.status === 422) return DATOS_INVALIDOS;
  if (error.status === 404) return VEHICULO_NO_ENCONTRADO;
  return SERVICIO_NO_DISPONIBLE;
}
