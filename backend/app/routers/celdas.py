from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response
from sqlalchemy.orm import Session

from app.database import get_session
from app.dependencies import requiere_administrador, usuario_actual
from app.schemas.celda import (
    CeldaActualizar,
    CeldaCrear,
    CeldaEstado,
    CeldaRespuesta,
    CeldasPagina,
    DisponibilidadRespuesta,
)
from app.services import celda as service

router = APIRouter(prefix="/celdas", tags=["Celdas"], dependencies=[Depends(usuario_actual)])
DatabaseSession = Annotated[Session, Depends(get_session)]
CellId = Annotated[int, Path(ge=1, le=9223372036854775807)]


@router.get("/disponibilidad", response_model=DisponibilidadRespuesta)
def disponibilidad(session: DatabaseSession):
    return service.disponibilidad(session)


@router.post("", response_model=CeldaRespuesta, status_code=201,
             dependencies=[Depends(requiere_administrador)])
def create(data: CeldaCrear, session: DatabaseSession):
    return service.create_cell(session, data)


@router.get("", response_model=CeldasPagina)
def list_all(
    session: DatabaseSession,
    offset: Annotated[int, Query(ge=0, le=9223372036854775807)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return service.list_cells(session, offset, limit)


@router.get("/{id}", response_model=CeldaRespuesta)
def get_one(id: CellId, session: DatabaseSession):
    return service.get_cell(session, id)


@router.patch("/{id}", response_model=CeldaRespuesta,
              dependencies=[Depends(requiere_administrador)])
def update(id: CellId, data: CeldaActualizar, session: DatabaseSession):
    return service.update_cell(session, id, data)


@router.patch("/{id}/estado", response_model=CeldaRespuesta,
              dependencies=[Depends(requiere_administrador)])
def change_state(id: CellId, data: CeldaEstado, session: DatabaseSession):
    return service.cambiar_estado(session, id, data.activa)


@router.delete("/{id}", status_code=204, dependencies=[Depends(requiere_administrador)])
def delete(id: CellId, session: DatabaseSession) -> Response:
    service.delete_cell(session, id)
    return Response(status_code=204)


