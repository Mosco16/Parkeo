import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, ValidatorFn } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { MOTIVOS_ANULACION, MotivoAnulacion, Pago, PagoCrear } from '../models/pago';
import { PagosService } from '../services/pagos.service';
import { fechaBogota, fechaHoraBogota } from '../utils/fechas';
import { mensajeApi } from '../utils/mensajes';

const nonBlank: ValidatorFn = (control) =>
  typeof control.value === 'string' && control.value.trim() ? null : { required: true };
const PATRON_CORREO = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const correo: ValidatorFn = (control) =>
  !control.value || PATRON_CORREO.test(String(control.value).trim().toLowerCase())
    ? null
    : { correo: true };
const normalizarPlaca = (value: string) => value.trim().toUpperCase();

@Component({
  selector: 'app-pagos',
  imports: [ReactiveFormsModule],
  templateUrl: './pagos.html',
  styleUrl: './pagos.css',
})
export class Pagos {
  private readonly api = inject(PagosService);
  private readonly fb = inject(FormBuilder);
  private readonly destroy = inject(DestroyRef);
  private readonly route = inject(ActivatedRoute);

  readonly motivos = MOTIVOS_ANULACION;
  readonly form = this.fb.nonNullable.group({
    placa: this.fb.nonNullable.control('', nonBlank),
    referencia: this.fb.nonNullable.control('', nonBlank),
    correo: this.fb.nonNullable.control('', correo),
    autorizar_avisos: this.fb.nonNullable.control(false),
  });
  readonly saving = signal(false);
  readonly errorPago = signal('');
  readonly ultimoPago = signal<Pago | null>(null);

  readonly consulta = this.fb.nonNullable.group({
    placa: this.fb.nonNullable.control('', nonBlank),
  });
  readonly items = signal<Pago[]>([]);
  readonly total = signal(0);
  readonly pagina = signal(1);
  readonly tamano = 10;
  readonly loading = signal(false);
  readonly buscado = signal(false);
  readonly errorHistorial = signal('');
  readonly paginas = computed(() => Math.max(1, Math.ceil(this.total() / this.tamano)));

  readonly anulando = signal<number | null>(null);
  readonly motivo = signal<MotivoAnulacion>(MOTIVOS_ANULACION[0]);
  readonly anulandoBusy = signal(false);
  readonly errorAnulacion = signal('');

  constructor() {
    const inicial = this.route.snapshot.queryParamMap.get('placa');
    if (inicial) {
      const placa = normalizarPlaca(inicial);
      this.form.controls.placa.setValue(placa, { emitEvent: false });
      this.consulta.controls.placa.setValue(placa, { emitEvent: false });
      this.buscar(1);
    }
  }

  registrar(): void {
    if (this.saving()) return;
    this.form.markAllAsTouched();
    this.errorPago.set('');
    const value = this.form.getRawValue();
    if (value.autorizar_avisos && !value.correo.trim()) {
      this.form.controls.correo.setErrors({ required: true });
      return;
    }
    if (this.form.invalid) return;

    const payload: PagoCrear = {
      placa: normalizarPlaca(value.placa),
      referencia: value.referencia.trim(),
    };
    const correo = value.correo.trim().toLowerCase();
    if (correo) payload.correo = correo;
    if (value.autorizar_avisos) payload.autorizar_avisos = true;

    this.saving.set(true);
    this.api
      .registrar(payload)
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe({
        next: (pago) => {
          this.saving.set(false);
          this.ultimoPago.set(pago);
          this.form.reset({
            placa: pago.placa,
            referencia: '',
            correo: '',
            autorizar_avisos: false,
          });
          this.consulta.controls.placa.setValue(pago.placa, { emitEvent: false });
          this.buscar(1);
        },
        error: (error: HttpErrorResponse) => {
          this.saving.set(false);
          this.errorPago.set(mensajeApi(error));
        },
      });
  }

  buscar(pagina = 1): void {
    if (this.loading()) return;
    this.consulta.controls.placa.markAsTouched();
    if (this.consulta.controls.placa.invalid) return;
    const value = normalizarPlaca(this.consulta.controls.placa.value);
    this.consulta.controls.placa.setValue(value, { emitEvent: false });
    this.loading.set(true);
    this.buscado.set(true);
    this.errorHistorial.set('');
    this.api
      .historial(value, pagina, this.tamano)
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe({
        next: (data) => {
          this.loading.set(false);
          this.items.set(data.items);
          this.total.set(data.total);
          this.pagina.set(data.pagina);
        },
        error: (error: HttpErrorResponse) => {
          this.loading.set(false);
          this.items.set([]);
          this.total.set(0);
          this.errorHistorial.set(mensajeApi(error));
        },
      });
  }

  preguntarAnulacion(pago: Pago): void {
    if (this.anulandoBusy()) return;
    this.anulando.set(pago.id);
    this.motivo.set(MOTIVOS_ANULACION[0]);
    this.errorAnulacion.set('');
  }

  cancelarAnulacion(): void {
    if (this.anulandoBusy()) return;
    this.anulando.set(null);
    this.errorAnulacion.set('');
  }

  confirmarAnulacion(): void {
    const id = this.anulando();
    if (id === null || this.anulandoBusy()) return;
    this.anulandoBusy.set(true);
    this.errorAnulacion.set('');
    this.api
      .anular(id, { motivo: this.motivo() })
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe({
        next: (pago) => {
          this.anulandoBusy.set(false);
          this.anulando.set(null);
          this.items.update((items) => items.map((item) => (item.id === pago.id ? pago : item)));
        },
        error: (error: HttpErrorResponse) => {
          this.anulandoBusy.set(false);
          this.errorAnulacion.set(mensajeApi(error));
        },
      });
  }

  onMotivo(event: Event): void {
    this.motivo.set((event.target as HTMLSelectElement).value as MotivoAnulacion);
  }

  errorCampo(campo: 'placa' | 'referencia' | 'correo'): string {
    const control = this.form.controls[campo];
    if (!control.touched || !control.errors) return '';
    if (control.errors['required']) {
      return campo === 'correo'
        ? 'Indica un correo para autorizar los avisos.'
        : 'Este campo es obligatorio.';
    }
    if (control.errors['correo']) return 'Introduce un correo válido o deja el campo vacío.';
    return 'Revisa este campo.';
  }

  valor(valor: number): string {
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      maximumFractionDigits: 0,
    }).format(valor);
  }

  fecha(iso: string): string {
    return fechaBogota(iso);
  }

  fechaHora(iso: string): string {
    return fechaHoraBogota(iso);
  }
}
