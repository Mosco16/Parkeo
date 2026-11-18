import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { timeout } from 'rxjs';
import { Pago, PagoAnular, PagoCrear, PagosPagina } from '../models/pago';
import { API_BASE_URL } from './api.service';

@Injectable({ providedIn: 'root' })
export class PagosService {
  private readonly http = inject(HttpClient);
  private readonly base = `${inject(API_BASE_URL)}/pagos`;

  registrar(data: PagoCrear) {
    return this.http.post<Pago>(this.base, data).pipe(timeout(15000));
  }

  anular(id: number, data: PagoAnular) {
    return this.http.post<Pago>(`${this.base}/${id}/anular`, data).pipe(timeout(15000));
  }

  historial(placa: string, pagina: number, tamano: number) {
    return this.http
      .get<PagosPagina>(this.base, {
        params: { placa, pagina, tamano },
      })
      .pipe(timeout(15000));
  }
}
