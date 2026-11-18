"""API de pagos con sesión simulada: códigos HTTP y mensajes públicos."""

from datetime import date, datetime, timezone
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
import pytest

from app.database import get_session
from app.dependencies import usuario_actual
from app.main import app
from app.models import Pago, Vehiculo

from conftest import con_pago, usuario_de_prueba


@pytest.fixture
def api():
    session = MagicMock()

    def override():
        yield session

    app.dependency_overrides[get_session] = override
    app.dependency_overrides[usuario_actual] = lambda: usuario_de_prueba(id=1)
    try:
        with TestClient(app) as client:
            yield client, session
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(usuario_actual, None)


def vehiculo(tipo="AUTOMOVIL") -> Vehiculo:
    return Vehiculo(id=1, placa="ABC123", color="Azul", modelo=2025, marca="Marca", tipo=tipo)


def guardar_con_id(session) -> None:
    session.flush.side_effect = lambda: setattr(session.add.call_args.args[0], "id", 42)


def test_post_pago_registra_y_devuelve_201(api, monkeypatch):
    client, session = api
    monkeypatch.setattr("app.services.pago.hoy_bogota", lambda: date(2027, 1, 31))
    session.scalar.side_effect = [vehiculo(), None]
    guardar_con_id(session)

    respuesta = client.post("/pagos", json={"placa": " abc123 ", "referencia": " REC-1 "})

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["id"] == 42
    assert cuerpo["placa"] == "ABC123"
    assert cuerpo["referencia"] == "REC-1"
    assert cuerpo["valor"] == 250000
    assert cuerpo["dia_corte"] == 31
    assert cuerpo["inicio_ciclo"] == "2027-01-31"
    assert cuerpo["vencimiento_ciclo"] == "2027-02-28"
    assert cuerpo["estado"] == "ACTIVO"
    assert cuerpo["usuario"] == "Prueba"
    session.commit.assert_called_once()


def test_post_pago_de_vehiculo_inexistente_responde_404(api):
    client, session = api
    session.scalar.return_value = None

    respuesta = client.post("/pagos", json={"placa": "ZZZ999", "referencia": "REC-1"})

    assert respuesta.status_code == 404
    assert respuesta.json() == {"detail": "Vehículo no encontrado"}


def test_post_pago_con_referencia_repetida_responde_409(api, monkeypatch):
    client, session = api
    monkeypatch.setattr("app.services.pago.hoy_bogota", lambda: date(2027, 1, 31))
    session.scalar.side_effect = [vehiculo(), 3]

    respuesta = client.post("/pagos", json={"placa": "ABC123", "referencia": "REC-1"})

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == (
        "La referencia del recibo ya está registrada en un pago activo."
    )


def test_post_pago_con_dos_ciclos_adelantados_responde_409(api, monkeypatch):
    client, session = api
    monkeypatch.setattr("app.services.pago.hoy_bogota", lambda: date(2027, 1, 31))
    actual = con_pago(vehiculo(), date(2027, 3, 1), referencia="R-0")
    session.scalar.side_effect = [actual, None]

    respuesta = client.post("/pagos", json={"placa": "ABC123", "referencia": "REC-1"})

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "Solo se puede pagar un ciclo por adelantado."


@pytest.mark.parametrize("cuerpo", [
    {"placa": "ABC123"},
    {"placa": "ABC123", "referencia": "   "},
    {"placa": "ABC123", "referencia": "REC-1", "valor": 1},
    {"placa": "ABC123", "referencia": "REC-1", "correo": "sin-arroba"},
])
def test_post_pago_valida_el_cuerpo(api, cuerpo):
    client, _ = api

    assert client.post("/pagos", json=cuerpo).status_code == 422


def test_post_anular_marca_el_pago(api):
    client, session = api
    usuario = usuario_de_prueba(id=1)
    actual = vehiculo()
    pago = con_pago(actual, date(2027, 2, 28), referencia="R-1").pagos[0]
    pago.id = 12
    pago.usuario = usuario
    pago.fecha_hora = datetime(2027, 1, 1, tzinfo=timezone.utc)
    session.get.return_value = pago

    respuesta = client.post("/pagos/12/anular", json={"motivo": "Pago duplicado"})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "ANULADO"
    assert cuerpo["motivo_anulacion"] == "Pago duplicado"


def test_post_anular_valida_el_motivo(api):
    client, _ = api

    respuesta = client.post("/pagos/12/anular", json={"motivo": "Porque sí"})

    assert respuesta.status_code == 422


def test_post_anular_un_pago_que_no_es_el_ultimo_responde_409(api):
    client, session = api
    usuario = usuario_de_prueba(id=1)
    actual = vehiculo()
    primero = con_pago(actual, date(2027, 1, 31), referencia="R-1").pagos[0]
    primero.id = 12
    primero.fecha_hora = datetime(2027, 1, 1, tzinfo=timezone.utc)
    primero.usuario = usuario
    ultimo = con_pago(actual, date(2027, 2, 28), referencia="R-2").pagos[-1]
    ultimo.id = 13
    ultimo.fecha_hora = datetime(2027, 2, 1, tzinfo=timezone.utc)
    ultimo.usuario = usuario
    session.get.return_value = primero

    respuesta = client.post("/pagos/12/anular", json={"motivo": "Otro"})

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == (
        "Solo se puede anular el último pago activo del vehículo."
    )


def test_get_historial_devuelve_la_pagina(api):
    client, session = api
    usuario = usuario_de_prueba(id=1)
    actual = vehiculo()
    pago = con_pago(actual, date(2027, 2, 28), referencia="R-1").pagos[0]
    pago.id = 12
    pago.usuario = usuario
    pago.fecha_hora = datetime(2027, 1, 1, tzinfo=timezone.utc)
    session.scalar.side_effect = [actual, 1]
    session.scalars.return_value.all.return_value = [pago]

    respuesta = client.get("/pagos", params={"placa": " abc123 ", "pagina": 2, "tamano": 5})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["total"] == 1
    assert cuerpo["pagina"] == 2 and cuerpo["tamano"] == 5
    assert [item["referencia"] for item in cuerpo["items"]] == ["R-1"]
    assert cuerpo["items"][0]["usuario"] == "Prueba"
    assert cuerpo["items"][0]["estado"] == "ACTIVO"


@pytest.mark.parametrize("parametros", [
    {},
    {"placa": ""},
    {"placa": "ABC123", "pagina": 0},
    {"placa": "ABC123", "tamano": 0},
    {"placa": "ABC123", "tamano": 101},
])
def test_get_historial_valida_parametros(api, parametros):
    client, _ = api

    assert client.get("/pagos", params=parametros).status_code == 422
