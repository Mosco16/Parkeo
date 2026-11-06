import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { SesionUsuario } from '../services/sesion-usuario.service';

const RUTA_LOGIN = '/auth/login';

/** Adjunta el token a cada llamada y cierra la sesión si el backend responde 401. */
export const authInterceptor: HttpInterceptorFn = (peticion, siguiente) => {
  const sesion = inject(SesionUsuario);
  const router = inject(Router);
  const token = sesion.token();
  const esLogin = peticion.url.endsWith(RUTA_LOGIN);
  const conToken =
    token && !esLogin
      ? peticion.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
      : peticion;

  return siguiente(conToken).pipe(
    catchError((error: unknown) => {
      if (error instanceof HttpErrorResponse && error.status === 401 && !esLogin) {
        sesion.cerrar();
        void router.navigate(['/login']);
      }
      return throwError(() => error);
    }),
  );
};
