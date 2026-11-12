"""Tests de /diames."""

from datetime import date, timedelta

import pytest

from crypto_tracker.alerts import formatear_diames
from crypto_tracker.diames import POR_DEFECTO, VENTANA, calcular, interpretar
from crypto_tracker.periodo import PeriodoError

INICIO = date(2026, 1, 1)


def _dias(n, precio_de, desde=INICIO):
    """n días seguidos, con el precio que diga precio_de(fecha, i)."""
    return [
        (desde + timedelta(days=i), precio_de(desde + timedelta(days=i), i))
        for i in range(n)
    ]


def _barato_el_15(fecha, i):
    return 90.0 if fecha.day == 15 else 100.0


def test_interpretar():
    assert interpretar("btc 180d") == ("bitcoin", 180 * 24)
    assert interpretar("") == ("", POR_DEFECTO)


def test_interpretar_mal():
    with pytest.raises(PeriodoError):
        interpretar("btc eth 30d")


def test_el_dia_mas_barato():
    r = calcular(_dias(120, _barato_el_15))

    assert r.barato.dia == 15
    assert r.barato.veces == 3  # febrero, marzo y abril; enero cae antes de la ventana
    assert r.barato.media < -9
    assert r.desde == INICIO + timedelta(days=VENTANA)


def test_una_subida_de_fondo_no_hace_barato_el_dia_1():
    # Sube un 0,5% cada día: contra la media de su mes, el 1 saldría el más barato.
    r = calcular(_dias(200, lambda f, i: 100 * 1.005**i))

    assert max(abs(d.media) for d in r.dias) < 0.1


def test_tercios():
    r = calcular(_dias(120, lambda f, i: 90.0 if f.day <= 10 else 105.0))
    medias = dict(r.tercios())

    assert list(medias) == ["Del 1 al 10", "Del 11 al 20", "Del 21 al final"]
    assert medias["Del 1 al 10"] < 0 < medias["Del 11 al 20"]


def test_con_huecos_no_cuenta_esos_dias():
    seguidos = _dias(40, _barato_el_15)
    # Diez días sin precio en medio: ninguna ventana queda entera.
    con_hueco = seguidos[:20] + seguidos[30:]
    assert calcular(con_hueco) is None


def test_sin_un_mes_seguido():
    assert calcular(_dias(2 * VENTANA, _barato_el_15)) is None
    assert calcular([]) is None


def test_formatear():
    r = calcular(_dias(120, _barato_el_15))
    texto = formatear_diames("bitcoin", r, hoy=date(2026, 11, 15))

    assert "📆 <b>Bitcoin</b> por días del mes, con 3 meses" in texto
    assert "🟢 Más barata, el día <b>15</b> (-9," in texto
    assert "🔴 Más cara, el día" in texto
    assert "Del 11 al 20: <b>-" in texto
    assert "← el mejor para comprar" in texto
    assert "Hoy es día 15: suele ser su día más barato" in texto
    assert "Con menos de 6 meses es casi azar" in texto
