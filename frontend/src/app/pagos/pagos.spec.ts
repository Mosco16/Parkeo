import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { Pago } from '../models/pago';
import { Pagos } from './pagos';

describe('Gestión de pagos', () => {
  let fixture: ComponentFixture<Pagos>;
  let component: Pagos;
  let http: HttpTestingController;

  const pago: Pago = {
    id: 5,
    placa: 'ABC123',
    valor: 250000,
    referencia: 'REF-001',
    fecha_hora: '2026-11-18T15:30:00Z',
    dia_corte: 5,
    inicio_ciclo: '2026-11-06',
    vencimiento_ciclo: '2026-12-05',
    estado: 'ACTIVO',
    motivo_anulacion: null,
    anulacion_fecha_hora: null,
    usuario: 'Operador',
  };
  const pagina = { items: [pago], total: 1, pagina: 1, tamano: 10 };

  const flushHistorial = () =>
    http.expectOne('/pagos?placa=ABC123&pagina=1&tamano=10').flush(pagina);

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Pagos],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(Pagos);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => http.verify());

  it('registra un pago con placa normalizada y referencia sin espacios', () => {
    component.form.patchValue({
      placa: ' abc123 ',
      referencia: ' REF-001 ',
      correo: ' Dueno@Correo.CO ',
      autorizar_avisos: true,
    });
    component.registrar();

    const peticion = http.expectOne('/pagos');
    expect(peticion.request.method).toBe('POST');
    expect(peticion.request.body).toEqual({
      placa: 'ABC123',
      referencia: 'REF-001',
      correo: 'dueno@correo.co',
      autorizar_avisos: true,
    });
    peticion.flush(pago);
    flushHistorial();

    expect(component.ultimoPago()?.placa).toBe('ABC123');
    expect(component.items().length).toBe(1);
  });

  it('omite campos opcionales vacíos al registrar', () => {
    component.form.patchValue({ placa: 'abc123', referencia: 'REF-001' });
    component.registrar();

    const peticion = http.expectOne('/pagos');
    expect(peticion.request.body).toEqual({ placa: 'ABC123', referencia: 'REF-001' });
    peticion.flush(pago);
    flushHistorial();
  });

  it('no envía el formulario incompleto ni autoriza avisos sin correo', () => {
    component.registrar();
    expect(component.errorCampo('placa')).toContain('obligatorio');
    http.expectNone('/pagos');

    component.form.patchValue({ placa: 'ABC123', referencia: 'REF-001', autorizar_avisos: true });
    component.registrar();
    expect(component.errorCampo('correo')).toContain('correo');
    http.expectNone('/pagos');
  });

  it('consulta el historial por placa y pagina', () => {
    component.consulta.controls.placa.setValue('abc123');
    component.buscar(1);

    const peticion = http.expectOne('/pagos?placa=ABC123&pagina=1&tamano=10');
    expect(peticion.request.method).toBe('GET');
    peticion.flush(pagina);
    fixture.detectChanges();

    expect(component.total()).toBe(1);
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('REF-001');
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('ACTIVO');
  });

  it('anula con el motivo seleccionado y actualiza la fila', () => {
    component.consulta.controls.placa.setValue('ABC123');
    component.buscar(1);
    flushHistorial();

    const anulado = { ...pago, estado: 'ANULADO' as const, motivo_anulacion: 'Pago duplicado' };
    component.preguntarAnulacion(pago);
    component.onMotivo({ target: { value: 'Pago duplicado' } } as unknown as Event);
    component.confirmarAnulacion();

    const peticion = http.expectOne('/pagos/5/anular');
    expect(peticion.request.body).toEqual({ motivo: 'Pago duplicado' });
    peticion.flush(anulado);

    expect(component.anulando()).toBeNull();
    expect(component.items()[0].estado).toBe('ANULADO');
    expect(component.items()[0].motivo_anulacion).toBe('Pago duplicado');
  });

  it('muestra el error del backend al anular sin cerrar el formulario', () => {
    component.consulta.controls.placa.setValue('ABC123');
    component.buscar(1);
    flushHistorial();

    component.preguntarAnulacion(pago);
    component.confirmarAnulacion();
    http
      .expectOne('/pagos/5/anular')
      .flush({ detail: 'Solo se puede anular el último pago activo.' }, { status: 409, statusText: 'Conflict' });
    fixture.detectChanges();

    expect(component.errorAnulacion()).toBe('Solo se puede anular el último pago activo.');
    expect(component.anulando()).toBe(5);
  });
});

describe('Pagos desde una placa externa', () => {
  it('prellena la placa de la URL y consulta su historial', async () => {
    await TestBed.configureTestingModule({
      imports: [Pagos],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { queryParamMap: convertToParamMap({ placa: 'abc123' }) } },
        },
      ],
    }).compileComponents();
    const http = TestBed.inject(HttpTestingController);
    const c = TestBed.createComponent(Pagos).componentInstance;

    expect(c.form.controls.placa.value).toBe('ABC123');
    expect(c.consulta.controls.placa.value).toBe('ABC123');
    http.expectOne('/pagos?placa=ABC123&pagina=1&tamano=10').flush({
      items: [],
      total: 0,
      pagina: 1,
      tamano: 10,
    });
    expect(c.buscado()).toBe(true);
    http.verify();
  });
});
