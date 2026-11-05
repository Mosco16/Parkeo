"""Escenarios E-10 a E-14 y corrección de entrada duplicada.

Cada prueba cita su escenario y su regla, y limpia por ids con un token propio.
"""
from datetime import date, datetime, timedelta, timezone
import os
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.database import get_engine
from app.dependencies import usuario_actual
from app.main import app
from app.models import Celda, Estancia, Usuario, Vehiculo

from conftest import usuario_de_prueba

pytestmark = pytest.mark.skipif(
    os.getenv('RUN_POSTGRES_TESTS') != '1', reason='Requiere PostgreSQL local.'
)

CELDA_NO_DISPONIBLE = 'La celda no está disponible o es de otro tipo.'
SIN_ENTRADA = 'El vehículo no tiene una entrada abierta.'
YA_DENTRO = 'Este vehículo ya figura dentro.'


@pytest.fixture
def datos():
    engine = get_engine()
    with engine.connect() as c:
        assert c.scalar(text('SELECT current_database()')) == 'autos_colombia'
        assert int(c.scalar(text('SELECT version_num FROM alembic_version'))) >= 5

    token = 'TEST-CAM-' + uuid4().hex.upper()
    vigente = date.today() + timedelta(days=30)
    with Session(engine) as s, s.begin():
        usuario = Usuario(
            documento=f'{token}-OP', nombre=f'{token}-OP', telefono='001',
            usuario=f'{token}-OP'.lower(), password_hash='hash-de-prueba', rol='OPERADOR',
        )
        celdas = [
            Celda(codigo=f'{token}-A1', tipo='AUTO'),
            Celda(codigo=f'{token}-A2', tipo='AUTO'),
            Celda(codigo=f'{token}-M1', tipo='MOTO'),
        ]
        vehiculos = {
            'auto': Vehiculo(placa=f'{token}-AUTO', color='Azul', modelo=2026, marca='Prueba',
                             tipo='AUTOMOVIL', fecha_vencimiento=vigente),
            'auto2': Vehiculo(placa=f'{token}-AUTO2', color='Gris', modelo=2026, marca='Prueba',
                              tipo='AUTOMOVIL', fecha_vencimiento=vigente),
        }
        s.add(usuario)
        s.add_all(celdas)
        s.add_all(vehiculos.values())
        s.flush()
        data = {
            'placas': {clave: vehiculo.placa for clave, vehiculo in vehiculos.items()},
            'ids': {clave: vehiculo.id for clave, vehiculo in vehiculos.items()},
            'vehiculos': [vehiculo.id for vehiculo in vehiculos.values()],
            'celdas': [c.id for c in celdas],
            'usuario': usuario.id,
        }
    app.dependency_overrides[usuario_actual] = lambda: usuario_de_prueba(
        id=data['usuario'], rol='OPERADOR'
    )
    try:
        yield data
    finally:
        app.dependency_overrides.pop(usuario_actual, None)
        with Session(engine) as s, s.begin():
            s.execute(delete(Estancia).where(Estancia.vehiculo_id.in_(data['vehiculos'])))
            s.execute(delete(Vehiculo).where(Vehiculo.id.in_(data['vehiculos'])))
            s.execute(delete(Celda).where(Celda.id.in_(data['celdas'])))
            s.execute(delete(Usuario).where(Usuario.id == data['usuario']))
        with Session(engine) as s:
            assert s.scalar(
                select(func.count()).select_from(Estancia)
                .where(Estancia.vehiculo_id.in_(data['vehiculos']))
            ) == 0


def entrada(d, clave='auto'):
    return {'placa': d['placas'][clave]}


def estado(d, clave='auto'):
    with TestClient(app) as client:
        return client.get('/estancias/vehiculo/' + d['placas'][clave]).json()


def disponibilidad(cliente):
    respuesta = cliente.get('/celdas/disponibilidad')
    assert respuesta.status_code == 200
    return respuesta.json()


def prueba_estado_celda(datos, celda_id, esperado):
    with TestClient(app) as client:
        celdas = disponibilidad(client)['celdas']
    assert next(c for c in celdas if c['id'] == celda_id)['estado'] == esperado


def test_e10_cambio_a_otra_celda_libre_del_mismo_tipo(datos):
    """E-10 / RN-CAN-01: la estancia queda en la celda nueva."""
    d = datos
    with TestClient(app) as client:
        assert client.post('/estancias/entrada', json=entrada(d)).status_code == 201
        actual = estado(d)['estancia']['celda']['id']
        libres = [
            c for c in disponibilidad(client)['celdas']
            if c['tipo'] == 'AUTO' and c['estado'] == 'DISPONIBLE' and c['id'] != actual
        ]
        assert libres, 'La prueba necesita otra celda AUTO libre.'
        destino = libres[0]['id']

        cambio = client.post('/estancias/cambiar-celda',
                             json={'placa': d['placas']['auto'], 'celda_id': destino})
        assert cambio.status_code == 200
        assert cambio.json()['celda']['id'] == destino

        despues = estado(d)
        assert despues['esta_dentro'] and despues['estancia']['celda']['id'] == destino
    prueba_estado_celda(d, actual, 'DISPONIBLE')
    prueba_estado_celda(d, destino, 'OCUPADA')


def test_e11_cambio_a_celda_ocupada_o_de_otro_tipo_no_cambia_nada(datos):
    """E-11 / RN-CAN-02: celda ocupada o de otro tipo devuelve 409 sin cambios."""
    d = datos
    with TestClient(app) as client:
        assert client.post('/estancias/entrada', json=entrada(d)).status_code == 201
        original = estado(d)['estancia']['celda']['id']

        assert client.post('/estancias/entrada', json=entrada(d, 'auto2')).status_code == 201
        ocupada = estado(d, 'auto2')['estancia']['celda']['id']

        cambio = client.post('/estancias/cambiar-celda',
                             json={'placa': d['placas']['auto'], 'celda_id': ocupada})
        assert cambio.status_code == 409
        assert cambio.json()['detail'] == CELDA_NO_DISPONIBLE

        moto = next(c for c in disponibilidad(client)['celdas'] if c['tipo'] == 'MOTO')
        cambio = client.post('/estancias/cambiar-celda',
                             json={'placa': d['placas']['auto'], 'celda_id': moto['id']})
        assert cambio.status_code == 409
        assert cambio.json()['detail'] == CELDA_NO_DISPONIBLE

        assert estado(d)['estancia']['celda']['id'] == original
    prueba_estado_celda(d, original, 'OCUPADA')
    prueba_estado_celda(d, ocupada, 'OCUPADA')


def test_e12_salida_cierra_la_estancia_y_libera_la_celda(datos):
    """E-12 / RN-SAL-01: la estancia queda CERRADA y la celda vuelve a DISPONIBLE."""
    d = datos
    with TestClient(app) as client:
        assert client.post('/estancias/entrada', json=entrada(d)).status_code == 201
        celda_id = estado(d)['estancia']['celda']['id']
        prueba_estado_celda(d, celda_id, 'OCUPADA')

        salida = client.post('/estancias/salida', json=entrada(d))
        assert salida.status_code == 200
        cerrada = salida.json()
        assert cerrada['salida'] is not None
        assert cerrada['usuario_salida_id'] == d['usuario']
        assert datetime.fromisoformat(cerrada['salida']) >= datetime.fromisoformat(cerrada['entrada'])

        despues = estado(d)
        assert despues['esta_dentro'] is False and despues['estancia'] is None
    prueba_estado_celda(d, celda_id, 'DISPONIBLE')


def test_e13_salida_con_mensualidad_vencida_no_se_bloquea(datos):
    """E-13 / RN-SAL-02: la salida nunca depende de la mensualidad."""
    d = datos
    with TestClient(app) as client:
        assert client.post('/estancias/entrada', json=entrada(d)).status_code == 201
        with Session(get_engine()) as s, s.begin():
            vehiculo = s.get(Vehiculo, d['ids']['auto'])
            vehiculo.fecha_vencimiento = date.today() - timedelta(days=1)
        assert estado(d)['mensualidad'] == 'VENCIDA'

        salida = client.post('/estancias/salida', json=entrada(d))
        assert salida.status_code == 200
        assert salida.json()['salida'] is not None


def test_e14_salida_sin_entrada_y_correccion_posterior(datos):
    """E-14 / RN-COR-05: tras el 409 se puede registrar entrada y salida."""
    d = datos
    with TestClient(app) as client:
        salida = client.post('/estancias/salida', json=entrada(d))
        assert salida.status_code == 409
        assert salida.json()['detail'] == SIN_ENTRADA

        assert client.post('/estancias/entrada', json=entrada(d)).status_code == 201
        salida = client.post('/estancias/salida', json=entrada(d))
        assert salida.status_code == 200
        assert salida.json()['salida'] is not None


def test_correccion_de_entrada_duplicada_conserva_el_historial(datos):
    """RN-COR-04 / RN-COR-03: dos estancias, ninguna borrada ni editada."""
    d = datos
    with TestClient(app) as client:
        primera = client.post('/estancias/entrada', json=entrada(d))
        assert primera.status_code == 201
        id_primera = primera.json()['id']
        entrada_primera = primera.json()['entrada']

        duplicada = client.post('/estancias/entrada', json=entrada(d))
        assert duplicada.status_code == 409
        assert duplicada.json()['detail'] == YA_DENTRO

        salida = client.post('/estancias/salida', json=entrada(d))
        assert salida.status_code == 200
        salida_primera = salida.json()['salida']

        segunda = client.post('/estancias/entrada', json=entrada(d))
        assert segunda.status_code == 201
        id_segunda = segunda.json()['id']

    with Session(get_engine()) as s:
        historial = list(s.scalars(
            select(Estancia).where(Estancia.vehiculo_id == d['ids']['auto']).order_by(Estancia.id)
        ))
    assert [e.id for e in historial] == [id_primera, id_segunda]
    primera_fila, segunda_fila = historial
    assert primera_fila.entrada.astimezone(timezone.utc) == datetime.fromisoformat(entrada_primera)
    assert primera_fila.salida is not None
    assert primera_fila.salida.astimezone(timezone.utc) == datetime.fromisoformat(salida_primera)
    assert segunda_fila.salida is None
