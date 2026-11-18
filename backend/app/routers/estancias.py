from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response
from sqlalchemy.orm import Session

from app.database import get_session
from app.dependencies import UsuarioAutenticado, usuario_actual
from app.schemas.estancia import (
    CambioCeldaCrear,
    EntradaCrear,
    EstanciaAbiertaRespuesta,
    EstanciaRespuesta,
    EstadoVehiculoRespuesta,
    HistorialCambiosPagina,
    SalidaCrear,
)
from app.schemas.vehiculo import Placa
from app.services.estancia import ServicioEstancia

router = APIRouter(prefix="/estancias", tags=["Estancias"], dependencies=[Depends(usuario_actual)])
DatabaseSession = Annotated[Session, Depends(get_session)]


@router.post("/entrada", response_model=EstanciaAbiertaRespuesta, status_code=201)
def entrada(
    data: EntradaCrear, session: DatabaseSession, usuario: UsuarioAutenticado
) -> EstanciaAbiertaRespuesta:
    return ServicioEstancia(session).entrada(data, usuario)


@router.post("/salida", response_model=EstanciaRespuesta)
def salida(
    data: SalidaCrear, session: DatabaseSession, usuario: UsuarioAutenticado
) -> EstanciaRespuesta:
    return ServicioEstancia(session).salida(data, usuario)


@router.post("/cambiar-celda", response_model=EstanciaAbiertaRespuesta)
def cambiar_celda(
    data: CambioCeldaCrear, session: DatabaseSession, usuario: UsuarioAutenticado
) -> EstanciaAbiertaRespuesta:
    return ServicioEstancia(session).cambiar_celda(data, usuario)


@router.get("/historial-cambios", response_model=HistorialCambiosPagina)
def historial_cambios(
    session: DatabaseSession,
    offset: Annotated[int, Query(ge=0, le=9223372036854775807)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return ServicioEstancia(session).historial_cambios(offset, limit)


@router.get("/vehiculo/{placa}", response_model=EstadoVehiculoRespuesta)
def consultar(placa: Placa, session: DatabaseSession) -> EstadoVehiculoRespuesta:
    return ServicioEstancia(session).consultar(placa)

