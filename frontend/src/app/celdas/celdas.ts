import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CeldaDisponible, EstadoCelda } from '../models/celda';
import { CeldasService } from '../services/celdas.service';

interface GrupoCeldas {
  tipo: 'AUTO' | 'MOTO';
  titulo: string;
  celdas: CeldaDisponible[];
}

@Component({
  selector: 'app-celdas',
  imports: [],
  templateUrl: './celdas.html',
  styleUrl: './celdas.css',
})
export class Celdas {
  private readonly api = inject(CeldasService);
  private readonly destroyRef = inject(DestroyRef);

  readonly celdas = signal<CeldaDisponible[]>([]);
  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly busy = computed(() => this.loading() || this.saving());
  readonly listError = signal('');
  readonly actionError = signal('');
  readonly success = signal('');

  readonly resumen = computed(() => {
    const celdas = this.celdas();
    const contar = (estado: EstadoCelda) => celdas.filter((c) => c.estado === estado).length;
    return {
      total: celdas.length,
      disponibles: contar('DISPONIBLE'),
      ocupadas: contar('OCUPADA'),
      mantenimiento: contar('MANTENIMIENTO'),
    };
  });

  readonly grupos = computed<GrupoCeldas[]>(() => {
    const celdas = this.celdas();
    return [
      {
        tipo: 'AUTO',
        titulo: 'Automóviles',
        celdas: celdas.filter((c) => c.tipo === 'AUTO'),
      },
      { tipo: 'MOTO', titulo: 'Motos', celdas: celdas.filter((c) => c.tipo === 'MOTO') },
    ];
  });

  constructor() {
    this.load();
  }

  load(): void {
    if (this.busy()) return;
    this.loading.set(true);
    this.listError.set('');
    this.api
      .disponibilidad()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (data) => {
          this.loading.set(false);
          this.celdas.set(data.celdas);
        },
        error: (error) => {
          this.loading.set(false);
          this.celdas.set([]);
          this.listError.set(this.errorMessage(error));
        },
      });
  }

  estadoTexto(celda: CeldaDisponible): string {
    switch (celda.estado) {
      case 'OCUPADA':
        return celda.placa ? `Ocupada · ${celda.placa}` : 'Ocupada';
      case 'MANTENIMIENTO':
        return 'Mantenimiento';
      default:
        return 'Disponible';
    }
  }

  /** Una celda con estancia abierta no se puede apagar (409 del servicio). */
  puedeAlternar(celda: CeldaDisponible): boolean {
    return !this.busy() && celda.estado !== 'OCUPADA';
  }

  alternar(celda: CeldaDisponible): void {
    if (!this.puedeAlternar(celda)) return;
    this.saving.set(true);
    this.actionError.set('');
    this.success.set('');
    this.api
      .cambiarEstado(celda.id, !celda.activa)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (actualizada) => {
          this.saving.set(false);
          this.success.set(
            `Celda ${actualizada.codigo} ${actualizada.activa ? 'habilitada' : 'en mantenimiento'}.`,
          );
          this.load();
        },
        error: (error) => {
          this.saving.set(false);
          this.actionError.set(this.errorMessage(error));
        },
      });
  }

  private errorMessage(error: HttpErrorResponse): string {
    if (error.status === 404) return 'La celda ya no existe. Actualiza el tablero.';
    if (error.status === 409)
      return 'No se puede poner en mantenimiento: la celda tiene una estancia abierta.';
    return 'No se pudo conectar con el servicio. Comprueba la conexión e intenta de nuevo.';
  }
}
