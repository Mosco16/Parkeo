"""Escenarios E-01 a E-09: registro de entrada con celda asignada por el sistema.

Cada prueba crea sus propios datos con un token irrepetible y limpia por ids.
Las comparaciones usan la celda que el sistema sugiere, nunca una celda fija.
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

MENSUALIDAD_VENCIDA = 'Pago pendiente: la mensualidad está vencida.'
SIN_CELDAS = 'No hay celdas libres para este tipo de vehículo.'
YA_DENTRO = 'Este vehículo ya figura dentro.'
NO_ENCONTRADO = 'Vehículo no encontrado.'


@pytest.fixture
def datos():
    engine = get_engine()
    with engine.connect() as c:
        assert c.scalar(text('SELECT current_database()')) == 'autos_colombia'
        assert int(c.scalar(text('SELECT version_num FROM alembic_version'))) >= 5

    token = 'TEST-ENT-' + uuid4().hex.upper()
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
        # ABC123 (auto), DEF456 (camioneta) y GHI12J (moto) con placa irrepetible.
        vehiculos = {
            'auto': Vehiculo(placa=f'{token}-AUTO', color='Azul', modelo=2026, marca='Prueba',
                             tipo='AUTOMOVIL', fecha_vencimiento=vigente),
            'camioneta': Vehiculo(placa=f'{token}-CAM', color='Gris', modelo=2026, marca='Prueba',
                                  tipo='CAMIONETA', fecha_vencimiento=vigente),
            'moto': Vehiculo(placa=f'{token}-MOTO', color='Rojo', modelo=2026, marca='Prueba',
                             tipo='MOTO', fecha_vencimiento=vigente),
            'vencido': Vehiculo(placa=f'{token}-VENC', color='Negro', modelo=2026, marca='Prueba',
                                tipo='AUTOMOVIL', fecha_vencimiento=date.today() - timedelta(days=5)),
            'borde': Vehiculo(placa=f'{token}-BORDE', color='Blanco', modelo=2026, marca='Prueba',
                              tipo='AUTOMOVIL', fecha_vencimiento=date(2026, 6, 15)),
        }
        s.add(usuario)
        s.add_all(celdas)
        s.add_all(vehiculos.values())
        s.flush()
        data = {
            'token': token,
            'usuario': usuario.id,
            'celdas': [c.id for c in celdas],
            'placas': {clave: vehiculo.placa for clave, vehiculo in vehiculos.items()},
            'ids': {clave: vehiculo.id for clave, vehiculo in vehiculos.items()},
            'vehiculos': [vehiculo.id for vehiculo in vehiculos.values()],
            'extras': {'vehiculos': [], 'usuarios': []},
        }

    app.dependency_overrides[usuario_actual] = lambda: usuario_de_prueba(
        id=data['usuario'], rol='OPERADOR'
    )
    try:
        yield data
    finally:
        app.dependency_overrides.pop(usuario_actual, None)
        ids = data['vehiculos'] + data['extras']['vehiculos']
        with Session(engine) as s, s.begin():
            s.execute(delete(Estancia).where(Estancia.vehiculo_id.in_(ids)))
            s.execute(delete(Vehiculo).where(Vehiculo.id.in_(ids)))
            s.execute(delete(Celda).where(Celda.id.in_(data['celdas'])))
            s.execute(delete(Usuario).where(
                Usuario.id.in_([data['usuario']] + data['extras']['usuarios'])
            ))
        with Session(engine) as s:
            assert s.scalar(
                select(func.count()).select_from(Estancia).where(Estancia.vehiculo_id.in_(ids))
            ) == 0


def entrada(d, clave='auto'):
    return {'placa': d['placas'][clave], 'usuario_id': d['usuario']}


def abiertas(d, clave='auto'):
    with Session(get_engine()) as s:
        return s.scalar(
            select(func.count()).select_from(Estancia).where(
                Estancia.vehiculo_id == d['ids'][clave], Estancia.salida.is_(None)
            )
        )


def ocupar_todas(d, tipo):
    """Ocupa toda celda libre del tipo, aunque existan datos de demostración."""
    engine = get_engine()
    with Session(engine) as s, s.begin():
        ocupadas = select(Estancia.celda_id).where(Estancia.salida.is_(None))
        libres = list(s.scalars(
            select(Celda).where(Celda.tipo == tipo, Celda.id.not_in(ocupadas))
        ))
        usuario = Usuario(
            documento=f"{d['token']}-OCUP", nombre=f"{d['token']}-OCUP", telefono=None,
            usuario=f"{d['token']}-OCUP".lower(), password_hash='hash-de-prueba', rol='OPERADOR',
        )
        s.add(usuario)
        s.flush()
        d['extras']['usuarios'].append(usuario.id)
        for numero, celda in enumerate(libres):
            vehiculo = Vehiculo(
                placa=f"{d['token']}-OCUP-{numero}", color='X', modelo=2020, marca='X',
                tipo='AUTOMOVIL', fecha_vencimiento=date(2030, 1, 1),
            )
            s.add(vehiculo)
            s.flush()
            d['extras']['vehiculos'].append(vehiculo.id)
            s.add(Estancia(
                vehiculo_id=vehiculo.id, celda_id=celda.id,
                usuario_entrada_id=usuario.id, entrada=datetime.now(timezone.utc),
            ))
    return len(libres)


def test_e01_auto_vigente_recibe_celda_auto(datos):
    d = datos
    with TestClient(app) as client:
        url = '/estancias/vehiculo/' + d['placas']['auto']
        sugerida = client.get(url).json()['celda_sugerida']
        assert sugerida is not None and sugerida['tipo'] == 'AUTO'

        result = client.post('/estancias/entrada', json=entrada(d))
        assert result.status_code == 201
        abierta = result.json()
        assert abierta['celda']['id'] == sugerida['id']
        assert abierta['celda']['tipo'] == 'AUTO'
        assert abierta['salida'] is None

        estado = client.get(url).json()
        assert estado['esta_dentro'] and estado['estancia']['id'] == abierta['id']
        assert estado['mensualidad'] == 'VIGENTE'


def test_e02_moto_recibe_celda_moto(datos):
    d = datos
    with TestClient(app) as client:
        result = client.post('/estancias/entrada', json=entrada(d, 'moto'))
        assert result.status_code == 201
        assert result.json()['celda']['tipo'] == 'MOTO'


def test_e03_camioneta_recibe_celda_auto(datos):
    d = datos
    with TestClient(app) as client:
        result = client.post('/estancias/entrada', json=entrada(d, 'camioneta'))
        assert result.status_code == 201
        assert result.json()['celda']['tipo'] == 'AUTO'


def test_e04_mensualidad_vencida_bloquea_la_entrada(datos):
    d = datos
    with TestClient(app) as client:
        result = client.post('/estancias/entrada', json=entrada(d, 'vencido'))
        assert result.status_code == 409
        assert result.json()['detail'] == MENSUALIDAD_VENCIDA
        assert abiertas(d, 'vencido') == 0


def test_e05_vence_hoy_ya_esta_vencida(datos, monkeypatch):
    d = datos
    from app.services import estancia as modulo

    monkeypatch.setattr(modulo, 'hoy_bogota', lambda: date(2026, 6, 15))
    with TestClient(app) as client:
        assert client.get('/estancias/vehiculo/' + d['placas']['borde']).json()['mensualidad'] == 'VENCIDA'
        result = client.post('/estancias/entrada', json=entrada(d, 'borde'))
        assert result.status_code == 409
        assert result.json()['detail'] == MENSUALIDAD_VENCIDA
        assert abiertas(d, 'borde') == 0


def test_e06_vence_manana_permite_la_entrada(datos, monkeypatch):
    d = datos
    from app.services import estancia as modulo

    monkeypatch.setattr(modulo, 'hoy_bogota', lambda: date(2026, 6, 14))
    with TestClient(app) as client:
        estado = client.get('/estancias/vehiculo/' + d['placas']['borde']).json()
        assert estado['mensualidad'] == 'VIGENTE'
        result = client.post('/estancias/entrada', json=entrada(d, 'borde'))
        assert result.status_code == 201
        assert abiertas(d, 'borde') == 1


def test_e07_sin_celdas_libres_del_tipo(datos):
    d = datos
    ocupar_todas(d, 'MOTO')
    with TestClient(app) as client:
        result = client.post('/estancias/entrada', json=entrada(d, 'moto'))
        assert result.status_code == 409
        assert result.json()['detail'] == SIN_CELDAS
        assert abiertas(d, 'moto') == 0


def test_e08_placa_no_registrada(datos):
    d = datos
    with TestClient(app) as client:
        result = client.post(
            '/estancias/entrada',
            json={'placa': 'INEXISTENTE-' + uuid4().hex, 'usuario_id': d['usuario']},
        )
        assert result.status_code == 404
        assert result.json()['detail'] == NO_ENCONTRADO


def test_e09_no_se_registra_dos_veces(datos):
    d = datos
    with TestClient(app) as client:
        assert client.post('/estancias/entrada', json=entrada(d)).status_code == 201
        result = client.post('/estancias/entrada', json=entrada(d))
        assert result.status_code == 409
        assert result.json()['detail'] == YA_DENTRO
        assert abiertas(d) == 1
