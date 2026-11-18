export const TIPOS_CELDA = ['AUTO', 'MOTO'] as const;
export type TipoCelda = (typeof TIPOS_CELDA)[number];

export interface CeldaCrear {
  codigo: string;
  tipo: TipoCelda;
}
export type CeldaActualizar = Partial<CeldaCrear>;
export interface Celda extends CeldaCrear {
  id: number;
  activa: boolean;
}
export interface CeldasPagina {
  items: Celda[];
  total: number;
  offset: number;
  limit: number;
}

/** S5: el estado se calcula en el backend, nunca se guarda. */
export type EstadoCelda = 'DISPONIBLE' | 'OCUPADA' | 'MANTENIMIENTO';

export interface CeldaDisponible {
  id: number;
  codigo: string;
  tipo: TipoCelda;
  activa: boolean;
  estado: EstadoCelda;
  placa: string | null;
}
export interface CupoTipo {
  total: number;
  libres: number;
}
export interface Disponibilidad {
  celdas: CeldaDisponible[];
  cupo: Record<TipoCelda, CupoTipo>;
}
