import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { App } from './app';
import { SesionUsuario } from './services/sesion-usuario.service';

const USUARIO = {
  id: 1,
  documento: '1001',
  nombre: 'Ana Gómez',
  telefono: null,
  usuario: 'ana.gomez',
  rol: 'ADMINISTRADOR' as const,
  activo: true,
  correo: null,
  direccion: null,
};

describe('Navegación', () => {
  beforeEach(async () => {
    sessionStorage.clear();
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [provideRouter([])],
    }).compileComponents();
  });
  afterEach(() => sessionStorage.clear());

  function crear() {
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();
    return fixture;
  }

  it('ofrece iniciar sesión cuando no hay usuario', () => {
    const fixture = crear();
    expect(
      (fixture.nativeElement as HTMLElement).querySelector('a[href="/login"]')?.textContent,
    ).toBe('Iniciar sesión');
  });

  it('muestra al usuario de la sesión y permite cerrarla', () => {
    TestBed.inject(SesionUsuario).iniciar({
      access_token: 'token',
      token_type: 'bearer',
      usuario: USUARIO,
    });
    const fixture = crear();
    const elemento = fixture.nativeElement as HTMLElement;

    expect(elemento.textContent).toContain('Ana Gómez');
    expect(elemento.textContent).toContain('Administrador');
    expect(elemento.querySelector('a[href="/login"]')).toBeNull();
    expect(elemento.querySelector('a[href="/gestion/vehiculos"]')?.textContent).toBe('Vehículos');
  });
});
