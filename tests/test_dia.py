"""Tests de /dia."""

from datetime import date, datetime, timedelta

import pytest

from crypto_tracker.alerts import formatear_dia
from crypto_tracker.dia import Dia, DiaError, calcular, cercano, interpretar, leer_fecha

HOY = date(2026, 10, 13)


def _a_las(dia, hora):
    # En la hora de aquí, que es como se cuentan los días
    return datetime(dia.year, dia.month, dia.day, hora).astimezone()


@pytest.mark.parametrize(
    "texto,esperado",
    [
        ("01/09", date(2026, 9, 1)),
        ("1/9", date(2026, 9, 1)),
        ("1-9", date(2026, 9, 1)),
        ("1.9.2025", date(2025, 9, 1)),
        ("01/09/25", date(2025, 9, 1)),
        ("25/12", date(2025, 12, 25)),  # aún no ha llegado: el del año pasado
        ("13/10", HOY),
        ("hoy", HOY),
        ("Ayer", date(2026, 10, 12)),
        ("anteayer", date(2026, 10, 11)),
        ("bitcoin", None),
        ("7d", None),
    ],
)
def test_leer_fecha(texto, esperado):
    assert leer_fecha(texto, HOY) == esperado


def test_leer_fecha_que_no_existe():
    with pytest.raises(DiaError, match="no existe"):
        leer_fecha("31/02", HOY)


def test_interpretar():
    assert interpretar("btc 01/09", HOY) == ("bitcoin", date(2026, 9, 1))
    assert interpretar("ayer", HOY) == ("", date(2026, 10, 12))


@pytest.mark.parametrize("argumento", ["", "bitcoin", "btc eth 01/09", "01/09 btc"])
def test_interpretar_mal(argumento):
    with pytest.raises(DiaError, match="/dia bitcoin 01/09"):
        interpretar(argumento, HOY)


def test_interpretar_en_el_futuro():
    with pytest.raises(DiaError, match="todavía no ha llegado"):
        interpretar("btc 01/01/2027", HOY)


def test_calcular():
    ayer = HOY - timedelta(days=1)
    serie = [
        (_a_las(ayer - timedelta(days=1), 23), 90),
        (_a_las(ayer, 0), 100),
        (_a_las(ayer, 9), 120),
        (_a_las(ayer, 15), 95),
        (_a_las(ayer, 23), 110),
        (_a_las(HOY, 10), 121),
    ]

    d = calcular(serie, ayer)

    assert (d.apertura, d.cierre, d.maximo, d.minimo, d.ahora) == (
        100,
        110,
        120,
        95,
        121,
    )
    assert d.en_el_dia == pytest.approx(10)
    assert d.desde == pytest.approx(10)


def test_calcular_sin_ese_dia():
    serie = [(_a_las(HOY - timedelta(days=5), 12), 100)]

    assert calcular(serie, HOY - timedelta(days=3)) is None
    assert calcular([], HOY) is None


def test_cercano():
    serie = [
        (_a_las(date(2026, 9, 1), 12), 100),
        (_a_las(date(2026, 9, 5), 12), 100),
        (_a_las(date(2026, 9, 9), 12), 100),
    ]

    assert cercano(serie, date(2026, 9, 4)) == date(2026, 9, 5)
    assert cercano(serie, date(2026, 9, 7)) == date(2026, 9, 5)  # empate: el de antes
    assert cercano(serie, date(2025, 1, 1)) == date(2026, 9, 1)
    assert cercano([], HOY) is None


def test_formatear():
    d = Dia(date(2026, 9, 1), 100, 110, 120, 95, 121)

    texto = formatear_dia("bitcoin", d, "eur", HOY)

    assert "📅 <b>Bitcoin</b> el 01/09" in texto
    assert "Cerró a <b>€110,00</b>, +10.00% en el día" in texto
    assert "Máximo €120,00 · mínimo €95,00" in texto
    assert "Desde entonces +10.00%: ahora €121,00" in texto


def test_formatear_hoy_y_de_otro_año():
    hoy = formatear_dia("bitcoin", Dia(HOY, 100, 110, 120, 95, 110), "eur", HOY)
    viejo = formatear_dia(
        "bitcoin", Dia(date(2025, 9, 1), 100, 110, 120, 95, 121), "eur", HOY
    )

    assert "<b>Bitcoin</b> hoy" in hoy
    assert "Va por <b>€110,00</b>" in hoy
    assert "Desde entonces" not in hoy
    assert "el 01/09/2025" in viejo


def test_formatear_con_un_solo_precio():
    texto = formatear_dia(
        "bitcoin", Dia(date(2026, 9, 1), 100, 100, 100, 100, 121), "eur", HOY
    )

    assert "Cerró a <b>€100,00</b>\n" in texto
    assert "en el día" not in texto
    assert "Máximo" not in texto
