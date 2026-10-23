import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, FormControl, ReactiveFormsModule, ValidatorFn } from '@angular/forms';
import { CeldaDisponible, TipoCelda } from '../models/celda';
import { EstadoVehiculo } from '../models/estancia';
import { TipoVehiculo } from '../models/vehiculo';
import { CeldasService } from '../services/celdas.service';
import { EstanciasService } from '../services/estancias.service';
import { fechaHoraBogota } from '../utils/fechas';
import { mensajeApi } from '../utils/mensajes';

const nonBlank: ValidatorFn = (c) =>
  typeof c.value === 'string' && c.value.trim() ? null : { required: true };
const placa = (value: string) => value.trim().toUpperCase();

/** RN-VEH-02: AUTOMOVIL y CAMIONETA usan celdas de tipo AUTO. */
function tipoCeldaRequerido(tipo: TipoVehiculo): TipoCelda {
  return tipo === 'MOTO' ? 'MOTO' : 'AUTO';
}

@Component({
  selector: 'app-cambiar-celda',
  imports: [ReactiveFormsModule],
  templateUrl: './cambiar-celda.html',
  styleUrl: './cambiar-celda.css',
})
export class CambiarCelda {
  private readonly estanciasApi = inject(EstanciasService);
  private readonly celdasApi = inject(CeldasService);
  private readonly fb = inject(FormBuilder);
  private readonly destroy = inject(DestroyRef);
  private version = 0;

  readonly consulta = this.fb.group({
    placa: this.fb.nonNullable.control('', nonBlank),
  });
  readonly celda: FormControl<number | null> = this.fb.control<number | null>(null);
  readonly estado = signal<EstadoVehiculo | null>(null);
  readonly libres = signal<CeldaDisponible[]>([]);
  readonly querying = signal(false);
  readonly cargandoOpciones = signal(false);
  readonly saving = signal(false);
  readonly busy = computed(
    () => this.querying() || this.cargandoOpciones() || this.saving(),
  );
  readonly errorConsulta = signal('');
  readonly errorAccion = signal('');
  readonly exito = signal('');

  constructor() {
    this.consulta.controls.placa.valueChanges
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe(() => {
        this.version++;
        this.estado.set(null);
        this.libres.set([]);
        this.celda.setValue(null);
        this.errorConsulta.set('');
        this.errorAccion.set('');
        this.exito.set('');
      });
  }

  buscar(): void {
    if (this.busy()) return;
    this.consulta.controls.placa.markAsTouched();
    if (this.consulta.controls.placa.invalid) return;
    const value = placa(this.consulta.controls.placa.value);
    this.consulta.controls.placa.setValue(value, { emitEvent: false });
    const version = ++this.version;
    this.estado.set(null);
    this.libres.set([]);
    this.celda.setValue(null);
    this.errorConsulta.set('');
    this.errorAccion.set('');
    this.exito.set('');
    this.querying.set(true);
    this.estanciasApi
      .consultar(value)
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe({
        next: (result) => {
          this.querying.set(false);
          if (version !== this.version) return;
          this.estado.set(result);
          if (result.esta_dentro && result.estancia) this.cargarOpciones();
        },
        error: (error) => {
          this.querying.set(false);
          if (version === this.version) this.errorConsulta.set(mensajeApi(error));
        },
      });
  }

  cargarOpciones(): void {
    const state = this.estado();
    if (!state?.esta_dentro || !state.estancia) return;
    const requerido = tipoCeldaRequerido(state.vehiculo.tipo);
    const version = this.version;
    this.cargandoOpciones.set(true);
    this.celdasApi
      .disponibilidad()
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe({
        next: (data) => {
          this.cargandoOpciones.set(false);
          if (version !== this.version) return;
          const actual = state.estancia?.celda_id;
          this.libres.set(
            data.celdas.filter(
              (item) =>
                item.estado === 'LIBRE' && item.tipo === requerido && item.id !== actual,
            ),
          );
          this.celda.setValue(null);
        },
        error: () => {
          this.cargandoOpciones.set(false);
          if (version === this.version)
            this.errorAccion.set(
              'No se pudieron cargar las celdas libres. Intenta de nuevo.',
            );
        },
      });
  }

  confirmar(): void {
    const state = this.estado();
    const destino = this.celda.value;
    if (!state?.esta_dentro || !state.estancia || destino === null || this.busy()) return;
    const actual = state.estancia.celda.codigo;
    this.saving.set(true);
    this.errorAccion.set('');
    this.exito.set('');
    this.estanciasApi
      .cambiarCelda({ placa: state.vehiculo.placa, celda_id: destino })
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe({
        next: (result) => {
          this.saving.set(false);
          this.estado.set({ ...state, estancia: result });
          this.exito.set(`Celda cambiada: de ${actual} a ${result.celda.codigo}.`);
          this.cargarOpciones();
        },
        error: (error) => {
          this.saving.set(false);
          this.errorAccion.set(mensajeApi(error));
          if (error.status === 409) this.cargarOpciones();
        },
      });
  }

  fecha(value: string): string {
    return fechaHoraBogota(value);
  }
}
