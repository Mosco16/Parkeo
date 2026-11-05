"""Dependencias compartidas: sesión autenticada y permisos por rol."""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import Usuario
from app.security import decode_access_token
from app.services.auth import AuthError, SESION_INVALIDA, cargar_usuario_autenticado

esquema_bearer = HTTPBearer(
    auto_error=False,
    scheme_name="BearerAuth",
    description="Token JWT emitido por POST /auth/login.",
)


def usuario_actual(
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(esquema_bearer)],
    session: Annotated[Session, Depends(get_session)],
) -> Usuario:
    if credenciales is None or credenciales.scheme.lower() != "bearer":
        raise AuthError(401, "Falta el token de sesión.")

    claims = decode_access_token(credenciales.credentials)
    if claims is None:
        raise AuthError(401, SESION_INVALIDA)

    try:
        usuario_id = int(claims["sub"])
    except (KeyError, TypeError, ValueError):
        raise AuthError(401, SESION_INVALIDA) from None
    if usuario_id < 1:
        raise AuthError(401, SESION_INVALIDA)

    return cargar_usuario_autenticado(session, usuario_id)


def requiere_administrador(
    usuario: Annotated[Usuario, Depends(usuario_actual)],
) -> Usuario:
    if not usuario.es_administrador():
        raise AuthError(403, "Esta acción requiere una cuenta administradora.")
    return usuario


UsuarioAutenticado = Annotated[Usuario, Depends(usuario_actual)]
Administrador = Annotated[Usuario, Depends(requiere_administrador)]
