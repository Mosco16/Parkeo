import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Historial } from './historial';

describe('Historial de cambios de celda', () => {
  let fixture: ComponentFixture<Historial>;
  let http: HttpTestingController;
  const cambio = {
    id: 7,
    fecha_hora: '2026-11-05T15:30:00Z',
    placa: 'ABC123',
    celda_anterior: 'A1',
    celda_nueva: 'A2',
    usuario: 'Ana Gómez',
  };
  const page = { items: [cambio], total: 1, offset: 0, limit: 10 };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Historial],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(Historial);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Cargando historial');
    http.expectOne('/estancias/historial-cambios?offset=0&limit=10').flush(page);
    fixture.detectChanges();
  });
  afterEach(() => http.verify());

  it('muestra la tabla con fecha, placa, celdas y usuario', () => {
    const root = fixture.nativeElement as HTMLElement;
    const fila = root.querySelector('tbody tr');

    expect(fila?.textContent).toContain('ABC123');
    expect(fila?.textContent).toContain('A1');
    expect(fila?.textContent).toContain('A2');
    expect(fila?.textContent).toContain('Ana Gómez');
    expect(fila?.textContent).toContain('2026');
    expect(root.textContent).toContain('Página 1 de 1');
  });

  it('pagina hacia adelante y hacia atrás', () => {
    const c = fixture.componentInstance;
    c.load(10);
    http
      .expectOne('/estancias/historial-cambios?offset=10&limit=10')
      .flush({ ...page, offset: 10, total: 12 });
    expect(c.page()).toBe(2);

    c.load(0);
    http.expectOne('/estancias/historial-cambios?offset=0&limit=10').flush({ ...page, total: 12 });
    expect(c.page()).toBe(1);
  });

  it('vuelve a la última página si el offset queda fuera de rango', () => {
    const c = fixture.componentInstance;
    c.load(50);
    http
      .expectOne('/estancias/historial-cambios?offset=50&limit=10')
      .flush({ items: [], total: 12, offset: 50, limit: 10 });
    const reintento = http.expectOne('/estancias/historial-cambios?offset=10&limit=10');
    reintento.flush({ ...page, offset: 10, total: 12 });

    expect(c.offset()).toBe(10);
    expect(c.items().length).toBe(1);
  });

  it('muestra el estado vacío cuando no hay cambios', () => {
    const c = fixture.componentInstance;
    c.load();
    http.expectOne('/estancias/historial-cambios?offset=0&limit=10').flush({
      items: [],
      total: 0,
      offset: 0,
      limit: 10,
    });
    fixture.detectChanges();

    const root = fixture.nativeElement as HTMLElement;
    expect(root.textContent).toContain('Aún no hay cambios registrados');
    expect(root.querySelector('table')).toBeNull();
  });

  it('informa el fallo de conexión y permite reintentar', () => {
    const c = fixture.componentInstance;
    c.load();
    http
      .expectOne('/estancias/historial-cambios?offset=0&limit=10')
      .error(new ProgressEvent('error'));
    fixture.detectChanges();

    expect(c.listError()).toContain('No se pudo cargar el historial');
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Reintentar');

    c.load();
    http.expectOne('/estancias/historial-cambios?offset=0&limit=10').flush(page);
    expect(c.listError()).toBe('');
  });
});
