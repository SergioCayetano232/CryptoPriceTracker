"""Tests de /sube."""

from datetime import datetime, timedelta, timezone

import pytest

from crypto_tracker.alerts import formatear_sube
from crypto_tracker.periodo import PeriodoError
from crypto_tracker.sube import Subida, calcular, interpretar

INICIO = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)


def _serie(*precios):
    return [(INICIO + timedelta(days=i), p) for i, p in enumerate(precios)]


def _dia(n):
    return INICIO + timedelta(days=n)


@pytest.mark.parametrize(
    "argumento,esperado",
    [
        ("bitcoin 7d", ("bitcoin", 168)),
        ("btc", ("bitcoin", 720)),
        ("", ("", 720)),
    ],
)
def test_interpretar(argumento, esperado):
    assert interpretar(argumento) == esperado


def test_interpretar_formato_malo():
    with pytest.raises(PeriodoError, match="/sube bitcoin 30d"):
        interpretar("bitcoin ethereum")


def test_calcular():
    # Sube de 80 a 120 (+50%), cae a 60 y sube a 84 (+40%).
    s = calcular(_serie(100.0, 80.0, 120.0, 60.0, 84.0))

    assert s.minimo == 60.0
    assert s.cuando_minimo == _dia(3)
    assert s.desde_minimo == pytest.approx(40)
    assert s.para_volver == pytest.approx(-28.571, 0.001)
    assert (s.valle, s.pico) == (80.0, 120.0)
    assert (s.cuando_valle, s.cuando_pico) == (_dia(1), _dia(2))
    assert s.mejor == pytest.approx(50)


def test_calcular_siempre_bajando():
    s = calcular(_serie(100.0, 90.0, 80.0))

    assert s.desde_minimo == 0
    assert s.para_volver == 0
    assert s.mejor == 0


def test_calcular_sin_precios():
    assert calcular([]) is None
    assert calcular(_serie(100.0)) is None


def test_formatear():
    s = Subida(60.0, _dia(3), 84.0, 80.0, _dia(1), 120.0, _dia(2))

    texto = formatear_sube("bitcoin", s, 720, "eur")

    assert texto.startswith("🚀 <b>Bitcoin</b>, últimos 30 días\n\n")
    assert "Ahora <b>€84,00</b>, <b>+40.00%</b> desde el mínimo" in texto
    assert "Para volver al mínimo tendría que bajar un <b>-28.57%</b>" in texto
    assert "Mejor subida <b>+50.00%</b>: de €80,00 el 02/10 a €120,00 el 03/10" in texto
    assert "Solo tengo" not in texto


def test_formatear_hace_cuanto_fue_el_minimo():
    s = Subida(60.0, _dia(3), 84.0, 80.0, _dia(1), 120.0, _dia(2))

    texto = formatear_sube("bitcoin", s, 720, "eur", ahora=_dia(13))

    assert "Mínimo €60,00 el 04/10, hace 10 días" in texto


def test_formatear_con_el_minimo_de_hoy_no_dice_hace():
    s = Subida(60.0, _dia(3), 84.0, 80.0, _dia(1), 120.0, _dia(2))

    texto = formatear_sube("bitcoin", s, 720, "eur", ahora=_dia(3))

    assert "Mínimo €60,00 el 04/10</i>" in texto


def test_formatear_en_el_minimo_y_sin_subidas():
    s = Subida(80.0, _dia(2), 80.0, 100.0, _dia(0), 100.0, _dia(0))

    texto = formatear_sube("solana", s, 168, "eur", desde=_dia(0))

    assert "está en su mínimo del tramo" in texto
    assert "Para volver" not in texto
    assert "No ha tenido ninguna subida en este tramo" in texto
    assert "Solo tengo precios desde el 01/10" in texto
