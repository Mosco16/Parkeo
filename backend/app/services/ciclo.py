"""Cálculo del ciclo de mensualidad: puro, sin base de datos (RN-VIG-02).

El día de corte se conserva entre ciclos porque el anclaje no se puede
reconstruir desde una fecha: un pago el 31 de enero vence el 28 de febrero y
el ciclo siguiente vuelve a vencer el 31 de marzo.
"""

import calendar
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.config import ZONA_HORARIA

TARIFAS = {"AUTOMOVIL": 250000, "CAMIONETA": 250000, "MOTO": 100000}


@dataclass(frozen=True)
class Ciclo:
    """Ciclo de mensualidad calculado; el día de corte se guarda en el pago."""

    dia_corte: int
    inicio_ciclo: date
    vencimiento_ciclo: date


def hoy_bogota() -> date:
    """Fecha de hoy en America/Bogota, nunca en UTC (RNF-04)."""
    return datetime.now(ZoneInfo(ZONA_HORARIA)).date()


def _ultimo_dia(anio: int, mes: int) -> int:
    return calendar.monthrange(anio, mes)[1]


def sumar_mes_anclado(fecha: date, dia: int) -> date:
    """Suma un mes conservando ``dia``; si el mes no lo tiene, usa su último día."""
    anio = fecha.year + (1 if fecha.month == 12 else 0)
    mes = 1 if fecha.month == 12 else fecha.month + 1
    return date(anio, mes, min(dia, _ultimo_dia(anio, mes)))


def mes_anterior_anclado(fecha: date, dia: int) -> date:
    """Resta un mes conservando ``dia``, con el mismo ajuste de mes corto."""
    anio = fecha.year if fecha.month > 1 else fecha.year - 1
    mes = fecha.month - 1 if fecha.month > 1 else 12
    return date(anio, mes, min(dia, _ultimo_dia(anio, mes)))


def calcular_ciclo(
    vencimiento_vigente: date | None,
    dia_corte: int | None,
    hoy: date,
) -> Ciclo:
    """Calcula el ciclo que cubre el pago registrado hoy (RN-VIG-02).

    - Sin pago previo, o pago vencido: el ciclo arranca hoy y reancla el corte.
    - Pago a tiempo (incluido el mismo día del vencimiento): el ciclo arranca
      en el vencimiento vigente y conserva el día de corte.
    """
    if vencimiento_vigente is None or dia_corte is None or hoy > vencimiento_vigente:
        corte = hoy.day
        return Ciclo(corte, hoy, sumar_mes_anclado(hoy, corte))
    return Ciclo(
        dia_corte,
        vencimiento_vigente,
        sumar_mes_anclado(vencimiento_vigente, dia_corte),
    )


def estado_mensualidad(vencimiento: date | None, hoy: date) -> str:
    """VIGENTE solo si hoy es anterior al vencimiento (RN-VIG-03, RN-VIG-05)."""
    if vencimiento is not None and hoy < vencimiento:
        return "VIGENTE"
    return "VENCIDA"


def supera_tope_adelantado(vencimiento_vigente: date | None, hoy: date) -> bool:
    """True si ya hay más de un ciclo por adelantado (RN-PAG-09)."""
    if vencimiento_vigente is None:
        return False
    return vencimiento_vigente > sumar_mes_anclado(hoy, hoy.day)


def tarifa_mensual(tipo: str) -> int:
    """Valor fijado por el sistema para el tipo de vehículo (RN-VIG-04)."""
    try:
        return TARIFAS[tipo]
    except KeyError:
        raise ValueError("El tipo de vehículo no tiene tarifa de mensualidad.") from None
