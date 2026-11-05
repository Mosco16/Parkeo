"""Autenticación de cuentas internas y carga del usuario de la sesión."""

from functools import lru_cache
import secrets

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import Usuario
from app.schemas.auth import LoginCrear
from app.security import create_access_token, hash_password, verify_password

CREDENCIALES_INVALIDAS = "Usuario o contraseña incorrectos."
SESION_INVALIDA = "El token de sesión no es válido o expiró."
CUENTA_INACTIVA = "La cuenta está inactiva. Contacta al administrador."
BASE_DE_DATOS_NO_DISPONIBLE = "No se pudo completar la operación con la base de datos."


class AuthError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail


@lru_cache(maxsize=1)
def _hash_ficticio() -> str:
    """Hash de un valor aleatorio para igualar el costo de un usuario inexistente."""
    return hash_password(secrets.token_urlsafe(32))


def autenticar(session: Session, data: LoginCrear) -> tuple[str, Usuario]:
    """Devuelve el token y la cuenta cuando las credenciales son válidas."""
    try:
        usuario = session.scalar(select(Usuario).where(Usuario.usuario == data.usuario))
    except SQLAlchemyError:
        session.rollback()
        raise AuthError(503, BASE_DE_DATOS_NO_DISPONIBLE) from None

    if usuario is None:
        # MISMA respuesta y costo similar que una contraseña incorrecta.
        verify_password(data.password, _hash_ficticio())
        raise AuthError(401, CREDENCIALES_INVALIDAS)

    if not verify_password(data.password, usuario.password_hash):
        raise AuthError(401, CREDENCIALES_INVALIDAS)

    if not usuario.activo:
        raise AuthError(403, CUENTA_INACTIVA)

    token = create_access_token(
        usuario_id=usuario.id,
        usuario=usuario.usuario,
        nombre=usuario.nombre,
        rol=usuario.rol,
    )
    return token, usuario


def cargar_usuario_autenticado(session: Session, usuario_id: int) -> Usuario:
    """Vuelve a verificar la cuenta en cada petición; desactivarla invalida la sesión."""
    try:
        usuario = session.get(Usuario, usuario_id)
    except SQLAlchemyError:
        session.rollback()
        raise AuthError(503, BASE_DE_DATOS_NO_DISPONIBLE) from None

    if usuario is None:
        raise AuthError(401, SESION_INVALIDA)
    if not usuario.activo:
        raise AuthError(403, CUENTA_INACTIVA)
    return usuario
