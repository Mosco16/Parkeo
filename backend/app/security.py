"""Hash de contraseñas y emisión/validación de tokens de sesión."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.config import load_security_settings

logger = logging.getLogger(__name__)

_SETTINGS = load_security_settings()
if _SETTINGS.ephemeral:
    logger.warning(
        "JWT_SECRET no está definido en backend/.env; se usa una clave efímera. "
        "Los tokens se invalidan al reiniciar el proceso."
    )

_MAX_PASSWORD_BYTES = 72
_BCRYPT_ROUNDS = 12


class PasswordError(ValueError):
    """Contraseña vacía o demasiado larga para bcrypt."""


def hash_password(password: str) -> str:
    """Devuelve un hash bcrypt listo para guardar en la base."""
    _validate_password(password)
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS))
    return hashed.decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    """Compara una contraseña con su hash sin filtrar errores internos."""
    try:
        _validate_password(password)
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except (PasswordError, TypeError, ValueError):
        return False


def create_access_token(*, usuario_id: int, usuario: str, nombre: str, rol: str) -> str:
    """Emite un JWT con la identidad y el rol del usuario."""
    emitted_at = datetime.now(timezone.utc)
    payload = {
        "sub": str(usuario_id),
        "usuario": usuario,
        "nombre": nombre,
        "rol": rol,
        "iat": emitted_at,
        "exp": emitted_at + timedelta(hours=_SETTINGS.expiration_hours),
    }
    return jwt.encode(payload, _SETTINGS.secret_key, algorithm=_SETTINGS.algorithm)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Devuelve los claims del token o None si es inválido o expiró."""
    if not isinstance(token, str) or not token.strip():
        return None
    try:
        payload = jwt.decode(token, _SETTINGS.secret_key, algorithms=[_SETTINGS.algorithm])
    except jwt.PyJWTError:
        return None
    if not isinstance(payload, dict) or not payload.get("sub"):
        return None
    return payload


def _validate_password(password: str) -> None:
    if not isinstance(password, str) or not password:
        raise PasswordError("La contraseña es obligatoria.")
    if len(password.encode("utf-8")) > _MAX_PASSWORD_BYTES:
        raise PasswordError("La contraseña no puede superar 72 bytes.")
