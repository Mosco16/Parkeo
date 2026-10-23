import { HttpErrorResponse } from '@angular/common/http';
import {
  DATOS_INVALIDOS,
  SERVICIO_NO_DISPONIBLE,
  VEHICULO_NO_ENCONTRADO,
  mensajeApi,
} from './mensajes';

describe('mensajeApi', () => {
  it('muestra el detail del backend en 404 y 409', () => {
    expect(
      mensajeApi(
        new HttpErrorResponse({
          status: 404,
          error: { detail: 'Vehículo no encontrado.' },
        }),
      ),
    ).toBe('Vehículo no encontrado.');
    expect(
      mensajeApi(
        new HttpErrorResponse({
          status: 409,
          error: { detail: 'Este vehículo ya figura dentro.' },
        }),
      ),
    ).toBe('Este vehículo ya figura dentro.');
  });

  it('usa un mensaje propio cuando un 404 no trae detalle', () => {
    expect(mensajeApi(new HttpErrorResponse({ status: 404 }))).toBe(VEHICULO_NO_ENCONTRADO);
    expect(VEHICULO_NO_ENCONTRADO).toBe('Vehículo no encontrado.');
  });

  it('resume los 422 y los fallos de red', () => {
    expect(mensajeApi(new HttpErrorResponse({ status: 422 }))).toBe(DATOS_INVALIDOS);
    expect(DATOS_INVALIDOS).toBe(
      'Datos inválidos. Revisa los campos e intenta de nuevo.',
    );
    expect(mensajeApi(new HttpErrorResponse({ status: 0 }))).toBe(SERVICIO_NO_DISPONIBLE);
    expect(SERVICIO_NO_DISPONIBLE).toBe(
      'El servicio no está disponible. Intente de nuevo.',
    );
  });
});
