"""Tests del tramo de /historico."""

from datetime import datetime, timedelta, timezone

import pytest

from crypto_tracker.periodo import PeriodoError, falta_principio, interpretar, nombre

# --- leer el tramo ---


@pytest.mark.parametrize(
    "argumento, esperado",
    [
        ("bitcoin", ("bitcoin", 24)),
        ("Bitcoin 7d", ("bitcoin", 168)),
        ("bitcoin 12h", ("bitcoin", 12)),
        ("bitcoin 30m", ("bitcoin", 0.5)),
        ("bitcoin 6", ("bitcoin", 6)),  # sin letra son horas, como en /mute
        ("", ("", 24)),
    ],
)
def test_interpretar(argumento, esperado):
    assert interpretar(argumento) == esperado


@pytest.mark.parametrize("argumento", ["bitcoin siempre", "bitcoin 0d", "bitcoin -2h"])
def test_interpretar_tramo_malo(argumento):
    with pytest.raises(PeriodoError):
        interpretar(argumento)


def test_interpretar_demasiadas_palabras():
    with pytest.raises(PeriodoError, match="/historico bitcoin 7d"):
        interpretar("bitcoin 7d ya")


def test_como_mucho_un_ano():
    assert interpretar("bitcoin 365d")[1] == 365 * 24

    with pytest.raises(PeriodoError, match="un año"):
        interpretar("bitcoin 400d")


# --- decirlo ---


@pytest.mark.parametrize(
    "horas, texto",
    [
        (24, "últimas 24 h"),
        (36, "últimas 36 h"),
        (168, "últimos 7 días"),
        (720, "últimos 30 días"),
        (60, "últimas 60 h"),  # dos dias y medio: mejor en horas que "2,5 días"
        (1, "última hora"),
        (1.5, "últimas 1,5 h"),
        (0.5, "últimos 30 min"),
    ],
)
def test_nombre(horas, texto):
    assert nombre(horas) == texto


# --- si faltan datos del principio ---

AHORA = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)


def test_con_datos_desde_el_principio_no_falta_nada():
    # el primer precio cae un ciclo despues del inicio: normal
    primero = AHORA - timedelta(hours=24) + timedelta(minutes=5)

    assert falta_principio(primero, AHORA, 24) is False


def test_recien_instalado_falta_el_principio():
    assert falta_principio(AHORA - timedelta(hours=3), AHORA, 24) is True


def test_en_tramos_largos_el_margen_crece():
    # en 30 dias, empezar seis horas tarde no es que falte nada
    primero = AHORA - timedelta(days=30) + timedelta(hours=6)

    assert falta_principio(primero, AHORA, 720) is False
    assert falta_principio(AHORA - timedelta(days=20), AHORA, 720) is True


def test_leer_un_tramo_suelto():
    from crypto_tracker.periodo import leer

    assert leer("7d") == 168
    with pytest.raises(PeriodoError):
        leer("mucho")
