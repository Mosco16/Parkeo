import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { App } from './app';
import { SesionUsuario } from './services/sesion-usuario.service';

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

describe('Shell de la aplicación', () => {
  beforeEach(async () => {
    sessionStorage.clear();
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [provideRouter([])],
    }).compileComponents();
  });
  afterEach(() => sessionStorage.clear());

  function crear() {
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();
    return fixture;
  }

  function iniciar(rol: 'ADMINISTRADOR' | 'OPERADOR') {
    TestBed.inject(SesionUsuario).iniciar({
      access_token: 'token',
      token_type: 'bearer',
      usuario: { ...USUARIO, rol },
    });
  }

  it('oculta el menú y la barra superior sin sesión', () => {
    const elemento = crear().nativeElement as HTMLElement;

    expect(elemento.querySelector('aside')).toBeNull();
    expect(elemento.querySelector('.topbar')).toBeNull();
    expect(elemento.querySelector('main')).not.toBeNull();
  });

  it('muestra el menú, el breadcrumb y el rol del usuario', () => {
    iniciar('ADMINISTRADOR');
    const elemento = crear().nativeElement as HTMLElement;

    expect(elemento.querySelector('.brand-name')?.textContent).toBe('Parkeo');
    expect(elemento.textContent).toContain('Autos Colombia');
    expect(elemento.textContent).toContain('Sede principal');
    expect(elemento.querySelector('.session-name strong')?.textContent).toBe('Ana Gómez');
    expect(elemento.querySelector('.session-name small')?.textContent).toBe('Administrador');
  });

  it('reserva la administración para el administrador', () => {
    iniciar('OPERADOR');
    const elemento = crear().nativeElement as HTMLElement;

    expect(elemento.querySelector('a[href="/gestion/celdas"]')).toBeNull();
    expect(elemento.querySelector('a[href="/gestion/usuarios"]')).toBeNull();
    expect(elemento.querySelector('a[href="/historial"]')?.textContent).toBe('Historial');
    expect(elemento.querySelector('a[href="/gestion/vehiculos"]')?.textContent).toBe('Vehículos');
  });

  it('muestra usuarios y celdas al administrador', () => {
    iniciar('ADMINISTRADOR');
    const elemento = crear().nativeElement as HTMLElement;

    expect(elemento.querySelector('a[href="/gestion/usuarios"]')?.textContent).toBe('Usuarios');
    expect(elemento.querySelector('a[href="/gestion/celdas"]')?.textContent).toBe('Celdas');
  });

  it('abre y cierra el menú lateral', () => {
    iniciar('OPERADOR');
    const fixture = crear();
    const componente = fixture.componentInstance as unknown as {
      menuAbierto: () => boolean;
      alternarMenu: () => void;
    };
    const elemento = fixture.nativeElement as HTMLElement;
    const boton = elemento.querySelector('.menu-toggle') as HTMLButtonElement;

    boton.click();
    fixture.detectChanges();
    expect(componente.menuAbierto()).toBe(true);
    expect(elemento.querySelector('aside')?.classList).toContain('abierto');

    (elemento.querySelector('.backdrop') as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(componente.menuAbierto()).toBe(false);
  });

  it('cierra la sesión y vuelve al login', () => {
    iniciar('OPERADOR');
    const fixture = crear();
    const router = TestBed.inject(Router);
    const navegar = vi.spyOn(router, 'navigate').mockResolvedValue(true);

    (fixture.nativeElement as HTMLElement).querySelector<HTMLButtonElement>('.session button')!.click();
    fixture.detectChanges();

    expect(TestBed.inject(SesionUsuario).autenticado()).toBe(false);
    expect(sessionStorage.getItem('parkeo.sesion')).toBeNull();
    expect(navegar).toHaveBeenCalledWith(['/login']);
  });
});
