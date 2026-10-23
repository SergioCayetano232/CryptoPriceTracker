"""Tests de /diasemana."""

from datetime import date, timedelta

import pytest

from crypto_tracker.alerts import formatear_diasemana
from crypto_tracker.diasemana import Dia, DiasSemana, calcular, interpretar
from crypto_tracker.periodo import PeriodoError

LUNES = date(2026, 10, 5)


def _dias(*precios, desde=LUNES):
    return [(desde + timedelta(days=i), p) for i, p in enumerate(precios)]


def test_media_por_dia_de_la_semana():
    # Dos semanas: los martes suben un 10% y los miércoles bajan un 10%.
    precios = [100, 110, 99, 99, 99, 99, 99, 99, 108.9, 98.01]
    s = calcular(_dias(*precios))

    nombres = [d.nombre for d in s.dias]
    assert nombres == [
        "Lunes",
        "Martes",
        "Miércoles",
        "Jueves",
        "Viernes",
        "Sábado",
        "Domingo",
    ]
    martes = s.dias[1]
    assert martes.media == pytest.approx(10)
    assert martes.veces == 2
    assert s.dias[0].veces == 1  # el primer lunes no tiene día anterior
    assert s.mejor.nombre == "Martes"
    assert s.peor.nombre == "Miércoles"
    assert s.desde == LUNES


def test_salta_los_huecos():
    dias = [(LUNES - timedelta(days=10), 50.0), *_dias(100, 105)]

    s = calcular(dias)

    assert [(d.nombre, d.veces) for d in s.dias] == [("Martes", 1)]
    assert s.desde == LUNES


def test_sin_dos_dias_seguidos():
    assert calcular([]) is None
    assert calcular(_dias(100)) is None
    assert calcular([(LUNES, 100.0), (LUNES + timedelta(days=2), 110.0)]) is None


def test_interpretar():
    assert interpretar("btc 30d") == ("bitcoin", 30 * 24)
    assert interpretar("solana") == ("solana", 90 * 24)
    assert interpretar("14d") == ("", 14 * 24)
    assert interpretar("") == ("", 90 * 24)
    with pytest.raises(PeriodoError):
        interpretar("btc eth 7d")


def test_formatear():
    s = DiasSemana([Dia("Lunes", 0.82, 12), Dia("Domingo", -1.5, 13)], LUNES)

    texto = formatear_diasemana("bitcoin", s, 90 * 24)

    assert texto.startswith("📅 <b>Bitcoin</b> por días de la semana, últimos 90 días")
    assert "🔺 Lunes: <b>+0.82%</b> · 12\n" in texto
    assert "🔻 Domingo: <b>-1.50%</b> · 13\n" in texto
    assert "Mejor: <b>lunes</b> · Peor: <b>domingo</b>" in texto
    assert "Solo tengo" not in texto


def test_formatear_un_solo_dia_e_incompleto():
    s = DiasSemana([Dia("Martes", 5.0, 1)], LUNES)

    texto = formatear_diasemana("solana", s, 90 * 24, incompleto=True)

    assert "Mejor:" not in texto
    assert "Solo tengo precios desde el 05/10." in texto


def test_de_una_fecha():
    s = DiasSemana([Dia("Lunes", 0.82, 12), Dia("Domingo", -1.5, 13)], LUNES)

    assert s.de(LUNES).media == 0.82
    assert s.de(LUNES + timedelta(days=6)).nombre == "Domingo"
    assert s.de(LUNES + timedelta(days=1)) is None


def test_formatear_dice_como_suele_ir_hoy():
    s = DiasSemana(
        [Dia("Lunes", 0.82, 12), Dia("Martes", 0.1, 12), Dia("Domingo", -1.5, 13)],
        LUNES,
    )

    lunes = formatear_diasemana("btc", s, 90 * 24, hoy=LUNES)
    martes = formatear_diasemana("btc", s, 90 * 24, hoy=LUNES + timedelta(days=1))
    domingo = formatear_diasemana("btc", s, 90 * 24, hoy=LUNES + timedelta(days=6))
    jueves = formatear_diasemana("btc", s, 90 * 24, hoy=LUNES + timedelta(days=3))

    assert "Hoy es lunes: suele ir +0.82%, su mejor día\n" in lunes
    assert "Hoy es martes: suele ir +0.10%\n" in martes
    assert "Hoy es domingo: suele ir -1.50%, su peor día\n" in domingo
    assert "Hoy es" not in jueves
