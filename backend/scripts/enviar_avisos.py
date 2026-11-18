"""Job idempotente de avisos de vencimiento (RN-AVI-01..06).

Envía un correo dos días antes del vencimiento vigente, una sola vez por ciclo,
y registra el resultado en la tabla ``aviso``.

Ejemplos:
    .\\.venv\\Scripts\\python.exe scripts\\enviar_avisos.py --dry-run
    .\\.venv\\Scripts\\python.exe scripts\\enviar_avisos.py --fecha 2026-11-20
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

# Permite ejecutar el archivo directamente desde backend/ o desde scripts/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session  # noqa: E402

from app.config import ConfigurationError, load_mail_settings  # noqa: E402
from app.database import get_engine  # noqa: E402
from app.services.aviso import ServicioAviso  # noqa: E402
from app.services.ciclo import hoy_bogota  # noqa: E402
from app.services.correo import SmtpCorreo, correo_sin_configurar  # noqa: E402


def argumentos(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Envía los avisos de vencimiento de mensualidad de Parkeo."
    )
    parser.add_argument(
        "--fecha",
        help="Fecha de referencia en America/Bogota (AAAA-MM-DD). Por defecto, hoy.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Lista los avisos pendientes sin enviar correos ni registrar nada.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = argumentos(argv)
    try:
        fecha = date.fromisoformat(args.fecha) if args.fecha else hoy_bogota()
    except ValueError:
        print("La fecha debe tener el formato AAAA-MM-DD.")
        return 2

    try:
        settings = load_mail_settings()
    except ConfigurationError as error:
        print(f"Configuración de correo inválida: {error}")
        return 2

    if args.dry_run:
        correo = correo_sin_configurar()
    elif settings is None:
        print("Falta configurar SMTP en backend/.env: no se envían avisos.")
        return 2
    else:
        correo = SmtpCorreo(settings)

    with Session(get_engine()) as session:
        resumen = ServicioAviso(session, correo).enviar(fecha=fecha, dry_run=args.dry_run)

    print(f"Fecha de referencia: {resumen.hoy.isoformat()}")
    print(f"Vencimientos avisados: {resumen.objetivo.isoformat()}")
    if args.dry_run:
        print(f"Avisos pendientes: {len(resumen.candidatos)}")
        for item in resumen.candidatos:
            print(f"  {item.placa} -> {item.correo}")
        print(f"Ya avisados para este ciclo: {resumen.omitidos}")
        return 0

    print(f"Enviados: {len(resumen.enviados)}")
    print(f"Fallidos: {len(resumen.fallidos)}")
    print(f"Omitidos (ya avisados): {resumen.omitidos}")
    for item in resumen.fallidos:
        print(f"  Falló {item.placa}: {item.detalle}")
    return 1 if resumen.fallidos else 0


if __name__ == "__main__":
    raise SystemExit(main())
