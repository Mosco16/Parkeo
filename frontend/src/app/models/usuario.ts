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

export interface LoginCrear {
  usuario: string;
  password: string;
}

export interface SesionRespuesta {
  access_token: string;
  token_type: 'bearer';
  usuario: Usuario;
}
