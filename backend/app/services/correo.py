"""Envío de los avisos de vencimiento por correo (RN-AVI-01).

El servicio queda detrás de la interfaz ``ServicioCorreo``: la implementación
real usa SMTP y las pruebas inyectan un doble que no abre conexiones. El
mensaje lleva el logo de Parkeo incrustado por CID a 200 px y una versión en
texto plano para clientes que no renderizan HTML.
"""

from __future__ import annotations

import smtplib
import ssl
from abc import ABC, abstractmethod
from datetime import date
from email.message import Message
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate, make_msgid
from pathlib import Path

from app.config import MailSettings

LOGO_PREDETERMINADO = (
    Path(__file__).resolve().parents[3] / "frontend" / "public" / "parkeo-logo.jpeg"
)
LOGO_CID = "parkeo-logo"
LOGO_PX = 200
ASUNTO = "Aviso de vencimiento de mensualidad — Parkeo"


class CorreoError(Exception):
    """Fallo de envío; el llamador registra el aviso como FALLIDO."""


class ServicioCorreo(ABC):
    """Interfaz mínima que el job de avisos necesita."""

    @abstractmethod
    def enviar_aviso(self, destinatario: str, placa: str, vencimiento: date) -> None:
        """Envía el aviso o lanza ``CorreoError``."""


def fecha_larga(vencimiento: date) -> str:
    return vencimiento.strftime("%d/%m/%Y")


def texto_plano(placa: str, vencimiento: date) -> str:
    return (
        "Hola,\n\n"
        f"La mensualidad del vehículo {placa} vence el {fecha_larga(vencimiento)}. "
        "Quedan dos días para renovarla.\n\n"
        "Puedes registrar el pago en la recepción del parqueadero. "
        "Si ya pagaste, ignora este mensaje.\n\n"
        "Parkeo — Parqueadero\n"
    )


def texto_html(placa: str, vencimiento: date) -> str:
    return f"""<!DOCTYPE html>
<html lang="es">
  <body style="margin:0;padding:24px;background:#f4f5f7;font-family:Segoe UI,Arial,sans-serif;color:#1f2933;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td align="center">
          <table role="presentation" width="520" cellpadding="0" cellspacing="0"
                 style="background:#ffffff;border-radius:12px;padding:32px;">
            <tr>
              <td align="center">
                <img src="cid:{LOGO_CID}" width="{LOGO_PX}" height="{LOGO_PX}"
                     alt="Parkeo" style="display:block;border:0;" />
              </td>
            </tr>
            <tr>
              <td style="padding-top:24px;">
                <h1 style="margin:0 0 12px;font-size:20px;">Tu mensualidad está por vencer</h1>
                <p style="margin:0 0 8px;font-size:15px;line-height:22px;">
                  La mensualidad del vehículo <strong>{placa}</strong> vence el
                  <strong>{fecha_larga(vencimiento)}</strong>. Quedan dos días para renovarla.
                </p>
                <p style="margin:0;font-size:15px;line-height:22px;">
                  Registra el pago en la recepción del parqueadero. Si ya pagaste,
                  ignora este mensaje.
                </p>
              </td>
            </tr>
            <tr>
              <td style="padding-top:24px;font-size:13px;color:#616e7c;">Parkeo — Parqueadero</td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


def construir_mensaje(
    destinatario: str,
    placa: str,
    vencimiento: date,
    settings: MailSettings,
    logo: Path | None = None,
) -> Message:
    """Arma el mensaje MIME con HTML, texto plano y el logo incrustado."""
    ruta = logo or LOGO_PREDETERMINADO
    if not ruta.is_file():
        raise CorreoError("No se encontró el logo para el aviso de vencimiento.")

    mensaje = MIMEMultipart("related")
    mensaje["Subject"] = ASUNTO
    mensaje["From"] = formataddr((settings.nombre, settings.remitente))
    mensaje["To"] = destinatario
    mensaje["Date"] = formatdate(localtime=False)
    mensaje["Message-ID"] = make_msgid(domain="parkeo.local")

    alternativa = MIMEMultipart("alternative")
    alternativa.attach(MIMEText(texto_plano(placa, vencimiento), "plain", "utf-8"))
    alternativa.attach(MIMEText(texto_html(placa, vencimiento), "html", "utf-8"))
    mensaje.attach(alternativa)

    imagen = MIMEImage(ruta.read_bytes(), _subtype="jpeg")
    imagen.add_header("Content-ID", f"<{LOGO_CID}>")
    imagen.add_header("Content-Disposition", "inline", filename=ruta.name)
    mensaje.attach(imagen)
    return mensaje


class SmtpCorreo(ServicioCorreo):
    """Implementación real sobre SMTP con STARTTLS o SSL."""

    def __init__(self, settings: MailSettings, logo: Path | None = None, timeout: int = 30) -> None:
        self.settings = settings
        self.logo = logo
        self.timeout = timeout

    def enviar_aviso(self, destinatario: str, placa: str, vencimiento: date) -> None:
        try:
            mensaje = construir_mensaje(destinatario, placa, vencimiento, self.settings, self.logo)
            contexto = ssl.create_default_context()
            if self.settings.tls == "ssl":
                servidor = smtplib.SMTP_SSL(
                    self.settings.host, self.settings.port, timeout=self.timeout, context=contexto
                )
            else:
                servidor = smtplib.SMTP(
                    self.settings.host, self.settings.port, timeout=self.timeout
                )
            with servidor:
                servidor.ehlo()
                if self.settings.tls == "inicio":
                    servidor.starttls(context=contexto)
                    servidor.ehlo()
                servidor.login(self.settings.usuario, self.settings.password)
                servidor.send_message(mensaje)
        except CorreoError:
            raise
        except (OSError, smtplib.SMTPException) as error:
            raise CorreoError(f"No se pudo enviar el aviso: {error.__class__.__name__}") from None


def correo_sin_configurar() -> ServicioCorreo:
    """Doble para ``--dry-run``: nunca contacta al servidor de correo."""

    class SinCorreo(ServicioCorreo):
        def enviar_aviso(self, destinatario: str, placa: str, vencimiento: date) -> None:
            raise CorreoError("El correo no está configurado.")

    return SinCorreo()
