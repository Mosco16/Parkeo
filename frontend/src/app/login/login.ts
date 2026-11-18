import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { SesionUsuario } from '../services/sesion-usuario.service';

@Component({
  selector: 'app-login',
  imports: [ReactiveFormsModule],
  templateUrl: './login.html',
  styleUrl: './login.css',
})
export class Login {
  private readonly auth = inject(AuthService);
  private readonly sesion = inject(SesionUsuario);
  private readonly router = inject(Router);
  private readonly ruta = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);
  private readonly fb = inject(FormBuilder);

  readonly form = this.fb.nonNullable.group({
    usuario: ['', [Validators.required]],
    password: ['', [Validators.required, Validators.minLength(8)]],
  });
  readonly enviando = signal(false);
  readonly error = signal('');

  get usuario() {
    return this.form.controls.usuario;
  }

  get password() {
    return this.form.controls.password;
  }

  enviar(): void {
    if (this.enviando()) return;
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.error.set('Ingresa tu usuario y contraseña.');
      return;
    }

    this.enviando.set(true);
    this.error.set('');
    this.auth
      .login(this.form.getRawValue())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (respuesta) => {
          this.sesion.iniciar(respuesta);
          const destino = this.ruta.snapshot.queryParamMap.get('returnUrl');
          void this.router.navigateByUrl(
            destino && destino.startsWith('/') ? destino : '/tablero',
          );
        },
        error: (error: unknown) => {
          this.enviando.set(false);
          this.error.set(this.mensaje(error));
        },
      });
  }

  private mensaje(error: unknown): string {
    if (!(error instanceof HttpErrorResponse)) {
      return 'No se pudo iniciar sesión. Intenta de nuevo.';
    }
    if (error.status === 401) return 'Usuario o contraseña incorrectos.';
    if (error.status === 403) return 'La cuenta está inactiva. Contacta al administrador.';
    if (error.status === 0) {
      return 'No se pudo conectar con el servidor. Verifica que la API esté disponible.';
    }
    return 'No se pudo iniciar sesión. Intenta de nuevo.';
  }
}
