import { Component, computed, inject, signal } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { SesionUsuario } from './services/sesion-usuario.service';

@Component({
  selector: 'app-root',
  imports: [RouterLink, RouterLinkActive, RouterOutlet],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  private readonly sesion = inject(SesionUsuario);
  private readonly router = inject(Router);
  readonly usuario = this.sesion.usuario;
  readonly administrador = this.sesion.administrador;
  readonly rol = computed(() => (this.administrador() ? 'Administrador' : 'Operador'));
  readonly menuAbierto = signal(false);

  alternarMenu(): void {
    this.menuAbierto.update((abierto) => !abierto);
  }

  cerrarMenu(): void {
    this.menuAbierto.set(false);
  }

  cerrarSesion(): void {
    this.cerrarMenu();
    this.sesion.cerrar();
    void this.router.navigate(['/login']);
  }
}
