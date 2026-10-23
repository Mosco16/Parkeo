import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { SesionOperador } from '../services/sesion-operador.service';

/** Las pantallas de operación exigen un operador activo (RN-OPE-02). */
export const operadorActivo: CanActivateFn = () => {
  const sesion = inject(SesionOperador);
  const router = inject(Router);
  return sesion.operador() ? true : router.createUrlTree(['/operador']);
};
