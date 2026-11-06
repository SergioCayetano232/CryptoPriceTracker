"""Tests de /calendario."""

from datetime import date

import pytest

from crypto_tracker.alerts import formatear_calendario
from crypto_tracker.calendario import CalendarioError, calcular, interpretar, semanas

HOY = date(2026, 11, 6)


def test_interpretar():
    assert interpretar("btc", HOY) == ("bitcoin", 2026, 11)
    assert interpretar("btc octubre", HOY) == ("bitcoin", 2026, 10)
    assert interpretar("", HOY) == ("", 2026, 11)
    assert interpretar("Octubre", HOY) == ("", 2026, 10)


def test_un_mes_que_no_ha_llegado_es_del_año_pasado():
    assert interpretar("eth diciembre", HOY) == ("ethereum", 2025, 12)


def test_interpretar_mal():
    with pytest.raises(CalendarioError, match="Escríbelo así"):
        interpretar("btc eth octubre", HOY)


# 31/10 a 100; luego 110, 99, (sin el 3), 99, 105
DIAS = [
    (date(2026, 10, 31), 100.0),
    (date(2026, 11, 1), 110.0),
    (date(2026, 11, 2), 99.0),
    (date(2026, 11, 4), 99.0),
    (date(2026, 11, 5), 105.0),
]


def test_calcular():
    m = calcular(DIAS, 2026, 11, date(2026, 11, 5))

    assert len(m.casillas) == 30
    uno, dos, tres, cuatro, cinco = m.casillas[:5]
    assert uno.cambio == pytest.approx(10)
    assert dos.cambio == pytest.approx(-10)
    assert tres.cambio is None
    # sin el 3 no sé cómo fue el 4
    assert cuatro.cambio is None
    assert cinco.cambio == pytest.approx(6.0606, abs=0.001)
    assert m.casillas[5].futuro
    assert not cinco.futuro
    assert (m.verdes, m.rojos) == (2, 1)
    assert m.mejor.dia == date(2026, 11, 1)
    assert m.peor.dia == date(2026, 11, 2)
    assert m.cambio == pytest.approx(5)


def test_un_dia_igual_no_es_ni_verde_ni_rojo():
    m = calcular(
        [(date(2026, 10, 31), 100.0), (date(2026, 11, 1), 100.0)], 2026, 11, HOY
    )

    assert m.casillas[0].cambio == 0
    assert (m.verdes, m.rojos) == (0, 0)


def test_lo_que_casi_no_se_mueve_cuenta_como_igual():
    m = calcular(
        [(date(2026, 10, 31), 100.0), (date(2026, 11, 1), 99.96)], 2026, 11, HOY
    )

    assert m.casillas[0].cambio == 0
    assert m.rojos == 0


def test_sin_el_mes_anterior_cuenta_desde_el_primero():
    m = calcular(DIAS[1:], 2026, 11, HOY)

    assert m.casillas[0].cambio is None
    assert m.cambio == pytest.approx(105 / 110 * 100 - 100)


def test_mes_pasado_no_mira_lo_de_despues():
    dias = [
        (date(2026, 9, 30), 100.0),
        (date(2026, 10, 31), 120.0),
        (date(2026, 11, 1), 500.0),
    ]
    m = calcular(dias, 2026, 10, HOY)

    assert not any(c.futuro for c in m.casillas)
    assert m.cambio == pytest.approx(20)


def test_sin_nada():
    m = calcular([], 2026, 11, HOY)

    assert m.con_dato == []
    assert m.mejor is None and m.cambio is None


def test_semanas_empiezan_en_lunes():
    # noviembre de 2026 empieza en domingo
    filas = semanas(calcular([], 2026, 11, HOY))

    assert filas[0][:6] == [None] * 6
    assert filas[0][6].dia == date(2026, 11, 1)
    assert all(len(f) == 7 for f in filas)
    assert filas[-1][0].dia == date(2026, 11, 30)


def test_formatear():
    m = calcular(DIAS, 2026, 11, date(2026, 11, 5))
    texto = formatear_calendario("bitcoin", m)

    assert "🗓 <b>Bitcoin en noviembre de 2026</b>" in texto
    assert "🟩 2 días en verde · 🟥 1 en rojo" in texto
    assert "Mejor, el 1: 🔺 +10,0%" in texto
    assert "Peor, el 2: 🔻 -10,0%" in texto
    assert "En el mes: 🔺 +5,0%" in texto
    assert "2 días sin precio" in texto


def test_formatear_sin_datos_del_mes():
    texto = formatear_calendario("bitcoin", calcular([], 2026, 11, HOY))

    assert "No tengo dos días seguidos con precio" in texto
