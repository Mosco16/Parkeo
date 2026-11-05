from datetime import date

import pytest
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app.models import Base, Celda, Usuario, Vehiculo

VENCIMIENTO = date(2027, 1, 31)


def nuevo_usuario(**cambios) -> Usuario:
    datos = {
        "documento": "1001",
        "nombre": "Prueba",
        "usuario": "prueba",
        "password_hash": "hash-de-prueba",
        "rol": "OPERADOR",
    }
    datos.update(cambios)
    return Usuario(**datos)


def test_normalizes_unique_identifiers_on_creation_and_assignment():
    vehicle = Vehiculo(placa=" \tabc123\n", color="Azul", modelo=2025, marca="Marca",
                       tipo="MOTO", fecha_vencimiento=VENCIMIENTO)
    cell = Celda(codigo=" a-01 ", tipo="AUTO")
    usuario = nuevo_usuario(usuario=" Ana.Gomez ")
    assert vehicle.placa == "ABC123"
    assert cell.codigo == "A-01"
    assert usuario.usuario == "ana.gomez"
    vehicle.placa = " xyz789 "
    cell.codigo = " b-02 "
    assert vehicle.placa == "XYZ789"
    assert cell.codigo == "B-02"


@pytest.mark.parametrize("model,attribute", [
    (Vehiculo, "placa"), (Vehiculo, "color"), (Vehiculo, "marca"),
    (Vehiculo, "tipo"), (Celda, "codigo"), (Celda, "tipo"),
    (Usuario, "documento"), (Usuario, "nombre"), (Usuario, "usuario"),
])
@pytest.mark.parametrize("value", ["", " \t\n", None])
def test_rejects_empty_text(model, attribute, value):
    with pytest.raises(ValueError):
        model(**{attribute: value})


@pytest.mark.parametrize("value", [0, 10000, True, "2025", 2025.5, None])
def test_rejects_invalid_year(value):
    with pytest.raises(ValueError):
        Vehiculo(modelo=value, fecha_vencimiento=VENCIMIENTO)


@pytest.mark.parametrize("value", ["MOTO", "AUTOMOVIL", "CAMIONETA"])
def test_vehicle_types(value):
    assert Vehiculo(tipo=value, fecha_vencimiento=VENCIMIENTO).tipo == value


def test_rejects_unknown_types_and_preserves_phone_text():
    with pytest.raises(ValueError):
        Vehiculo(tipo="CAMION", fecha_vencimiento=VENCIMIENTO)
    assert nuevo_usuario(telefono="+57 00123").telefono == "+57 00123"
    with pytest.raises(ValueError, match="tipo debe ser AUTO o MOTO."):
        Celda(tipo="Categoría futura")


def test_rol_solo_admite_administrador_u_operador():
    assert nuevo_usuario(rol="ADMINISTRADOR").es_administrador() is True
    assert nuevo_usuario(rol="OPERADOR").es_administrador() is False
    for valor in ("ADMIN", "", "admin", None):
        with pytest.raises(ValueError):
            nuevo_usuario(rol=valor)


def test_telefono_correo_y_direccion_son_opcionales():
    usuario = nuevo_usuario()
    assert usuario.telefono is None
    assert usuario.correo is None
    assert usuario.direccion is None
    with pytest.raises(ValueError):
        nuevo_usuario(telefono="  ")
    with pytest.raises(ValueError):
        nuevo_usuario(correo="  ")
    with pytest.raises(ValueError):
        nuevo_usuario(direccion="  ")


def test_required_columns_and_identity():
    for name in ("vehiculo", "celda", "usuario"):
        table = Base.metadata.tables[name]
        assert isinstance(table.c.id.type, sa.BigInteger)
        assert table.c.id.identity.always is True
    assert all(not column.nullable for column in Base.metadata.tables["vehiculo"].columns)
    assert all(not column.nullable for column in Base.metadata.tables["celda"].columns)
    usuario = Base.metadata.tables["usuario"]
    assert {column.name for column in usuario.columns if column.nullable} == {
        "telefono", "correo", "direccion",
    }
    assert usuario.c.activo.server_default is not None


def test_usuario_tiene_unicos_y_restricciones():
    tabla = Base.metadata.tables["usuario"]
    unicos = {
        tuple(constraint.columns.keys())
        for constraint in tabla.constraints
        if isinstance(constraint, sa.UniqueConstraint)
    }
    assert unicos == {("documento",), ("usuario",)}
    checks = {
        constraint.name
        for constraint in tabla.constraints
        if isinstance(constraint, sa.CheckConstraint)
    }
    assert {
        "ck_usuario_documento_no_vacio",
        "ck_usuario_nombre_no_vacio",
        "ck_usuario_telefono_no_vacio",
        "ck_usuario_usuario_no_vacio",
        "ck_usuario_usuario_normalizado",
        "ck_usuario_rol",
    } <= checks


def test_usuario_compila_ddl_postgresql():
    ddl = str(CreateTable(Base.metadata.tables["usuario"]).compile(dialect=postgresql.dialect()))
    assert "BIGINT GENERATED ALWAYS AS IDENTITY" in ddl
    assert "rol IN ('ADMINISTRADOR', 'OPERADOR')" in ddl
    assert "usuario = lower(regexp_replace(usuario" in ddl
