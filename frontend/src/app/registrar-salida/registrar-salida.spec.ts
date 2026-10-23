import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { RegistrarSalida } from './registrar-salida';
import { SesionOperador } from '../services/sesion-operador.service';

describe('Registrar salida', () => {
  let http: HttpTestingController;
  let c: RegistrarSalida;
  const celda = { id: 2, codigo: 'A1', tipo: 'AUTO' };
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
    celda_id: 2,
    entrada: '2026-10-19T15:00:00Z',
    salida: null,
    operador_entrada_id: 4,
    operador_salida_id: null,
    celda,
  };
  const dentro = {
    vehiculo,
    esta_dentro: true,
    estancia,
    mensualidad: 'VIGENTE' as const,
    celda_sugerida: null,
  };

  beforeEach(() => {
    sessionStorage.clear();
    TestBed.configureTestingModule({
      imports: [RegistrarSalida],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    TestBed.inject(SesionOperador).iniciar({ id: 4, nombre: 'Ana', telefono: '001' });
    http = TestBed.inject(HttpTestingController);
    c = TestBed.createComponent(RegistrarSalida).componentInstance;
  });

  afterEach(() => http.verify());

  function consultar(estado: object) {
    c.consulta.controls.placa.setValue(' abc123 ');
    c.buscar();
    http.expectOne('/estancias/vehiculo/ABC123').flush(estado);
  }

  it('resume la estancia y confirma con el operador en turno', () => {
    consultar(dentro);
    expect(c.estado()?.estancia?.celda.codigo).toBe('A1');

    c.confirmarSalida();
    c.confirmarSalida();
    const req = http.expectOne('/estancias/salida');
    expect(req.request.body).toEqual({ placa: 'ABC123', operador_id: 4 });
    req.flush({ ...estancia, salida: '2026-10-19T22:30:00Z', operador_salida_id: 4 });
    expect(c.exitoSalida()).toContain('Salida registrada');
    expect(c.exitoSalida()).toContain('A1');
    expect(c.exitoSalida()).toContain(c.fecha('2026-10-19T22:30:00Z'));
    expect(c.estado()).toBeNull();
  });

  it('avisa de la mensualidad vencida sin bloquear la salida', () => {
    consultar({ ...dentro, mensualidad: 'VENCIDA' });
    c.confirmarSalida();
    http.expectOne('/estancias/salida').flush({
      ...estancia,
      salida: '2026-10-19T22:30:00Z',
      operador_salida_id: 4,
    });
    expect(c.exitoSalida()).toContain('Salida registrada');
  });

  it('ofrece registrar la entrada cuando no hay estancia abierta', () => {
    consultar({ ...dentro, esta_dentro: false, estancia: null });
    const router = TestBed.inject(Router);
    const navegar = vi.spyOn(router, 'navigate').mockResolvedValue(true);
    c.confirmarSalida();
    http.expectNone('/estancias/salida');
    c.irAEntrada();
    expect(navegar).toHaveBeenCalledWith(['/control-acceso'], {
      queryParams: { placa: 'ABC123', volver: 'salida' },
    });
  });

  it('muestra el mensaje del backend y los fallos de conexión', () => {
    c.consulta.controls.placa.setValue('ABC123');
    c.buscar();
    http.expectOne('/estancias/vehiculo/ABC123').flush(dentro);
    c.confirmarSalida();
    http
      .expectOne('/estancias/salida')
      .flush(
        { detail: 'El vehículo no tiene una entrada abierta.' },
        { status: 409, statusText: 'Conflict' },
      );
    expect(c.errorConsulta()).toBe('El vehículo no tiene una entrada abierta.');

    c.consulta.controls.placa.setValue('ABC123');
    c.buscar();
    http.expectOne('/estancias/vehiculo/ABC123').error(new ProgressEvent('error'));
    expect(c.errorConsulta()).toContain('El servicio no está disponible');
  });
});

describe('Registrar salida después de la entrada', () => {
  let http: HttpTestingController;

  beforeEach(() => {
    sessionStorage.clear();
    TestBed.configureTestingModule({
      imports: [RegistrarSalida],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { queryParamMap: convertToParamMap({ placa: 'abc123' }) } },
        },
      ],
    });
    TestBed.inject(SesionOperador).iniciar({ id: 4, nombre: 'Ana', telefono: '001' });
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('carga la placa devuelta por la pantalla de entrada y consulta la estancia', () => {
    const c = TestBed.createComponent(RegistrarSalida).componentInstance;
    expect(c.consulta.controls.placa.value).toBe('ABC123');
    http.expectOne('/estancias/vehiculo/ABC123').flush({
      vehiculo: {
        id: 1,
        placa: 'ABC123',
        marca: 'Renault',
        color: 'Azul',
        modelo: 2026,
        tipo: 'AUTOMOVIL',
        fecha_vencimiento: '2027-01-31',
      },
      esta_dentro: true,
      estancia: {
        id: 3,
        vehiculo_id: 1,
        celda_id: 2,
        entrada: '2026-10-19T15:00:00Z',
        salida: null,
        operador_entrada_id: 4,
        operador_salida_id: null,
        celda: { id: 2, codigo: 'A1', tipo: 'AUTO' },
      },
      mensualidad: 'VIGENTE',
      celda_sugerida: null,
    });
    expect(c.estado()?.esta_dentro).toBe(true);
  });
});
