import { Injectable, signal } from '@angular/core';
import { Operador } from '../models/operador';

const CLAVE = 'autos-colombia.operador';

/** RN-OPE-02: no hay login; el operador activo se guarda en la sesión del navegador. */
@Injectable({ providedIn: 'root' })
export class SesionOperador {
  private readonly actual = signal<Operador | null>(this.leer());
  readonly operador = this.actual.asReadonly();

  iniciar(operador: Operador): void {
    this.actual.set(operador);
    try {
      sessionStorage.setItem(CLAVE, JSON.stringify(operador));
    } catch {
      // Si el almacenamiento no está disponible, la sesión sigue en memoria.
    }
  }

  cerrar(): void {
    this.actual.set(null);
    try {
      sessionStorage.removeItem(CLAVE);
    } catch {
      // Sin almacenamiento no hay nada que limpiar.
    }
  }

  private leer(): Operador | null {
    try {
      const crudo = sessionStorage.getItem(CLAVE);
      if (!crudo) return null;
      const dato = JSON.parse(crudo) as Partial<Operador> | null;
      if (!dato || typeof dato.id !== 'number' || typeof dato.nombre !== 'string') return null;
      return {
        id: dato.id,
        nombre: dato.nombre,
        telefono: typeof dato.telefono === 'string' ? dato.telefono : '',
      };
    } catch {
      return null;
    }
  }
}
