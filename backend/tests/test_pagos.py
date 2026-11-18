"""Servicio de pagos con sesión simulada: reglas RN-PAG, RN-ANU y RN-HIS."""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from app.models import Pago, Vehiculo
from app.schemas.pago import PagoAnular, PagoCrear
from app.services.ciclo import hoy_bogota, mes_anterior_anclado, sumar_mes_anclado
from app.services.pago import (
    NO_ES_ULTIMO_PAGO,
    PAGO_YA_ANULADO,
    REFERENCIA_REPETIDA,
    TOPE_ADELANTADO,
    VEHICULO_NO_ENCONTRADO,
    PagoError,
    ServicioPago,
)

from conftest import usuario_de_prueba

HOY = date(2027, 1, 31)


@pytest.fixture
def reloj(monkeypatch):
    monkeypatch.setattr("app.services.pago.hoy_bogota", lambda: HOY)
    return HOY


def nuevo_vehiculo(**cambios) -> Vehiculo:
    datos = {
        "id": 1,
        "placa": "ABC123",
        "color": "Azul",
        "modelo": 2025,
        "marca": "Marca",
        "tipo": "AUTOMOVIL",
    }
    datos.update(cambios)
    return Vehiculo(**datos)


def nuevo_pago(vehiculo, usuario, vencimiento, referencia="R-1", **cambios) -> Pago:
    datos = {
        "id": cambios.pop("id", 10),
        "vehiculo": vehiculo,
        "usuario": usuario,
        "valor": 250000,
        "referencia": referencia,
        "fecha_hora": datetime(2027, 1, 1, tzinfo=timezone.utc),
        "dia_corte": vencimiento.day,
        "inicio_ciclo": mes_anterior_anclado(vencimiento, 31),
        "vencimiento_ciclo": vencimiento,
    }
    datos.update(cambios)
    return Pago(**datos)


def sesion_que_guarda(vehiculo, referencia_activa=None) -> MagicMock:
    session = MagicMock()
    session.scalar.side_effect = [vehiculo, referencia_activa]

    def flush_asigna_id():
        session.add.call_args.args[0].id = 77

    session.flush.side_effect = flush_asigna_id
    return session


def test_primer_pago_calcula_ciclo_valor_y_usuario(reloj):
    vehiculo = nuevo_vehiculo()
    usuario = usuario_de_prueba(id=5)
    session = sesion_que_guarda(vehiculo)

    resultado = ServicioPago(session).registrar(
        PagoCrear(placa=" abc123 ", referencia="  REC-001  "), usuario
    )

    pago = session.add.call_args.args[0]
    assert isinstance(pago, Pago)
    assert pago.referencia == "REC-001"
    assert pago.valor == 250000  # RN-VIG-04: tarifa de automóvil
    assert pago.dia_corte == 31
    assert pago.inicio_ciclo == HOY
    assert pago.vencimiento_ciclo == date(2027, 2, 28)
    assert pago.usuario_id == 5 or pago.usuario is usuario
    assert resultado.id == 77
    assert resultado.estado == "ACTIVO"
    assert resultado.placa == "ABC123"
    session.commit.assert_called_once()


def test_pago_a_tiempo_conserva_el_dia_de_corte(reloj):
    usuario = usuario_de_prueba(id=5)
    vehiculo = nuevo_vehiculo()
    anterior = nuevo_pago(vehiculo, usuario, date(2027, 2, 15), referencia="R-0")
    session = sesion_que_guarda(vehiculo)

    resultado = ServicioPago(session).registrar(
        PagoCrear(placa="ABC123", referencia="R-1"), usuario
    )

    # RN-VIG-02: pagar a tiempo encadena desde el vencimiento vigente.
    assert vehiculo.fecha_vencimiento == date(2027, 3, 15)
    assert resultado.dia_corte == 15
    assert resultado.inicio_ciclo == date(2027, 2, 15)
    assert resultado.vencimiento_ciclo == date(2027, 3, 15)
    assert anterior.estado == "ACTIVO"


def test_pago_vencido_reancla_el_corte_al_dia_del_pago(reloj):
    usuario = usuario_de_prueba(id=5)
    vehiculo = nuevo_vehiculo()
    nuevo_pago(vehiculo, usuario, date(2027, 1, 15), referencia="R-0")
    session = sesion_que_guarda(vehiculo)

    resultado = ServicioPago(session).registrar(
        PagoCrear(placa="ABC123", referencia="R-1"), usuario
    )

    assert resultado.dia_corte == 31
    assert resultado.inicio_ciclo == HOY
    assert resultado.vencimiento_ciclo == date(2027, 2, 28)


def test_moto_paga_la_tarifa_reducida(reloj):
    vehiculo = nuevo_vehiculo(tipo="MOTO")
    session = sesion_que_guarda(vehiculo)

    resultado = ServicioPago(session).registrar(
        PagoCrear(placa="ABC123", referencia="R-1"), usuario_de_prueba(id=5)
    )

    assert resultado.valor == 100000


def test_vehiculo_inexistente_responde_404(reloj):
    session = MagicMock()
    session.scalar.return_value = None

    with pytest.raises(PagoError) as error:
        ServicioPago(session).registrar(
            PagoCrear(placa="ZZZ999", referencia="R-1"), usuario_de_prueba()
        )

    assert error.value.status_code == 404
    assert error.value.detail == VEHICULO_NO_ENCONTRADO
    session.add.assert_not_called()


def test_referencia_activa_repetida_responde_409(reloj):
    session = sesion_que_guarda(nuevo_vehiculo(), referencia_activa=12)

    with pytest.raises(PagoError) as error:
        ServicioPago(session).registrar(
            PagoCrear(placa="ABC123", referencia="R-1"), usuario_de_prueba()
        )

    assert error.value.status_code == 409
    assert error.value.detail == REFERENCIA_REPETIDA
    session.add.assert_not_called()


def test_tope_de_un_ciclo_adelantado_responde_409(reloj):
    usuario = usuario_de_prueba()
    vehiculo = nuevo_vehiculo()
    vencimiento = sumar_mes_anclado(HOY, HOY.day)
    nuevo_pago(vehiculo, usuario, vencimiento + timedelta(days=1), referencia="R-0")
    session = sesion_que_guarda(vehiculo)

    with pytest.raises(PagoError) as error:
        ServicioPago(session).registrar(
            PagoCrear(placa="ABC123", referencia="R-1"), usuario
        )

    assert error.value.status_code == 409
    assert error.value.detail == TOPE_ADELANTADO
    session.add.assert_not_called()


def test_pagar_hasta_el_tope_esta_permitido(reloj):
    usuario = usuario_de_prueba()
    vehiculo = nuevo_vehiculo()
    # El vencimiento vigente es exactamente hoy + 1 mes: todavía se admite.
    nuevo_pago(vehiculo, usuario, sumar_mes_anclado(HOY, HOY.day), referencia="R-0")
    session = sesion_que_guarda(vehiculo)

    resultado = ServicioPago(session).registrar(
        PagoCrear(placa="ABC123", referencia="R-1"), usuario
    )

    assert resultado.inicio_ciclo == date(2027, 2, 28)


def test_guardar_correo_y_autorizar_avisos(reloj):
    vehiculo = nuevo_vehiculo()
    usuario = usuario_de_prueba(id=5)
    session = sesion_que_guarda(vehiculo)

    ServicioPago(session).registrar(
        PagoCrear(placa="ABC123", referencia="R-1",
                  correo=" Dueno@Correo.CO ", autorizar_avisos=True),
        usuario,
    )

    assert vehiculo.correo == "dueno@correo.co"
    assert vehiculo.avisos_autorizados is True
    assert vehiculo.autorizacion_usuario_id == 5
    assert vehiculo.autorizacion_fecha_hora is not None


def test_autorizar_sin_correo_responde_422(reloj):
    session = sesion_que_guarda(nuevo_vehiculo())

    with pytest.raises(PagoError) as error:
        ServicioPago(session).registrar(
            PagoCrear(placa="ABC123", referencia="R-1", autorizar_avisos=True),
            usuario_de_prueba(),
        )

    assert error.value.status_code == 422
    session.add.assert_not_called()


def test_anular_marca_el_pago_sin_borrarlo(reloj):
    usuario = usuario_de_prueba(id=9)
    vehiculo = nuevo_vehiculo()
    pago = nuevo_pago(vehiculo, usuario, date(2027, 2, 28))
    session = MagicMock()
    session.get.return_value = pago

    resultado = ServicioPago(session).anular(
        10, PagoAnular(motivo="Pago duplicado"), usuario
    )

    assert pago.anulacion_fecha_hora is not None
    assert pago.anulacion_usuario_id == 9
    assert pago.anulacion_motivo == "Pago duplicado"
    assert resultado.estado == "ANULADO"
    assert resultado.motivo_anulacion == "Pago duplicado"
    session.delete.assert_not_called()
    session.commit.assert_called_once()


def test_anular_exige_que_sea_el_ultimo_pago_activo(reloj):
    usuario = usuario_de_prueba(id=9)
    vehiculo = nuevo_vehiculo()
    primero = nuevo_pago(vehiculo, usuario, date(2027, 1, 31), referencia="R-1",
                         id=10, fecha_hora=datetime(2027, 1, 1, tzinfo=timezone.utc))
    nuevo_pago(vehiculo, usuario, date(2027, 2, 28), referencia="R-2", id=11,
               fecha_hora=datetime(2027, 2, 1, tzinfo=timezone.utc))
    session = MagicMock()
    session.get.return_value = primero

    with pytest.raises(PagoError) as error:
        ServicioPago(session).anular(10, PagoAnular(motivo="Otro"), usuario)

    assert error.value.status_code == 409
    assert error.value.detail == NO_ES_ULTIMO_PAGO
    assert primero.estado == "ACTIVO"
    session.commit.assert_not_called()


def test_no_se_puede_anular_dos_veces(reloj):
    usuario = usuario_de_prueba(id=9)
    vehiculo = nuevo_vehiculo()
    pago = nuevo_pago(vehiculo, usuario, date(2027, 2, 28),
                      anulacion_fecha_hora=datetime(2027, 3, 1, tzinfo=timezone.utc),
                      anulacion_usuario_id=9, anulacion_motivo="Otro")
    session = MagicMock()
    session.get.return_value = pago

    with pytest.raises(PagoError) as error:
        ServicioPago(session).anular(10, PagoAnular(motivo="Otro"), usuario)

    assert error.value.status_code == 409
    assert error.value.detail == PAGO_YA_ANULADO


def test_anular_pago_inexistente_responde_404(reloj):
    session = MagicMock()
    session.get.return_value = None

    with pytest.raises(PagoError) as error:
        ServicioPago(session).anular(99, PagoAnular(motivo="Otro"), usuario_de_prueba())

    assert error.value.status_code == 404


def test_historial_mas_reciente_primero_y_paginado(reloj):
    usuario = usuario_de_prueba(id=5)
    vehiculo = nuevo_vehiculo()
    pago = nuevo_pago(vehiculo, usuario, date(2027, 2, 28))
    session = MagicMock()
    session.scalar.side_effect = [vehiculo, 1]
    session.scalars.return_value.all.return_value = [pago]

    resultado = ServicioPago(session).historial("ABC123", pagina=2, tamano=5)

    consulta = str(session.scalars.call_args.args[0])
    assert "ORDER BY pago.fecha_hora DESC, pago.id DESC" in consulta
    assert "LIMIT" in consulta and "OFFSET" in consulta
    assert resultado.total == 1
    assert resultado.pagina == 2 and resultado.tamano == 5
    assert resultado.items[0].referencia == "R-1"


def test_historial_de_vehiculo_inexistente_responde_404(reloj):
    session = MagicMock()
    session.scalar.return_value = None

    with pytest.raises(PagoError) as error:
        ServicioPago(session).historial("ZZZ999", 1, 20)

    assert error.value.status_code == 404
