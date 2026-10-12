"""Tests de leer el precio con las variaciones de 1 h, 24 h y 7 dias."""

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
