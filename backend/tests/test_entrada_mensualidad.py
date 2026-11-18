"""S11 / RN-ENT-03: la entrada se bloquea con la mensualidad derivada vencida.

Sin PostgreSQL: sesión simulada con un vehículo en memoria y sus pagos activos.
"""
from datetime import timedelta
from unittest.mock import MagicMock

import pytest

from app.models import Vehiculo
from app.schemas.estancia import EntradaCrear
from app.services.ciclo import hoy_bogota
from app.services.estancia import EstanciaError, ServicioEstancia

from conftest import con_pago, usuario_de_prueba

PAGO_PENDIENTE = "Pago pendiente: la mensualidad está vencida."


def vehiculo_con(pago: bool, dias: int | None = None) -> Vehiculo:
    vehiculo = Vehiculo(
        id=1, placa="ABC123", color="Azul", modelo=2025, marca="Marca",
        tipo="AUTOMOVIL", avisos_autorizados=False,
    )
    if pago:
        con_pago(vehiculo, hoy_bogota() + timedelta(days=dias or 0))
    return vehiculo


def test_entrada_con_mensualidad_vigente_no_se_bloquea(monkeypatch):
    session = MagicMock()
    session.scalar.side_effect = [vehiculo_con(True, dias=5), None]
    session.in_transaction.return_value = False
    monkeypatch.setattr(ServicioEstancia, "_celda_libre", lambda self, tipo, bloquear: None)

    # Sin celdas libres el error es otro: no es el bloqueo por mensualidad.
    with pytest.raises(EstanciaError) as error:
        ServicioEstancia(session).entrada(EntradaCrear(placa="ABC123"), usuario_de_prueba())

    assert error.value.detail != PAGO_PENDIENTE
    assert error.value.status_code == 409


@pytest.mark.parametrize("dias", [0, -5])
def test_entrada_con_mensualidad_vencida_responde_409(dias):
    session = MagicMock()
    session.scalar.return_value = vehiculo_con(True, dias=dias)

    with pytest.raises(EstanciaError) as error:
        ServicioEstancia(session).entrada(EntradaCrear(placa="ABC123"), usuario_de_prueba())

    assert error.value.status_code == 409
    assert error.value.detail == PAGO_PENDIENTE


def test_entrada_sin_pagos_activos_responde_409():
    """RN-VIG-05: sin pagos no hay vencimiento y la mensualidad está vencida."""
    session = MagicMock()
    session.scalar.return_value = vehiculo_con(False)

    with pytest.raises(EstanciaError) as error:
        ServicioEstancia(session).entrada(EntradaCrear(placa="ABC123"), usuario_de_prueba())

    assert error.value.status_code == 409
    assert error.value.detail == PAGO_PENDIENTE


def test_entrada_de_vehiculo_inexistente_responde_404():
    session = MagicMock()
    session.scalar.return_value = None

    with pytest.raises(EstanciaError) as error:
        ServicioEstancia(session).entrada(EntradaCrear(placa="ZZZ999"), usuario_de_prueba())

    assert error.value.status_code == 404
