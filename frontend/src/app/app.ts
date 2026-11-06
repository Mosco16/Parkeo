import { Component, inject } from '@angular/core';
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

  cerrarSesion(): void {
    this.sesion.cerrar();
    void this.router.navigate(['/login']);
  }
}
