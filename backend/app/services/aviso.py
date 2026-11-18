"""Job de avisos de vencimiento: dos días antes, una vez por ciclo (RN-AVI-01..06).

Se ejecuta desde ``scripts/enviar_avisos.py``. Es idempotente: el índice único
parcial ``uq_aviso_enviado`` impide dos avisos ENVIADO para el mismo vehículo y
vencimiento, y el servicio consulta antes de enviar.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import Aviso, Vehiculo
from app.services.ciclo import hoy_bogota
from app.services.correo import CorreoError, ServicioCorreo

DIAS_ANTICIPACION = 2
DETALLE_SIN_CONFIGURAR = "El correo no está configurado."


@dataclass
class ResultadoAviso:
    placa: str
    correo: str
    vencimiento: date
    resultado: str
    detalle: str | None = None


@dataclass
class ResumenAvisos:
    """Resultado del job; ``candidatos`` solo se llena en ``--dry-run``."""

    hoy: date
    objetivo: date
    enviados: list[ResultadoAviso] = field(default_factory=list)
    fallidos: list[ResultadoAviso] = field(default_factory=list)
    omitidos: int = 0
    candidatos: list[ResultadoAviso] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.enviados) + len(self.fallidos)


class ServicioAviso:
    def __init__(
        self,
        session: Session,
        correo: ServicioCorreo,
        dias_anticipacion: int = DIAS_ANTICIPACION,
    ) -> None:
        self.session = session
        self.correo = correo
        self.dias_anticipacion = dias_anticipacion

    def _ya_avisado(self, vehiculo_id: int, vencimiento: date) -> bool:
        encontrado = self.session.scalar(
            select(Aviso.id).where(
                Aviso.vehiculo_id == vehiculo_id,
                Aviso.fecha_vencimiento == vencimiento,
                Aviso.resultado == "ENVIADO",
            )
        )
        return encontrado is not None

    def _candidatos(self, objetivo: date) -> list[Vehiculo]:
        """Vehículos autorizados cuyo vencimiento vigente cae en ``objetivo``."""
        vehiculos = self.session.scalars(
            select(Vehiculo).where(
                Vehiculo.correo.is_not(None),
                Vehiculo.avisos_autorizados.is_(True),
            )
        ).all()
        return [vehiculo for vehiculo in vehiculos if vehiculo.fecha_vencimiento == objetivo]

    def _registrar(self, vehiculo: Vehiculo, objetivo: date, resultado: str,
                   detalle: str | None) -> None:
        self.session.add(
            Aviso(
                vehiculo_id=vehiculo.id,
                correo=vehiculo.correo,
                fecha_vencimiento=objetivo,
                resultado=resultado,
                detalle=detalle,
                fecha_hora=datetime.now(timezone.utc),
            )
        )
        self.session.commit()

    def enviar(self, fecha: date | None = None, dry_run: bool = False) -> ResumenAvisos:
        """Envía (o solo lista con ``dry_run``) los avisos del día indicado."""
        hoy = fecha or hoy_bogota()
        objetivo = hoy + timedelta(days=self.dias_anticipacion)
        resumen = ResumenAvisos(hoy=hoy, objetivo=objetivo)

        for vehiculo in self._candidatos(objetivo):
            detalle_base = ResultadoAviso(
                placa=vehiculo.placa,
                correo=vehiculo.correo,
                vencimiento=objetivo,
                resultado="PENDIENTE",
            )
            if self._ya_avisado(vehiculo.id, objetivo):
                resumen.omitidos += 1
                continue
            if dry_run:
                resumen.candidatos.append(detalle_base)
                continue
            try:
                self.correo.enviar_aviso(vehiculo.correo, vehiculo.placa, objetivo)
            except CorreoError as error:
                self._registrar_seguro(
                    vehiculo, objetivo, "FALLIDO", str(error), resumen, detalle_base
                )
                continue
            self._registrar_seguro(vehiculo, objetivo, "ENVIADO", None, resumen, detalle_base)
        return resumen

    def _registrar_seguro(
        self,
        vehiculo: Vehiculo,
        objetivo: date,
        resultado: str,
        detalle: str | None,
        resumen: ResumenAvisos,
        base: ResultadoAviso,
    ) -> None:
        """Registra el intento; una carrera con el índice único se omite."""
        try:
            self._registrar(vehiculo, objetivo, resultado, detalle)
        except IntegrityError:
            # Otro proceso ya envió el aviso de este ciclo.
            self.session.rollback()
            resumen.omitidos += 1
            return
        except SQLAlchemyError:
            self.session.rollback()
            raise
        registrado = ResultadoAviso(
            placa=base.placa,
            correo=base.correo,
            vencimiento=base.vencimiento,
            resultado=resultado,
            detalle=detalle,
        )
        if resultado == "ENVIADO":
            resumen.enviados.append(registrado)
        else:
            resumen.fallidos.append(registrado)
