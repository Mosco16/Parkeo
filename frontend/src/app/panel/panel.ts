import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { CeldaDisponible, EstadoCelda } from '../models/celda';
import { ApiService } from '../services/api.service';
import { CeldasService } from '../services/celdas.service';
import { SesionUsuario } from '../services/sesion-usuario.service';

interface GrupoCeldas {
  tipo: 'AUTO' | 'MOTO';
  titulo: string;
  celdas: CeldaDisponible[];
}

@Component({
  selector: 'app-panel',
  imports: [RouterLink],
  templateUrl: './panel.html',
  styleUrl: './panel.css',
})
export class Panel {
  private readonly celdasApi = inject(CeldasService);
  private readonly api = inject(ApiService);
  private readonly sesion = inject(SesionUsuario);
  private readonly destroy = inject(DestroyRef);

  readonly usuario = this.sesion.usuario;
  readonly administrador = this.sesion.administrador;
  readonly celdas = signal<CeldaDisponible[]>([]);
  readonly cargando = signal(false);
  readonly error = signal('');
  readonly servicio = signal<'comprobando' | 'disponible' | 'sin-conexion'>('comprobando');

  readonly kpis = computed(() => {
    const celdas = this.celdas();
    const contar = (estado: EstadoCelda) => celdas.filter((c) => c.estado === estado).length;
    const total = celdas.length;
    const ocupadas = contar('OCUPADA');
    return {
      total,
      ocupadas,
      disponibles: contar('DISPONIBLE'),
      mantenimiento: contar('MANTENIMIENTO'),
      ocupacion: total ? Math.round((ocupadas / total) * 100) : 0,
    };
  });

  readonly grupos = computed<GrupoCeldas[]>(() => {
    const celdas = this.celdas();
    return [
      {
        tipo: 'AUTO',
        titulo: 'Automóviles',
        celdas: celdas.filter((c) => c.tipo === 'AUTO'),
      },
      { tipo: 'MOTO', titulo: 'Motos', celdas: celdas.filter((c) => c.tipo === 'MOTO') },
    ];
  });

  readonly servicioTexto = computed(() => {
    switch (this.servicio()) {
      case 'disponible':
        return 'Servicio disponible';
      case 'sin-conexion':
        return 'Sin conexión con la API';
      default:
        return 'Comprobando servicio…';
    }
  });

  constructor() {
    this.cargar();
    this.verificarServicio();
  }

  cargar(): void {
    if (this.cargando()) return;
    this.cargando.set(true);
    this.error.set('');
    this.celdasApi
      .disponibilidad()
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe({
        next: (data) => {
          this.cargando.set(false);
          this.celdas.set(data.celdas);
        },
        error: () => {
          this.cargando.set(false);
          this.celdas.set([]);
          this.error.set('No se pudo cargar el resumen. Revisa la conexión e intenta de nuevo.');
        },
      });
  }

  estadoCelda(celda: CeldaDisponible): string {
    switch (celda.estado) {
      case 'OCUPADA':
        return celda.placa ? `Ocupada por ${celda.placa}` : 'Ocupada';
      case 'MANTENIMIENTO':
        return 'En mantenimiento';
      default:
        return 'Disponible';
    }
  }

  private verificarServicio(): void {
    this.api
      .health()
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe({
        next: (respuesta) =>
          this.servicio.set(respuesta?.status === 'ok' ? 'disponible' : 'sin-conexion'),
        error: () => this.servicio.set('sin-conexion'),
      });
  }
}
