"""Historial de cambios de celda sin depender de PostgreSQL."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
import pytest

from app.database import get_session
from app.main import app
from app.models import Base, CambioCelda, Celda, Estancia
from app.services.estancia import EstanciaError, ServicioEstancia

from conftest import token_para, usuario_de_prueba

ENTRADA = datetime(2026, 10, 19, 10, tzinfo=timezone.utc)


@pytest.fixture
def api():
    session = MagicMock()
    session.get.return_value = usuario_de_prueba()

    def override():
        yield session

    app.dependency_overrides[get_session] = override
    try:
        with TestClient(app) as client:
            client.headers["Authorization"] = f"Bearer {token_para(1)}"
            yield client, session
    finally:
        app.dependency_overrides.pop(get_session, None)


def escenario(tipo_destino: str = "AUTO", activa: bool = True):
    session = MagicMock()
    vehiculo = SimpleNamespace(id=1, tipo="AUTOMOVIL")
    estancia = Estancia(
        id=10,
        vehiculo_id=1,
        celda_id=5,
        entrada=ENTRADA,
        usuario_entrada_id=7,
        salida=None,
    )
    actual = Celda(id=5, codigo="A1", tipo="AUTO", activa=True)
    destino = Celda(id=6, codigo="A2", tipo=tipo_destino, activa=activa)
    session.scalar.side_effect = [vehiculo, estancia, None]
    session.get.side_effect = lambda entidad, clave, *a, **k: {
        5: actual,
        6: destino,
    }[clave]
    return session, estancia, destino


def test_el_cambio_exitoso_registra_el_historial_en_la_transaccion():
    session, estancia, destino = escenario()
    usuario = usuario_de_prueba(id=7)

    resultado = ServicioEstancia(session).cambiar_celda(
        SimpleNamespace(placa="ABC123", celda_id=destino.id), usuario
    )

    assert resultado.celda.codigo == "A2"
    assert estancia.celda_id == 6
    cambio = next(
        llamada.args[0]
        for llamada in session.add.call_args_list
        if isinstance(llamada.args[0], CambioCelda)
    )
    assert cambio.estancia_id == 10
    assert cambio.celda_anterior_id == 5
    assert cambio.celda_nueva_id == 6
    assert cambio.usuario_id == 7
    assert cambio.fecha_hora.tzinfo is not None
    session.flush.assert_called()


def test_la_misma_celda_se_rechaza_sin_historial():
    session, _, _ = escenario()

    with pytest.raises(EstanciaError) as error:
        ServicioEstancia(session).cambiar_celda(
            SimpleNamespace(placa="ABC123", celda_id=5), usuario_de_prueba(id=7)
        )

    assert error.value.status_code == 409
    assert "distinta" in error.value.detail
    session.add.assert_not_called()


def test_una_celda_invalida_no_escribe_historial():
    session, _, _ = escenario(tipo_destino="MOTO")

    with pytest.raises(EstanciaError) as error:
        ServicioEstancia(session).cambiar_celda(
            SimpleNamespace(placa="ABC123", celda_id=6), usuario_de_prueba(id=7)
        )

    assert error.value.status_code == 409
    session.add.assert_not_called()


def test_la_tabla_tiene_columnas_restricciones_e_indice():
    tabla = Base.metadata.tables["cambio_celda"]

    assert set(tabla.columns.keys()) == {
        "id",
        "estancia_id",
        "celda_anterior_id",
        "celda_nueva_id",
        "usuario_id",
        "fecha_hora",
    }
    nombres = {restriccion.name for restriccion in tabla.constraints}
    assert {
        "ck_cambio_celda_celdas_distintas",
        "fk_cambio_celda_estancia",
        "fk_cambio_celda_celda_anterior",
        "fk_cambio_celda_celda_nueva",
        "fk_cambio_celda_usuario",
    } <= nombres
    assert "ix_cambio_celda_fecha_hora" in {indice.name for indice in tabla.indexes}


def test_historial_ordena_del_mas_reciente_al_mas_antiguo():
    session = MagicMock()
    session.scalar.return_value = 0
    session.execute.return_value = []

    resultado = ServicioEstancia(session).historial_cambios(0, 20)

    consulta = str(session.execute.call_args.args[0])
    assert "ORDER BY cambio_celda.fecha_hora DESC" in consulta
    assert consulta.count("JOIN celda AS") == 2
    assert resultado == {"items": [], "total": 0, "offset": 0, "limit": 20}


def test_historial_vacio_devuelve_la_pagina(api):
    client, session = api
    session.scalar.return_value = 0
    session.execute.return_value = []

    respuesta = client.get("/estancias/historial-cambios")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"items": [], "total": 0, "offset": 0, "limit": 20}


@pytest.mark.parametrize("parametros", [
    "offset=-1",
    "limit=0",
    "limit=101",
    "offset=abc",
])
def test_historial_valida_la_paginacion(api, parametros):
    client, _ = api

    assert client.get(f"/estancias/historial-cambios?{parametros}").status_code == 422
