"""Registro, anulación e historial de pagos de mensualidad (RN-PAG, RN-ANU)."""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.models import Pago, Usuario, Vehiculo
from app.schemas.pago import PagoAnular, PagoCrear, PagoRespuesta, PagosPagina
from app.services.ciclo import (
    calcular_ciclo,
    hoy_bogota,
    supera_tope_adelantado,
    tarifa_mensual,
)

VEHICULO_NO_ENCONTRADO = "Vehículo no encontrado"
PAGO_NO_ENCONTRADO = "Pago no encontrado."
REFERENCIA_REPETIDA = "La referencia del recibo ya está registrada en un pago activo."
TOPE_ADELANTADO = "Solo se puede pagar un ciclo por adelantado."
NO_ES_ULTIMO_PAGO = "Solo se puede anular el último pago activo del vehículo."
PAGO_YA_ANULADO = "El pago ya está anulado."
FALTA_CORREO = "Falta el correo para autorizar los avisos."


class PagoError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail


def _respuesta(pago: Pago, vehiculo: Vehiculo) -> PagoRespuesta:
    """Materializa la respuesta antes del commit (la sesión expira al confirmar)."""
    return PagoRespuesta(
        id=pago.id,
        placa=vehiculo.placa,
        valor=pago.valor,
        referencia=pago.referencia,
        fecha_hora=pago.fecha_hora,
        dia_corte=pago.dia_corte,
        inicio_ciclo=pago.inicio_ciclo,
        vencimiento_ciclo=pago.vencimiento_ciclo,
        estado=pago.estado,
        motivo_anulacion=pago.anulacion_motivo,
        anulacion_fecha_hora=pago.anulacion_fecha_hora,
        usuario=pago.usuario.nombre,
    )


class ServicioPago:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _vehiculo(self, placa: str) -> Vehiculo:
        vehiculo = self.session.scalar(select(Vehiculo).where(Vehiculo.placa == placa))
        if vehiculo is None:
            raise PagoError(404, VEHICULO_NO_ENCONTRADO)
        return vehiculo

    def _referencia_activa(self, referencia: str) -> bool:
        encontrada = self.session.scalar(
            select(Pago.id).where(
                Pago.referencia == referencia,
                Pago.anulacion_fecha_hora.is_(None),
            )
        )
        return encontrada is not None

    def _contacto(self, vehiculo: Vehiculo, datos: PagoCrear, usuario: Usuario) -> None:
        """Actualiza correo y autorización de avisos junto con el pago (RN-AVI-04)."""
        if datos.autorizar_avisos and not (datos.correo or vehiculo.correo):
            raise PagoError(422, FALTA_CORREO)
        if datos.correo is not None:
            vehiculo.correo = datos.correo
        if datos.autorizar_avisos is None:
            return
        if datos.autorizar_avisos:
            vehiculo.avisos_autorizados = True
            vehiculo.autorizacion_usuario_id = usuario.id
            vehiculo.autorizacion_fecha_hora = datetime.now(timezone.utc)
        else:
            vehiculo.avisos_autorizados = False
            vehiculo.autorizacion_usuario_id = None
            vehiculo.autorizacion_fecha_hora = None

    def registrar(self, datos: PagoCrear, usuario: Usuario) -> PagoRespuesta:
        """Registra un pago con valor y ciclo calculados por el servidor (RN-PAG-05)."""
        vehiculo = self._vehiculo(datos.placa)
        # RN-PAG-06: la referencia se repite solo entre pagos activos.
        if self._referencia_activa(datos.referencia):
            raise PagoError(409, REFERENCIA_REPETIDA)
        hoy = hoy_bogota()
        vencimiento = vehiculo.fecha_vencimiento
        # RN-PAG-09: como máximo un ciclo por adelantado.
        if supera_tope_adelantado(vencimiento, hoy):
            raise PagoError(409, TOPE_ADELANTADO)

        ciclo = calcular_ciclo(vencimiento, vehiculo.dia_corte, hoy)
        pago = Pago(
            vehiculo=vehiculo,
            usuario=usuario,
            valor=tarifa_mensual(vehiculo.tipo),
            referencia=datos.referencia,
            fecha_hora=datetime.now(timezone.utc),
            dia_corte=ciclo.dia_corte,
            inicio_ciclo=ciclo.inicio_ciclo,
            vencimiento_ciclo=ciclo.vencimiento_ciclo,
        )
        self._contacto(vehiculo, datos, usuario)
        self.session.add(pago)
        try:
            self.session.flush()
            respuesta = _respuesta(pago, vehiculo)
            self.session.commit()
        except IntegrityError as error:
            self.session.rollback()
            code = getattr(error.orig, "sqlstate", None)
            constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
            if code == "23505" and constraint == "uq_pago_referencia_activa":
                raise PagoError(409, REFERENCIA_REPETIDA) from None
            raise PagoError(
                409, "La operación entra en conflicto con los datos existentes."
            ) from None
        except SQLAlchemyError:
            self.session.rollback()
            raise PagoError(503, "No se pudo completar la operación con la base de datos.") from None
        return respuesta

    def anular(self, pago_id: int, datos: PagoAnular, usuario: Usuario) -> PagoRespuesta:
        """RN-ANU-01: el pago no se borra ni se edita, se marca como anulado."""
        pago = self.session.get(Pago, pago_id)
        if pago is None:
            raise PagoError(404, PAGO_NO_ENCONTRADO)
        if pago.estado == "ANULADO":
            raise PagoError(409, PAGO_YA_ANULADO)
        vehiculo = pago.vehiculo
        activos = vehiculo.pagos_activos
        ultimo = max(activos, key=lambda activo: (activo.fecha_hora, activo.id or 0))
        # RN-ANU-03: solo el último pago activo, para no dejar huecos en el ciclo.
        if ultimo.id != pago.id:
            raise PagoError(409, NO_ES_ULTIMO_PAGO)
        pago.anular(datetime.now(timezone.utc), usuario, datos.motivo)
        respuesta = _respuesta(pago, vehiculo)
        try:
            self.session.commit()
        except SQLAlchemyError:
            self.session.rollback()
            raise PagoError(503, "No se pudo completar la operación con la base de datos.") from None
        return respuesta

    def historial(self, placa: str, pagina: int, tamano: int) -> PagosPagina:
        """RN-HIS-01: activos y anulados, del más reciente al más antiguo."""
        vehiculo = self._vehiculo(placa)
        total = self.session.scalar(
            select(func.count()).select_from(Pago).where(Pago.vehiculo_id == vehiculo.id)
        )
        pagos = self.session.scalars(
            select(Pago)
            .where(Pago.vehiculo_id == vehiculo.id)
            .options(joinedload(Pago.usuario))
            .order_by(Pago.fecha_hora.desc(), Pago.id.desc())
            .offset((pagina - 1) * tamano)
            .limit(tamano)
        ).all()
        return PagosPagina(
            items=[_respuesta(pago, vehiculo) for pago in pagos],
            total=total or 0,
            pagina=pagina,
            tamano=tamano,
        )
