import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Usuarios } from './usuarios';

describe('Gestión de usuarios', () => {
  let fixture: ComponentFixture<Usuarios>;
  let http: HttpTestingController;
  const usuario = {
    id: 1,
    documento: '1001',
    nombre: 'Ana Gómez',
    telefono: '+57 00123',
    usuario: 'ana.gomez',
    rol: 'OPERADOR' as const,
    activo: true,
    correo: null,
    direccion: null,
    creado_en: '2026-11-05T10:00:00',
    actualizado_en: '2026-11-05T10:00:00',
  };
  const page = { items: [usuario], total: 1, offset: 0, limit: 10 };

  const valoresFormulario = {
    documento: '1001',
    nombre: 'Ana Gómez',
    usuario: 'ana.gomez',
    telefono: '',
    correo: '',
    direccion: '',
    password: '',
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Usuarios],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(Usuarios);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Cargando usuarios');
    http.expectOne('/usuarios?offset=0&limit=10').flush(page);
    fixture.detectChanges();
  });
  afterEach(() => http.verify());

  it('lista las cuentas con su estado', () => {
    const root = fixture.nativeElement as HTMLElement;

    expect(root.querySelector('table')?.textContent).toContain('ana.gomez');
    expect(root.querySelector('.badge')?.textContent).toContain('Activo');
    expect(root.textContent).toContain('Usuarios registrados');
  });

  it('crea desde el HTML recortando los textos y sin enviar opcionales vacíos', () => {
    const c = fixture.componentInstance;
    c.nuevo();
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    for (const [key, value] of Object.entries({
      documento: ' 1001 ',
      nombre: ' Ana Gómez ',
      usuario: ' ANA.GOMEZ ',
      password: ' Parkeo2026* ',
    })) {
      const input = root.querySelector<HTMLInputElement>(`#${key}`)!;
      input.value = value;
      input.dispatchEvent(new Event('input', { bubbles: true }));
    }
    c.save();
    const request = http.expectOne({ method: 'POST', url: '/usuarios' });
    expect(request.request.body).toEqual({
      documento: '1001',
      nombre: 'Ana Gómez',
      usuario: 'ana.gomez',
      password: 'Parkeo2026*',
    });
    request.flush(usuario);
    http.expectOne('/usuarios?offset=0&limit=10').flush(page);
    expect(c.success()).toContain('registrado');
  });

  it('rechaza campos obligatorios vacíos y la contraseña corta', () => {
    const c = fixture.componentInstance;
    c.nuevo();
    c.form.setValue({ ...valoresFormulario, documento: ' ', password: 'Parkeo2026*' });
    c.save();
    expect(c.fieldError('documento')).toContain('obligatorio');
    expect(c.actionError()).toContain('Revisa');

    c.form.setValue({ ...valoresFormulario, password: 'corta' });
    c.save();
    expect(c.actionError()).toContain('contraseña');
    http.expectNone('/usuarios');
  });

  it('edita con PATCH sin enviar contraseña y conserva el estado', () => {
    const c = fixture.componentInstance;
    c.editar(usuario);
    http.expectOne('/usuarios/1').flush(usuario);
    expect(c.form.controls.password.value).toBe('');
    c.form.controls.telefono.setValue(' 00045 ');
    c.save();
    const request = http.expectOne({ method: 'PATCH', url: '/usuarios/1' });
    expect(request.request.body).toEqual({
      documento: '1001',
      nombre: 'Ana Gómez',
      usuario: 'ana.gomez',
      telefono: '00045',
    });
    request.flush({ ...usuario, telefono: '00045' });
    http.expectOne('/usuarios?offset=0&limit=10').flush(page);
    expect(c.success()).toContain('actualizado');
  });

  it('activa y desactiva una cuenta sin borrarla', () => {
    const c = fixture.componentInstance;
    c.cambiarEstado(usuario);
    const request = http.expectOne({ method: 'PATCH', url: '/usuarios/1/estado' });
    expect(request.request.body).toEqual({ activo: false });
    request.flush({ ...usuario, activo: false });
    http.expectOne('/usuarios?offset=0&limit=10').flush({
      ...page,
      items: [{ ...usuario, activo: false }],
    });
    expect(c.success()).toContain('desactivado');
  });

  it('restablece la contraseña de una cuenta', () => {
    const c = fixture.componentInstance;
    c.pedirReset(usuario);
    c.resetForm.setValue({ password: 'Parkeo2026*' });
    c.resetPassword();
    const request = http.expectOne({
      method: 'POST',
      url: '/usuarios/1/restablecer-password',
    });
    expect(request.request.body).toEqual({ password: 'Parkeo2026*' });
    request.flush(usuario);
    expect(c.resetTarget()).toBeNull();
    expect(c.success()).toContain('restablecida');
  });

  it('muestra el conflicto por documento o usuario duplicado', () => {
    const c = fixture.componentInstance;
    c.nuevo();
    c.form.setValue({
      ...valoresFormulario,
      password: 'Parkeo2026*',
    });
    c.save();
    http
      .expectOne('/usuarios')
      .flush({ detail: 'duplicado' }, { status: 409, statusText: 'Conflict' });
    expect(c.actionError()).toContain('ya están registrados');
  });

  it('pagina y permite reintentar el listado tras un fallo de conexión', () => {
    const c = fixture.componentInstance;
    c.load(10);
    http.expectOne('/usuarios?offset=10&limit=10').flush({ ...page, offset: 10, total: 11 });
    expect(c.page()).toBe(2);

    c.load();
    http.expectOne('/usuarios?offset=10&limit=10').error(new ProgressEvent('error'));
    expect(c.listError()).toContain('No se pudo conectar');

    c.load();
    http.expectOne('/usuarios?offset=10&limit=10').flush({ ...page, offset: 10, total: 11 });
    expect(c.listError()).toBe('');
  });
});
