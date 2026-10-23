import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { SeleccionOperador } from './seleccion-operador';

describe('Selección de operador', () => {
  let http: HttpTestingController;
  const operador = { id: 4, nombre: 'Ana', telefono: '001' };

  beforeEach(async () => {
    sessionStorage.clear();
    await TestBed.configureTestingModule({
      imports: [SeleccionOperador],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  function crear() {
    const fixture = TestBed.createComponent(SeleccionOperador);
    fixture.detectChanges();
    http
      .expectOne('/operadores?offset=0&limit=100')
      .flush({ items: [operador], total: 1, offset: 0, limit: 100 });
    fixture.detectChanges();
    return fixture;
  }

  it('lista los operadores y exige elegir uno para iniciar', () => {
    const fixture = crear();
    expect(fixture.componentInstance.operadores().length).toBe(1);

    fixture.componentInstance.iniciarTurno();
    expect(fixture.componentInstance.error()).toContain('Selecciona un operador');
    expect(sessionStorage.getItem('autos-colombia.operador')).toBeNull();
  });

  it('inicia el turno y navega al tablero', () => {
    const fixture = crear();
    const router = TestBed.inject(Router);
    const navegar = vi.spyOn(router, 'navigate').mockResolvedValue(true);

    fixture.componentInstance.elegir(4);
    fixture.componentInstance.iniciarTurno();

    expect(navegar).toHaveBeenCalledWith(['/tablero']);
    expect(sessionStorage.getItem('autos-colombia.operador')).toContain('Ana');
  });
});
