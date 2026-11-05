"""Inicio de sesión, token y permisos por rol sin depender de PostgreSQL."""

from functools import lru_cache
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.database import get_session
from app.main import app
from app.schemas.auth import LoginCrear
from app.security import decode_access_token, hash_password

from conftest import token_para, usuario_de_prueba

CLAVE = "Parkeo2026*"


@lru_cache(maxsize=1)
def hash_valido() -> str:
    """Un solo hash bcrypt por sesión de pruebas: el costo 12 es lento."""
    return hash_password(CLAVE)


@pytest.fixture
def api():
    session = MagicMock()
    session.get.return_value = usuario_de_prueba()
    session.scalar.return_value = usuario_de_prueba()
    session.scalars.return_value = []

    def override():
        yield session

    app.dependency_overrides[get_session] = override
    try:
        with TestClient(app) as client:
            yield client, session
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_login_exitoso_devuelve_token_y_rol(api):
    client, session = api
    session.scalar.return_value = usuario_de_prueba(
        password_hash=hash_valido(), rol="ADMINISTRADOR"
    )

    respuesta = client.post("/auth/login", json={"usuario": " Prueba ", "password": CLAVE})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["token_type"] == "bearer"
    assert cuerpo["usuario"]["rol"] == "ADMINISTRADOR"
    assert "password_hash" not in cuerpo["usuario"]
    claims = decode_access_token(cuerpo["access_token"])
    assert claims is not None
    assert claims["sub"] == "1"
    assert claims["rol"] == "ADMINISTRADOR"


def test_login_normaliza_el_nombre_de_usuario():
    assert LoginCrear(usuario=" Ana.Gomez ", password=CLAVE).usuario == "ana.gomez"


def test_login_password_incorrecta_es_401_generico(api):
    client, session = api
    session.scalar.return_value = usuario_de_prueba(password_hash=hash_valido())

    respuesta = client.post("/auth/login", json={"usuario": "prueba", "password": "otra-clave"})

    assert respuesta.status_code == 401
    assert respuesta.json()["detail"] == "Usuario o contraseña incorrectos."
    assert respuesta.headers["WWW-Authenticate"] == "Bearer"


def test_login_usuario_inexistente_usa_el_mismo_mensaje(api):
    client, session = api
    session.scalar.return_value = None

    respuesta = client.post("/auth/login", json={"usuario": "nadie", "password": CLAVE})

    assert respuesta.status_code == 401
    assert respuesta.json()["detail"] == "Usuario o contraseña incorrectos."


def test_login_cuenta_inactiva_es_403(api):
    client, session = api
    session.scalar.return_value = usuario_de_prueba(
        password_hash=hash_valido(), activo=False
    )

    respuesta = client.post("/auth/login", json={"usuario": "prueba", "password": CLAVE})

    assert respuesta.status_code == 403
    assert "inactiva" in respuesta.json()["detail"]


def test_login_con_base_caida_no_filtra_el_driver(api):
    client, session = api
    session.scalar.side_effect = SQLAlchemyError("PRIVATE DRIVER DETAILS")

    respuesta = client.post("/auth/login", json={"usuario": "prueba", "password": CLAVE})

    assert respuesta.status_code == 503
    assert "PRIVATE" not in respuesta.text
    session.rollback.assert_called_once()


@pytest.mark.parametrize("payload", [
    {},
    {"usuario": "prueba"},
    {"password": CLAVE},
    {"usuario": "", "password": CLAVE},
    {"usuario": " \t\n", "password": CLAVE},
    {"usuario": "prueba", "password": ""},
    {"usuario": "prueba", "password": " \t\n"},
    {"usuario": 123, "password": CLAVE},
    {"usuario": "prueba", "password": 123},
    {"usuario": "prueba", "password": CLAVE, "rol": "ADMINISTRADOR"},
    {"usuario": "prueba", "password": CLAVE, "token": "x"},
])
def test_login_payload_invalido_es_422(api, payload):
    client, session = api

    assert client.post("/auth/login", json=payload).status_code == 422
    session.scalar.assert_not_called()


def test_me_sin_token_es_401(api):
    client, _ = api

    respuesta = client.get("/auth/me")

    assert respuesta.status_code == 401
    assert respuesta.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize("scheme", ["Bearer", "bearer"])
def test_me_con_token_invalido_es_401(api, scheme):
    client, _ = api

    respuesta = client.get("/auth/me", headers={"Authorization": f"{scheme} no-es-un-token"})

    assert respuesta.status_code == 401
    assert "válido" in respuesta.json()["detail"]


def test_me_con_esquema_distinto_es_401(api):
    client, _ = api

    assert client.get("/auth/me", headers={"Authorization": "Basic abc"}).status_code == 401


def test_me_con_token_valido_devuelve_la_cuenta(api):
    client, _ = api

    respuesta = client.get("/auth/me", headers={"Authorization": f"Bearer {token_para(1)}"})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["id"] == 1
    assert cuerpo["usuario"] == "prueba"
    assert "password_hash" not in cuerpo


def test_me_desactiva_la_sesion_si_la_cuenta_esta_inactiva(api):
    client, session = api
    session.get.return_value = usuario_de_prueba(activo=False)

    respuesta = client.get("/auth/me", headers={"Authorization": f"Bearer {token_para(1)}"})

    assert respuesta.status_code == 403
    assert "inactiva" in respuesta.json()["detail"]


def test_me_rechaza_una_cuenta_eliminada(api):
    client, session = api
    session.get.return_value = None

    respuesta = client.get("/auth/me", headers={"Authorization": f"Bearer {token_para(1)}"})

    assert respuesta.status_code == 401


def test_me_con_base_caida_no_filtra_el_driver(api):
    client, session = api
    session.get.side_effect = SQLAlchemyError("PRIVATE DRIVER DETAILS")

    respuesta = client.get("/auth/me", headers={"Authorization": f"Bearer {token_para(1)}"})

    assert respuesta.status_code == 503
    assert "PRIVATE" not in respuesta.text


def test_health_y_openapi_siguen_siendo_publicos():
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        schema = client.get("/openapi.json")
        assert schema.status_code == 200
        assert "securitySchemes" in schema.json()["components"]


@pytest.mark.parametrize("ruta", ["/vehiculos", "/celdas", "/celdas/disponibilidad",
                                  "/estancias/vehiculo/ABC123", "/usuarios"])
def test_rutas_protegidas_exigen_token(ruta):
    with TestClient(app) as client:
        assert client.get(ruta).status_code == 401


def test_operador_no_puede_gestionar_cuentas(api):
    client, session = api
    session.get.return_value = usuario_de_prueba(rol="OPERADOR")

    respuesta = client.get("/usuarios", headers={"Authorization": f"Bearer {token_para(1)}"})

    assert respuesta.status_code == 403
    assert "administradora" in respuesta.json()["detail"]


def test_administrador_puede_listar_cuentas(api):
    client, session = api
    session.get.return_value = usuario_de_prueba(rol="ADMINISTRADOR")
    session.scalar.return_value = 0
    session.scalars.return_value = []

    respuesta = client.get(
        "/usuarios", headers={"Authorization": f"Bearer {token_para(1, 'ADMINISTRADOR')}"}
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"items": [], "total": 0, "offset": 0, "limit": 20}


def test_operador_no_puede_crear_celdas(api):
    client, session = api
    session.get.return_value = usuario_de_prueba(rol="OPERADOR")

    respuesta = client.post(
        "/celdas",
        json={"codigo": "X1", "tipo": "AUTO"},
        headers={"Authorization": f"Bearer {token_para(1)}"},
    )

    assert respuesta.status_code == 403


def test_token_de_otra_firma_es_rechazado():
    with TestClient(app) as client:
        respuesta = client.get(
            "/auth/me",
            headers={"Authorization": (
                "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
                "eyJzdWIiOiIxIn0.firma-invalida"
            )},
        )
        assert respuesta.status_code == 401
