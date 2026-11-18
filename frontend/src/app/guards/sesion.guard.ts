import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { SesionUsuario } from '../services/sesion-usuario.service';

/** Toda pantalla interna exige una sesión iniciada (S3). */
export const sesionActiva: CanActivateFn = (_ruta, estado) => {
  const sesion = inject(SesionUsuario);
  const router = inject(Router);
  return sesion.autenticado()
    ? true
    : router.createUrlTree(['/login'], { queryParams: { returnUrl: estado.url } });
};

/** Usuarios y mantenimiento de celdas son exclusivos del administrador (S3, S5). */
export const soloAdministrador: CanActivateFn = (_ruta, estado) => {
  const sesion = inject(SesionUsuario);
  const router = inject(Router);
  if (!sesion.autenticado()) {
    return router.createUrlTree(['/login'], { queryParams: { returnUrl: estado.url } });
  }
  return sesion.administrador() ? true : router.createUrlTree(['/tablero']);
};
