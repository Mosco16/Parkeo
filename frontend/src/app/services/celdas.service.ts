import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { timeout } from 'rxjs';
import { Celda, CeldasPagina, Disponibilidad } from '../models/celda';

import { API_BASE_URL } from './api.service';

@Injectable({ providedIn: 'root' })
export class CeldasService {
  private readonly http = inject(HttpClient);
  private readonly base = inject(API_BASE_URL);
  private readonly cells = `${this.base}/celdas`;

  list(offset: number, limit: number) {
    return this.http
      .get<CeldasPagina>(this.cells, { params: { offset, limit } })
      .pipe(timeout(15000));
  }
  get(id: number) {
    return this.http.get<Celda>(`${this.cells}/${id}`).pipe(timeout(15000));
  }
  disponibilidad() {
    return this.http
      .get<Disponibilidad>(`${this.cells}/disponibilidad`)
      .pipe(timeout(15000));
  }
  /** S5: solo el administrador enciende o apaga; no se edita código ni tipo. */
  cambiarEstado(id: number, activa: boolean) {
    return this.http
      .patch<Celda>(`${this.cells}/${id}/estado`, { activa })
      .pipe(timeout(15000));
  }
}
