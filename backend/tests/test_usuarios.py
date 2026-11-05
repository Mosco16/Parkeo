"""Errores HTTP y rollback del módulo de usuarios sin depender de PostgreSQL."""
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.database import get_session
from app.main import app
from app.models import Usuario
from app.schemas.usuario import UsuarioCrear


def usuario_de_prueba(**cambios) -> Usuario:
    datos = {
        "id": 1,
        "documento": "1001",
        "nombre": "Prueba",
        "telefono": "001",
        "usuario": "prueba",
        "password_hash": "hash-de-prueba",
        "rol": "OPERADOR",
        "activo": True,
        "correo": None,
        "direccion": None,
        "creado_en": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "actualizado_en": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }
    datos.update(cambios)
    return Usuario(**datos)


@pytest.fixture
def api():
    session = MagicMock()
    session.get.return_value = usuario_de_prueba()

    def override():
        yield session

    app.dependency_overrides[get_session] = override
    try:
        with TestClient(app) as client:
            yield client, session
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.parametrize("field,value", [
    ("documento", None), ("documento", ""), ("documento", " \t\n"), ("documento", 123),
    ("nombre", None), ("nombre", ""), ("nombre", " \t\n"), ("nombre", 123),
    ("usuario", None), ("usuario", ""), ("usuario", " \t\n"), ("usuario", 123),
    ("password", None), ("password", ""), ("password", " \t\n"), ("password", 123),
    ("password", "corta"),
    # Teléfono, correo y dirección son opcionales: solo se valida lo enviado.
    ("telefono", ""), ("telefono", " \t\n"), ("telefono", 123),
    ("correo", ""), ("correo", 123),
    ("direccion", ""), ("direccion", 123),
])
def test_invalid_fields_are_422_without_writes(api, field, value):
    client, session = api
    payload = {
        "documento": "1001",
        "nombre": "Prueba",
        "usuario": "prueba",
        "password": "Parkeo2026*",
        field: value,
    }
    assert client.post("/usuarios", json=payload).status_code == 422
    assert client.patch("/usuarios/1", json={field: value}).status_code == 422
    session.commit.assert_not_called()


@pytest.mark.parametrize("payload", [{}, {"nombre": "Prueba", "telefono": "001"},
                                     {"documento": "1001", "nombre": "Prueba",
                                      "usuario": "prueba", "password": "Parkeo2026*", "id": 1},
                                     {"documento": "1001", "nombre": "Prueba",
                                      "usuario": "prueba", "password": "Parkeo2026*", "rol": "ADMINISTRADOR"}])
def test_creation_requires_fields_and_forbids_id_y_rol(api, payload):
    client, session = api
    assert client.post("/usuarios", json=payload).status_code == 422
    session.commit.assert_not_called()


def test_datos_opcionales_y_usuario_normalizado():
    datos = UsuarioCrear(documento=" 1001 ", nombre=" Prueba ", usuario=" Ana.Gomez ",
                         password="Parkeo2026*")
    assert datos.telefono is None
    assert datos.correo is None
    assert datos.direccion is None
    assert datos.usuario == "ana.gomez"
    assert datos.documento == "1001"


def test_patch_forbids_id_rol_y_password(api):
    client, session = api
    for payload in ({"id": 2}, {"rol": "ADMINISTRADOR"}, {"password": "OtraClave1*"}):
        assert client.patch("/usuarios/1", json=payload).status_code == 422
    session.commit.assert_not_called()


def test_get_devuelve_la_cuenta_sin_password(api):
    client, _ = api
    respuesta = client.get("/usuarios/1")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["usuario"] == "prueba"
    assert "password" not in cuerpo and "password_hash" not in cuerpo


def test_no_se_puede_cambiar_el_estado_de_un_administrador(api):
    client, session = api
    session.get.return_value = usuario_de_prueba(rol="ADMINISTRADOR")
    resultado = client.patch("/usuarios/1/estado", json={"activo": False})
    assert resultado.status_code == 403


@pytest.mark.parametrize("constraint,detail", [
    ("uq_usuario_documento", "Ya existe una cuenta con ese documento."),
    ("uq_usuario_usuario", "Ese nombre de usuario ya está en uso."),
])
def test_duplicados_devuelven_409_con_mensaje_especifico(api, constraint, detail):
    client, session = api
    driver_error = Exception("PRIVATE DRIVER DETAILS")
    driver_error.sqlstate = "23505"
    driver_error.diag = type("Diag", (), {"constraint_name": constraint})()
    session.commit.side_effect = IntegrityError("INSERT", {}, driver_error)

    resultado = client.post("/usuarios", json={
        "documento": "1001", "nombre": "Prueba", "usuario": "prueba",
        "password": "Parkeo2026*",
    })

    assert resultado.status_code == 409
    assert resultado.json()["detail"] == detail
    assert "PRIVATE" not in resultado.text
    session.rollback.assert_called_once()


def test_database_failure_rolls_back_and_is_generic(api):
    client, session = api
    session.get.side_effect = SQLAlchemyError("PRIVATE DRIVER DETAILS")
    resultado = client.get("/usuarios/1")
    assert resultado.status_code == 503
    assert "PRIVATE" not in resultado.text
    session.rollback.assert_called_once()
