import { computed, Injectable, signal } from '@angular/core';
import { SesionRespuesta, Usuario } from '../models/usuario';

/** Decisión D2: el token y el usuario viven en sessionStorage, no en localStorage. */
const CLAVE = 'parkeo.sesion';

@Injectable({ providedIn: 'root' })
export class SesionUsuario {
  private readonly actual = signal<SesionRespuesta | null>(this.leer());
  readonly usuario = computed<Usuario | null>(() => this.actual()?.usuario ?? null);
  readonly autenticado = computed(() => this.actual() !== null);
  readonly administrador = computed(() => this.usuario()?.rol === 'ADMINISTRADOR');

  iniciar(sesion: SesionRespuesta): void {
    this.actual.set(sesion);
    try {
      sessionStorage.setItem(CLAVE, JSON.stringify(sesion));
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

  token(): string | null {
    return this.actual()?.access_token ?? null;
  }

  private leer(): SesionRespuesta | null {
    try {
      const crudo = sessionStorage.getItem(CLAVE);
      if (!crudo) return null;
      const dato = JSON.parse(crudo) as Partial<SesionRespuesta> | null;
      const usuario = dato?.usuario as Partial<Usuario> | undefined;
      if (
        !dato ||
        typeof dato.access_token !== 'string' ||
        !usuario ||
        typeof usuario.id !== 'number' ||
        typeof usuario.nombre !== 'string' ||
        (usuario.rol !== 'ADMINISTRADOR' && usuario.rol !== 'OPERADOR')
      ) {
        return null;
      }
      return dato as SesionRespuesta;
    } catch {
      return null;
    }
  }
}
