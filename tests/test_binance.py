"""Tests de los precios de respaldo de Binance, sin llamar a la API."""

import pytest
import requests

from crypto_tracker import binance

DATOS = [
    {"symbol": "BTCUSDT", "price": "110000.00"},
    {"symbol": "ETHUSDT", "price": "4400.00"},
    {"symbol": "EURUSDT", "price": "1.10"},
    {"symbol": "ETHBTC", "price": "0.04"},
]


class RespuestaFalsa:
    def __init__(self, status=200, data=None):
        self.status_code = status
        self._data = DATOS if data is None else data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        if isinstance(self._data, Exception):
            raise self._data
        return self._data


def test_en_euros_divide_por_lo_que_vale_el_euro():
    p = binance.leer(DATOS, ["bitcoin", "ethereum"], "eur")

    assert p["bitcoin"] == pytest.approx(100000)
    assert p["ethereum"] == pytest.approx(4000)


def test_en_dolares_tal_cual():
    assert binance.leer(DATOS, ["bitcoin"], "usd") == {"bitcoin": 110000.0}


def test_otra_moneda_no_se_inventa():
    assert binance.leer(DATOS, ["bitcoin"], "gbp") == {}


def test_sin_el_euro_no_hay_precios_en_euros():
    sin_euro = [d for d in DATOS if d["symbol"] != "EURUSDT"]

    assert binance.leer(sin_euro, ["bitcoin"], "eur") == {}


def test_la_que_no_tiene_binance_no_sale():
    p = binance.leer(DATOS, ["bitcoin", "solana", "una-rara"], "usd")

    assert p == {"bitcoin": 110000.0}


def test_las_estables_no_se_piden():
    assert binance.pares(["tether", "usd-coin", "bitcoin"]) == {"bitcoin": "BTCUSDT"}


def test_ignora_basura():
    datos = [
        {"symbol": "BTCUSDT", "price": "nan"},
        {"symbol": "ETHUSDT", "price": None},
        "esto no",
        {"symbol": "SOLUSDT", "price": "-3"},
    ]

    assert binance.leer(datos, ["bitcoin", "ethereum", "solana"], "usd") == {}
    assert binance.leer({"code": -1}, ["bitcoin"], "usd") == {}


def test_precios_pide_una_vez_y_convierte(monkeypatch):
    llamadas = []

    def get(url, timeout=None):
        llamadas.append(url)
        return RespuestaFalsa()

    monkeypatch.setattr(requests, "get", get)

    assert binance.precios(["bitcoin"], "eur") == {"bitcoin": pytest.approx(100000)}
    assert llamadas == [binance.URL]


def test_sin_nada_que_pedir_no_llama(monkeypatch):
    def no_llamar(*a, **k):
        raise AssertionError("no debería llamar a Binance")

    monkeypatch.setattr(requests, "get", no_llamar)

    assert binance.precios(["una-rara", "tether"], "eur") == {}
    assert binance.precios(["bitcoin"], "gbp") == {}


def test_sin_conexion(monkeypatch):
    def falla(*a, **k):
        raise requests.ConnectionError()

    monkeypatch.setattr(requests, "get", falla)

    with pytest.raises(binance.BinanceError):
        binance.precios(["bitcoin"], "eur")


def test_bloqueado_en_el_pais(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: RespuestaFalsa(451))

    with pytest.raises(binance.BinanceError):
        binance.precios(["bitcoin"], "eur")


def test_no_es_json(monkeypatch):
    malo = RespuestaFalsa(data=ValueError("no json"))
    monkeypatch.setattr(requests, "get", lambda *a, **k: malo)

    with pytest.raises(binance.BinanceError):
        binance.precios(["bitcoin"], "eur")
