import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { Panel } from './panel';
import { SesionUsuario } from '../services/sesion-usuario.service';

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

const celdas = [
  { id: 1, codigo: 'A1', tipo: 'AUTO', activa: true, estado: 'OCUPADA', placa: 'ABC123' },
  { id: 2, codigo: 'A2', tipo: 'AUTO', activa: true, estado: 'DISPONIBLE', placa: null },
  { id: 3, codigo: 'A3', tipo: 'AUTO', activa: false, estado: 'MANTENIMIENTO', placa: null },
  { id: 4, codigo: 'M1', tipo: 'MOTO', activa: true, estado: 'DISPONIBLE', placa: null },
];

describe('Panel de resumen', () => {
  let http: HttpTestingController;

  beforeEach(async () => {
    sessionStorage.clear();
    await TestBed.configureTestingModule({
      imports: [Panel],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
    sessionStorage.clear();
  });

  function crear(rol: 'ADMINISTRADOR' | 'OPERADOR' = 'ADMINISTRADOR') {
    TestBed.inject(SesionUsuario).iniciar({
      access_token: 'token',
      token_type: 'bearer',
      usuario: { ...USUARIO, rol },
    });
    const fixture = TestBed.createComponent(Panel);
    fixture.detectChanges();
    return fixture;
  }

  function responder(celdasRespuesta = celdas) {
    http.expectOne('/celdas/disponibilidad').flush({
      celdas: celdasRespuesta,
      cupo: { AUTO: { total: 3, libres: 1 }, MOTO: { total: 1, libres: 1 } },
    });
    http.expectOne('/health').flush({ status: 'ok' });
  }

  it('calcula los indicadores del parqueadero', () => {
    const fixture = crear();
    responder();
    fixture.detectChanges();

    expect(fixture.componentInstance.kpis()).toEqual({
      total: 4,
      ocupadas: 1,
      disponibles: 2,
      mantenimiento: 1,
      ocupacion: 25,
    });
    const texto = (fixture.nativeElement as HTMLElement).textContent;
    expect(texto).toContain('25% de ocupación');
  });

  it('agrupa el mapa por tipo y marca cada estado', () => {
    const fixture = crear();
    responder();
    fixture.detectChanges();
    const elemento = fixture.nativeElement as HTMLElement;

    const grupos = elemento.querySelectorAll('.grupo');
    expect(grupos.length).toBe(2);
    expect(grupos[0].textContent).toContain('Automóviles');
    expect(grupos[0].querySelectorAll('.cell').length).toBe(3);
    expect(grupos[1].querySelectorAll('.cell').length).toBe(1);
    expect(elemento.querySelectorAll('.cell.ocupada').length).toBe(1);
    expect(elemento.querySelector('.cell.ocupada')?.textContent).toContain('ABC123');
    expect(elemento.querySelectorAll('.cell.mantenimiento').length).toBe(1);
  });

  it('muestra el estado del servicio', () => {
    const fixture = crear();
    responder();
    fixture.detectChanges();

    expect((fixture.nativeElement as HTMLElement).querySelector('.service')?.textContent).toContain(
      'Servicio disponible',
    );
  });

  it('ofrece gestionar usuarios y celdas al administrador', () => {
    const fixture = crear('ADMINISTRADOR');
    responder();
    fixture.detectChanges();
    const elemento = fixture.nativeElement as HTMLElement;

    expect(elemento.querySelector('a[href="/gestion/usuarios"]')).not.toBeNull();
    expect(elemento.querySelector('a[href="/gestion/celdas"]')).not.toBeNull();
  });

  it('no ofrece la administración al operador', () => {
    const fixture = crear('OPERADOR');
    responder();
    fixture.detectChanges();
    const elemento = fixture.nativeElement as HTMLElement;

    expect(elemento.querySelector('a[href="/gestion/usuarios"]')).toBeNull();
    expect(elemento.querySelector('a[href="/gestion/celdas"]')).toBeNull();
  });

  it('informa el error al cargar y permite reintentar', () => {
    const fixture = crear();
    http.expectOne('/celdas/disponibilidad').error(new ProgressEvent('error'));
    http.expectOne('/health').flush({ status: 'ok' });
    fixture.detectChanges();

    expect((fixture.nativeElement as HTMLElement).textContent).toContain('No se pudo cargar');

    fixture.componentInstance.cargar();
    http.expectOne('/celdas/disponibilidad').flush({
      celdas,
      cupo: { AUTO: { total: 3, libres: 1 }, MOTO: { total: 1, libres: 1 } },
    });
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).querySelectorAll('.cell').length).toBe(4);
  });
});
