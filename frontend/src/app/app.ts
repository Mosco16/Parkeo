import { Component, inject } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { SesionOperador } from './services/sesion-operador.service';

@Component({
  selector: 'app-root',
  imports: [RouterLink, RouterLinkActive, RouterOutlet],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  private readonly sesion = inject(SesionOperador);
  private readonly router = inject(Router);
  readonly operador = this.sesion.operador;

  cambiarOperador(): void {
    this.sesion.cerrar();
    void this.router.navigate(['/operador']);
  }
}
