from functools import wraps

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import Usuario
from app.schemas.usuario import UsuarioActualizar, UsuarioCrear
from app.security import PasswordError, hash_password

ROL_OPERADOR = "OPERADOR"


class UsuarioError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail


def database_operation(operation):
    """Centraliza rollback y mensajes públicos sin detalles del driver."""

    @wraps(operation)
    def wrapped(session: Session, *args, **kwargs):
        try:
            return operation(session, *args, **kwargs)
        except UsuarioError:
            session.rollback()
            raise
        except IntegrityError as error:
            session.rollback()
            code = getattr(error.orig, "sqlstate", None)
            constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
            if code == "23505" and constraint == "uq_usuario_documento":
                raise UsuarioError(409, "Ya existe una cuenta con ese documento.") from None
            if code == "23505" and constraint == "uq_usuario_usuario":
                raise UsuarioError(409, "Ese nombre de usuario ya está en uso.") from None
            if code == "23505":
                raise UsuarioError(409, "La cuenta entra en conflicto con los datos existentes.") from None
            if code == "23503":
                raise UsuarioError(409, "La cuenta tiene registros relacionados.") from None
            if code in {"23502", "23514"}:
                raise UsuarioError(422, "Los datos incumplen las restricciones de la cuenta.") from None
            raise UsuarioError(409, "La operación entra en conflicto con los datos existentes.") from None
        except SQLAlchemyError:
            session.rollback()
            raise UsuarioError(503, "No se pudo completar la operación con la base de datos.") from None

    return wrapped


def find_usuario(session: Session, usuario_id: int) -> Usuario:
    usuario = session.get(Usuario, usuario_id)
    if usuario is None:
        raise UsuarioError(404, "Usuario no encontrado.")
    return usuario


def _hash_or_422(password: str) -> str:
    try:
        return hash_password(password)
    except PasswordError as error:
        raise UsuarioError(422, str(error)) from None


@database_operation
def create_usuario(session: Session, data: UsuarioCrear) -> Usuario:
    usuario = Usuario(
        documento=data.documento,
        nombre=data.nombre,
        telefono=data.telefono,
        usuario=data.usuario,
        password_hash=_hash_or_422(data.password),
        rol=ROL_OPERADOR,
        activo=True,
        correo=data.correo,
        direccion=data.direccion,
    )
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return usuario


@database_operation
def list_usuarios(session: Session, offset: int, limit: int) -> dict:
    filtro = Usuario.rol == ROL_OPERADOR
    total = session.scalar(select(func.count()).select_from(Usuario).where(filtro))
    items = list(
        session.scalars(
            select(Usuario).where(filtro).order_by(Usuario.id).offset(offset).limit(limit)
        )
    )
    return {"items": items, "total": total, "offset": offset, "limit": limit}


@database_operation
def get_usuario(session: Session, usuario_id: int) -> Usuario:
    return find_usuario(session, usuario_id)


@database_operation
def update_usuario(session: Session, usuario_id: int, data: UsuarioActualizar) -> Usuario:
    usuario = find_usuario(session, usuario_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(usuario, key, value)
    session.commit()
    session.refresh(usuario)
    return usuario


@database_operation
def cambiar_estado(session: Session, usuario_id: int, activo: bool) -> Usuario:
    usuario = find_usuario(session, usuario_id)
    if usuario.rol == "ADMINISTRADOR":
        raise UsuarioError(403, "No se puede cambiar el estado de una cuenta administradora.")
    usuario.activo = activo
    session.commit()
    session.refresh(usuario)
    return usuario


@database_operation
def restablecer_password(session: Session, usuario_id: int, password: str) -> Usuario:
    usuario = find_usuario(session, usuario_id)
    usuario.password_hash = _hash_or_422(password)
    session.commit()
    session.refresh(usuario)
    return usuario
