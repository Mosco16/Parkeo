"""Migración 0006 en modo SQL offline: no abre conexión ni toca datos reales."""

from io import StringIO
from pathlib import Path

from alembic import command
from alembic.config import Config


def sql_de_migracion(rango: str, upgrade: bool = True) -> str:
    output = StringIO()
    config = Config(
        str(Path(__file__).resolve().parents[1] / "alembic.ini"), output_buffer=output
    )
    if upgrade:
        command.upgrade(config, rango, sql=True)
    else:
        command.downgrade(config, rango, sql=True)
    return output.getvalue()


def test_migracion_0006_agrega_activa_con_valor_por_defecto():
    sql = sql_de_migracion("0005:0006")

    assert "ALTER TABLE celda ADD COLUMN activa BOOLEAN DEFAULT true NOT NULL;" in sql
    # No se recrea la tabla ni se pierden celdas existentes.
    assert "CREATE TABLE celda" not in sql
    assert "DROP TABLE" not in sql
    assert "DELETE FROM" not in sql


def test_migracion_0006_downgrade_elimina_la_columna():
    sql = sql_de_migracion("0006:0005", upgrade=False)

    assert "ALTER TABLE celda DROP COLUMN activa;" in sql
    assert "DROP TABLE" not in sql
    assert "DELETE FROM" not in sql
