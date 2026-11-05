from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, field_validator

from app.models import required_text

Texto = Annotated[str, BeforeValidator(lambda value: required_text(value, "El campo"))]
Codigo = Annotated[Texto, AfterValidator(str.upper)]
TipoCelda = Literal["AUTO", "MOTO"]


class CeldaCrear(BaseModel):
    model_config = ConfigDict(extra="forbid")
    codigo: Codigo
    tipo: TipoCelda


class CeldaActualizar(BaseModel):
    model_config = ConfigDict(extra="forbid")
    codigo: Codigo | None = None
    tipo: TipoCelda | None = None

    @field_validator("*", mode="before")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("Los campos enviados no pueden ser nulos.")
        return value


class CeldaEstado(BaseModel):
    """S5: el administrador solo enciende o apaga la celda."""

    model_config = ConfigDict(extra="forbid")
    activa: bool


class CeldaRespuesta(CeldaCrear):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: int
    activa: bool


class CeldasPagina(BaseModel):
    items: list[CeldaRespuesta]
    total: int
    offset: int
    limit: int


EstadoCelda = Literal["DISPONIBLE", "OCUPADA", "MANTENIMIENTO"]


class CeldaDisponible(BaseModel):
    """RN-CEL-03: el estado se calcula, nunca se guarda."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: int
    codigo: str
    tipo: TipoCelda
    activa: bool
    estado: EstadoCelda


class CupoTipo(BaseModel):
    total: int
    libres: int


class DisponibilidadRespuesta(BaseModel):
    celdas: list[CeldaDisponible]
    cupo: dict[str, CupoTipo]
