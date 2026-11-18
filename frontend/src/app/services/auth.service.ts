import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { timeout } from 'rxjs';
import { LoginCrear, SesionRespuesta, Usuario } from '../models/usuario';
import { API_BASE_URL } from './api.service';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly base = `${inject(API_BASE_URL)}/auth`;

  login(data: LoginCrear) {
    return this.http.post<SesionRespuesta>(`${this.base}/login`, data).pipe(timeout(15000));
  }

  me() {
    return this.http.get<Usuario>(`${this.base}/me`).pipe(timeout(15000));
  }
}
