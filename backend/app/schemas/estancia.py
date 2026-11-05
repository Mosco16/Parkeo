from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.celda import CeldaRespuesta
from app.schemas.vehiculo import Placa, VehiculoRespuesta

Identificador = Annotated[int, Field(strict=True, ge=1, le=9223372036854775807)]


class EntradaCrear(BaseModel):
    """RN-ENT-05: el usuario no escoge la celda; la asigna el servicio."""

    model_config = ConfigDict(extra="forbid")
    placa: Placa


class SalidaCrear(BaseModel):
    model_config = ConfigDict(extra="forbid")
    placa: Placa


class CambioCeldaCrear(BaseModel):
    model_config = ConfigDict(extra="forbid")
    placa: Placa
    celda_id: Identificador


class EstanciaRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vehiculo_id: int
    celda_id: int
    entrada: datetime
    salida: datetime | None
    usuario_entrada_id: int
    usuario_salida_id: int | None

    @field_validator("entrada", "salida")
    @classmethod
    def fechas_utc(cls, value: datetime | None) -> datetime | None:
        return value.astimezone(timezone.utc) if value is not None else None


class EstanciaAbiertaRespuesta(EstanciaRespuesta):
    celda: CeldaRespuesta


class EstadoVehiculoRespuesta(BaseModel):
    vehiculo: VehiculoRespuesta
    esta_dentro: bool
    estancia: EstanciaAbiertaRespuesta | None
    mensualidad: Literal["VIGENTE", "VENCIDA"]
    celda_sugerida: CeldaRespuesta | None = None
