"""Contratos de pago de mensualidad, anulación e historial."""

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import MOTIVOS_ANULACION
from app.schemas.vehiculo import Correo, Placa, Texto

Booleano = Annotated[bool, Field(strict=True)]


class PagoCrear(BaseModel):
    """RN-PAG-01 y RN-PAG-04: el operador digita placa y referencia, nada más."""

    model_config = ConfigDict(extra="forbid")

    placa: Placa
    referencia: Texto
    correo: Correo | None = None
    autorizar_avisos: Booleano | None = None


class PagoAnular(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motivo: str

    @field_validator("motivo")
    @classmethod
    def motivo_del_catalogo(cls, value: str) -> str:
        if value not in MOTIVOS_ANULACION:
            raise ValueError("El motivo no pertenece al catálogo de anulación.")
        return value


class PagoRespuesta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    placa: str
    valor: int
    referencia: str
    fecha_hora: datetime
    dia_corte: int
    inicio_ciclo: date
    vencimiento_ciclo: date
    estado: Literal["ACTIVO", "ANULADO"]
    motivo_anulacion: str | None = None
    anulacion_fecha_hora: datetime | None = None
    usuario: str


class PagosPagina(BaseModel):
    items: list[PagoRespuesta]
    total: int
    pagina: int
    tamano: int
