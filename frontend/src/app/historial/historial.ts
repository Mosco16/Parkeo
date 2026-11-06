import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CambioCeldaHistorial } from '../models/estancia';
import { EstanciasService } from '../services/estancias.service';
import { fechaHoraBogota } from '../utils/fechas';

@Component({
  selector: 'app-historial',
  imports: [],
  templateUrl: './historial.html',
  styleUrl: './historial.css',
})
export class Historial {
  private readonly api = inject(EstanciasService);
  private readonly destroyRef = inject(DestroyRef);

  readonly items = signal<CambioCeldaHistorial[]>([]);
  readonly total = signal(0);
  readonly offset = signal(0);
  readonly limit = 10;
  readonly loading = signal(false);
  readonly listError = signal('');
  readonly page = computed(() => Math.floor(this.offset() / this.limit) + 1);
  readonly pages = computed(() => Math.max(1, Math.ceil(this.total() / this.limit)));

  constructor() {
    this.load();
  }

  load(offset = this.offset()): void {
    if (this.loading()) return;
    this.loading.set(true);
    this.listError.set('');
    this.api
      .historialCambios(offset, this.limit)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (data) => {
          this.loading.set(false);
          if (offset > 0 && offset >= data.total) {
            this.load(Math.max(0, Math.floor((data.total - 1) / this.limit) * this.limit));
            return;
          }
          this.items.set(data.items);
          this.total.set(data.total);
          this.offset.set(offset);
        },
        error: () => {
          this.loading.set(false);
          this.listError.set(
            'No se pudo cargar el historial. Comprueba la conexión e intenta de nuevo.',
          );
        },
      });
  }

  fecha(valor: string): string {
    return fechaHoraBogota(valor);
  }
}
