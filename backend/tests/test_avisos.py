"""S10 / RN-AVI-01..06: mensaje con logo, job idempotente y registro de avisos.

Las pruebas no abren conexiones SMTP ni tocan PostgreSQL: usan un doble de
``ServicioCorreo`` y una sesión simulada.
"""

from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

from app.config import MailSettings
from app.models import Aviso, Vehiculo
from app.services.aviso import DIAS_ANTICIPACION, ResumenAvisos, ServicioAviso
from app.services.correo import (
    LOGO_CID,
    CorreoError,
    ServicioCorreo,
    construir_mensaje,
)

HOY = date(2026, 11, 18)
VENCE = date(2026, 11, 20)
SETTINGS = MailSettings(
    host="smtp.ejemplo.test",
    port=587,
    tls="inicio",
    usuario="avisos@ejemplo.test",
    password="secreto",
    remitente="avisos@ejemplo.test",
    nombre="Parkeo",
)


def vehiculo(placa: str = "ABC123", correo: str | None = "dueno@correo.co",
             autorizado: bool = True, vencimiento: date | None = VENCE) -> Vehiculo:
    datos = dict(
        id=1,
        placa=placa,
        color="Azul",
        modelo=2025,
        marca="Marca",
        tipo="AUTOMOVIL",
        correo=correo,
        avisos_autorizados=autorizado,
    )
    coche = Vehiculo(**datos)
    if vencimiento is not None:
        from conftest import con_pago

        con_pago(coche, vencimiento)
    return coche


class CorreoDoble(ServicioCorreo):
    def __init__(self, fallar: bool = False) -> None:
        self.fallar = fallar
        self.llamadas: list[tuple[str, str, date]] = []

    def enviar_aviso(self, destinatario: str, placa: str, vencimiento: date) -> None:
        self.llamadas.append((destinatario, placa, vencimiento))
        if self.fallar:
            raise CorreoError("No se pudo enviar el aviso: SMTPException")


def sesion_con(vehiculos: list[Vehiculo], ya_avisados: set[int] | None = None):
    """Sesión simulada: ``_ya_avisado`` responde en el orden de los vehículos."""
    session = MagicMock()
    session.scalars.return_value.all.return_value = vehiculos
    ya_avisados = ya_avisados or set()
    # ``_ya_avisado`` devuelve el id del aviso encontrado o None.
    session.scalar.side_effect = [
        coche.id if indice in ya_avisados else None
        for indice, coche in enumerate(vehiculos)
    ]
    return session


# --- Mensaje ---------------------------------------------------------------


def test_mensaje_lleva_texto_html_y_logo_por_cid(tmp_path):
    logo = tmp_path / "parkeo-logo.jpeg"
    logo.write_bytes(b"\xff\xd8\xff\xe0logo-de-prueba")

    mensaje = construir_mensaje("dueno@correo.co", "ABC123", VENCE, SETTINGS, logo)

    partes = {parte.get_content_type(): parte for parte in mensaje.walk()}
    html = partes["text/html"].get_payload(decode=True).decode("utf-8")
    plano = partes["text/plain"].get_payload(decode=True).decode("utf-8")

    assert "ABC123" in plano and "20/11/2026" in plano
    assert "ABC123" in html and "20/11/2026" in html
    assert f'width="{200}"' in html
    assert f"cid:{LOGO_CID}" in html


def test_logo_se_adjunta_como_inline_con_content_id(tmp_path):
    logo = tmp_path / "parkeo-logo.jpeg"
    logo.write_bytes(b"\xff\xd8\xff\xe0logo-de-prueba")

    mensaje = construir_mensaje("dueno@correo.co", "ABC123", VENCE, SETTINGS, logo)

    imagenes = [p for p in mensaje.walk() if p.get_content_type() == "image/jpeg"]
    assert len(imagenes) == 1
    assert imagenes[0]["Content-ID"] == f"<{LOGO_CID}>"
    assert imagenes[0]["Content-Disposition"].startswith("inline")


def test_mensaje_usa_remitente_y_asunto_configurados(tmp_path):
    logo = tmp_path / "parkeo-logo.jpeg"
    logo.write_bytes(b"\xff\xd8\xff\xe0logo-de-prueba")

    mensaje = construir_mensaje("dueno@correo.co", "ABC123", VENCE, SETTINGS, logo)

    assert "Parkeo" in mensaje["From"]
    assert SETTINGS.remitente in mensaje["From"]
    assert "vencimiento" in mensaje["Subject"].lower()


def test_sin_logo_el_mensaje_falla_con_error_publico(tmp_path):
    with pytest.raises(CorreoError):
        construir_mensaje(
            "dueno@correo.co", "ABC123", VENCE, SETTINGS, tmp_path / "no-existe.jpeg"
        )


# --- Job de avisos ---------------------------------------------------------


def test_envia_solo_al_vencimiento_de_dos_dias_y_registra_enviado():
    coche = vehiculo()
    session = sesion_con([coche])
    correo = CorreoDoble()

    resumen = ServicioAviso(session, correo).enviar(fecha=HOY)

    assert resumen.objetivo == VENCE
    assert resumen.total == 1
    assert resumen.enviados[0].placa == "ABC123"
    assert correo.llamadas == [("dueno@correo.co", "ABC123", VENCE)]
    aviso = session.add.call_args_list[0].args[0]
    assert isinstance(aviso, Aviso)
    assert aviso.resultado == "ENVIADO"
    assert aviso.fecha_vencimiento == VENCE
    assert aviso.detalle is None
    session.commit.assert_called_once()


def test_ignora_vehiculos_que_no_vence_en_la_fecha_objetivo():
    lejano = vehiculo(placa="DEF456", vencimiento=date(2026, 11, 25))
    session = sesion_con([lejano])
    correo = CorreoDoble()

    resumen = ServicioAviso(session, correo).enviar(fecha=HOY)

    assert resumen.total == 0
    assert correo.llamadas == []
    session.add.assert_not_called()


def test_no_duplica_aviso_enviado_para_el_mismo_ciclo():
    coche = vehiculo()
    session = sesion_con([coche], ya_avisados={0})
    correo = CorreoDoble()

    resumen = ServicioAviso(session, correo).enviar(fecha=HOY)

    assert resumen.omitidos == 1
    assert resumen.total == 0
    assert correo.llamadas == []
    session.add.assert_not_called()


def test_fallo_de_correo_se_registra_como_fallido_y_sigue_con_el_resto():
    primero = vehiculo(placa="AAA111")
    segundo = vehiculo(placa="BBB222")
    session = sesion_con([primero, segundo])
    correo = CorreoDoble(fallar=True)

    resumen = ServicioAviso(session, correo).enviar(fecha=HOY)

    assert len(resumen.fallidos) == 2
    assert resumen.enviados == []
    assert len(correo.llamadas) == 2
    resultados = [call.args[0].resultado for call in session.add.call_args_list]
    assert resultados == ["FALLIDO", "FALLIDO"]
    assert "SMTPException" in session.add.call_args_list[0].args[0].detalle


def test_carrera_con_el_indice_unico_omite_sin_reventar():
    coche = vehiculo()
    session = sesion_con([coche])
    session.commit.side_effect = IntegrityError("INSERT", {}, Exception("uq_aviso_enviado"))

    resumen = ServicioAviso(session, CorreoDoble()).enviar(fecha=HOY)

    assert resumen.omitidos == 1
    assert resumen.enviados == []
    session.rollback.assert_called_once()


def test_dry_run_lista_candidatos_sin_enviar_ni_registrar():
    coche = vehiculo()
    session = sesion_con([coche])
    correo = CorreoDoble()

    resumen = ServicioAviso(session, correo).enviar(fecha=HOY, dry_run=True)

    assert isinstance(resumen, ResumenAvisos)
    assert [c.placa for c in resumen.candidatos] == ["ABC123"]
    assert correo.llamadas == []
    session.add.assert_not_called()
    session.commit.assert_not_called()


def test_la_anticipacion_es_de_dos_dias():
    coche = vehiculo(vencimiento=HOY + timedelta(days=2))
    session = sesion_con([coche])

    resumen = ServicioAviso(session, CorreoDoble()).enviar(fecha=HOY)

    assert DIAS_ANTICIPACION == 2
    assert resumen.total == 1
