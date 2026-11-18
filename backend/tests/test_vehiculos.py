from types import SimpleNamespace
from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.models import Vehiculo
from app.schemas.vehiculo import VehiculoActualizar, VehiculoCrear, VehiculoRespuesta
from app.services.ciclo import hoy_bogota
from app.services.vehiculo import VehiculoError, delete_vehicle

from conftest import con_pago


def nuevo_vehiculo(**cambios) -> Vehiculo:
    datos = {
        "id": 1,
        "placa": "ABC123",
        "color": "Azul",
        "modelo": 2025,
        "marca": "Marca",
        "tipo": "AUTOMOVIL",
        "avisos_autorizados": False,
    }
    datos.update(cambios)
    return Vehiculo(**datos)


@pytest.mark.parametrize("field", ["placa", "color", "modelo", "marca", "tipo", "correo"])
def test_patch_rejects_explicit_null(field):
    with pytest.raises(ValidationError):
        VehiculoActualizar(**{field: None})


@pytest.mark.parametrize("field", ["placa", "color", "marca", "tipo"])
def test_patch_rejects_blank_text(field):
    with pytest.raises(ValidationError):
        VehiculoActualizar(**{field: " \t\n"})


def test_patch_only_supplied_fields_and_no_id():
    assert VehiculoActualizar(placa=" abc123 ").model_dump(exclude_unset=True) == {"placa": "ABC123"}
    assert VehiculoActualizar().model_dump(exclude_unset=True) == {}
    with pytest.raises(ValidationError):
        VehiculoActualizar(id=1)


def test_creation_requires_every_field():
    with pytest.raises(ValidationError):
        VehiculoCrear(placa="ABC123")


def test_creation_no_acepta_vencimiento_manual_y_valida_correo():
    # RN-VIG-01: el vencimiento se deriva de los pagos, no se escribe a mano.
    with pytest.raises(ValidationError):
        VehiculoCrear(placa="ABC123", color="Azul", modelo=2025, marca="Marca",
                      tipo="MOTO", fecha_vencimiento="2027-01-31")
    creado = VehiculoCrear(placa=" ABC123 ", color="Azul", modelo=2025, marca="Marca",
                           tipo="MOTO", correo=" Dueno@Correo.CO ")
    assert creado.placa == "ABC123" and creado.correo == "dueno@correo.co"
    with pytest.raises(ValidationError):
        VehiculoCrear(placa="ABC123", color="Azul", modelo=2025, marca="Marca",
                      tipo="MOTO", correo="sin-arroba")


def test_respuesta_expone_vencimiento_derivado_y_mensualidad():
    """S12: el vencimiento y la mensualidad son de solo lectura y derivados."""
    hoy = hoy_bogota()
    vehiculo = con_pago(nuevo_vehiculo(), hoy + timedelta(days=5))

    respuesta = VehiculoRespuesta.model_validate(vehiculo)

    assert respuesta.fecha_vencimiento == hoy + timedelta(days=5)
    assert respuesta.mensualidad == "VIGENTE"
    assert set(respuesta.model_dump()) == {
        "id", "placa", "color", "modelo", "marca", "tipo", "correo",
        "avisos_autorizados", "fecha_vencimiento", "mensualidad",
    }


def test_respuesta_sin_pagos_esta_vencida():
    respuesta = VehiculoRespuesta.model_validate(nuevo_vehiculo())

    assert respuesta.fecha_vencimiento is None
    assert respuesta.mensualidad == "VENCIDA"


def test_respuesta_con_vencimiento_hoy_ya_esta_vencida():
    """RN-VIG-03: si vence hoy, la mensualidad ya figura VENCIDA."""
    vehiculo = con_pago(nuevo_vehiculo(), hoy_bogota())

    assert VehiculoRespuesta.model_validate(vehiculo).mensualidad == "VENCIDA"


def test_delete_foreign_key_conflict_rolls_back_without_related_deletes():
    session = MagicMock()
    vehicle = session.get.return_value
    driver_error = Exception("private database details")
    driver_error.sqlstate = "23503"
    driver_error.diag = SimpleNamespace(constraint_name="some_foreign_key")
    session.commit.side_effect = IntegrityError("DELETE", {}, driver_error)
    with pytest.raises(VehiculoError) as result:
        delete_vehicle(session, 1)
    assert result.value.status_code == 409
    assert "private" not in result.value.detail
    session.rollback.assert_called_once()
    session.delete.assert_called_once_with(vehicle)
