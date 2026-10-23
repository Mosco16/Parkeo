import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { ControlAcceso } from './control-acceso';
import { SesionOperador } from '../services/sesion-operador.service';

describe('Registrar entrada', () => {
  let http: HttpTestingController;
  let c: ControlAcceso;
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
  const fuera = {
    vehiculo,
    esta_dentro: false,
    estancia: null,
    mensualidad: 'VIGENTE' as const,
    celda_sugerida: celda,
  };
  const dentro = {
    ...fuera,
    esta_dentro: true,
    estancia: {
      id: 3,
      vehiculo_id: 1,
      celda_id: 2,
      entrada: '2026-10-19T15:00:00Z',
      salida: null,
      operador_entrada_id: 4,
      operador_salida_id: null,
      celda,
    },
    celda_sugerida: null,
  };

  beforeEach(() => {
    sessionStorage.clear();
    TestBed.configureTestingModule({
      imports: [ControlAcceso],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    TestBed.inject(SesionOperador).iniciar({ id: 4, nombre: 'Ana', telefono: '001' });
    http = TestBed.inject(HttpTestingController);
    c = TestBed.createComponent(ControlAcceso).componentInstance;
  });

  afterEach(() => http.verify());

  function consultar(estado: object) {
    c.consulta.controls.placa.setValue(' abc123 ');
    c.buscar();
    http.expectOne('/estancias/vehiculo/ABC123').flush(estado);
  }

  it('muestra la tarjeta y la celda sugerida sin enviar celda al confirmar', () => {
    consultar(fuera);
    expect(c.estado()?.vehiculo.placa).toBe('ABC123');
    expect(c.estado()?.celda_sugerida?.codigo).toBe('A1');

    c.confirmarEntrada();
    c.confirmarEntrada();
    const req = http.expectOne('/estancias/entrada');
    expect(req.request.body).toEqual({ placa: 'ABC123', operador_id: 4 });
    req.flush({ ...dentro.estancia, celda });
    expect(c.exitoEntrada()).toContain('ABC123');
    expect(c.exitoEntrada()).toContain('A1');
    expect(c.exitoEntrada()).toContain('Bogotá');
    expect(c.estado()).toBeNull();
  });

  it('bloquea la entrada con mensualidad vencida y muestra el vencimiento', () => {
    consultar({ ...fuera, mensualidad: 'VENCIDA' });
    c.confirmarEntrada();
    http.expectNone('/estancias/entrada');
    expect(c.estado()?.mensualidad).toBe('VENCIDA');
  });

  it('avisa cuando el vehículo ya figura dentro con su hora de entrada', () => {
    consultar(dentro);
    c.confirmarEntrada();
    http.expectNone('/estancias/entrada');
    expect(c.estado()?.esta_dentro).toBe(true);
    expect(c.fecha(dentro.estancia.entrada)).toContain('10:00:00');
  });

  it('avisa cuando no hay celdas libres del tipo', () => {
    consultar({ ...fuera, celda_sugerida: null });
    c.confirmarEntrada();
    http.expectNone('/estancias/entrada');
    expect(c.estado()?.celda_sugerida).toBeNull();
  });

  it('rechaza placas vacías y conserva el mensaje del backend', () => {
    c.consulta.controls.placa.setValue('   ');
    c.buscar();
    http.expectNone('/estancias/vehiculo/');

    c.consulta.controls.placa.setValue('ZZZ999');
    c.buscar();
    http
      .expectOne('/estancias/vehiculo/ZZZ999')
      .flush({ detail: 'Vehículo no encontrado.' }, { status: 404, statusText: 'Not Found' });
    expect(c.errorConsulta()).toBe('Vehículo no encontrado.');

    c.consulta.controls.placa.setValue('ABC123');
    c.buscar();
    http.expectOne('/estancias/vehiculo/ABC123').error(new ProgressEvent('error'));
    expect(c.errorConsulta()).toContain('No se pudo conectar');
  });

  it('presenta el mismo instante en hora de Bogotá', () => {
    expect(c.fecha('2026-10-19T15:00:00Z')).toBe(c.fecha('2026-10-19T10:00:00-05:00'));
    expect(c.fecha('2026-10-19T15:00:00Z')).toContain('10:00:00');
  });

  it('cierra la estancia anterior y registra la entrada con una salida y una entrada normales', () => {
    consultar(dentro);
    c.abrirConfirmacion();
    expect(c.confirmando()).toBe(true);

    c.corregirEntrada();
    expect(c.confirmando()).toBe(false);
    const salida = http.expectOne('/estancias/salida');
    expect(salida.request.body).toEqual({ placa: 'ABC123', operador_id: 4 });
    salida.flush({
      ...dentro.estancia,
      salida: '2026-10-19T22:00:00Z',
      operador_salida_id: 4,
    });
    expect(c.aviso()).toBe('Estancia cerrada.');

    http.expectOne('/estancias/vehiculo/ABC123').flush(fuera);
    const entrada = http.expectOne('/estancias/entrada');
    expect(entrada.request.body).toEqual({ placa: 'ABC123', operador_id: 4 });
    entrada.flush({ ...dentro.estancia, id: 9, celda });
    expect(c.exitoEntrada()).toContain('Estancia cerrada.');
    expect(c.exitoEntrada()).toContain('Entrada registrada');
    http.expectNone('/estancias/salida');
  });

  it('avisa que la estancia anterior ya quedó cerrada si falla la entrada nueva', () => {
    consultar(dentro);
    c.abrirConfirmacion();
    c.corregirEntrada();
    http.expectOne('/estancias/salida').flush({
      ...dentro.estancia,
      salida: '2026-10-19T22:00:00Z',
      operador_salida_id: 4,
    });
    http.expectOne('/estancias/vehiculo/ABC123').flush(fuera);
    http.expectOne('/estancias/entrada').error(new ProgressEvent('error'));
    expect(c.errorConsulta()).toContain('La estancia anterior ya quedó cerrada');
  });

  it('cancela la confirmación sin cerrar la estancia', () => {
    consultar(dentro);
    c.abrirConfirmacion();
    c.cancelarConfirmacion();
    expect(c.confirmando()).toBe(false);
    http.expectNone('/estancias/salida');
  });
});

describe('Registrar entrada desde la salida', () => {
  let http: HttpTestingController;
  const celda = { id: 2, codigo: 'A1', tipo: 'AUTO' };
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

  beforeEach(() => {
    sessionStorage.clear();
    TestBed.configureTestingModule({
      imports: [ControlAcceso],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: {
              queryParamMap: convertToParamMap({ placa: 'abc123', volver: 'salida' }),
            },
          },
        },
      ],
    });
    TestBed.inject(SesionOperador).iniciar({ id: 4, nombre: 'Ana', telefono: '001' });
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('carga la placa de la URL y vuelve a la salida al registrar la entrada', () => {
    const router = TestBed.inject(Router);
    const navegar = vi.spyOn(router, 'navigate').mockResolvedValue(true);
    const c = TestBed.createComponent(ControlAcceso).componentInstance;
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
      esta_dentro: false,
      estancia: null,
      mensualidad: 'VIGENTE',
      celda_sugerida: celda,
    });
    c.confirmarEntrada();
    http.expectOne('/estancias/entrada').flush(estancia);

    expect(navegar).toHaveBeenCalledWith(['/salida'], { queryParams: { placa: 'ABC123' } });
  });
});
