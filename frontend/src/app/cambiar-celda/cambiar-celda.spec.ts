import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { CambiarCelda } from './cambiar-celda';

describe('Cambiar celda', () => {
  let http: HttpTestingController;
  let c: CambiarCelda;
  const celdaA1 = { id: 1, codigo: 'A1', tipo: 'AUTO' as const };
  const celdaA2 = { id: 2, codigo: 'A2', tipo: 'AUTO' as const };
  const vehiculo = {
    id: 1,
    placa: 'ABC123',
    marca: 'Renault',
    color: 'Azul',
    modelo: 2026,
    tipo: 'AUTOMOVIL' as const,
    fecha_vencimiento: '2027-01-31',
  };
  const estancia = {
    id: 3,
    vehiculo_id: 1,
    celda_id: 1,
    entrada: '2026-10-19T15:00:00Z',
    salida: null,
    operador_entrada_id: 4,
    operador_salida_id: null,
    celda: celdaA1,
  };
  const dentro = {
    vehiculo,
    esta_dentro: true,
    estancia,
    mensualidad: 'VIGENTE' as const,
    celda_sugerida: null,
  };
  const celdas = [
    { ...celdaA1, estado: 'OCUPADA' as const },
    { ...celdaA2, estado: 'LIBRE' as const },
    { id: 9, codigo: 'M1', tipo: 'MOTO' as const, estado: 'LIBRE' as const },
    { id: 3, codigo: 'A3', tipo: 'AUTO' as const, estado: 'OCUPADA' as const },
  ];

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [CambiarCelda],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
    c = TestBed.createComponent(CambiarCelda).componentInstance;
  });

  afterEach(() => http.verify());

  function consultar(estado: object) {
    c.consulta.controls.placa.setValue(' abc123 ');
    c.buscar();
    http.expectOne('/estancias/vehiculo/ABC123').flush(estado);
  }

  function disponibilidad() {
    http.expectOne('/celdas/disponibilidad').flush({ celdas, cupo: {} });
  }

  it('muestra la celda actual y solo ofrece celdas libres del mismo tipo', () => {
    consultar(dentro);
    disponibilidad();

    expect(c.estado()?.estancia?.celda.codigo).toBe('A1');
    expect(c.libres().map((item) => item.codigo)).toEqual(['A2']);

    c.celda.setValue(2);
    c.confirmar();
    const req = http.expectOne('/estancias/cambiar-celda');
    expect(req.request.body).toEqual({ placa: 'ABC123', celda_id: 2 });
    req.flush({ ...estancia, celda_id: 2, celda: celdaA2 });
    expect(c.exito()).toContain('de A1 a A2');
    disponibilidad();
  });

  it('avisa cuando el vehículo no tiene una entrada abierta', () => {
    consultar({ ...dentro, esta_dentro: false, estancia: null });
    http.expectNone('/celdas/disponibilidad');
    c.confirmar();
    http.expectNone('/estancias/cambiar-celda');
    expect(c.estado()?.esta_dentro).toBe(false);
  });

  it('muestra el conflicto del backend y recarga las celdas libres', () => {
    consultar(dentro);
    disponibilidad();
    c.celda.setValue(2);
    c.confirmar();
    http.expectOne('/estancias/cambiar-celda').flush(
      { detail: 'La celda no está disponible o es de otro tipo.' },
      { status: 409, statusText: 'Conflict' },
    );
    expect(c.errorAccion()).toBe('La celda no está disponible o es de otro tipo.');
    disponibilidad();
    expect(c.libres().map((item) => item.codigo)).toEqual(['A2']);
  });

  it('informa cuando la placa no existe y cuando falla la conexión', () => {
    c.consulta.controls.placa.setValue('ZZZ999');
    c.buscar();
    http
      .expectOne('/estancias/vehiculo/ZZZ999')
      .flush({ detail: 'Vehículo no encontrado.' }, { status: 404, statusText: 'Not Found' });
    expect(c.errorConsulta()).toBe('Vehículo no encontrado.');

    c.consulta.controls.placa.setValue('ABC123');
    c.buscar();
    http.expectOne('/estancias/vehiculo/ABC123').error(new ProgressEvent('error'));
    expect(c.errorConsulta()).toContain('El servicio no está disponible');
  });
});
