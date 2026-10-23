"""GET /celdas/disponibilidad: estado calculado y cupo por tipo (RN-CEL-03)."""
from datetime import date, datetime, timedelta, timezone
import os
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.database import get_engine
from app.main import app
from app.models import Celda, Estancia, Operador, Vehiculo

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
        operador = Operador(nombre=f'{token}-OP', telefono='001')
        celdas = [Celda(codigo=f'{token}-A1', tipo='AUTO'), Celda(codigo=f'{token}-M1', tipo='MOTO')]
        vehiculo = Vehiculo(placa=f'{token}-AUTO', color='Azul', modelo=2026, marca='Prueba',
                            tipo='AUTOMOVIL', fecha_vencimiento=date.today() + timedelta(days=30))
        s.add(operador)
        s.add_all(celdas)
        s.add(vehiculo)
        s.flush()
        data = {
            'celdas': [c.id for c in celdas],
            'vehiculo': vehiculo.id,
            'placa': vehiculo.placa,
            'operador': operador.id,
        }
    try:
        yield data
    finally:
        with Session(engine) as s, s.begin():
            s.execute(delete(Estancia).where(Estancia.vehiculo_id == data['vehiculo']))
            s.execute(delete(Vehiculo).where(Vehiculo.id == data['vehiculo']))
            s.execute(delete(Celda).where(Celda.id.in_(data['celdas'])))
            s.execute(delete(Operador).where(Operador.id == data['operador']))


def mapa(cliente):
    respuesta = cliente.get('/celdas/disponibilidad')
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    return cuerpo, {c['id']: c for c in cuerpo['celdas']}


def test_estado_cambia_con_la_estancia_abierta(datos):
    d = datos
    with TestClient(app) as client:
        cuerpo, antes = mapa(client)
        assert antes[d['celdas'][0]]['estado'] == 'LIBRE'
        cupo_antes = cuerpo['cupo']['AUTO']

        entrada = client.post('/estancias/entrada',
                              json={'placa': d['placa'], 'operador_id': d['operador']})
        assert entrada.status_code == 201
        celda = entrada.json()['celda']['id']

        cuerpo, despues = mapa(client)
        assert despues[celda]['estado'] == 'OCUPADA'
        assert cuerpo['cupo']['AUTO']['total'] == cupo_antes['total']
        assert cuerpo['cupo']['AUTO']['libres'] == cupo_antes['libres'] - 1

        assert client.post('/estancias/salida',
                           json={'placa': d['placa'], 'operador_id': d['operador']}).status_code == 200
        cuerpo, liberada = mapa(client)
        assert liberada[celda]['estado'] == 'LIBRE'
        assert cuerpo['cupo']['AUTO'] == cupo_antes


def test_cupo_coincide_con_la_lista_de_celdas(datos):
    with TestClient(app) as client:
        cuerpo, _ = mapa(client)
    for tipo in ('AUTO', 'MOTO'):
        celdas = [c for c in cuerpo['celdas'] if c['tipo'] == tipo]
        assert cuerpo['cupo'][tipo] == {
            'total': len(celdas),
            'libres': sum(1 for c in celdas if c['estado'] == 'LIBRE'),
        }
