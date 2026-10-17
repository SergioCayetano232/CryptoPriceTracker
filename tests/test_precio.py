"""Tests de leer el precio con las variaciones de 1 h, 24 h y 7 dias."""

from crypto_tracker.alerts import formatear_precio
from crypto_tracker.cartera import Valor
from crypto_tracker.precio import Precio, leer


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
