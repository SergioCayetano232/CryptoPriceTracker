"""Tests de leer el precio con las variaciones de 1 h, 24 h y 7 dias."""

from datetime import datetime, timezone

import pytest

from crypto_tracker.alerts import formatear_precio
from crypto_tracker.cartera import Valor
from crypto_tracker.maximo import Maximo
from crypto_tracker.precio import Precio, en_sats, leer


def _moneda(coin_id="bitcoin", **cambios):
    datos = {
        "id": coin_id,
        "current_price": 63000,
        "price_change_percentage_24h_in_currency": 2.5,
        "price_change_percentage_7d_in_currency": -4.25,
        "price_change_percentage_1h_in_currency": 0.3,
    }
    return {**datos, **cambios}


def test_leer():
    esperado = {"bitcoin": Precio("bitcoin", 63000.0, 2.5, -4.25, 0.3)}

    assert leer([_moneda()]) == esperado


def test_leer_con_volumen():
    p = leer([_moneda(total_volume=32_500_000_000)])["bitcoin"]

    assert p.volumen == 32_500_000_000


def test_leer_volumen_raro_o_cero_es_sin_volumen():
    datos = [_moneda("a", total_volume=None), _moneda("b", total_volume=0)]

    assert [p.volumen for p in leer(datos).values()] == [None, None]


def test_leer_con_el_puesto():
    assert leer([_moneda(market_cap_rank=5)])["bitcoin"].puesto == 5


def test_leer_puesto_raro_es_sin_puesto():
    datos = [
        _moneda("a", market_cap_rank=None),
        _moneda("b", market_cap_rank=0),
        _moneda("c", market_cap_rank="5"),
    ]

    assert [p.puesto for p in leer(datos).values()] == [None, None, None]


def test_leer_con_minimo_y_maximo_de_24h():
    p = leer([_moneda(low_24h=61800, high_24h=64250.5)])["bitcoin"]

    assert (p.minimo_24h, p.maximo_24h) == (61800.0, 64250.5)


def test_leer_rango_24h_con_el_precio_fuera_lo_estira():
    datos = [
        _moneda("a", current_price=61000, low_24h=61800, high_24h=64250),
        _moneda("b", current_price=65000, low_24h=61800, high_24h=64250),
    ]

    assert [(p.minimo_24h, p.maximo_24h) for p in leer(datos).values()] == [
        (61000.0, 64250.0),
        (61800.0, 65000.0),
    ]


def test_leer_rango_24h_cojo_o_al_reves_es_sin_rango():
    datos = [
        _moneda("a", low_24h=61800, high_24h=None),
        _moneda("b", low_24h=0, high_24h=64000),
        _moneda("c", low_24h=65000, high_24h=64000),
    ]

    assert [(p.minimo_24h, p.maximo_24h) for p in leer(datos).values()] == [
        (None, None)
    ] * 3


def test_leer_lo_emitido():
    p = leer([_moneda(circulating_supply=19_950_000, max_supply=21_000_000)])

    assert p["bitcoin"].emitido == pytest.approx(95.0)
    assert p["bitcoin"].tope == 21_000_000


def test_leer_sin_tope_o_pasado_de_el_es_sin_emitido():
    datos = [
        _moneda("a", circulating_supply=120_000_000, max_supply=None),
        _moneda("b", circulating_supply=None, max_supply=21_000_000),
        _moneda("c", circulating_supply=22_000_000, max_supply=21_000_000),
    ]

    assert [(p.emitido, p.tope) for p in leer(datos).values()] == [(None, None)] * 3


def test_leer_con_el_maximo_historico():
    p = leer([_moneda(ath=98000, ath_date="2024-12-17T15:02:41.429Z")])["bitcoin"]

    assert p.maximo.maximo == 98000
    assert p.maximo.fecha.date().isoformat() == "2024-12-17"


def test_leer_maximo_raro_es_sin_maximo():
    assert leer([_moneda(ath=98000, ath_date=None)])["bitcoin"].maximo is None


def test_leer_con_30_dias():
    p = leer([_moneda(price_change_percentage_30d_in_currency=-12.3)])["bitcoin"]

    assert p.en_30d == -12.3


def test_leer_sin_variaciones():
    datos = [
        _moneda(
            price_change_percentage_24h_in_currency=None,
            price_change_percentage_7d_in_currency="x",
            price_change_percentage_1h_in_currency=None,
        )
    ]

    assert leer(datos)["bitcoin"] == Precio("bitcoin", 63000.0, None, None)


def test_leer_sin_precio_no_vale():
    datos = [_moneda("a", current_price=None), _moneda("b", current_price=0)]

    assert leer(datos) == {}


def test_leer_ignora_basura():
    assert list(leer([None, {"current_price": 1}, _moneda()])) == ["bitcoin"]
    assert leer({"status": {"error_code": 429}}) == {}


def test_formatear_con_lo_que_tienes():
    tuyo = Valor("bitcoin", 1120.0, 1000.0, 0.016)

    texto = formatear_precio("bitcoin", 70000.0, 2.5, "eur", tuyo=tuyo)

    assert "💼 Tienes 0,016, que valen <b>€1.120,00</b>  🔺 +12.00% (+€120,00)" in texto


def test_formatear_con_lo_que_tienes_sin_invertido():
    tuyo = Valor("bitcoin", 1120.0, None, 0.016)

    texto = formatear_precio("bitcoin", 70000.0, 2.5, "eur", tuyo=tuyo)

    assert texto.endswith("que valen <b>€1.120,00</b>")


def test_formatear_sin_volumen_no_sale():
    assert "Volumen" not in formatear_precio("bitcoin", 70000.0, 2.5, "eur")


def test_formatear_volumen_en_otra_moneda():
    texto = formatear_precio("bitcoin", 70000.0, 2.5, "usd", volumen=850_000)

    assert "<i>Volumen en 24 h: $850.000</i>" in texto


def test_formatear_con_puesto_y_volumen():
    texto = formatear_precio(
        "solana", 150.0, 2.5, "eur", volumen=4_200_000_000, puesto=6
    )

    assert "\n<i>Puesto #6 · volumen en 24 h: €4.200 millones</i>" in texto


def test_formatear_con_puesto_sin_volumen():
    texto = formatear_precio("solana", 150.0, 2.5, "eur", puesto=6)

    assert "\n<i>Puesto #6</i>" in texto


def test_formatear_con_minimo_y_maximo_de_24h():
    texto = formatear_precio(
        "bitcoin", 63000.0, 2.5, "eur", -4.25, rango_24h=(61800.0, 64250.5)
    )

    assert "en 7 días\n<i>Mínimo €61.800,00 · máximo €64.250,50 en 24 h</i>" in texto


def test_formatear_sin_rango_24h_no_sale():
    assert "Mínimo" not in formatear_precio("bitcoin", 63000.0, 2.5, "eur")


def test_formatear_lo_emitido():
    texto = formatear_precio(
        "bitcoin", 63000.0, 2.5, "eur", puesto=1, emitido=(95.04, 21_000_000)
    )

    assert "<i>Puesto #1</i>\n<i>Emitido el 95.0% de 21 millones</i>" in texto


def test_formatear_sin_emitido_no_sale():
    assert "Emitido" not in formatear_precio("ethereum", 2000.0, 2.5, "eur")


def test_formatear_con_30_dias():
    texto = formatear_precio("bitcoin", 63000.0, 2.5, "eur", -4.25, en_30d=-12.3)

    assert "🔻 -4.25% en 7 días\n🔻 -12.30% en 30 días" in texto


def test_formatear_sin_30_dias_no_sale():
    assert "30 días" not in formatear_precio("bitcoin", 63000.0, 2.5, "eur", -4.25)


AHORA = datetime(2025, 10, 18, tzinfo=timezone.utc)


def test_formatear_con_el_maximo_historico():
    m = Maximo("bitcoin", 63000.0, 98000.0, datetime(2024, 12, 17, tzinfo=timezone.utc))

    texto = formatear_precio("bitcoin", 63000.0, 2.5, "eur", maximo=m, ahora=AHORA)

    assert texto.endswith(
        "\n<i>Máximo histórico €98.000,00 hace 10 meses · le falta +55.56%</i>"
    )


def test_formatear_en_maximos():
    m = Maximo("bitcoin", 99000.0, 98000.0, AHORA)

    texto = formatear_precio("bitcoin", 99000.0, 2.5, "eur", maximo=m, ahora=AHORA)

    assert texto.endswith("\n🎉 <i>Está en su máximo histórico</i>")


def test_en_sats():
    assert en_sats("solana", 92.13, 72463.0) == pytest.approx(127140.7, abs=0.1)
    assert en_sats("pepe", 0.00000346, 72463.0) == pytest.approx(0.004775, rel=1e-3)


def test_en_sats_ni_bitcoin_ni_sin_su_precio():
    assert en_sats("bitcoin", 72463.0, 72463.0) is None
    assert en_sats("solana", 92.13, None) is None


def test_formatear_en_sats():
    texto = formatear_precio("solana", 92.13, 2.5, "eur", sats=127140.7)

    assert texto.startswith("💰 <b>Solana</b>  €92,13  <i>(127.141 sats)</i>\n")


def test_formatear_menos_de_un_sat_no_es_cero():
    texto = formatear_precio("pepe", 0.00000346, 2.5, "eur", sats=0.004775)

    assert "<i>(0,004775 sats)</i>" in texto
