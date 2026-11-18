from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.database import get_session
from app.dependencies import usuario_actual
from app.models import Usuario
from app.schemas.pago import PagoAnular, PagoCrear, PagoRespuesta, PagosPagina
from app.services.pago import ServicioPago

router = APIRouter(prefix="/pagos", tags=["Pagos"])
DatabaseSession = Annotated[Session, Depends(get_session)]
UsuarioActual = Annotated[Usuario, Depends(usuario_actual)]
PagoId = Annotated[int, Path(ge=1, le=9223372036854775807)]
PlacaQuery = Annotated[str, Query(min_length=1, max_length=20)]


@router.post("", response_model=PagoRespuesta, status_code=201)
def registrar(datos: PagoCrear, session: DatabaseSession, usuario: UsuarioActual):
    return ServicioPago(session).registrar(datos, usuario)


@router.post("/{id}/anular", response_model=PagoRespuesta)
def anular(id: PagoId, datos: PagoAnular, session: DatabaseSession, usuario: UsuarioActual):
    return ServicioPago(session).anular(id, datos, usuario)


@router.get("", response_model=PagosPagina)
def historial(
    session: DatabaseSession,
    placa: PlacaQuery,
    pagina: Annotated[int, Query(ge=1, le=100000)] = 1,
    tamano: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return ServicioPago(session).historial(placa.strip().upper(), pagina, tamano)
