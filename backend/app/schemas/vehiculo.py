import re

from datetime import date
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, computed_field, field_validator

from app.models import required_text
from app.services.ciclo import estado_mensualidad, hoy_bogota

Texto = Annotated[str, BeforeValidator(lambda value: required_text(value, "El campo"))]
Placa = Annotated[Texto, AfterValidator(str.upper)]
Anio = Annotated[int, Field(strict=True, ge=1, le=9999)]
TipoVehiculo = Annotated[
    Literal["MOTO", "AUTOMOVIL", "CAMIONETA"],
    BeforeValidator(lambda value: required_text(value, "tipo")),
]

PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validar_correo(value: str) -> str:
    """Correo opcional con formato válido, sin espacios en los extremos (sección 4)."""
    value = value.strip().lower()
    if not PATRON_CORREO.match(value):
        raise ValueError("El correo no tiene un formato válido.")
    return value


Correo = Annotated[str, BeforeValidator(lambda value: required_text(value, "correo")), AfterValidator(validar_correo)]


class VehiculoCrear(BaseModel):
    """El vencimiento ya no se escribe: se deriva de los pagos (RN-VIG-01)."""

    model_config = ConfigDict(extra="forbid")

    placa: Placa
    color: Texto
    modelo: Anio
    marca: Texto
    tipo: TipoVehiculo
    correo: Correo | None = None


class VehiculoActualizar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    placa: Placa | None = None
    color: Texto | None = None
    modelo: Anio | None = None
    marca: Texto | None = None
    tipo: TipoVehiculo | None = None
    correo: Correo | None = None

    @field_validator("*", mode="before")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("Los campos enviados no pueden ser nulos.")
        return value


class VehiculoRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: int
    placa: str
    color: str
    modelo: int
    marca: str
    tipo: TipoVehiculo
    correo: str | None = None
    avisos_autorizados: bool = False
    fecha_vencimiento: date | None = None

    @computed_field
    @property
    def mensualidad(self) -> str:
        """Derivada del vencimiento vigente, nunca escrita por el cliente (S12)."""
        return estado_mensualidad(self.fecha_vencimiento, hoy_bogota())


class VehiculosPagina(BaseModel):
    items: list[VehiculoRespuesta]
    total: int
    offset: int
    limit: int
