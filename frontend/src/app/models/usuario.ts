export type Rol = 'ADMINISTRADOR' | 'OPERADOR';

export interface Usuario {
  id: number;
  documento: string;
  nombre: string;
  telefono: string | null;
  usuario: string;
  rol: Rol;
  activo: boolean;
  correo: string | null;
  direccion: string | null;
}

/** S4: cuenta que se crea desde la aplicación; el rol lo asigna el servicio. */
export interface UsuarioCrear {
  documento: string;
  nombre: string;
  telefono?: string | null;
  usuario: string;
  password: string;
  correo?: string | null;
  direccion?: string | null;
}

export interface UsuarioActualizar {
  documento?: string;
  nombre?: string;
  telefono?: string;
  usuario?: string;
  correo?: string;
  direccion?: string;
}

export interface UsuarioDetalle extends Usuario {
  creado_en: string;
  actualizado_en: string;
}

export interface UsuariosPagina {
  items: UsuarioDetalle[];
  total: number;
  offset: number;
  limit: number;
}

export interface LoginCrear {
  usuario: string;
  password: string;
}

export interface SesionRespuesta {
  access_token: string;
  token_type: 'bearer';
  usuario: Usuario;
}
