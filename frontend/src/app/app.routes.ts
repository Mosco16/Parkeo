import { Routes } from '@angular/router';
import { operadorActivo } from './guards/operador.guard';

export const routes: Routes = [
  {
    path: 'operador',
    title: 'Iniciar turno | Autos Colombia',
    loadComponent: () =>
      import('./seleccion-operador/seleccion-operador').then((m) => m.SeleccionOperador),
  },
  {
    path: 'control-acceso',
    title: 'Registrar entrada | Autos Colombia',
    canActivate: [operadorActivo],
    loadComponent: () => import('./control-acceso/control-acceso').then((m) => m.ControlAcceso),
  },
  {
    path: 'gestion/operadores',
    title: 'Operadores | Autos Colombia',
    loadComponent: () => import('./operadores/operadores').then((m) => m.Operadores),
  },
  {
    path: 'gestion/celdas',
    title: 'Celdas | Autos Colombia',
    loadComponent: () => import('./celdas/celdas').then((m) => m.Celdas),
  },
  { path: '', pathMatch: 'full', loadComponent: () => import('./home/home').then((m) => m.Home) },
  {
    path: 'gestion/vehiculos',
    title: 'Vehículos | Autos Colombia',
    loadComponent: () => import('./vehiculos/vehiculos').then((m) => m.Vehiculos),
  },
  { path: '**', redirectTo: '' },
];
