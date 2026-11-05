from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.database import get_session
from app.schemas.usuario import (
    EstadoUsuario,
    RestablecerPassword,
    UsuarioActualizar,
    UsuarioCrear,
    UsuarioRespuesta,
    UsuariosPagina,
)
from app.services import usuario as service

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])
DatabaseSession = Annotated[Session, Depends(get_session)]
UsuarioId = Annotated[int, Path(ge=1, le=9223372036854775807)]


@router.post("", response_model=UsuarioRespuesta, status_code=201)
def create(data: UsuarioCrear, session: DatabaseSession):
    return service.create_usuario(session, data)


@router.get("", response_model=UsuariosPagina)
def list_all(
    session: DatabaseSession,
    offset: Annotated[int, Query(ge=0, le=9223372036854775807)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict:
    return service.list_usuarios(session, offset, limit)


@router.get("/{id}", response_model=UsuarioRespuesta)
def get_one(id: UsuarioId, session: DatabaseSession):
    return service.get_usuario(session, id)


@router.patch("/{id}", response_model=UsuarioRespuesta)
def update(id: UsuarioId, data: UsuarioActualizar, session: DatabaseSession):
    return service.update_usuario(session, id, data)


@router.patch("/{id}/estado", response_model=UsuarioRespuesta)
def change_state(id: UsuarioId, data: EstadoUsuario, session: DatabaseSession):
    return service.cambiar_estado(session, id, data.activo)


@router.post("/{id}/restablecer-password", response_model=UsuarioRespuesta)
def reset_password(id: UsuarioId, data: RestablecerPassword, session: DatabaseSession):
    return service.restablecer_password(session, id, data.password)
