"""Tests de /caida."""

from datetime import datetime, timedelta, timezone

import pytest

from crypto_tracker.alerts import formatear_caida
from crypto_tracker.caida import Caida, calcular, interpretar
from crypto_tracker.periodo import PeriodoError

INICIO = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)


def _serie(*precios):
    return [(INICIO + timedelta(days=i), p) for i, p in enumerate(precios)]


def _dia(n):
    return INICIO + timedelta(days=n)


@pytest.mark.parametrize(
    "argumento,esperado",
    [
        ("bitcoin 7d", ("bitcoin", 168)),
        ("btc", ("bitcoin", 720)),  # sin tramo, 30 dias
        ("12h", ("", 12)),
        ("", ("", 720)),
    ],
)
def test_interpretar(argumento, esperado):
    assert interpretar(argumento) == esperado


def test_interpretar_formato_malo():
    with pytest.raises(PeriodoError, match="/caida bitcoin 30d"):
        interpretar("bitcoin ethereum")


def test_calcular():
    c = calcular(_serie(100, 120, 90, 115, 130, 117))

    assert (c.maximo, c.cuando_maximo, c.ahora) == (130, _dia(4), 117)
    assert c.desde_maximo == pytest.approx(-10)
    # La peor fue de 120 a 90, aunque luego subiera a un máximo nuevo
    assert (c.pico, c.cuando_pico) == (120, _dia(1))
    assert (c.valle, c.cuando_valle) == (90, _dia(2))
    assert c.peor == pytest.approx(-25)


def test_calcular_la_peor_es_en_porcentaje():
    # 200 -> 150 es -25%, 100 -> 80 es -20%: gana la primera aunque baje menos
    c = calcular(_serie(100, 80, 200, 150))

    assert (c.pico, c.valle) == (200, 150)


def test_calcular_solo_sube():
    c = calcular(_serie(100, 110, 120))

    assert c.desde_maximo == 0
    assert c.para_recuperar == 0
    assert c.peor == 0


def test_para_recuperar_no_es_simetrico():
    c = calcular(_serie(100, 80))

    assert c.desde_maximo == pytest.approx(-20)
    assert c.para_recuperar == pytest.approx(25)


def test_calcular_con_empate_se_queda_el_ultimo_maximo():
    c = calcular(_serie(120, 100, 120, 110))

    assert c.cuando_maximo == _dia(2)


def test_calcular_sin_datos():
    assert calcular([]) is None
    assert calcular(_serie(100)) is None


def test_formatear():
    c = Caida(130, _dia(4), 117, 120, _dia(1), 90, _dia(2))

    texto = formatear_caida("bitcoin", c, 720, "eur")

    assert "📉 <b>Bitcoin</b>, últimos 30 días" in texto
    assert "Ahora <b>€117,00</b>, <b>-10.00%</b> desde el máximo" in texto
    assert "Máximo €130,00 el 05/10" in texto
    assert "Para volver al máximo tiene que subir un <b>+11.11%</b>" in texto
    assert "Peor caída <b>-25.00%</b>: de €120,00 el 02/10 a €90,00 el 03/10" in texto
    assert "Solo tengo" not in texto


def test_formatear_hace_cuanto_fue_el_maximo():
    c = Caida(130, _dia(4), 117, 120, _dia(1), 90, _dia(2))

    texto = formatear_caida("bitcoin", c, 720, "eur", ahora=_dia(14))

    assert "Máximo €130,00 el 05/10, hace 10 días" in texto


def test_formatear_con_el_maximo_de_hoy_no_dice_hace():
    c = Caida(130, _dia(4), 117, 120, _dia(1), 90, _dia(2))

    texto = formatear_caida("bitcoin", c, 720, "eur", ahora=_dia(4))

    assert "Máximo €130,00 el 05/10</i>" in texto


def test_formatear_en_maximos_y_sin_caidas():
    c = Caida(120, _dia(2), 120, 100, _dia(0), 100, _dia(0))

    texto = formatear_caida("bitcoin", c, 168, "eur", desde=INICIO)

    assert "está en su máximo del tramo" in texto
    assert "Para volver" not in texto
    assert "No ha tenido ninguna caída" in texto
    assert "Solo tengo precios desde el" in texto
