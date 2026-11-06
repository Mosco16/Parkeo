import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, ValidatorFn } from '@angular/forms';
import { ErrorApi } from '../models/vehiculo';
import { UsuarioActualizar, UsuarioCrear, UsuarioDetalle } from '../models/usuario';
import { UsuariosService } from '../services/usuarios.service';

const nonBlank: ValidatorFn = (control) =>
  typeof control.value === 'string' && control.value.trim() ? null : { required: true };
const minLength =
  (minimo: number): ValidatorFn =>
  (control) => {
    const valor = typeof control.value === 'string' ? control.value : '';
    return valor.length >= minimo ? null : { minlength: true };
  };

type Field =
  | 'documento'
  | 'nombre'
  | 'usuario'
  | 'telefono'
  | 'correo'
  | 'direccion'
  | 'password';

@Component({
  selector: 'app-usuarios',
  imports: [ReactiveFormsModule],
  templateUrl: './usuarios.html',
  styleUrl: './usuarios.css',
})
export class Usuarios {
  private readonly api = inject(UsuariosService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly fb = inject(FormBuilder);

  readonly form = this.fb.group({
    documento: this.fb.nonNullable.control('', nonBlank),
    nombre: this.fb.nonNullable.control('', nonBlank),
    usuario: this.fb.nonNullable.control('', nonBlank),
    telefono: this.fb.nonNullable.control(''),
    correo: this.fb.nonNullable.control(''),
    direccion: this.fb.nonNullable.control(''),
    password: this.fb.nonNullable.control(''),
  });
  readonly resetForm = this.fb.group({
    password: this.fb.nonNullable.control('', [nonBlank, minLength(8)]),
  });

  readonly items = signal<UsuarioDetalle[]>([]);
  readonly total = signal(0);
  readonly offset = signal(0);
  readonly limit = 10;
  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly busy = computed(() => this.loading() || this.saving());
  readonly showForm = signal(false);
  readonly editing = signal<number | null>(null);
  readonly resetTarget = signal<UsuarioDetalle | null>(null);
  readonly listError = signal('');
  readonly actionError = signal('');
  readonly success = signal('');
  readonly page = computed(() => Math.floor(this.offset() / this.limit) + 1);
  readonly pages = computed(() => Math.max(1, Math.ceil(this.total() / this.limit)));

  constructor() {
    this.load();
  }

  load(offset = this.offset()): void {
    if (this.busy()) return;
    this.loading.set(true);
    this.listError.set('');
    this.api
      .list(offset, this.limit)
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
        error: (error) => {
          this.loading.set(false);
          this.listError.set(this.errorMessage(error));
        },
      });
  }

  nuevo(): void {
    if (this.busy()) return;
    this.form.reset();
    this.editing.set(null);
    this.showForm.set(true);
    this.resetTarget.set(null);
    this.actionError.set('');
    this.success.set('');
  }

  editar(usuario: UsuarioDetalle): void {
    if (this.busy()) return;
    this.loading.set(true);
    this.actionError.set('');
    this.success.set('');
    this.resetTarget.set(null);
    this.api
      .get(usuario.id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (data) => {
          this.loading.set(false);
          this.editing.set(data.id);
          this.form.reset({
            documento: data.documento,
            nombre: data.nombre,
            usuario: data.usuario,
            telefono: data.telefono ?? '',
            correo: data.correo ?? '',
            direccion: data.direccion ?? '',
            password: '',
          });
          this.showForm.set(true);
        },
        error: (error) => {
          this.loading.set(false);
          this.actionError.set(this.errorMessage(error));
        },
      });
  }

  cancelar(): void {
    if (this.busy()) return;
    this.showForm.set(false);
    this.actionError.set('');
  }

  fieldError(field: Field): string {
    const control = this.form.controls[field];
    if (!control.touched || !control.errors) return '';
    if (control.errors['server']) return String(control.errors['server']);
    if (control.errors['required']) return 'Este campo es obligatorio y no puede estar vacío.';
    if (control.errors['minlength']) return 'La contraseña debe tener al menos 8 caracteres.';
    return 'Revisa este campo.';
  }

  save(): void {
    if (this.busy()) return;
    this.form.markAllAsTouched();
    if (this.form.invalid) {
      this.actionError.set('Revisa los campos señalados antes de guardar el usuario.');
      return;
    }
    const value = this.form.getRawValue();
    const id = this.editing();
    const password = value.password.trim();
    if (id === null && password.length < 8) {
      this.actionError.set('La contraseña inicial debe tener al menos 8 caracteres.');
      this.form.controls.password.markAsTouched();
      return;
    }
    const opcionales = {
      telefono: value.telefono.trim() || undefined,
      correo: value.correo.trim() || undefined,
      direccion: value.direccion.trim() || undefined,
    };
    this.saving.set(true);
    this.actionError.set('');
    this.success.set('');
    const request =
      id === null
        ? this.api.create({
            documento: value.documento.trim(),
            nombre: value.nombre.trim(),
            usuario: value.usuario.trim().toLowerCase(),
            password,
            ...opcionales,
          } satisfies UsuarioCrear)
        : this.api.update(id, {
            documento: value.documento.trim(),
            nombre: value.nombre.trim(),
            usuario: value.usuario.trim().toLowerCase(),
            ...opcionales,
          } satisfies UsuarioActualizar);
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (usuario) => {
        this.saving.set(false);
        this.showForm.set(false);
        this.success.set(
          `Usuario ${usuario.usuario} ${id === null ? 'registrado' : 'actualizado'} correctamente.`,
        );
        this.load();
      },
      error: (error: HttpErrorResponse) => {
        this.saving.set(false);
        this.actionError.set(this.errorMessage(error));
        const body = error.error as ErrorApi | null;
        if (error.status === 422 && Array.isArray(body?.detail)) {
          for (const issue of body.detail) {
            const field = issue.loc.at(-1);
            if (typeof field === 'string' && Object.hasOwn(this.form.controls, field)) {
              this.form.controls[field as Field].setErrors({
                server: 'El servicio rechazó este valor. Revisa el campo.',
              });
              this.form.controls[field as Field].markAsTouched();
            }
          }
        }
      },
    });
  }

  cambiarEstado(usuario: UsuarioDetalle): void {
    if (this.busy()) return;
    this.saving.set(true);
    this.actionError.set('');
    this.success.set('');
    this.api
      .cambiarEstado(usuario.id, !usuario.activo)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (actualizado) => {
          this.saving.set(false);
          this.success.set(
            `Usuario ${actualizado.usuario} ${actualizado.activo ? 'activado' : 'desactivado'} correctamente.`,
          );
          this.load();
        },
        error: (error) => {
          this.saving.set(false);
          this.actionError.set(this.errorMessage(error));
        },
      });
  }

  pedirReset(usuario: UsuarioDetalle): void {
    if (this.busy()) return;
    this.showForm.set(false);
    this.resetTarget.set(usuario);
    this.resetForm.reset();
    this.actionError.set('');
    this.success.set('');
  }

  cancelarReset(): void {
    if (this.busy()) return;
    this.resetTarget.set(null);
    this.actionError.set('');
  }

  resetPassword(): void {
    const usuario = this.resetTarget();
    if (!usuario || this.busy()) return;
    this.resetForm.markAllAsTouched();
    if (this.resetForm.invalid) {
      this.actionError.set('La contraseña debe tener al menos 8 caracteres.');
      return;
    }
    this.saving.set(true);
    this.actionError.set('');
    this.success.set('');
    this.api
      .restablecerPassword(usuario.id, this.resetForm.getRawValue().password)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (actualizado) => {
          this.saving.set(false);
          this.resetTarget.set(null);
          this.success.set(
            `Contraseña de ${actualizado.usuario} restablecida. Compártela por un canal seguro.`,
          );
        },
        error: (error) => {
          this.saving.set(false);
          this.actionError.set(this.errorMessage(error));
        },
      });
  }

  private errorMessage(error: HttpErrorResponse): string {
    if (error.status === 404) return 'El usuario ya no existe. Actualiza el listado.';
    if (error.status === 409)
      return 'El documento o el nombre de usuario ya están registrados.';
    if (error.status === 422)
      return 'Revisa los datos: hay campos que no cumplen las validaciones.';
    return 'No se pudo conectar con el servicio. Comprueba la conexión y actualiza el listado antes de reintentar.';
  }
}
