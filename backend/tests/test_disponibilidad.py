"""GET /celdas/disponibilidad: estado calculado y cupo por tipo (RN-CEL-03)."""
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


@pytest.fixture
def datos():
    engine = get_engine()
    with engine.connect() as c:
        assert c.scalar(text('SELECT current_database()')) == 'autos_colombia'
    token = 'TEST-DIS-' + uuid4().hex.upper()
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
        vehiculo = Vehiculo(placa=f'{token}-AUTO', color='Azul', modelo=2026, marca='Prueba',
                            tipo='AUTOMOVIL', fecha_vencimiento=date.today() + timedelta(days=30))
        s.add(usuario)
        s.add_all(celdas)
        s.add(vehiculo)
        s.flush()
        data = {
            'token': token,
            'celdas': [c.id for c in celdas],
            'vehiculo': vehiculo.id,
            'placa': vehiculo.placa,
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
            s.execute(delete(Estancia).where(Estancia.vehiculo_id == data['vehiculo']))
            s.execute(delete(Vehiculo).where(Vehiculo.id == data['vehiculo']))
            s.execute(delete(Celda).where(Celda.id.in_(data['celdas'])))
            s.execute(delete(Usuario).where(Usuario.id == data['usuario']))


def mapa(cliente):
    respuesta = cliente.get('/celdas/disponibilidad')
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    return cuerpo, {c['id']: c for c in cuerpo['celdas']}


def test_estado_cambia_con_la_estancia_abierta(datos):
    d = datos
    with TestClient(app) as client:
        cuerpo, antes = mapa(client)
        assert antes[d['celdas'][0]]['estado'] == 'DISPONIBLE'
        cupo_antes = cuerpo['cupo']['AUTO']

        entrada = client.post('/estancias/entrada', json={'placa': d['placa']})
        assert entrada.status_code == 201
        celda = entrada.json()['celda']['id']

        cuerpo, despues = mapa(client)
        assert despues[celda]['estado'] == 'OCUPADA'
        assert cuerpo['cupo']['AUTO']['total'] == cupo_antes['total']
        assert cuerpo['cupo']['AUTO']['libres'] == cupo_antes['libres'] - 1

        assert client.post('/estancias/salida',
                           json={'placa': d['placa']}).status_code == 200
        cuerpo, liberada = mapa(client)
        assert liberada[celda]['estado'] == 'DISPONIBLE'
        assert cuerpo['cupo']['AUTO'] == cupo_antes


def test_cupo_coincide_con_la_lista_de_celdas(datos):
    with TestClient(app) as client:
        cuerpo, _ = mapa(client)
    for tipo in ('AUTO', 'MOTO'):
        celdas = [c for c in cuerpo['celdas'] if c['tipo'] == tipo]
        assert cuerpo['cupo'][tipo] == {
            'total': len(celdas),
            'libres': sum(1 for c in celdas if c['estado'] == 'DISPONIBLE'),
        }


def test_celda_en_mantenimiento_no_se_asigna_ni_se_desactiva_ocupada(datos):
    d = datos
    objetivo = d['celdas'][0]
    app.dependency_overrides[usuario_actual] = lambda: usuario_de_prueba(
        id=d['usuario'], rol='ADMINISTRADOR'
    )
    try:
        with TestClient(app) as client:
            apagada = client.patch(f'/celdas/{objetivo}/estado', json={'activa': False})
            assert apagada.status_code == 200
            assert apagada.json()['activa'] is False

            cuerpo, celdas = mapa(client)
            assert celdas[objetivo]['estado'] == 'MANTENIMIENTO'
            assert celdas[objetivo]['activa'] is False
            assert cuerpo['cupo']['AUTO']['libres'] == sum(
                1 for c in cuerpo['celdas']
                if c['tipo'] == 'AUTO' and c['estado'] == 'DISPONIBLE'
            )

            entrada = client.post('/estancias/entrada', json={'placa': d['placa']})
            assert entrada.status_code == 201
            ocupada = entrada.json()['celda']['id']
            assert ocupada != objetivo

            # S5: una celda con estancia abierta no se puede apagar.
            conflicto = client.patch(f'/celdas/{ocupada}/estado', json={'activa': False})
            assert conflicto.status_code == 409
            assert 'estancia abierta' in conflicto.json()['detail']

            assert client.post('/estancias/salida',
                               json={'placa': d['placa']}).status_code == 200
            reactivada = client.patch(f'/celdas/{objetivo}/estado', json={'activa': True})
            assert reactivada.status_code == 200
            _, final = mapa(client)
            assert final[objetivo]['estado'] == 'DISPONIBLE'
    finally:
        app.dependency_overrides[usuario_actual] = lambda: usuario_de_prueba(
            id=d['usuario'], rol='OPERADOR'
        )
