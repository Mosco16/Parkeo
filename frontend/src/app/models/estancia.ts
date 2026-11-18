import { Celda } from './celda';
import { Vehiculo } from './vehiculo';

export interface EntradaCrear {
  placa: string;
}
export interface CambioCeldaCrear {
  placa: string;
  celda_id: number;
}
export interface SalidaCrear {
  placa: string;
}
export interface Estancia {
  id: number;
  vehiculo_id: number;
  celda_id: number;
  entrada: string;
  salida: string | null;
  usuario_entrada_id: number;
  usuario_salida_id: number | null;
}
export interface EstanciaAbierta extends Estancia {
  celda: Celda;
}
export interface EstadoVehiculo {
  vehiculo: Vehiculo;
  esta_dentro: boolean;
  estancia: EstanciaAbierta | null;
  mensualidad: 'VIGENTE' | 'VENCIDA';
  celda_sugerida: Celda | null;
}

/** S6: fila de solo lectura del historial de cambios de celda. */
export interface CambioCeldaHistorial {
  id: number;
  fecha_hora: string;
  placa: string;
  celda_anterior: string;
  celda_nueva: string;
  usuario: string;
}

export interface HistorialCambiosPagina {
  items: CambioCeldaHistorial[];
  total: number;
  offset: number;
  limit: number;
}
