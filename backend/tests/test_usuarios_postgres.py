"""CRUD de usuarios en autos_colombia, sin DDL y con rollback de los datos nuevos."""
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.database import get_engine, get_session
from app.main import app
from app.models import Usuario

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "1", reason="Requiere PostgreSQL local."
)


def test_usuarios_structure_and_crud():
    with get_engine().connect() as connection:
        transaction = connection.begin()
        try:
            assert connection.scalar(text("SELECT current_database()")) == "autos_colombia"
            assert int(connection.scalar(text("SELECT version_num FROM alembic_version"))) >= 5
            inspector = inspect(connection)

            columns = {c["name"]: c for c in inspector.get_columns("usuario")}
            assert set(columns) == {
                "id", "documento", "nombre", "telefono", "usuario", "password_hash",
                "rol", "activo", "correo", "direccion", "creado_en", "actualizado_en",
            }
            assert str(columns["id"]["type"]) == "BIGINT"
            assert columns["id"]["identity"]["always"] is True
            assert str(columns["activo"]["type"]) == "BOOLEAN"
            assert {name for name, c in columns.items() if c["nullable"]} == {
                "telefono", "correo", "direccion",
            }
            assert inspector.get_pk_constraint("usuario")["constrained_columns"] == ["id"]
            uniques = {tuple(u["column_names"]) for u in inspector.get_unique_constraints("usuario")}
            assert uniques == {("documento",), ("usuario",)}
            checks = {c["name"] for c in inspector.get_check_constraints("usuario")}
            assert {
                "ck_usuario_documento_no_vacio", "ck_usuario_nombre_no_vacio",
                "ck_usuario_telefono_no_vacio", "ck_usuario_usuario_no_vacio",
                "ck_usuario_usuario_normalizado", "ck_usuario_rol",
            } <= checks

            with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                def override():
                    yield session

                app.dependency_overrides[get_session] = override
                with TestClient(app) as client:
                    initial = client.get("/usuarios").json()
                    assert initial["offset"] == 0 and initial["limit"] == 20

                    sufijo = uuid4().hex
                    payload = {
                        "documento": f"TEST-DOC-{sufijo}",
                        "nombre": "  Operador de prueba  ",
                        "telefono": " +57 00123 ",
                        "usuario": f"TEST.{sufijo}",
                        "password": "Parkeo2026*",
                        "correo": "prueba@parkeo.local",
                    }
                    created = client.post("/usuarios", json=payload)
                    assert created.status_code == 201
                    item = created.json()
                    assert item["nombre"] == "Operador de prueba"
                    assert item["telefono"] == "+57 00123"
                    assert item["usuario"] == f"test.{sufijo}".lower()
                    assert item["rol"] == "OPERADOR"
                    assert item["activo"] is True
                    assert "password_hash" not in item

                    ruta = f"/usuarios/{item['id']}"
                    assert client.get(ruta).json() == item

                    duplicado_documento = client.post("/usuarios", json={
                        **payload, "usuario": f"otro.{sufijo}",
                    })
                    assert duplicado_documento.status_code == 409
                    assert duplicado_documento.json()["detail"] == "Ya existe una cuenta con ese documento."

                    duplicado_usuario = client.post("/usuarios", json={
                        **payload, "documento": f"TEST-OTRO-{sufijo}",
                    })
                    assert duplicado_usuario.status_code == 409
                    assert duplicado_usuario.json()["detail"] == "Ese nombre de usuario ya está en uso."

                    for query in ("limit=0", "limit=101", "offset=-1"):
                        assert client.get("/usuarios?" + query).status_code == 422
                    for invalid_id in ("0", "-1", "9223372036854775808", "abc"):
                        assert client.get("/usuarios/" + invalid_id).status_code == 422
                    for invalid in ({"nombre": None}, {"documento": " \t"}, {"usuario": ""},
                                    {"id": 2}, {"rol": "ADMINISTRADOR"},
                                    {"password": "OtraClave1*"}):
                        assert client.patch(ruta, json=invalid).status_code == 422

                    changed = client.patch(ruta, json={"telefono": " 00045 "})
                    assert changed.status_code == 200
                    item["telefono"] = "00045"
                    assert changed.json()["telefono"] == "00045"

                    estado = client.patch(f"{ruta}/estado", json={"activo": False})
                    assert estado.status_code == 200
                    assert estado.json()["activo"] is False

                    restablecida = client.post(f"{ruta}/restablecer-password",
                                               json={"password": "NuevaClave2026*"})
                    assert restablecida.status_code == 200
                    assert restablecida.json()["id"] == item["id"]

                    guardado = session.get(Usuario, item["id"])
                    assert guardado.activo is False
                    assert guardado.password_hash != "NuevaClave2026*"
                    assert guardado.password_hash.startswith("$2")

                    assert client.get("/health").json() == {"status": "ok"}
                    assert client.get("/vehiculos?limit=1").status_code == 200
                    assert client.get("/celdas?limit=1").status_code == 200
        finally:
            app.dependency_overrides.pop(get_session, None)
            transaction.rollback()
