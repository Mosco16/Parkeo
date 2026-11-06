import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { timeout } from 'rxjs';
import {
  CambioCeldaCrear,
  EntradaCrear,
  SalidaCrear,
  Estancia,
  EstanciaAbierta,
  EstadoVehiculo,
  HistorialCambiosPagina,
} from '../models/estancia';
import { API_BASE_URL } from './api.service';

@Injectable({ providedIn: 'root' })
export class EstanciasService {
  private readonly http = inject(HttpClient);
  private readonly base = `${inject(API_BASE_URL)}/estancias`;

  entrada(data: EntradaCrear) {
    return this.http.post<EstanciaAbierta>(`${this.base}/entrada`, data).pipe(timeout(15000));
  }
  salida(data: SalidaCrear) {
    return this.http.post<Estancia>(`${this.base}/salida`, data).pipe(timeout(15000));
  }
  cambiarCelda(data: CambioCeldaCrear) {
    return this.http
      .post<EstanciaAbierta>(`${this.base}/cambiar-celda`, data)
      .pipe(timeout(15000));
  }
  consultar(placa: string) {
    return this.http
      .get<EstadoVehiculo>(`${this.base}/vehiculo/${encodeURIComponent(placa)}`)
      .pipe(timeout(15000));
  }
  /** S6: historial paginado, de más reciente a más antiguo. */
  historialCambios(offset: number, limit: number) {
    return this.http
      .get<HistorialCambiosPagina>(`${this.base}/historial-cambios`, {
        params: { offset, limit },
      })
      .pipe(timeout(15000));
  }
}
