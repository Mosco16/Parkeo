import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { timeout } from 'rxjs';
import {
  UsuarioActualizar,
  UsuarioCrear,
  UsuarioDetalle,
  UsuariosPagina,
} from '../models/usuario';

import { API_BASE_URL } from './api.service';

@Injectable({ providedIn: 'root' })
export class UsuariosService {
  private readonly http = inject(HttpClient);
  private readonly base = inject(API_BASE_URL);
  private readonly users = `${this.base}/usuarios`;

  list(offset: number, limit: number) {
    return this.http
      .get<UsuariosPagina>(this.users, { params: { offset, limit } })
      .pipe(timeout(15000));
  }
  get(id: number) {
    return this.http.get<UsuarioDetalle>(`${this.users}/${id}`).pipe(timeout(15000));
  }
  create(data: UsuarioCrear) {
    return this.http.post<UsuarioDetalle>(this.users, data).pipe(timeout(15000));
  }
  update(id: number, data: UsuarioActualizar) {
    return this.http.patch<UsuarioDetalle>(`${this.users}/${id}`, data).pipe(timeout(15000));
  }
  cambiarEstado(id: number, activo: boolean) {
    return this.http
      .patch<UsuarioDetalle>(`${this.users}/${id}/estado`, { activo })
      .pipe(timeout(15000));
  }
  restablecerPassword(id: number, password: string) {
    return this.http
      .post<UsuarioDetalle>(`${this.users}/${id}/restablecer-password`, { password })
      .pipe(timeout(15000));
  }
}
