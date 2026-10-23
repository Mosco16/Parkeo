import { Celda } from './celda';
import { Vehiculo } from './vehiculo';

export interface EntradaCrear {
  placa: string;
  operador_id: number;
}
export interface CambioCeldaCrear {
  placa: string;
  celda_id: number;
}
export interface SalidaCrear {
  placa: string;
  operador_id: number;
}
export interface Estancia {
  id: number;
  vehiculo_id: number;
  celda_id: number;
  entrada: string;
  salida: string | null;
  operador_entrada_id: number;
  operador_salida_id: number | null;
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
