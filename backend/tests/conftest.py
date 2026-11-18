"""Ayudas compartidas: cuentas y tokens de prueba sin tocar PostgreSQL."""

from datetime import date, datetime, timedelta, timezone

from app.models import Pago, Usuario, Vehiculo
from app.security import create_access_token

FECHA_PRUEBA = datetime(2026, 1, 1, tzinfo=timezone.utc)


def usuario_de_prueba(**cambios) -> Usuario:
    datos = {
        "id": 1,
        "documento": "1001",
        "nombre": "Prueba",
        "telefono": "001",
        "usuario": "prueba",
        "password_hash": "hash-de-prueba",
        "rol": "OPERADOR",
        "activo": True,
        "correo": None,
        "direccion": None,
        "creado_en": FECHA_PRUEBA,
        "actualizado_en": FECHA_PRUEBA,
    }
    datos.update(cambios)
    return Usuario(**datos)


def con_pago(
    vehiculo: Vehiculo,
    vencimiento: date,
    referencia: str | None = None,
    dia_corte: int | None = None,
    usuario_id: int = 1,
) -> Vehiculo:
    """Adjunta un pago activo en memoria para derivar el vencimiento (RN-VIG-01).

    El vencimiento del vehículo ya no se escribe: se calcula con
    ``max(vencimiento_ciclo)`` de sus pagos activos.
    """
    inicio = date(vencimiento.year, vencimiento.month, 1) - timedelta(days=1)
    vehiculo.pagos.append(
        Pago(
            vehiculo_id=vehiculo.id,
            usuario_id=usuario_id,
            valor=250000,
            referencia=referencia or f"REF-{vehiculo.placa}",
            dia_corte=dia_corte or vencimiento.day,
            inicio_ciclo=inicio,
            vencimiento_ciclo=vencimiento,
        )
    )
    return vehiculo


def token_para(usuario_id: int, rol: str = "OPERADOR") -> str:
    """Token legible por el backend; solo se usa ``sub`` al cargar la cuenta."""
    return create_access_token(
        usuario_id=usuario_id,
        usuario=f"usuario-{usuario_id}",
        nombre=f"Usuario {usuario_id}",
        rol=rol,
    )


def encabezado(usuario_id: int, rol: str = "OPERADOR") -> dict[str, str]:
    return {"Authorization": f"Bearer {token_para(usuario_id, rol)}"}
