import importlib.util
from datetime import date
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app.models import Base, Celda, Operador, Vehiculo

VENCIMIENTO = date(2027, 1, 31)


def test_normalizes_unique_identifiers_on_creation_and_assignment():
    vehicle = Vehiculo(placa=" \tabc123\n", color="Azul", modelo=2025, marca="Marca",
                       tipo="MOTO", fecha_vencimiento=VENCIMIENTO)
    cell = Celda(codigo=" a-01 ", tipo="AUTO")
    assert vehicle.placa == "ABC123"
    assert cell.codigo == "A-01"
    vehicle.placa = " xyz789 "
    cell.codigo = " b-02 "
    assert vehicle.placa == "XYZ789"
    assert cell.codigo == "B-02"


@pytest.mark.parametrize("model,attribute", [
    (Vehiculo, "placa"), (Vehiculo, "color"), (Vehiculo, "marca"),
    (Vehiculo, "tipo"), (Celda, "codigo"), (Celda, "tipo"), (Operador, "nombre"),
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
    assert Operador(telefono="+57 00123").telefono == "+57 00123"
    with pytest.raises(ValueError, match="tipo debe ser AUTO o MOTO."):
        Celda(tipo="Categoría futura")


def test_telefono_es_opcional():
    assert Operador(nombre="Prueba").telefono is None
    with pytest.raises(ValueError):
        Operador(nombre="Prueba", telefono="  ")


def test_required_columns_and_identity():
    for name in ("vehiculo", "celda", "operador"):
        table = Base.metadata.tables[name]
        assert isinstance(table.c.id.type, sa.BigInteger)
        assert table.c.id.identity.always is True
    assert all(not column.nullable for column in Base.metadata.tables["vehiculo"].columns)
    assert all(not column.nullable for column in Base.metadata.tables["celda"].columns)
    assert Base.metadata.tables["operador"].c.telefono.nullable is True


def test_migrations_match_models_without_connecting(monkeypatch):
    """Aplica 0001, 0003 y 0004 sobre un MetaData vacío; nunca abre conexión."""
    metadata = sa.MetaData()
    versions = Path(__file__).resolve().parents[1] / "migrations/versions"

    def create_table(name, *args):
        return sa.Table(name, metadata, *args)

    def add_column(table_name, column, **kwargs):
        metadata.tables[table_name].append_column(column)

    def alter_column(table_name, column_name, **kwargs):
        column = metadata.tables[table_name].c[column_name]
        if "nullable" in kwargs:
            column.nullable = kwargs["nullable"]

    def create_check_constraint(name, table_name, condition, **kwargs):
        metadata.tables[table_name].append_constraint(
            sa.CheckConstraint(condition, name=name)
        )

    from alembic import context, op
    monkeypatch.setattr(op, "create_table", create_table)
    monkeypatch.setattr(op, "add_column", add_column)
    monkeypatch.setattr(op, "alter_column", alter_column)
    monkeypatch.setattr(op, "create_check_constraint", create_check_constraint)
    monkeypatch.setattr(op, "execute", lambda *args, **kwargs: None)
    monkeypatch.setattr(context, "is_offline_mode", lambda: True)

    for filename in ("0001_modelos_iniciales.py", "0003_mensualidad_y_tipo_celda.py",
                     "0004_telefono_operador_opcional.py"):
        spec = importlib.util.spec_from_file_location(filename, versions / filename)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        migration.upgrade()

    assert set(metadata.tables) == {"vehiculo", "celda", "operador"}
    for name, table in metadata.tables.items():
        model_table = Base.metadata.tables[name]
        assert [(c.name, str(c.type), c.nullable) for c in table.columns] == [
            (c.name, str(c.type), c.nullable) for c in model_table.columns
        ]

        def constraints(t):
            return {(c.name, str(c.sqltext)) for c in t.constraints if isinstance(c, sa.CheckConstraint)}

        assert constraints(table) == constraints(model_table)

        def unique_columns(t):
            return {tuple(c.columns.keys()) for c in t.constraints if isinstance(c, sa.UniqueConstraint)}

        assert unique_columns(table) == unique_columns(model_table)
        ddl = str(CreateTable(table).compile(dialect=postgresql.dialect()))
        assert "BIGINT GENERATED ALWAYS AS IDENTITY" in ddl
