from datetime import date, datetime, timezone
from functools import wraps
from zoneinfo import ZoneInfo

from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import ZONA_HORARIA
from app.models import Celda, Estancia, Usuario, Vehiculo, required_text
from app.schemas.celda import CeldaRespuesta
from app.schemas.estancia import (
    CambioCeldaCrear,
    EntradaCrear,
    EstanciaAbiertaRespuesta,
    EstanciaRespuesta,
    EstadoVehiculoRespuesta,
    SalidaCrear,
)
from app.schemas.vehiculo import VehiculoRespuesta


class EstanciaError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail


def transaccion(operation):
    """Una transacción por solicitud; materializa la respuesta antes del commit."""

    @wraps(operation)
    def wrapped(self, *args, **kwargs):
        try:
            with self.session.begin():
                return operation(self, *args, **kwargs)
        except EstanciaError:
            raise
        except IntegrityError as error:
            self.session.rollback()
            code = getattr(error.orig, "sqlstate", None)
            constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
            if code == "23505":
                if constraint == "uq_estancia_vehiculo_abierta":
                    raise EstanciaError(409, "Este vehículo ya figura dentro.") from None
                if constraint == "uq_estancia_celda_abierta":
                    raise EstanciaError(409, "La celda no está disponible o es de otro tipo.") from None
            if code == "23503":
                raise EstanciaError(404, "Una de las referencias ya no existe. Actualiza los datos.") from None
            if code in {"23502", "23514"}:
                raise EstanciaError(422, "Los datos incumplen las restricciones de la estancia.") from None
            raise EstanciaError(409, "La operación entra en conflicto con los datos existentes.") from None
        except SQLAlchemyError:
            self.session.rollback()
            raise EstanciaError(503, "No se pudo completar la operación con la base de datos.") from None

    return wrapped


def hoy_bogota() -> date:
    return datetime.now(ZoneInfo(ZONA_HORARIA)).date()


def mensualidad(vehiculo: Vehiculo) -> str:
    # VIGENTE solo si hoy es anterior a fecha_vencimiento. Si vence hoy, ya es VENCIDA.
    if hoy_bogota() < vehiculo.fecha_vencimiento:
        return "VIGENTE"
    return "VENCIDA"


def tipo_celda_requerido(vehiculo: Vehiculo) -> str:
    if vehiculo.tipo == "MOTO":
        return "MOTO"
    # AUTOMOVIL y CAMIONETA usan AUTO (RN-VEH-02)
    return "AUTO"


class ServicioEstancia:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _vehiculo(self, placa: str) -> Vehiculo:
        vehiculo = self.session.scalar(select(Vehiculo).where(Vehiculo.placa == placa))
        if vehiculo is None:
            raise EstanciaError(404, "Vehículo no encontrado.")
        return vehiculo

    def _celda_libre(self, tipo: str, bloquear: bool):
        # Una celda está libre si no tiene estancia abierta (RN-CEL-03).
        ocupada = (
            select(Estancia.id)
            .where(Estancia.celda_id == Celda.id, Estancia.salida.is_(None))
            .exists()
        )
        query = (
            select(Celda)
            .where(Celda.tipo == tipo, ~ocupada)
            .order_by(func.length(Celda.codigo), Celda.codigo)
            .limit(1)
        )
        if bloquear:
            # E-15: la segunda entrada no espera; toma la siguiente celda libre.
            query = query.with_for_update(skip_locked=True, of=Celda)
        return self.session.scalar(query)

    @transaccion
    def entrada(self, data: EntradaCrear, usuario: Usuario) -> EstanciaAbiertaRespuesta:
        vehiculo = self._vehiculo(data.placa)

        if mensualidad(vehiculo) == "VENCIDA":
            raise EstanciaError(409, "Pago pendiente: la mensualidad está vencida.")

        if self.session.scalar(
            select(Estancia.id).where(
                Estancia.vehiculo_id == vehiculo.id, Estancia.salida.is_(None)
            )
        ) is not None:
            raise EstanciaError(409, "Este vehículo ya figura dentro.")

        tipo = tipo_celda_requerido(vehiculo)
        intento = 0
        estancia = None
        celda = None
        while intento < 2:
            celda = self._celda_libre(tipo, bloquear=True)
            if celda is None:
                raise EstanciaError(409, "No hay celdas libres para este tipo de vehículo.")
            try:
                # Savepoint: si el índice único rechaza la celda, la transacción
                # exterior sigue viva y el reintento es posible (E-15).
                with self.session.begin_nested():
                    estancia = Estancia(
                        vehiculo_id=vehiculo.id,
                        celda_id=celda.id,
                        usuario_entrada_id=usuario.id,
                        entrada=datetime.now(timezone.utc),
                    )
                    self.session.add(estancia)
                    self.session.flush()
                break
            except IntegrityError as error:
                constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
                if constraint != "uq_estancia_celda_abierta":
                    raise
                intento += 1
        if estancia is None or celda is None:
            raise EstanciaError(409, "La celda no está disponible o es de otro tipo.")

        return EstanciaAbiertaRespuesta(
            **EstanciaRespuesta.model_validate(estancia).model_dump(),
            celda=CeldaRespuesta.model_validate(celda),
        )

    @transaccion
    def salida(self, data: SalidaCrear, usuario: Usuario) -> EstanciaRespuesta:
        vehiculo = self._vehiculo(data.placa)
        # PostgreSQL vuelve a evaluar salida IS NULL tras esperar el bloqueo.
        estancia = self.session.scalar(
            select(Estancia)
            .where(Estancia.vehiculo_id == vehiculo.id, Estancia.salida.is_(None))
            .with_for_update()
        )
        if estancia is None:
            raise EstanciaError(409, "El vehículo no tiene una entrada abierta.")
        try:
            estancia.cerrar(datetime.now(timezone.utc), usuario)
        except ValueError:
            raise EstanciaError(409, "No se puede cerrar la estancia con su estado o fecha actuales.") from None
        self.session.flush()
        return EstanciaRespuesta.model_validate(estancia)

    @transaccion
    def cambiar_celda(self, data: CambioCeldaCrear) -> EstanciaAbiertaRespuesta:
        vehiculo = self._vehiculo(data.placa)
        estancia = self.session.scalar(
            select(Estancia)
            .where(Estancia.vehiculo_id == vehiculo.id, Estancia.salida.is_(None))
            .with_for_update()
        )
        if estancia is None:
            raise EstanciaError(409, "El vehículo no tiene una entrada abierta.")

        celda_destino = self.session.get(Celda, data.celda_id)
        if celda_destino is None:
            raise EstanciaError(404, "Celda no encontrada.")

        celda_actual = self.session.get(Celda, estancia.celda_id)
        tipo_requerido = tipo_celda_requerido(vehiculo)
        if celda_destino.tipo != tipo_requerido or celda_destino.tipo != celda_actual.tipo:
            raise EstanciaError(409, "La celda no está disponible o es de otro tipo.")
        if self.session.scalar(
            select(Estancia.id).where(
                Estancia.celda_id == celda_destino.id,
                Estancia.salida.is_(None),
                Estancia.id != estancia.id,
            )
        ) is not None:
            raise EstanciaError(409, "La celda no está disponible o es de otro tipo.")

        try:
            estancia.celda_id = celda_destino.id
            with self.session.begin_nested():
                self.session.flush()
        except IntegrityError as error:
            code = getattr(error.orig, "sqlstate", None)
            constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
            if code == "23505" and constraint == "uq_estancia_celda_abierta":
                raise EstanciaError(409, "La celda no está disponible o es de otro tipo.") from None
            raise
        self.session.refresh(estancia)
        celda_final = self.session.get(Celda, estancia.celda_id)
        return EstanciaAbiertaRespuesta(
            **EstanciaRespuesta.model_validate(estancia).model_dump(),
            celda=CeldaRespuesta.model_validate(celda_final),
        )

    @transaccion
    def consultar(self, placa: str) -> EstadoVehiculoRespuesta:
        placa = required_text(placa, "placa").upper()
        row = self.session.execute(
            select(Vehiculo, Estancia, Celda)
            .outerjoin(Estancia, and_(Estancia.vehiculo_id == Vehiculo.id, Estancia.salida.is_(None)))
            .outerjoin(Celda, Celda.id == Estancia.celda_id)
            .where(Vehiculo.placa == placa)
        ).one_or_none()
        if row is None:
            raise EstanciaError(404, "Vehículo no encontrado.")
        vehiculo, estancia, celda = row
        m = mensualidad(vehiculo)
        abierta = None
        if estancia is not None:
            abierta = EstanciaAbiertaRespuesta(
                **EstanciaRespuesta.model_validate(estancia).model_dump(),
                celda=CeldaRespuesta.model_validate(celda),
            )
        celda_sugerida = None
        if estancia is None and m == "VIGENTE":
            sugerida = self._celda_libre(tipo_celda_requerido(vehiculo), bloquear=False)
            if sugerida is not None:
                celda_sugerida = CeldaRespuesta.model_validate(sugerida)
        return EstadoVehiculoRespuesta(
            vehiculo=VehiculoRespuesta.model_validate(vehiculo),
            esta_dentro=estancia is not None,
            estancia=abierta,
            mensualidad=m,
            celda_sugerida=celda_sugerida,
        )
