import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { SesionUsuario } from '../services/sesion-usuario.service';
import { Login } from './login';

const USUARIO = {
  id: 1,
  documento: '1001',
  nombre: 'Ana Gómez',
  telefono: '3001234567',
  usuario: 'ana.gomez',
  rol: 'OPERADOR' as const,
  activo: true,
  correo: null,
  direccion: null,
};

describe('Inicio de sesión', () => {
  let http: HttpTestingController;

  beforeEach(async () => {
    sessionStorage.clear();
    await TestBed.configureTestingModule({
      imports: [Login],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
    sessionStorage.clear();
  });

  function crear() {
    const fixture = TestBed.createComponent(Login);
    fixture.detectChanges();
    return fixture;
  }

  function completar(fixture: ReturnType<typeof crear>, usuario: string, password: string) {
    fixture.componentInstance.form.setValue({ usuario, password });
  }

  it('exige usuario y contraseña antes de llamar a la API', () => {
    const fixture = crear();

    fixture.componentInstance.enviar();

    expect(fixture.componentInstance.error()).toContain('usuario y contraseña');
    http.expectNone('/auth/login');
  });

  it('inicia sesión, guarda el token y navega al tablero', () => {
    const fixture = crear();
    const router = TestBed.inject(Router);
    const navegar = vi.spyOn(router, 'navigateByUrl').mockResolvedValue(true);
    completar(fixture, 'ana.gomez', 'Parkeo2026*');

    fixture.componentInstance.enviar();

    const peticion = http.expectOne('/auth/login');
    expect(peticion.request.method).toBe('POST');
    expect(peticion.request.body).toEqual({ usuario: 'ana.gomez', password: 'Parkeo2026*' });
    peticion.flush({ access_token: 'token-de-prueba', token_type: 'bearer', usuario: USUARIO });

    const sesion = TestBed.inject(SesionUsuario);
    expect(sesion.autenticado()).toBe(true);
    expect(sesion.usuario()?.nombre).toBe('Ana Gómez');
    expect(sesion.token()).toBe('token-de-prueba');
    expect(sessionStorage.getItem('parkeo.sesion')).toContain('token-de-prueba');
    expect(navegar).toHaveBeenCalledWith('/tablero');
  });

  it('muestra el error de credenciales sin crear sesión', () => {
    const fixture = crear();
    completar(fixture, 'ana.gomez', 'ClaveIncorrecta1');

    fixture.componentInstance.enviar();
    http
      .expectOne('/auth/login')
      .flush({ detail: 'Credenciales inválidas.' }, { status: 401, statusText: 'Unauthorized' });

    expect(fixture.componentInstance.error()).toBe('Usuario o contraseña incorrectos.');
    expect(TestBed.inject(SesionUsuario).autenticado()).toBe(false);
    expect(fixture.componentInstance.enviando()).toBe(false);
  });

  it('distingue una cuenta inactiva y los fallos de conexión', () => {
    const fixture = crear();
    completar(fixture, 'ana.gomez', 'Parkeo2026*');

    fixture.componentInstance.enviar();
    http
      .expectOne('/auth/login')
      .flush({ detail: 'Cuenta inactiva.' }, { status: 403, statusText: 'Forbidden' });
    expect(fixture.componentInstance.error()).toContain('inactiva');

    fixture.componentInstance.enviar();
    http.expectOne('/auth/login').error(new ProgressEvent('error'));
    expect(fixture.componentInstance.error()).toContain('No se pudo conectar');
  });
});
