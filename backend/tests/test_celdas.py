"""Estados de celda y mantenimiento sin depender de PostgreSQL."""

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.models import Celda
from app.schemas.celda import CeldaEstado, CeldaDisponible, CeldaRespuesta
from app.services.celda import CeldaError, cambiar_estado, disponibilidad
from app.services.estancia import ServicioEstancia


def celda(celda_id: int, codigo: str, tipo: str = "AUTO", activa: bool = True) -> Celda:
    return Celda(id=celda_id, codigo=codigo, tipo=tipo, activa=activa)


def test_disponibilidad_distingue_los_tres_estados():
    session = MagicMock()
    session.scalars.side_effect = [
        [
            celda(1, "A1"),
            celda(2, "A2"),
            celda(3, "A3", activa=False),
            celda(4, "M1", tipo="MOTO"),
        ],
        [2],
    ]

    resultado = disponibilidad(session)

    estados = {c["id"]: c["estado"] for c in resultado["celdas"]}
    assert estados == {
        1: "DISPONIBLE",
        2: "OCUPADA",
        3: "MANTENIMIENTO",
        4: "DISPONIBLE",
    }
    assert resultado["cupo"]["AUTO"] == {"total": 3, "libres": 1}
    assert resultado["cupo"]["MOTO"] == {"total": 1, "libres": 1}
    assert {c["id"]: c["activa"] for c in resultado["celdas"]}[3] is False


def test_mantenimiento_tiene_prioridad_sobre_ocupada():
    session = MagicMock()
    # Una celda apagada nunca se ofrece, aunque tuviera una estancia abierta.
    session.scalars.side_effect = [[celda(1, "A1", activa=False)], [1]]

    resultado = disponibilidad(session)

    assert resultado["celdas"][0]["estado"] == "MANTENIMIENTO"
    assert resultado["cupo"]["AUTO"] == {"total": 1, "libres": 0}


def test_no_desactiva_una_celda_con_estancia_abierta():
    session = MagicMock()
    session.get.return_value = celda(1, "A1")
    session.scalar.return_value = 7

    with pytest.raises(CeldaError) as error:
        cambiar_estado(session, 1, False)

    assert error.value.status_code == 409
    assert "estancia abierta" in error.value.detail
    session.commit.assert_not_called()


def test_apaga_y_enciende_una_celda_libre():
    session = MagicMock()
    session.get.return_value = celda(1, "A1")
    session.scalar.return_value = None

    assert cambiar_estado(session, 1, False).activa is False
    session.commit.assert_called_once()
    assert cambiar_estado(session, 1, True).activa is True


def test_celda_inexistente_es_404():
    session = MagicMock()
    session.get.return_value = None

    with pytest.raises(CeldaError) as error:
        cambiar_estado(session, 99, False)

    assert error.value.status_code == 404


def test_el_estado_solo_acepta_un_booleano():
    assert CeldaEstado(activa=False).activa is False
    with pytest.raises(ValidationError):
        CeldaEstado(activa=None)
    with pytest.raises(ValidationError):
        CeldaEstado(activa="quizás")
    with pytest.raises(ValidationError):
        CeldaEstado(activa=True, extra=1)


def test_las_respuestas_incluyen_activa():
    respuesta = CeldaRespuesta(id=1, codigo="A1", tipo="AUTO", activa=True)
    assert respuesta.activa is True
    disponible = CeldaDisponible(
        id=1, codigo="A1", tipo="AUTO", activa=False, estado="MANTENIMIENTO"
    )
    assert disponible.activa is False


def test_la_entrada_solo_considera_celdas_activas():
    session = MagicMock()
    session.scalar.return_value = None

    assert ServicioEstancia(session)._celda_libre("AUTO", bloquear=False) is None

    consulta = str(session.scalar.call_args.args[0])
    assert "celda.activa" in consulta
    assert "IS true" in consulta
