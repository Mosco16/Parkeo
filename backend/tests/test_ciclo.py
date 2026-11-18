"""Cálculo puro del ciclo de mensualidad y la vigencia (RN-VIG-02..05).

Sin base de datos: estos casos fijan el anclaje del día de corte, el bisiesto
y el borde del mismo día del vencimiento.
"""
from dataclasses import FrozenInstanceError, is_dataclass
from datetime import date

import pytest

from app.services import ciclo
from app.services.ciclo import (
    calcular_ciclo,
    estado_mensualidad,
    mes_anterior_anclado,
    sumar_mes_anclado,
    supera_tope_adelantado,
    tarifa_mensual,
)


def test_primer_pago_ancla_el_dia_de_hoy():
    resultado = calcular_ciclo(None, None, date(2027, 1, 31))
    assert resultado.dia_corte == 31
    assert resultado.inicio_ciclo == date(2027, 1, 31)
    # 2027 no es bisiesto: vence el último día de febrero.
    assert resultado.vencimiento_ciclo == date(2027, 2, 28)


def test_anio_bisiesto_usa_el_29_de_febrero():
    resultado = calcular_ciclo(None, None, date(2028, 1, 31))
    assert resultado.vencimiento_ciclo == date(2028, 2, 29)


def test_el_dia_de_corte_se_conserva_tras_un_mes_corto():
    """31 ene -> 28 feb, y el ciclo siguiente vuelve al 31 de marzo (E-16)."""
    primero = calcular_ciclo(None, None, date(2027, 1, 31))
    segundo = calcular_ciclo(primero.vencimiento_ciclo, primero.dia_corte,
                             date(2027, 2, 28))
    assert segundo.dia_corte == 31
    assert segundo.inicio_ciclo == date(2027, 2, 28)
    assert segundo.vencimiento_ciclo == date(2027, 3, 31)


def test_pago_el_mismo_dia_del_vencimiento_encadena_el_ciclo():
    """E-17: pagar el día del vencimiento no pierde ni regala días."""
    resultado = calcular_ciclo(date(2027, 3, 31), 31, date(2027, 3, 31))
    assert resultado.inicio_ciclo == date(2027, 3, 31)
    assert resultado.vencimiento_ciclo == date(2027, 4, 30)
    assert resultado.dia_corte == 31


def test_pago_vencido_reancla_el_corte_al_dia_del_pago():
    """E-19: un pago tardío arranca un ciclo nuevo desde hoy."""
    resultado = calcular_ciclo(date(2027, 3, 31), 31, date(2027, 4, 15))
    assert resultado.dia_corte == 15
    assert resultado.inicio_ciclo == date(2027, 4, 15)
    assert resultado.vencimiento_ciclo == date(2027, 5, 15)


def test_pago_adelantado_cuenta_desde_el_vencimiento_vigente():
    resultado = calcular_ciclo(date(2027, 5, 15), 15, date(2027, 4, 20))
    assert resultado.inicio_ciclo == date(2027, 5, 15)
    assert resultado.vencimiento_ciclo == date(2027, 6, 15)


def test_vigencia_usa_el_borde_del_mismo_dia():
    hoy = date(2027, 5, 15)
    assert estado_mensualidad(date(2027, 5, 16), hoy) == "VIGENTE"
    # RN-VIG-03: si el vencimiento es hoy, ya está vencida.
    assert estado_mensualidad(hoy, hoy) == "VENCIDA"
    assert estado_mensualidad(date(2027, 5, 14), hoy) == "VENCIDA"
    # RN-VIG-05: sin pagos activos no hay vencimiento.
    assert estado_mensualidad(None, hoy) == "VENCIDA"


def test_tope_de_un_ciclo_por_adelantado():
    hoy = date(2027, 1, 31)
    tope = sumar_mes_anclado(hoy, hoy.day)  # 28 feb 2027
    assert tope == date(2027, 2, 28)
    assert supera_tope_adelantado(tope, hoy) is False
    assert supera_tope_adelantado(date(2027, 3, 1), hoy) is True
    assert supera_tope_adelantado(None, hoy) is False


@pytest.mark.parametrize("tipo,valor", [
    ("AUTOMOVIL", 250000), ("CAMIONETA", 250000), ("MOTO", 100000),
])
def test_tarifa_por_tipo(tipo, valor):
    assert tarifa_mensual(tipo) == valor


def test_tipo_desconocido_no_tiene_tarifa():
    with pytest.raises(ValueError):
        tarifa_mensual("BICICLETA")


def test_mes_anterior_anclado_respeta_meses_cortos():
    assert mes_anterior_anclado(date(2027, 3, 31), 31) == date(2027, 2, 28)
    assert mes_anterior_anclado(date(2027, 1, 31), 31) == date(2026, 12, 31)
    assert mes_anterior_anclado(date(2028, 3, 31), 31) == date(2028, 2, 29)
    assert mes_anterior_anclado(date(2027, 5, 30), 15) == date(2027, 4, 15)


def test_ciclo_es_inmutable():
    resultado = calcular_ciclo(None, None, date(2027, 1, 31))
    assert is_dataclass(resultado)
    with pytest.raises(FrozenInstanceError):
        resultado.dia_corte = 1


def test_hoy_bogota_devuelve_una_fecha():
    assert isinstance(ciclo.hoy_bogota(), date)
