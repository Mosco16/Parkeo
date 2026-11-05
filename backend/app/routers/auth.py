from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_session
from app.dependencies import UsuarioAutenticado
from app.schemas.auth import LoginCrear, SesionRespuesta
from app.schemas.usuario import UsuarioRespuesta
from app.services import auth as service

router = APIRouter(prefix="/auth", tags=["Autenticación"])
DatabaseSession = Annotated[Session, Depends(get_session)]


@router.post("/login", response_model=SesionRespuesta)
def login(data: LoginCrear, session: DatabaseSession) -> SesionRespuesta:
    token, usuario = service.autenticar(session, data)
    return SesionRespuesta(access_token=token, usuario=usuario)


@router.get("/me", response_model=UsuarioRespuesta)
def me(usuario: UsuarioAutenticado) -> UsuarioRespuesta:
    return usuario
