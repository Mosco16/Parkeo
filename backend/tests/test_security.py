from app.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_password_no_guarda_texto_plano():
    hashed = hash_password("Parkeo2026*")

    assert hashed != "Parkeo2026*"
    assert hashed.startswith("$2")
    assert verify_password("Parkeo2026*", hashed) is True
    assert verify_password("otra-clave", hashed) is False


def test_verify_password_rechaza_hash_invalido():
    assert verify_password("Parkeo2026*", "no-es-un-hash") is False


def test_token_contiene_identidad_y_rol():
    token = create_access_token(
        usuario_id=7,
        usuario="ana.gomez",
        nombre="Ana Gómez",
        rol="OPERADOR",
    )

    payload = decode_access_token(token)

    assert payload is not None
    assert payload["sub"] == "7"
    assert payload["usuario"] == "ana.gomez"
    assert payload["nombre"] == "Ana Gómez"
    assert payload["rol"] == "OPERADOR"


def test_token_invalido_devuelve_none():
    assert decode_access_token("no-es-un-token") is None
    assert decode_access_token("") is None


def test_token_expirado_devuelve_none():
    from datetime import datetime, timedelta, timezone

    import jwt as pyjwt

    from app import security

    ajustes = security._SETTINGS
    vencido = pyjwt.encode(
        {
            "sub": "1",
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
        },
        ajustes.secret_key,
        algorithm=ajustes.algorithm,
    )

    assert decode_access_token(vencido) is None


def test_token_firmado_con_otra_clave_devuelve_none():
    import jwt as pyjwt

    ajeno = pyjwt.encode({"sub": "1"}, "otra-clave-distinta-de-32-bytes-o-mas", algorithm="HS256")

    assert decode_access_token(ajeno) is None
