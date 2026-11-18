import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, ValidatorFn } from '@angular/forms';
import { CeldaDisponible, Disponibilidad, TipoCelda } from '../models/celda';
import { EstadoVehiculo } from '../models/estancia';
import { CeldasService } from '../services/celdas.service';
import { EstanciasService } from '../services/estancias.service';
import { mensajeApi } from '../utils/mensajes';

const nonBlank: ValidatorFn = (c) =>
  typeof c.value === 'string' && c.value.trim() ? null : { required: true };
const placa = (value: string) => value.trim().toUpperCase();

@Component({
  selector: 'app-tablero',
  imports: [ReactiveFormsModule],
  templateUrl: './tablero.html',
  styleUrl: './tablero.css',
})
export class Tablero {
  private readonly celdasApi = inject(CeldasService);
  private readonly estanciasApi = inject(EstanciasService);
  private readonly fb = inject(FormBuilder);
  private readonly destroy = inject(DestroyRef);
  private version = 0;

  readonly celdas = signal<CeldaDisponible[]>([]);
  readonly cupo = signal<Disponibilidad['cupo'] | null>(null);
  readonly loading = signal(false);
  readonly error = signal('');
  readonly consulta = this.fb.group({
    placa: this.fb.nonNullable.control('', nonBlank),
  });
  readonly estado = signal<EstadoVehiculo | null>(null);
  readonly querying = signal(false);
  readonly errorConsulta = signal('');
  readonly ocupadas = computed(() => this.celdas().filter((c) => c.estado === 'OCUPADA').length);

  constructor() {
    this.cargar();
    this.consulta.controls.placa.valueChanges
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe(() => {
        this.version++;
        this.estado.set(null);
        this.errorConsulta.set('');
      });
  }

  cargar(): void {
    if (this.loading()) return;
    this.loading.set(true);
    this.error.set('');
    this.celdasApi
      .disponibilidad()
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe({
        next: (data) => {
          this.loading.set(false);
          this.celdas.set(data.celdas);
          this.cupo.set(data.cupo);
        },
        error: () => {
          this.loading.set(false);
          this.celdas.set([]);
          this.cupo.set(null);
          this.error.set('No se pudo cargar el tablero. Revisa la conexión e intenta de nuevo.');
        },
      });
  }

  buscar(): void {
    if (this.querying()) return;
    this.consulta.controls.placa.markAsTouched();
    if (this.consulta.controls.placa.invalid) return;
    const value = placa(this.consulta.controls.placa.value);
    this.consulta.controls.placa.setValue(value, { emitEvent: false });
    const version = ++this.version;
    this.estado.set(null);
    this.errorConsulta.set('');
    this.querying.set(true);
    this.estanciasApi
      .consultar(value)
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe({
        next: (result) => {
          this.querying.set(false);
          if (version === this.version) this.estado.set(result);
        },
        error: (error) => {
          this.querying.set(false);
          if (version === this.version) this.errorConsulta.set(mensajeApi(error));
        },
      });
  }

  cupoTexto(tipo: TipoCelda): string {
    const valor = this.cupo()?.[tipo];
    if (!valor) return '';
    return `${valor.libres} libres de ${valor.total}`;
  }

  textoEstado(celda: CeldaDisponible): string {
    switch (celda.estado) {
      case 'OCUPADA':
        return 'Ocupada';
      case 'MANTENIMIENTO':
        return 'Mantenimiento';
      default:
        return 'Disponible';
    }
  }

  etiqueta(celda: CeldaDisponible): string {
    const detalle = celda.placa ? ` (${celda.placa})` : '';
    return `${celda.codigo}: ${this.textoEstado(celda).toLowerCase()}${detalle}`;
  }
}
