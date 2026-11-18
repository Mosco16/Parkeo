export const TIPOS_VEHICULO = ['MOTO', 'AUTOMOVIL', 'CAMIONETA'] as const;
export type TipoVehiculo = (typeof TIPOS_VEHICULO)[number];
export type Mensualidad = 'VIGENTE' | 'VENCIDA';
export interface VehiculoCrear {
  placa: string;
  color: string;
  modelo: number;
  marca: string;
  tipo: TipoVehiculo;
  /** Correo para los avisos de vencimiento; opcional. */
  correo?: string | null;
}
export type VehiculoActualizar = Partial<VehiculoCrear>;
export interface Vehiculo extends Omit<VehiculoCrear, 'correo'> {
  id: number;
  correo: string | null;
  avisos_autorizados: boolean;
  /** Derivada de los pagos activos: solo lectura (RN-VIG-01). */
  fecha_vencimiento: string | null;
  mensualidad: Mensualidad;
}
export interface VehiculosPagina {
  items: Vehiculo[];
  total: number;
  offset: number;
  limit: number;
}
export interface ErrorValidacion {
  loc: (string | number)[];
  msg: string;
  type: string;
}
export interface ErrorApi {
  detail?: string | ErrorValidacion[];
}
