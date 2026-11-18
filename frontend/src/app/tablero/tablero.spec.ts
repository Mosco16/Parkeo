import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Tablero } from './tablero';

describe('Tablero', () => {
  let fixture: ComponentFixture<Tablero>;
  let http: HttpTestingController;
  const celdas = [
    { id: 1, codigo: 'A1', tipo: 'AUTO', activa: true, estado: 'DISPONIBLE', placa: null },
    { id: 2, codigo: 'A2', tipo: 'AUTO', activa: true, estado: 'OCUPADA', placa: 'ABC123' },
    { id: 3, codigo: 'M1', tipo: 'MOTO', activa: false, estado: 'MANTENIMIENTO', placa: null },
  ];
  const cupo = {
    AUTO: { total: 70, libres: 69 },
    MOTO: { total: 10, libres: 10 },
  };
  const vehiculo = {
    id: 1,
    placa: 'ABC123',
    marca: 'Renault',
    color: 'Azul',
    modelo: 2026,
    tipo: 'AUTOMOVIL' as const,
    fecha_vencimiento: '2027-01-31',
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Tablero],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(Tablero);
    fixture.detectChanges();
  });

  afterEach(() => http.verify());

  function tablero() {
    http.expectOne('/celdas/disponibilidad').flush({ celdas, cupo });
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  it('muestra las celdas, el cupo por tipo y distingue las ocupadas por texto', () => {
    const root = tablero();
    expect(root.querySelectorAll('.cell').length).toBe(3);
    expect(root.querySelectorAll('.cell.taken').length).toBe(1);
    expect(root.querySelector('.cell.taken')?.textContent).toContain('Ocupada');
    expect(root.querySelector('.cell.taken')?.textContent).toContain('ABC123');
    expect(root.querySelectorAll('.cell.maintenance').length).toBe(1);
    expect(root.textContent).toContain('Autos: 69 libres de 70');
    expect(root.textContent).toContain('Motos: 10 libres de 10');
  });

  it('consulta una placa y muestra DENTRO y la mensualidad', () => {
    tablero();
    const c = fixture.componentInstance;
    c.consulta.controls.placa.setValue(' abc123 ');
    c.buscar();
    http.expectOne('/estancias/vehiculo/ABC123').flush({
      vehiculo,
      esta_dentro: true,
      estancia: null,
      mensualidad: 'VENCIDA',
      celda_sugerida: null,
    });
    fixture.detectChanges();
    const texto = (fixture.nativeElement as HTMLElement).textContent;
    expect(texto).toContain('DENTRO');
    expect(texto).toContain('VENCIDA');
  });

  it('informa el error de carga y permite actualizar', () => {
    http
      .expectOne('/celdas/disponibilidad')
      .error(new ProgressEvent('error'));
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('No se pudo cargar');

    fixture.componentInstance.cargar();
    const root = tablero();
    expect(root.querySelectorAll('.cell').length).toBe(3);
  });
});
