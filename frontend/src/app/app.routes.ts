import { Routes } from '@angular/router';
import { sesionActiva, soloAdministrador } from './guards/sesion.guard';

export const routes: Routes = [
  {
    path: 'login',
    title: 'Iniciar sesión | Parkeo',
    loadComponent: () => import('./login/login').then((m) => m.Login),
  },
  {
    path: 'tablero',
    title: 'Tablero | Parkeo',
    canActivate: [sesionActiva],
    loadComponent: () => import('./tablero/tablero').then((m) => m.Tablero),
  },
  {
    path: 'control-acceso',
    title: 'Registrar entrada | Parkeo',
    canActivate: [sesionActiva],
    loadComponent: () => import('./control-acceso/control-acceso').then((m) => m.ControlAcceso),
  },
  {
    path: 'salida',
    title: 'Registrar salida | Parkeo',
    canActivate: [sesionActiva],
    loadComponent: () =>
      import('./registrar-salida/registrar-salida').then((m) => m.RegistrarSalida),
  },
  {
    path: 'cambiar-celda',
    title: 'Cambiar celda | Parkeo',
    canActivate: [sesionActiva],
    loadComponent: () => import('./cambiar-celda/cambiar-celda').then((m) => m.CambiarCelda),
  },
  {
    path: 'gestion/celdas',
    title: 'Celdas | Parkeo',
    canActivate: [sesionActiva, soloAdministrador],
    loadComponent: () => import('./celdas/celdas').then((m) => m.Celdas),
  },
  {
    path: 'gestion/usuarios',
    title: 'Usuarios | Parkeo',
    canActivate: [sesionActiva, soloAdministrador],
    loadComponent: () => import('./usuarios/usuarios').then((m) => m.Usuarios),
  },
  {
    path: '',
    pathMatch: 'full',
    title: 'Inicio | Parkeo',
    canActivate: [sesionActiva],
    loadComponent: () => import('./panel/panel').then((m) => m.Panel),
  },
  {
    path: 'gestion/vehiculos',
    title: 'Vehículos | Parkeo',
    canActivate: [sesionActiva],
    loadComponent: () => import('./vehiculos/vehiculos').then((m) => m.Vehiculos),
  },
  { path: '**', redirectTo: '' },
];
