import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Celdas } from './celdas';

describe('Gestión de celdas', () => {
  let fixture: ComponentFixture<Celdas>;
  let http: HttpTestingController;

  const celdas = [
    { id: 1, codigo: 'A1', tipo: 'AUTO', activa: true, estado: 'DISPONIBLE', placa: null },
    { id: 2, codigo: 'A2', tipo: 'AUTO', activa: true, estado: 'OCUPADA', placa: 'ABC123' },
    { id: 3, codigo: 'A3', tipo: 'AUTO', activa: false, estado: 'MANTENIMIENTO', placa: null },
    { id: 4, codigo: 'M1', tipo: 'MOTO', activa: true, estado: 'DISPONIBLE', placa: null },
  ] as const;
  const disponibilidad = {
    celdas,
    cupo: { AUTO: { total: 3, libres: 1 }, MOTO: { total: 1, libres: 1 } },
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Celdas],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(Celdas);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Cargando celdas');
    http.expectOne('/celdas/disponibilidad').flush(disponibilidad);
    fixture.detectChanges();
  });
  afterEach(() => http.verify());

  it('muestra el resumen y agrupa las celdas por tipo con su estado', () => {
    const root = fixture.nativeElement as HTMLElement;

    expect(root.textContent).toContain('4 total');
    expect(root.textContent).toContain('2 disponibles');
    expect(root.textContent).toContain('1 ocupadas');
    expect(root.textContent).toContain('1 en mantenimiento');
    expect(root.querySelectorAll('.panel').length).toBe(2);
    expect(root.querySelectorAll('.cell').length).toBe(4);
    expect(root.querySelector('.cell.ocupada')?.textContent).toContain('ABC123');
    expect(root.querySelector('.cell.mantenimiento')?.textContent).toContain('Mantenimiento');
  });

  it('pone una celda disponible en mantenimiento y recarga el mapa', () => {
    const c = fixture.componentInstance;
    c.alternar(celdas[0]);
    const request = http.expectOne({ method: 'PATCH', url: '/celdas/1/estado' });
    expect(request.request.body).toEqual({ activa: false });
    request.flush({ ...celdas[0], activa: false });
    http.expectOne('/celdas/disponibilidad').flush(disponibilidad);
    expect(c.success()).toContain('en mantenimiento');
  });

  it('habilita una celda en mantenimiento', () => {
    const c = fixture.componentInstance;
    c.alternar(celdas[2]);
    const request = http.expectOne({ method: 'PATCH', url: '/celdas/3/estado' });
    expect(request.request.body).toEqual({ activa: true });
    request.flush({ ...celdas[2], activa: true });
    http.expectOne('/celdas/disponibilidad').flush(disponibilidad);
    expect(c.success()).toContain('habilitada');
  });

  it('no permite apagar una celda ocupada', () => {
    const root = fixture.nativeElement as HTMLElement;
    const botones = root.querySelectorAll<HTMLButtonElement>('.cell button');

    expect(botones[1].disabled).toBe(true);
    expect(botones[1].textContent).toContain('Mantenimiento');
    expect(fixture.componentInstance.puedeAlternar(celdas[1])).toBe(false);
    http.expectNone({ method: 'PATCH', url: '/celdas/2/estado' });
  });

  it('informa el conflicto del servicio al apagar una celda con estancia', () => {
    const c = fixture.componentInstance;
    c.alternar(celdas[0]);
    http
      .expectOne({ method: 'PATCH', url: '/celdas/1/estado' })
      .flush({ detail: 'ocupada' }, { status: 409, statusText: 'Conflict' });

    expect(c.actionError()).toContain('estancia abierta');
    expect(c.busy()).toBe(false);
  });

  it('muestra el fallo de conexión y permite reintentar', () => {
    const c = fixture.componentInstance;
    c.load();
    http.expectOne('/celdas/disponibilidad').error(new ProgressEvent('error'));

    expect(c.listError()).toContain('No se pudo conectar');
    expect(c.celdas().length).toBe(0);

    c.load();
    http.expectOne('/celdas/disponibilidad').flush(disponibilidad);
    expect(c.celdas().length).toBe(4);
  });
});
