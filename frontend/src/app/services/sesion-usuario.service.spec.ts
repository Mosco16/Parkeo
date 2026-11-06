import { TestBed } from '@angular/core/testing';
import { SesionUsuario } from './sesion-usuario.service';

const USUARIO = {
  id: 1,
  documento: '1001',
  nombre: 'Ana Gómez',
  telefono: null,
  usuario: 'ana.gomez',
  rol: 'OPERADOR' as const,
  activo: true,
  correo: null,
  direccion: null,
};

describe('Sesión de usuario', () => {
  beforeEach(() => sessionStorage.clear());
  afterEach(() => sessionStorage.clear());

  it('inicia y cierra la sesión en sessionStorage', () => {
    const sesion = TestBed.inject(SesionUsuario);

    sesion.iniciar({ access_token: 'token', token_type: 'bearer', usuario: USUARIO });

    expect(sesion.autenticado()).toBe(true);
    expect(sesion.usuario()?.usuario).toBe('ana.gomez');
    expect(sesion.administrador()).toBe(false);
    expect(sessionStorage.getItem('parkeo.sesion')).toContain('token');

    sesion.cerrar();
    expect(sesion.autenticado()).toBe(false);
    expect(sessionStorage.getItem('parkeo.sesion')).toBeNull();
  });

  it('reconoce al administrador por su rol', () => {
    const sesion = TestBed.inject(SesionUsuario);
    sesion.iniciar({
      access_token: 'token',
      token_type: 'bearer',
      usuario: { ...USUARIO, rol: 'ADMINISTRADOR' },
    });

    expect(sesion.administrador()).toBe(true);
  });

  it('descarta una sesión guardada con datos incompletos', () => {
    sessionStorage.setItem('parkeo.sesion', JSON.stringify({ access_token: 'token' }));

    expect(TestBed.inject(SesionUsuario).autenticado()).toBe(false);
  });

  it('ignora un almacenamiento corrupto', () => {
    sessionStorage.setItem('parkeo.sesion', '{roto');

    expect(TestBed.inject(SesionUsuario).autenticado()).toBe(false);
  });
});
