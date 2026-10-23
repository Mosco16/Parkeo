from fastapi.testclient import TestClient
import pytest

from app.database import get_session
from app.main import app
from app.schemas.estancia import EntradaCrear


@pytest.fixture(autouse=True)
def sin_postgres():
    """RNF-11: validar el cuerpo no puede depender de una base local."""

    def sesion_simulada():
        yield object()

    app.dependency_overrides[get_session] = sesion_simulada
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_openapi_y_salud():
    with TestClient(app) as client:
        schema = client.get('/openapi.json').json()
        for path, method in [('/estancias/entrada', 'post'), ('/estancias/salida', 'post'),
                             ('/estancias/cambiar-celda', 'post'),
                             ('/estancias/vehiculo/{placa}', 'get'),
                             ('/celdas/disponibilidad', 'get')]:
            assert method in schema['paths'][path]
        assert client.get('/health').json() == {'status': 'ok'}


@pytest.mark.parametrize('payload', [
    {},
    {'placa': ' ', 'operador_id': 1},
    {'placa': None, 'operador_id': 1},
    {'placa': 'TEST', 'operador_id': 0},
    {'placa': 'TEST', 'operador_id': True},
    {'placa': 'TEST', 'operador_id': '1'},
    {'placa': 'TEST', 'operador_id': None},
    {'placa': 'TEST', 'operador_id': 9223372036854775808},
    {'placa': 'TEST', 'operador_id': 1, 'entrada': '2026-01-01'},
    # RN-ENT-05: el operador ya no elige la celda; enviarla es inválido.
    {'placa': 'TEST', 'operador_id': 1, 'celda_id': 1},
])
def test_entrada_invalida(payload):
    with TestClient(app) as client:
        assert client.post('/estancias/entrada', json=payload).status_code == 422


def test_entrada_valida_solo_con_placa_y_operador():
    data = EntradaCrear(placa=' abc123 ', operador_id=1)
    assert data.model_dump() == {'placa': 'ABC123', 'operador_id': 1}


def test_salida_no_admite_celda_ni_fecha():
    with TestClient(app) as client:
        for extra in ({'celda_id': 1}, {'salida': '2026-01-01'}, {'id': 1}):
            assert client.post('/estancias/salida', json={'placa': 'TEST', 'operador_id': 1, **extra}).status_code == 422
        assert client.get('/estancias/vehiculo/%20%20').status_code == 422


def test_cambio_de_celda_exige_placa_y_celda():
    with TestClient(app) as client:
        for payload in ({}, {'placa': 'TEST'}, {'celda_id': 1},
                        {'placa': 'TEST', 'celda_id': 0},
                        {'placa': 'TEST', 'celda_id': 1, 'operador_id': 1}):
            assert client.post('/estancias/cambiar-celda', json=payload).status_code == 422
