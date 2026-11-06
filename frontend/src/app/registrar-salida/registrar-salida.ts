import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, ValidatorFn } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { EstadoVehiculo } from '../models/estancia';
import { EstanciasService } from '../services/estancias.service';
import { SesionUsuario } from '../services/sesion-usuario.service';
import { fechaBogota, fechaHoraBogota } from '../utils/fechas';
import { mensajeApi } from '../utils/mensajes';

const nonBlank: ValidatorFn = (c) =>
  typeof c.value === 'string' && c.value.trim() ? null : { required: true };
const placa = (value: string) => value.trim().toUpperCase();

@Component({
  selector: 'app-registrar-salida',
  imports: [ReactiveFormsModule],
  templateUrl: './registrar-salida.html',
  styleUrl: './registrar-salida.css',
})
export class RegistrarSalida {
  private readonly api = inject(EstanciasService);
  private readonly sesion = inject(SesionUsuario);
  private readonly fb = inject(FormBuilder);
  private readonly destroy = inject(DestroyRef);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private version = 0;

  readonly usuario = this.sesion.usuario;
  readonly consulta = this.fb.group({
    placa: this.fb.nonNullable.control('', nonBlank),
  });
  readonly estado = signal<EstadoVehiculo | null>(null);
  readonly querying = signal(false);
  readonly saving = signal(false);
  readonly busy = computed(() => this.querying() || this.saving());
  readonly errorConsulta = signal('');
  readonly exitoSalida = signal('');

  constructor() {
    this.consulta.controls.placa.valueChanges
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe(() => {
        this.version++;
        this.estado.set(null);
        this.errorConsulta.set('');
        this.exitoSalida.set('');
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
    this.errorConsulta.set('');
    this.exitoSalida.set('');
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
          if (version === this.version) this.errorConsulta.set(mensajeApi(error));
        },
      });
  }

  confirmarSalida(): void {
    const state = this.estado();
    if (!state?.esta_dentro || !state.estancia || this.busy()) return;
    const value = placa(this.consulta.controls.placa.value);
    if (state.vehiculo.placa !== value) return;
    const celda = state.estancia.celda;
    this.saving.set(true);
    this.errorConsulta.set('');
    this.exitoSalida.set('');
    this.api
      .salida({ placa: value })
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe({
        next: (result) => {
          this.saving.set(false);
          this.estado.set(null);
          this.exitoSalida.set(
            `Salida registrada: ${value}, celda ${celda.codigo}, ${this.fecha(result.salida!)}.`,
          );
        },
        error: (error) => {
          this.saving.set(false);
          this.estado.set(null);
          this.errorConsulta.set(mensajeApi(error));
        },
      });
  }

  irAEntrada(): void {
    void this.router.navigate(['/control-acceso'], {
      queryParams: { placa: placa(this.consulta.controls.placa.value), volver: 'salida' },
    });
  }

  fecha(value: string): string {
    return fechaHoraBogota(value);
  }

  vence(value: string): string {
    return fechaBogota(value);
  }
}
