export const MOTIVOS_ANULACION = [
  'Error de digitación',
  'Valor incorrecto',
  'Pago duplicado',
  'Recibo no válido',
  'Otro',
] as const;
export type MotivoAnulacion = (typeof MOTIVOS_ANULACION)[number];

export type EstadoPago = 'ACTIVO' | 'ANULADO';

/** RN-PAG-01 y RN-PAG-04: el operador solo digita placa y referencia. */
export interface PagoCrear {
  placa: string;
  referencia: string;
  /** Correo para los avisos; opcional. */
  correo?: string | null;
  autorizar_avisos?: boolean | null;
}

export interface PagoAnular {
  motivo: MotivoAnulacion;
}

export interface Pago {
  id: number;
  placa: string;
  valor: number;
  referencia: string;
  fecha_hora: string;
  dia_corte: number;
  inicio_ciclo: string;
  vencimiento_ciclo: string;
  estado: EstadoPago;
  motivo_anulacion: string | null;
  anulacion_fecha_hora: string | null;
  usuario: string;
}

export interface PagosPagina {
  items: Pago[];
  total: number;
  pagina: number;
  tamano: number;
}
