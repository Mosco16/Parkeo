from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator

from app.models import required_text

Texto = Annotated[str, BeforeValidator(lambda value: required_text(value, "El campo"))]
Password = Annotated[
    str,
    BeforeValidator(lambda value: required_text(value, "La contraseña")),
    Field(min_length=8, max_length=72),
]


class UsuarioCrear(BaseModel):
    """Datos de una cuenta de operador; el rol siempre lo asigna el servicio."""

    model_config = ConfigDict(extra="forbid")
    documento: Texto
    nombre: Texto
    telefono: Texto | None = None
    usuario: Texto
    password: Password
    correo: Texto | None = None
    direccion: Texto | None = None

    @field_validator("usuario")
    @classmethod
    def normalizar_usuario(cls, value: str) -> str:
        return value.strip().lower()


class UsuarioActualizar(BaseModel):
    model_config = ConfigDict(extra="forbid")
    documento: Texto | None = None
    nombre: Texto | None = None
    telefono: Texto | None = None
    usuario: Texto | None = None
    correo: Texto | None = None
    direccion: Texto | None = None

    @field_validator("*", mode="before")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("Los campos enviados no pueden ser nulos.")
        return value

    @field_validator("usuario")
    @classmethod
    def normalizar_usuario(cls, value: str) -> str:
        return value.strip().lower()


class EstadoUsuario(BaseModel):
    model_config = ConfigDict(extra="forbid")
    activo: bool


class RestablecerPassword(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: Password


class UsuarioRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    documento: str
    nombre: str
    telefono: str | None
    usuario: str
    rol: str
    activo: bool
    correo: str | None
    direccion: str | None
    creado_en: datetime
    actualizado_en: datetime


class UsuariosPagina(BaseModel):
    items: list[UsuarioRespuesta]
    total: int
    offset: int
    limit: int
