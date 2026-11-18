"""Migraciones 0008 y 0009 en modo SQL offline: no abren conexión ni tocan datos."""
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


def test_migracion_0008_offline_crea_pago_e_indice_parcial():
    sql = sql_de_migracion("0007:0008")
    assert "CREATE TABLE pago" in sql
    assert "dia_corte INTEGER NOT NULL" in sql
    assert "vencimiento_ciclo DATE NOT NULL" in sql
    # RN-PAG-06: la referencia solo es única entre pagos activos.
    assert ("CREATE UNIQUE INDEX uq_pago_referencia_activa ON pago (referencia) "
            "WHERE anulacion_fecha_hora IS NULL;") in sql
    assert "ck_pago_ciclo_orden" in sql
    assert "ck_pago_motivo_anulacion" in sql
    assert "CREATE TABLE vehiculo" not in sql


def test_migracion_0009_offline_agrega_correo_aviso_y_quita_vencimiento():
    sql = sql_de_migracion("0008:0009")
    assert "ALTER TABLE vehiculo ADD COLUMN correo TEXT;" in sql
    assert "ALTER TABLE vehiculo ADD COLUMN avisos_autorizados BOOLEAN DEFAULT false NOT NULL;" in sql
    assert "CREATE TABLE aviso" in sql
    # RN-AVI-02: un solo aviso ENVIADO por vehículo y vencimiento.
    assert ("CREATE UNIQUE INDEX uq_aviso_enviado ON aviso (vehiculo_id, fecha_vencimiento) "
            "WHERE resultado = 'ENVIADO';") in sql
    # RN-VIG-01: el vencimiento deja de ser una columna del vehículo.
    assert "ALTER TABLE vehiculo DROP COLUMN fecha_vencimiento;" in sql
    assert "CREATE TABLE pago" not in sql
