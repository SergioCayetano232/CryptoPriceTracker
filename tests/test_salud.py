"""Tests del aviso de caidas."""

from datetime import datetime, timedelta, timezone

from crypto_tracker.salud import Pulso, mensaje_parado

INICIO = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)


def _min(minutos):
    return INICIO + timedelta(minutes=minutos)


def test_un_fallo_suelto_no_avisa():
    pulso = Pulso(minutos=30)

    assert pulso.fallo("Sin conexion", _min(0)) is None
    assert pulso.exito(_min(5)) is None


def test_avisa_al_llegar_al_margen():
    pulso = Pulso(minutos=30)

    for minuto in (0, 5, 10, 15, 20, 25):
        assert pulso.fallo("Sin conexion", _min(minuto)) is None

    texto = pulso.fallo("Sin conexion con CoinGecko", _min(30))

    assert texto is not None
    assert "30 min" in texto
    assert "Sin conexion con CoinGecko" in texto


def test_no_repite_el_aviso_mientras_sigue_caido():
    pulso = Pulso(minutos=30)
    pulso.fallo("x", _min(0))
    assert pulso.fallo("x", _min(30)) is not None

    for minuto in (35, 60, 120):
        assert pulso.fallo("x", _min(minuto)) is None


def test_avisa_cuando_vuelve():
    pulso = Pulso(minutos=30)
    pulso.fallo("x", _min(0))
    pulso.fallo("x", _min(30))

    texto = pulso.exito(_min(45))

    assert texto is not None
    assert "45 min" in texto


def test_tras_volver_puede_avisar_de_otra_caida():
    pulso = Pulso(minutos=30)
    pulso.fallo("x", _min(0))
    pulso.fallo("x", _min(30))
    pulso.exito(_min(35))

    # la cuenta empieza de cero, no desde la caida de antes
    assert pulso.fallo("x", _min(40)) is None
    assert pulso.fallo("x", _min(70)) is not None


def test_un_exito_en_medio_reinicia_la_cuenta():
    pulso = Pulso(minutos=30)
    pulso.fallo("x", _min(0))
    pulso.fallo("x", _min(25))
    pulso.exito(_min(26))

    assert pulso.fallo("x", _min(31)) is None


def test_duracion_en_horas():
    pulso = Pulso(minutos=30)
    pulso.fallo("x", _min(0))

    assert "2 h 5 min" in pulso.fallo("x", _min(125))
    assert "3 h" in pulso.exito(_min(180))


def test_escapa_el_error():
    pulso = Pulso(minutos=0)

    texto = pulso.fallo("<b>raro</b>", _min(0))

    assert "<b>raro</b>" not in texto
    assert "&lt;b&gt;" in texto


def test_mensaje_parado():
    texto = mensaje_parado(10, "ValueError: <mal>")

    assert "10 errores" in texto
    assert "&lt;mal&gt;" in texto
