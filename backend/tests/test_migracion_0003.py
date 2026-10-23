"""Migración 0003 en modo SQL offline: no abre conexión ni toca estancia."""
from io import StringIO
from pathlib import Path

from alembic import command
from alembic.config import Config


def sql_de_migracion(rango: str) -> str:
    output = StringIO()
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"),
                    output_buffer=output)
    command.upgrade(config, rango, sql=True)
    return output.getvalue()


def test_migracion_0003_offline_agrega_vencimiento_y_tipo():
    sql = sql_de_migracion("0002:0003")
    assert "ALTER TABLE vehiculo ADD COLUMN fecha_vencimiento DATE;" in sql
    assert "UPDATE vehiculo SET fecha_vencimiento = CURRENT_DATE + 30" in sql
    assert "ALTER TABLE vehiculo ALTER COLUMN fecha_vencimiento SET NOT NULL;" in sql
    assert "ALTER TABLE celda ADD CONSTRAINT ck_celda_tipo CHECK (tipo IN ('AUTO', 'MOTO'));" in sql
    # La tabla estancia no se modifica en esta revisión.
    assert "estancia" not in sql.lower()
    assert "DROP TABLE" not in sql


def test_migracion_0003_offline_no_regenera_tablas_existentes():
    sql = sql_de_migracion("0002:0003")
    assert "CREATE TABLE vehiculo" not in sql
    assert "CREATE TABLE celda" not in sql
    assert "CREATE TABLE operador" not in sql
