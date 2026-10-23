import { TestBed } from '@angular/core/testing';
import { SesionOperador } from './sesion-operador.service';

describe('SesionOperador', () => {
  beforeEach(() => sessionStorage.clear());

  it('guarda, recupera y cierra el operador activo', () => {
    const sesion = TestBed.inject(SesionOperador);
    expect(sesion.operador()).toBeNull();

    sesion.iniciar({ id: 4, nombre: 'Ana', telefono: '001' });
    expect(sesion.operador()?.nombre).toBe('Ana');
    expect(JSON.parse(sessionStorage.getItem('autos-colombia.operador')!)).toEqual({
      id: 4,
      nombre: 'Ana',
      telefono: '001',
    });

    sesion.cerrar();
    expect(sesion.operador()).toBeNull();
    expect(sessionStorage.getItem('autos-colombia.operador')).toBeNull();
  });

  it('funciona aunque el almacenamiento falle', () => {
    const guardar = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('sin almacenamiento');
    });
    const sesion = TestBed.inject(SesionOperador);
    expect(() => sesion.iniciar({ id: 5, nombre: 'Luis', telefono: '' })).not.toThrow();
    expect(sesion.operador()?.id).toBe(5);
    guardar.mockRestore();
  });

  it('ignora un contenido inválido en la sesión', () => {
    sessionStorage.setItem('autos-colombia.operador', '{"id":"x"}');
    const sesion = TestBed.inject(SesionOperador);
    expect(sesion.operador()).toBeNull();
  });
});
