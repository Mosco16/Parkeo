"""E-15 / RN-ENT-07: dos entradas simultáneas nunca comparten celda.

El escenario aísla las celdas de prueba ocupando cualquier otra celda AUTO libre,
así el resultado no depende de datos de demostración.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
import os
from threading import Barrier
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import delete, event, func, select, text
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
        assert c.scalar(text('SELECT version_num FROM alembic_version')) in {'0003', '0004'}

    token = 'TEST-CONC-' + uuid4().hex.upper()
    vigente = date.today() + timedelta(days=30)
    with Session(engine) as s, s.begin():
        operador = Operador(nombre=f'{token}-OP', telefono='001')
        celdas = [Celda(codigo=f'{token}-A{n}', tipo='AUTO') for n in (1, 2)]
        vehiculos = [
            Vehiculo(placa=f'{token}-{n}', color='Azul', modelo=2026, marca='Prueba',
                     tipo='AUTOMOVIL', fecha_vencimiento=vigente)
            for n in (1, 2)
        ]
        s.add(operador)
        s.add_all(celdas)
        s.add_all(vehiculos)
        s.flush()
        data = {
            'celdas': [c.id for c in celdas],
            'vehiculos': [v.id for v in vehiculos],
            'placas': [v.placa for v in vehiculos],
            'operador': operador.id,
            'extras': {'vehiculos': [], 'operadores': []},
        }

    aislar(data, token)

    try:
        yield data
    finally:
        todos = data['vehiculos'] + data['extras']['vehiculos']
        with Session(engine) as s, s.begin():
            s.execute(delete(Estancia).where(Estancia.vehiculo_id.in_(todos)))
            s.execute(delete(Vehiculo).where(Vehiculo.id.in_(todos)))
            s.execute(delete(Celda).where(Celda.id.in_(data['celdas'])))
            s.execute(delete(Operador).where(
                Operador.id.in_([data['operador']] + data['extras']['operadores'])
            ))
        with Session(engine) as s:
            assert s.scalar(
                select(func.count()).select_from(Estancia).where(Estancia.vehiculo_id.in_(todos))
            ) == 0


def aislar(d, token):
    """Ocupa toda celda AUTO libre que no sea parte del escenario."""
    engine = get_engine()
    with Session(engine) as s, s.begin():
        ocupadas = select(Estancia.celda_id).where(Estancia.salida.is_(None))
        otras = list(s.scalars(
            select(Celda).where(
                Celda.tipo == 'AUTO',
                Celda.id.not_in(d['celdas']),
                Celda.id.not_in(ocupadas),
            )
        ))
        operador = Operador(nombre=f'{token}-OCUP', telefono=None)
        s.add(operador)
        s.flush()
        d['extras']['operadores'].append(operador.id)
        for numero, celda in enumerate(otras):
            vehiculo = Vehiculo(
                placa=f'{token}-OCUP-{numero}', color='X', modelo=2020, marca='X',
                tipo='AUTOMOVIL', fecha_vencimiento=date(2030, 1, 1),
            )
            s.add(vehiculo)
            s.flush()
            d['extras']['vehiculos'].append(vehiculo.id)
            s.add(Estancia(
                vehiculo_id=vehiculo.id, celda_id=celda.id,
                operador_entrada_id=operador.id, entrada=datetime.now(timezone.utc),
            ))


def test_e15_dos_entradas_simultaneas_toman_celdas_distintas(datos):
    """E-15 / RN-ENT-07: ninguna recibe error y no hay dos estancias por celda."""
    d = datos
    with TestClient(app) as client:
        sugerencias = [
            client.get('/estancias/vehiculo/' + placa).json()['celda_sugerida']['id']
            for placa in d['placas']
        ]
    # Ambos vehículos compiten por la misma celda sugerida.
    assert sugerencias[0] == sugerencias[1] == min(d['celdas'])

    barrier = Barrier(2)
    engine = get_engine()

    def antes_de_insertar(conn, cursor, statement, parameters, context, executemany):
        if 'INSERT INTO estancia' in statement:
            barrier.wait(timeout=15)

    event.listen(engine, 'before_cursor_execute', antes_de_insertar)

    def entrar(placa):
        with TestClient(app) as client:
            respuesta = client.post(
                '/estancias/entrada', json={'placa': placa, 'operador_id': d['operador']}
            )
            return respuesta.status_code, respuesta.json()

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            resultados = list(pool.map(entrar, d['placas']))
    finally:
        event.remove(engine, 'before_cursor_execute', antes_de_insertar)

    assert [estado for estado, _ in resultados] == [201, 201], resultados
    celdas = [cuerpo['celda']['id'] for _, cuerpo in resultados]
    assert len(set(celdas)) == 2
    assert set(celdas) == set(d['celdas'])

    with Session(engine) as s:
        estancias = list(s.scalars(
            select(Estancia).where(Estancia.vehiculo_id.in_(d['vehiculos']))
        ))
        por_celda = dict(s.execute(
            select(Estancia.celda_id, func.count())
            .where(Estancia.salida.is_(None))
            .group_by(Estancia.celda_id)
        ).all())
    assert len(estancias) == 2
    assert all(estancia.salida is None for estancia in estancias)
    assert max(por_celda.get(celda, 0) for celda in d['celdas']) == 1
