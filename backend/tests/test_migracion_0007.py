"""Migración 0007 en modo SQL offline: no abre conexión ni toca datos reales."""

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


def test_migracion_0007_crea_el_historial_con_fks_y_check():
    sql = sql_de_migracion("0006:0007")

    assert "CREATE TABLE cambio_celda" in sql
    for columna in (
        "estancia_id BIGINT NOT NULL",
        "celda_anterior_id BIGINT NOT NULL",
        "celda_nueva_id BIGINT NOT NULL",
        "usuario_id BIGINT NOT NULL",
        "fecha_hora TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL",
    ):
        assert columna in sql
    assert "ck_cambio_celda_celdas_distintas CHECK (celda_anterior_id <> celda_nueva_id)" in sql
    for fk in (
        "fk_cambio_celda_estancia",
        "fk_cambio_celda_celda_anterior",
        "fk_cambio_celda_celda_nueva",
        "fk_cambio_celda_usuario",
    ):
        assert fk in sql
    assert "CREATE INDEX ix_cambio_celda_fecha_hora ON cambio_celda (fecha_hora)" in sql
    # No se recrean tablas existentes ni se pierden datos.
    assert "CREATE TABLE estancia" not in sql
    assert "CREATE TABLE celda" not in sql
    assert "CREATE TABLE usuario" not in sql
    assert "DELETE FROM" not in sql


def test_migracion_0007_downgrade_elimina_indice_y_tabla():
    sql = sql_de_migracion("0007:0006", upgrade=False)

    assert "DROP INDEX ix_cambio_celda_fecha_hora" in sql
    assert "DROP TABLE cambio_celda" in sql
    assert "DROP TABLE estancia" not in sql
    assert "DELETE FROM" not in sql
