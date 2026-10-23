import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Router } from '@angular/router';
import { EMPTY, expand, reduce, throwError } from 'rxjs';
import { Operador } from '../models/operador';
import { OperadoresService } from '../services/operadores.service';
import { SesionOperador } from '../services/sesion-operador.service';

@Component({
  selector: 'app-seleccion-operador',
  templateUrl: './seleccion-operador.html',
  styleUrl: './seleccion-operador.css',
})
export class SeleccionOperador {
  private readonly api = inject(OperadoresService);
  private readonly sesion = inject(SesionOperador);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  readonly operadores = signal<Operador[]>([]);
  readonly activo = this.sesion.operador;
  readonly seleccionado = signal<number | null>(this.sesion.operador()?.id ?? null);
  readonly loading = signal(false);
  readonly error = signal('');

  constructor() {
    this.cargar();
  }

  cargar(): void {
    if (this.loading()) return;
    this.loading.set(true);
    this.error.set('');
    this.api
      .list(0, 100)
      .pipe(
        expand((pagina) => {
          const siguiente = pagina.offset + pagina.items.length;
          if (siguiente >= pagina.total) return EMPTY;
          if (!pagina.items.length) {
            return throwError(() => new Error('Catálogo incompleto. Recarga las opciones.'));
          }
          return this.api.list(siguiente, 100);
        }),
        reduce((items, pagina) => [...items, ...pagina.items], [] as Operador[]),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (items) => {
          this.loading.set(false);
          this.operadores.set(items);
        },
        error: () => {
          this.loading.set(false);
          this.error.set('No se pudieron cargar los operadores. Intenta de nuevo.');
        },
      });
  }

  elegir(id: number): void {
    this.seleccionado.set(id);
    this.error.set('');
  }

  iniciarTurno(): void {
    const operador = this.operadores().find((item) => item.id === this.seleccionado());
    if (!operador) {
      this.error.set('Selecciona un operador para iniciar el turno.');
      return;
    }
    this.sesion.iniciar(operador);
    void this.router.navigate(['/tablero']);
  }
}
