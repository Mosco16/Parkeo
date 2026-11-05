from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, field_validator

from app.models import required_text
from app.schemas.usuario import UsuarioRespuesta

Texto = Annotated[str, BeforeValidator(lambda value: required_text(value, "El campo"))]


class LoginCrear(BaseModel):
    """Credenciales internas; el rol nunca se envía, lo decide el servidor."""

    model_config = ConfigDict(extra="forbid")
    usuario: Texto
    password: Texto

    @field_validator("usuario")
    @classmethod
    def normalizar_usuario(cls, value: str) -> str:
        return value.strip().lower()


class SesionRespuesta(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    usuario: UsuarioRespuesta
