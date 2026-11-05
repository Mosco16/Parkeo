from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest
import sqlalchemy as sa

from app.models import Estancia, Usuario

ENTRADA = datetime(2026, 10, 19, 10, tzinfo=timezone.utc)


def nuevo_usuario(usuario_id: int | None = 7) -> Usuario:
    return Usuario(
        id=usuario_id,
        documento="1001",
        nombre="Prueba",
        telefono="001",
        usuario="prueba",
        password_hash="hash-de-prueba",
        rol="OPERADOR",
    )


def test_cerrar_asigna_fecha_relacion_e_id_sin_sesion():
    estancia = Estancia(entrada=ENTRADA)
    usuario = nuevo_usuario()
    assert estancia.esta_abierta() is True
    # Misma hora absoluta con otro huso: la igualdad está permitida.
    salida = ENTRADA.astimezone(timezone(timedelta(hours=-5)))
    estancia.cerrar(salida, usuario)
    assert estancia.esta_abierta() is False
    assert estancia.salida == salida
    assert estancia.usuario_salida is usuario
    assert estancia.usuario_salida_id == 7
    with pytest.raises(ValueError, match="cerrada"):
        estancia.cerrar(ENTRADA + timedelta(hours=1), usuario)
    assert estancia.salida == salida


@pytest.mark.parametrize("salida", [None, "2026-10-19", datetime(2026, 10, 19), ENTRADA - timedelta(microseconds=1)])
def test_rechaza_fecha_invalida_sin_cambiar_estado(salida):
    estancia = Estancia(entrada=ENTRADA)
    with pytest.raises(ValueError):
        estancia.cerrar(salida, nuevo_usuario())
    assert estancia.esta_abierta()
    assert estancia.usuario_salida is None
    assert estancia.usuario_salida_id is None


@pytest.mark.parametrize("entrada", [None, datetime(2026, 10, 19)])
def test_cerrar_requiere_entrada_cargada_con_zona(entrada):
    with pytest.raises(ValueError, match="entrada"):
        Estancia(entrada=entrada).cerrar(ENTRADA, nuevo_usuario())


@pytest.mark.parametrize("usuario", [None, 7, nuevo_usuario(usuario_id=None)])
def test_usuario_invalido_no_deja_cierre_parcial(usuario):
    estancia = Estancia(entrada=ENTRADA)
    with pytest.raises(ValueError, match="usuario"):
        estancia.cerrar(ENTRADA, usuario)
    assert estancia.salida is None
    assert estancia.usuario_salida_id is None


def test_relaciones_y_columnas():
    mapper = sa.inspect(Estancia)
    assert mapper.relationships.usuario_entrada.local_columns == {
        Estancia.__table__.c.usuario_entrada_id
    }
    assert mapper.relationships.usuario_salida.local_columns == {
        Estancia.__table__.c.usuario_salida_id
    }
    for relation in mapper.relationships:
        assert not relation.cascade.delete and not relation.cascade.delete_orphan
    table = Estancia.__table__
    assert {c.name for c in table.c if c.nullable} == {"salida", "usuario_salida_id"}
    assert isinstance(table.c.id.type, sa.BigInteger) and table.c.id.identity.always
    assert table.c.entrada.type.timezone and table.c.salida.type.timezone
    assert str(table.c.entrada.server_default.arg) == "now()"
    assert len(table.foreign_keys) == 4
    assert all(fk.ondelete == "RESTRICT" for fk in table.foreign_keys)


def test_alembic_offline_solo_agrega_estancia():
    output = StringIO()
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"), output_buffer=output)
    command.upgrade(config, "0001:0002", sql=True)
    sql = output.getvalue()
    assert "CREATE TABLE estancia" in sql
    assert "CREATE TABLE vehiculo" not in sql
    assert "DROP TABLE" not in sql
    assert sql.count("WHERE salida IS NULL") == 2
    assert sql.count("ON DELETE RESTRICT") == 4
    assert "TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL" in sql
    assert "CHECK (salida >= entrada)" in sql
    assert "CHECK ((salida IS NULL) = (operador_salida_id IS NULL))" in sql
    assert "CREATE INDEX ix_estancia_vehiculo_entrada ON estancia (vehiculo_id, entrada)" in sql
