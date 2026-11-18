"""DATOS DE DEMOSTRACIÓN para Parkeo.

Este script NO es una migración: solo carga datos de ejemplo en una base que ya
tiene las tablas creadas (``python -m alembic -c alembic.ini upgrade head``).

Es idempotente: se puede ejecutar varias veces sin duplicar registros, porque
usa los códigos únicos de celdas (``codigo``), las placas de vehículos
(``placa``), el nombre de usuario de las cuentas internas (``usuario``) y la
referencia del pago demo. Los vencimientos se recalculan respecto a hoy en
America/Bogota para que la demostración siga sirviendo con el paso del tiempo.

Cuentas de demostración (solo desarrollo):
- ``admin`` / ``Parkeo2026*`` con rol ADMINISTRADOR.
- ``ana.gomez``, ``carlos.perez`` y ``laura.rios`` / ``Parkeo2026*`` con rol
  OPERADOR.

Uso (PowerShell, desde la raíz del repositorio):

    Push-Location backend
    try { .\\.venv\\Scripts\\python.exe scripts\\cargar_datos_demo.py } finally { Pop-Location }

No imprime credenciales ni la URL de conexión. Se niega a ejecutarse si la base
conectada no se llama igual que ``DB_NAME`` en ``backend/.env``.
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# Permite ejecutar el archivo directamente desde backend/ o desde scripts/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select, text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.config import load_database_settings  # noqa: E402
from app.database import get_engine  # noqa: E402
from app.models import Celda, Pago, Usuario, Vehiculo  # noqa: E402
from app.security import hash_password  # noqa: E402
from app.services.ciclo import hoy_bogota, mes_anterior_anclado  # noqa: E402

BANNER = "DATOS DE DEMOSTRACIÓN"
PASSWORD_DEMO = "Parkeo2026*"

# RN-VIG-04: la tarifa la fija el sistema, no el operador.
TARIFAS = {"AUTOMOVIL": 250000, "CAMIONETA": 250000, "MOTO": 100000}

CELDAS: list[tuple[str, str]] = [
    *[(f"A{numero}", "AUTO") for numero in range(1, 71)],
    *[(f"M{numero}", "MOTO") for numero in range(1, 11)],
]

# documento, nombre, teléfono, usuario, rol, correo
USUARIOS: list[tuple[str, str, str, str, str, str]] = [
    ("1000000001", "Administrador Parkeo", "3000000000", "admin", "ADMINISTRADOR", "admin@parkeo.local"),
    ("1000000002", "Ana Gómez", "3001234567", "ana.gomez", "OPERADOR", "ana.gomez@parkeo.local"),
    ("1000000003", "Carlos Pérez", "3109876543", "carlos.perez", "OPERADOR", "carlos.perez@parkeo.local"),
    ("1000000004", "Laura Ríos", "3205556677", "laura.rios", "OPERADOR", "laura.rios@parkeo.local"),
]


def vehiculos(hoy: date) -> list[tuple[str, str, str, str, int, str, date]]:
    """Placa, tipo, marca, color, modelo, correo de avisos y vencimiento.

    El vencimiento no se guarda en el vehículo: se deriva del pago de
    mensualidad que crea ``cargar_pagos`` (RN-VIG-01).
    """
    return [
        # Vigente: permite registrar entrada.
        ("ABC123", "AUTOMOVIL", "Renault", "Blanco", 2021, "demo.abc123@parkeo.local",
         hoy + timedelta(days=30)),
        # Por vencer en dos días: dispara el aviso de vencimiento (RN-AVI-01).
        ("DEF456", "CAMIONETA", "Toyota", "Gris", 2020, "demo.def456@parkeo.local",
         hoy + timedelta(days=2)),
        # Vencida: bloquea la entrada y muestra pago pendiente.
        ("GHI12J", "MOTO", "Bajaj", "Rojo", 2023, "demo.ghi12j@parkeo.local",
         hoy - timedelta(days=10)),
        # Vence hoy: cuenta como VENCIDA (RN-VIG-03).
        ("DEMO01", "AUTOMOVIL", "Chevrolet", "Azul", 2019, "demo.auto01@parkeo.local",
         hoy),
        # Vigente con holgura, para pruebas de salida y cambio de celda.
        ("DEMO02", "MOTO", "Honda", "Negro", 2022, "demo.moto02@parkeo.local",
         hoy + timedelta(days=90)),
    ]


def _mes_anterior(fecha: date, dia: int) -> date:
    """Inicio del ciclo que termina en ``fecha``, anclado al día de corte."""
    return mes_anterior_anclado(fecha, dia)


def verificar_base(session: Session, nombre_configurado: str) -> str:
    actual = session.execute(text("SELECT current_database()")).scalar_one()
    if actual != nombre_configurado:
        raise SystemExit(
            "Se canceló la carga: la base conectada no coincide con DB_NAME de backend/.env."
        )
    return actual


def cargar_celdas(session: Session) -> tuple[int, int]:
    existentes = {celda.codigo: celda for celda in session.scalars(select(Celda))}
    creadas = actualizadas = 0
    for codigo, tipo in CELDAS:
        celda = existentes.get(codigo)
        if celda is None:
            session.add(Celda(codigo=codigo, tipo=tipo))
            creadas += 1
        elif celda.tipo != tipo:
            celda.tipo = tipo
            actualizadas += 1
    return creadas, actualizadas


def cargar_usuarios(session: Session) -> int:
    existentes = {usuario.usuario: usuario for usuario in session.scalars(select(Usuario))}
    creados = 0
    for documento, nombre, telefono, usuario, rol, correo in USUARIOS:
        actual = existentes.get(usuario)
        if actual is None:
            session.add(
                Usuario(
                    documento=documento,
                    nombre=nombre,
                    telefono=telefono,
                    usuario=usuario,
                    password_hash=hash_password(PASSWORD_DEMO),
                    rol=rol,
                    activo=True,
                    correo=correo,
                )
            )
            creados += 1
        elif actual.rol != rol:
            actual.rol = rol
    return creados


def cargar_vehiculos(session: Session) -> tuple[int, int]:
    existentes = {vehiculo.placa: vehiculo for vehiculo in session.scalars(select(Vehiculo))}
    admin = session.scalar(select(Usuario).where(Usuario.usuario == "admin"))
    creados = actualizados = 0
    for placa, tipo, marca, color, modelo, correo, _vence in vehiculos(hoy_bogota()):
        vehiculo = existentes.get(placa)
        if vehiculo is None:
            vehiculo = Vehiculo(
                placa=placa,
                tipo=tipo,
                marca=marca,
                color=color,
                modelo=modelo,
                correo=correo,
            )
            session.add(vehiculo)
            creados += 1
        elif vehiculo.correo != correo:
            vehiculo.correo = correo
            actualizados += 1
        # La demostración deja los avisos autorizados por el administrador.
        if admin is not None and not vehiculo.avisos_autorizados:
            vehiculo.avisos_autorizados = True
            vehiculo.autorizacion_usuario_id = admin.id
            vehiculo.autorizacion_fecha_hora = datetime.now(timezone.utc)
            actualizados += 1
    return creados, actualizados


def cargar_pagos(session: Session) -> tuple[int, int]:
    """Un pago demo por vehículo, idempotente y con fechas relativas a hoy."""
    admin = session.scalar(select(Usuario).where(Usuario.usuario == "admin"))
    if admin is None:
        return 0, 0
    creados = actualizados = 0
    for placa, tipo, _marca, _color, _modelo, _correo, vencimiento in vehiculos(hoy_bogota()):
        vehiculo = session.scalar(select(Vehiculo).where(Vehiculo.placa == placa))
        if vehiculo is None:
            continue
        referencia = f"DEMO-{placa}"
        activos = vehiculo.pagos_activos
        if not activos:
            dia_corte = vencimiento.day
            session.add(
                Pago(
                    vehiculo=vehiculo,
                    usuario=admin,
                    valor=TARIFAS[tipo],
                    referencia=referencia,
                    dia_corte=dia_corte,
                    inicio_ciclo=_mes_anterior(vencimiento, dia_corte),
                    vencimiento_ciclo=vencimiento,
                )
            )
            creados += 1
            continue
        # Mantiene las fechas relativas al día de la ejecución.
        demo = next((pago for pago in activos if pago.referencia == referencia), None)
        if demo is not None and demo.vencimiento_ciclo != vencimiento:
            demo.dia_corte = vencimiento.day
            demo.inicio_ciclo = _mes_anterior(vencimiento, demo.dia_corte)
            demo.vencimiento_ciclo = vencimiento
            actualizados += 1
    return creados, actualizados


def main() -> int:
    print(BANNER)
    print("Este script carga datos de ejemplo; no es una migración ni borra historial.")

    settings = load_database_settings()
    with Session(get_engine()) as session:
        nombre = verificar_base(session, settings.name)
        celdas_creadas, celdas_actualizadas = cargar_celdas(session)
        usuarios_creados = cargar_usuarios(session)
        vehiculos_creados, vehiculos_actualizados = cargar_vehiculos(session)
        pagos_creados, pagos_actualizados = cargar_pagos(session)
        session.commit()

    print(f"Base de datos: {nombre}")
    print(f"Celdas: {celdas_creadas} creadas, {celdas_actualizadas} actualizadas.")
    print(f"Usuarios: {usuarios_creados} creados.")
    print(f"Vehículos: {vehiculos_creados} creados, {vehiculos_actualizados} actualizados.")
    print(f"Pagos: {pagos_creados} creados, {pagos_actualizados} actualizados.")
    print("Listo. Vuelve a ejecutarlo cuando quieras: no duplica registros.")
    print(BANNER)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as error:  # noqa: BLE001
        # No se imprime el error crudo para no filtrar datos de conexión.
        print(
            f"No se pudo cargar la demostración ({type(error).__name__}). "
            "Revisa que la base exista y tenga las migraciones aplicadas.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
