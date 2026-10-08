"""Tests de /tendencias."""

from crypto_tracker.tendencias import MAXIMO, Tendencia, leer


def _moneda(coin_id="pepe", **cambios):
    item = {
        "id": coin_id,
        "name": "Pepe",
        "symbol": "pepe",
        "market_cap_rank": 30,
        "data": {"price_change_percentage_24h": {"eur": 12.5, "usd": 13.1}},
    }
    return {"item": {**item, **cambios}}


def test_leer():
    datos = {"coins": [_moneda()]}

    assert leer(datos, "eur") == [Tendencia("pepe", "Pepe", "PEPE", 30, 12.5)]
    assert leer(datos, "USD")[0].variacion == 13.1


def test_leer_lo_que_falta():
    datos = {
        "coins": [_moneda(name=None, symbol=None, market_cap_rank=None, data=None)]
    }

    assert leer(datos, "eur") == [Tendencia("pepe", "pepe", "", None, None)]


def test_leer_variacion_rara():
    datos = {"coins": [_moneda(data={"price_change_percentage_24h": {"eur": "x"}})]}

    assert leer(datos, "eur")[0].variacion is None
    assert leer({"coins": [_moneda()]}, "gbp")[0].variacion is None


def test_leer_ignora_basura():
    datos = {"coins": [None, {"item": None}, {"item": {"name": "Sin id"}}, _moneda()]}

    assert [t.coin_id for t in leer(datos, "eur")] == ["pepe"]


def test_leer_algo_que_no_es_lo_esperado():
    assert leer([], "eur") == []
    assert leer({"error": "no"}, "eur") == []


def test_leer_corta_y_respeta_el_orden():
    datos = {"coins": [_moneda(f"moneda-{i}") for i in range(15)]}

    ids = [t.coin_id for t in leer(datos, "eur")]

    assert ids == [f"moneda-{i}" for i in range(MAXIMO)]
