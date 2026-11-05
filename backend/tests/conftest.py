"""Ayudas compartidas: cuentas y tokens de prueba sin tocar PostgreSQL."""

from datetime import datetime, timezone

from app.models import Usuario
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
