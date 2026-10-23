import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, ValidatorFn } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { EstadoVehiculo } from '../models/estancia';
import { EstanciasService } from '../services/estancias.service';
import { SesionOperador } from '../services/sesion-operador.service';
import { fechaBogota, fechaHoraBogota } from '../utils/fechas';

const nonBlank: ValidatorFn = (c) =>
  typeof c.value === 'string' && c.value.trim() ? null : { required: true };
const placa = (value: string) => value.trim().toUpperCase();

@Component({
  selector: 'app-control-acceso',
  imports: [ReactiveFormsModule],
  templateUrl: './control-acceso.html',
  styleUrl: './control-acceso.css',
})
export class ControlAcceso {
  private readonly api = inject(EstanciasService);
  private readonly sesion = inject(SesionOperador);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly fb = inject(FormBuilder);
  private readonly destroy = inject(DestroyRef);
  private readonly volverASalida = this.route.snapshot.queryParamMap.get('volver') === 'salida';
  private version = 0;

  readonly operador = this.sesion.operador;
  readonly consulta = this.fb.group({
    placa: this.fb.nonNullable.control('', nonBlank),
  });
  readonly estado = signal<EstadoVehiculo | null>(null);
  readonly querying = signal(false);
  readonly saving = signal(false);
  readonly busy = computed(() => this.querying() || this.saving());
  readonly confirmando = signal(false);
  readonly errorConsulta = signal('');
  readonly aviso = signal('');
  readonly exitoEntrada = signal('');

  constructor() {
    this.consulta.controls.placa.valueChanges
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe(() => {
        this.version++;
        this.estado.set(null);
        this.confirmando.set(false);
        this.errorConsulta.set('');
        this.aviso.set('');
        this.exitoEntrada.set('');
      });

    const inicial = this.route.snapshot.queryParamMap.get('placa');
    if (inicial) {
      this.consulta.controls.placa.setValue(inicial.toUpperCase(), { emitEvent: false });
      this.buscar();
    }
  }

  buscar(): void {
    if (this.busy()) return;
    this.consulta.controls.placa.markAsTouched();
    if (this.consulta.controls.placa.invalid) return;
    const value = placa(this.consulta.controls.placa.value);
    this.consulta.controls.placa.setValue(value, { emitEvent: false });
    const version = ++this.version;
    this.estado.set(null);
    this.confirmando.set(false);
    this.errorConsulta.set('');
    this.aviso.set('');
    this.exitoEntrada.set('');
    this.querying.set(true);
    this.api
      .consultar(value)
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe({
        next: (result) => {
          this.querying.set(false);
          if (version === this.version) this.estado.set(result);
        },
        error: (error) => {
          this.querying.set(false);
          if (version === this.version) this.errorConsulta.set(this.mensaje(error));
        },
      });
  }

  confirmarEntrada(): void {
    const operador = this.operador();
    const state = this.estado();
    if (!operador || !state || this.busy()) return;
    if (
      state.esta_dentro ||
      state.mensualidad === 'VENCIDA' ||
      !state.celda_sugerida ||
      state.vehiculo.placa !== placa(this.consulta.controls.placa.value)
    )
      return;
    this.saving.set(true);
    this.errorConsulta.set('');
    this.aviso.set('');
    this.exitoEntrada.set('');
    this.entradaNormal(state.vehiculo.placa, operador.id, false);
  }

  abrirConfirmacion(): void {
    if (this.busy()) return;
    this.confirmando.set(true);
    this.errorConsulta.set('');
  }

  cancelarConfirmacion(): void {
    this.confirmando.set(false);
  }

  /**
   * RN-COR-01..05: cierra la estancia anterior con una salida normal y, si
   * funciona, registra una entrada nueva. Nunca borra ni edita el historial.
   */
  corregirEntrada(): void {
    const operador = this.operador();
    const state = this.estado();
    if (!operador || !state?.esta_dentro || this.busy()) return;
    const placaActual = state.vehiculo.placa;
    this.saving.set(true);
    this.confirmando.set(false);
    this.errorConsulta.set('');
    this.aviso.set('');
    this.exitoEntrada.set('');
    this.api
      .salida({ placa: placaActual, operador_id: operador.id })
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe({
        next: () => {
          this.aviso.set('Estancia cerrada.');
          this.api
            .consultar(placaActual)
            .pipe(takeUntilDestroyed(this.destroy))
            .subscribe({
              next: (nuevo) => {
                this.estado.set(nuevo);
                if (
                  nuevo.esta_dentro ||
                  nuevo.mensualidad === 'VENCIDA' ||
                  !nuevo.celda_sugerida
                ) {
                  this.saving.set(false);
                  return;
                }
                this.entradaNormal(placaActual, operador.id, true);
              },
              error: () => {
                this.saving.set(false);
                this.estado.set(null);
                this.errorConsulta.set(
                  'Estancia cerrada. No se pudo consultar el vehículo para registrar la entrada; vuelve a consultar la placa.',
                );
              },
            });
        },
        error: (error) => {
          this.saving.set(false);
          this.errorConsulta.set(this.mensaje(error));
        },
      });
  }

  fecha(value: string): string {
    return fechaHoraBogota(value);
  }

  vence(value: string): string {
    return fechaBogota(value);
  }

  private entradaNormal(placaActual: string, operadorId: number, correccion: boolean): void {
    this.api
      .entrada({ placa: placaActual, operador_id: operadorId })
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe({
        next: (result) => {
          this.saving.set(false);
          const prefijo = correccion ? 'Estancia cerrada. ' : '';
          const mensaje = `${prefijo}Entrada registrada: ${placaActual}, celda ${result.celda.codigo}, ${this.fecha(result.entrada)}.`;
          this.estado.set(null);
          if (this.volverASalida) {
            void this.router.navigate(['/salida'], { queryParams: { placa: placaActual } });
            return;
          }
          this.exitoEntrada.set(mensaje);
        },
        error: (error) => {
          this.saving.set(false);
          const detalle = this.mensaje(error);
          this.estado.set(null);
          this.errorConsulta.set(
            correccion ? `${detalle} La estancia anterior ya quedó cerrada.` : detalle,
          );
        },
      });
  }

  mensaje(error: HttpErrorResponse): string {
    if ([404, 409].includes(error.status) && typeof error.error?.detail === 'string')
      return error.error.detail;
    if (error.status === 422) return 'Datos inválidos. Revisa la placa e intenta de nuevo.';
    return 'No se pudo conectar con el servicio. Consulta el vehículo antes de reintentar.';
  }
}
