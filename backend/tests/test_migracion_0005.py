"""Migración 0005 en modo SQL offline: no abre conexión ni toca datos reales."""
from io import StringIO
from pathlib import Path

from alembic import command
from alembic.config import Config

HASH_TEMPORAL = "$2b$12$x/pxVMzR2xesb0vERJcYVuOjT75NDf5JyIiKurS2mYxJAhUIU6a6C"


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


def test_migracion_0005_offline_renombra_operador_a_usuario():
    sql = sql_de_migracion("0004:0005")

    assert "ALTER TABLE operador RENAME TO usuario;" in sql
    assert "ALTER TABLE usuario RENAME CONSTRAINT operador_pkey TO usuario_pkey;" in sql
    assert (
        "ALTER TABLE usuario RENAME CONSTRAINT ck_operador_nombre_no_vacio "
        "TO ck_usuario_nombre_no_vacio;" in sql
    )
    assert (
        "ALTER TABLE usuario RENAME CONSTRAINT ck_operador_telefono_no_vacio "
        "TO ck_usuario_telefono_no_vacio;" in sql
    )

    # Las FKs de estancia se renombran sin recrear la tabla ni sus datos.
    assert "ALTER TABLE estancia RENAME operador_entrada_id TO usuario_entrada_id;" in sql
    assert "ALTER TABLE estancia RENAME operador_salida_id TO usuario_salida_id;" in sql
    assert (
        "ALTER TABLE estancia RENAME CONSTRAINT fk_estancia_operador_entrada "
        "TO fk_estancia_usuario_entrada;" in sql
    )
    assert (
        "ALTER TABLE estancia RENAME CONSTRAINT fk_estancia_operador_salida "
        "TO fk_estancia_usuario_salida;" in sql
    )

    # Columnas nuevas de la cuenta, con valores por defecto seguros.
    for columna, definicion in [
        ("documento", "TEXT"),
        ("usuario", "TEXT"),
        ("password_hash", "TEXT"),
        ("rol", "TEXT"),
        ("activo", "BOOLEAN DEFAULT true NOT NULL"),
        ("correo", "TEXT"),
        ("direccion", "TEXT"),
        ("creado_en", "TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL"),
        ("actualizado_en", "TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL"),
    ]:
        assert f"ALTER TABLE usuario ADD COLUMN {columna} {definicion};" in sql

    # Las cuentas existentes reciben credenciales temporales y rol OPERADOR.
    assert "UPDATE usuario SET documento = 'DOC' || id, usuario = 'op' || id" in sql
    assert f"password_hash = '{HASH_TEMPORAL}'" in sql
    assert "rol = 'OPERADOR', activo = true WHERE documento IS NULL;" in sql

    for columna in ("documento", "usuario", "password_hash", "rol"):
        assert f"ALTER TABLE usuario ALTER COLUMN {columna} SET NOT NULL;" in sql

    for restriccion, definicion in [
        ("uq_usuario_documento", "UNIQUE (documento)"),
        ("uq_usuario_usuario", "UNIQUE (usuario)"),
        ("ck_usuario_documento_no_vacio", "CHECK (documento ~ '[^[:space:]]')"),
        ("ck_usuario_usuario_no_vacio", "CHECK (usuario ~ '[^[:space:]]')"),
        (
            "ck_usuario_usuario_normalizado",
            "CHECK (usuario = lower(regexp_replace(usuario, "
            "'^[[:space:]]+|[[:space:]]+$', '', 'g')))",
        ),
        ("ck_usuario_rol", "CHECK (rol IN ('ADMINISTRADOR', 'OPERADOR'))"),
    ]:
        assert f"ALTER TABLE usuario ADD CONSTRAINT {restriccion} {definicion};" in sql

    # No se recrean tablas ni se pierden datos.
    assert "CREATE TABLE" not in sql
    assert "DROP TABLE" not in sql
    assert "DELETE FROM" not in sql


def test_migracion_0005_offline_downgrade_revierte_el_esquema():
    sql = sql_de_migracion("0005:0004", upgrade=False)

    for restriccion in (
        "ck_usuario_rol",
        "ck_usuario_usuario_normalizado",
        "ck_usuario_usuario_no_vacio",
        "ck_usuario_documento_no_vacio",
        "uq_usuario_usuario",
        "uq_usuario_documento",
    ):
        assert f"ALTER TABLE usuario DROP CONSTRAINT {restriccion};" in sql

    orden_columnas = [
        "actualizado_en",
        "creado_en",
        "direccion",
        "correo",
        "activo",
        "rol",
        "password_hash",
        "usuario",
        "documento",
    ]
    posiciones = [sql.index(f"ALTER TABLE usuario DROP COLUMN {c};") for c in orden_columnas]
    assert posiciones == sorted(posiciones)

    assert (
        "ALTER TABLE estancia RENAME CONSTRAINT fk_estancia_usuario_salida "
        "TO fk_estancia_operador_salida;" in sql
    )
    assert (
        "ALTER TABLE estancia RENAME CONSTRAINT fk_estancia_usuario_entrada "
        "TO fk_estancia_operador_entrada;" in sql
    )
    assert "ALTER TABLE estancia RENAME usuario_salida_id TO operador_salida_id;" in sql
    assert "ALTER TABLE estancia RENAME usuario_entrada_id TO operador_entrada_id;" in sql
    assert "ALTER TABLE usuario RENAME TO operador;" in sql
    assert "DROP TABLE" not in sql
    assert "DELETE FROM" not in sql
