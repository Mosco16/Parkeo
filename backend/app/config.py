"""Configuración privada desde backend/.env y variables de entorno."""

import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"

# RNF-04: toda decisión de negocio sobre fechas usa la zona horaria de Bogotá.
ZONA_HORARIA = "America/Bogota"


class ConfigurationError(ValueError):
    """Error que contiene únicamente nombres de variables, nunca sus valores."""


@dataclass(frozen=True)
class DatabaseSettings:
    host: str
    port: int
    name: str = field(repr=False)
    user: str = field(repr=False)
    password: str = field(repr=False)
    connect_timeout: int = 5


@dataclass(frozen=True)
class SecuritySettings:
    secret_key: str = field(repr=False)
    algorithm: str = "HS256"
    expiration_hours: int = 8
    ephemeral: bool = False


@dataclass(frozen=True)
class MailSettings:
    """Configuración SMTP para los avisos de vencimiento (RN-AVI-01)."""

    host: str
    port: int
    tls: str
    usuario: str = field(repr=False)
    password: str = field(repr=False)
    remitente: str = field(repr=False)
    nombre: str = "Parkeo"


def load_database_settings() -> DatabaseSettings:
    # No interpolar $ ni ${...} dentro de las contraseñas.
    values = {**dotenv_values(ENV_FILE, encoding="utf-8-sig", interpolate=False), **os.environ}
    required = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD", "DB_CONNECT_TIMEOUT")
    missing = [
        key for key in required
        if not (values.get(key) or "").strip()
        or (values.get(key) or "").startswith("CAMBIAR_")
    ]
    if missing:
        raise ConfigurationError("Completa en backend/.env: " + ", ".join(missing))

    def positive_integer(key: str, maximum: int) -> int:
        try:
            number = int(values[key])
        except (ValueError, TypeError):
            raise ConfigurationError(f"{key} debe ser un entero válido.") from None
        if not 1 <= number <= maximum:
            raise ConfigurationError(f"{key} debe estar entre 1 y {maximum}.")
        return number

    return DatabaseSettings(
        host=values["DB_HOST"],
        port=positive_integer("DB_PORT", 65535),
        name=values["DB_NAME"],
        user=values["DB_USER"],
        password=values["DB_PASSWORD"],
        connect_timeout=positive_integer("DB_CONNECT_TIMEOUT", 60),
    )


def load_security_settings() -> SecuritySettings:
    """Lee la clave JWT; si falta, genera una efímera solo para desarrollo."""
    values = {**dotenv_values(ENV_FILE, encoding="utf-8-sig", interpolate=False), **os.environ}
    secret = (values.get("JWT_SECRET") or "").strip()
    provided = bool(secret) and not secret.startswith("CAMBIAR_")
    if not provided:
        secret = secrets.token_urlsafe(48)

    raw_hours = (values.get("JWT_EXPIRATION_HOURS") or "8").strip()
    try:
        hours = int(raw_hours)
    except (ValueError, TypeError):
        raise ConfigurationError("JWT_EXPIRATION_HOURS debe ser un entero válido.") from None
    if not 1 <= hours <= 168:
        raise ConfigurationError("JWT_EXPIRATION_HOURS debe estar entre 1 y 168.")

    return SecuritySettings(secret_key=secret, expiration_hours=hours, ephemeral=not provided)


def load_mail_settings() -> MailSettings | None:
    """Devuelve la configuración SMTP, o None si el correo no está configurado.

    Los avisos son opcionales en desarrollo: sin configuración el sistema sigue
    funcionando y el job de avisos informa que falta configurar el correo.
    """
    values = {**dotenv_values(ENV_FILE, encoding="utf-8-sig", interpolate=False), **os.environ}
    required = ("SMTP_HOST", "SMTP_USUARIO", "SMTP_PASSWORD", "SMTP_REMITENTE")
    if any(
        not (values.get(key) or "").strip() or (values.get(key) or "").startswith("CAMBIAR_")
        for key in required
    ):
        return None

    tls = (values.get("SMTP_TLS") or "inicio").strip().lower()
    if tls not in {"inicio", "ssl", "ninguno"}:
        raise ConfigurationError("SMTP_TLS debe ser inicio, ssl o ninguno.")
    raw_port = (values.get("SMTP_PORT") or "587").strip()
    try:
        port = int(raw_port)
    except (ValueError, TypeError):
        raise ConfigurationError("SMTP_PORT debe ser un entero válido.") from None
    if not 1 <= port <= 65535:
        raise ConfigurationError("SMTP_PORT debe estar entre 1 y 65535.")

    return MailSettings(
        host=values["SMTP_HOST"].strip(),
        port=port,
        tls=tls,
        usuario=values["SMTP_USUARIO"].strip(),
        password=values["SMTP_PASSWORD"].strip(),
        remitente=values["SMTP_REMITENTE"].strip(),
        nombre=(values.get("SMTP_NOMBRE") or "Parkeo").strip(),
    )
