"""Tests del cliente de CoinGecko, sin red."""

import pytest
import requests

from crypto_tracker import coingecko


class RespuestaFalsa:
    def __init__(self, data=None, status=200):
        self.status_code = status
        self._data = data if data is not None else {}

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            error = requests.HTTPError(f"HTTP {self.status_code}")
            error.response = self
            raise error


def test_precios_correctos(monkeypatch):
    datos = {"bitcoin": {"eur": 63000.0}, "ethereum": {"eur": 3200.0}}
    monkeypatch.setattr(requests, "get", lambda *a, **k: RespuestaFalsa(datos))

    precios = coingecko.get_prices(["bitcoin", "ethereum"], "eur")

    assert precios == {"bitcoin": 63000.0, "ethereum": 3200.0}


def test_lista_vacia_no_llama(monkeypatch):
    def no_llamar(*a, **k):
        raise AssertionError("no deberia llamar a la API")

    monkeypatch.setattr(requests, "get", no_llamar)

    assert coingecko.get_prices([], "eur") == {}


def test_id_desconocido_se_omite(monkeypatch):
    # un id mal escrito no da error, la API devuelve 200 y no lo incluye
    datos = {"bitcoin": {"eur": 63000.0}}
    monkeypatch.setattr(requests, "get", lambda *a, **k: RespuestaFalsa(datos))

    precios = coingecko.get_prices(["bitcoin", "inventada"], "eur")

    assert precios == {"bitcoin": 63000.0}


def test_moneda_que_no_esta_en_la_respuesta(monkeypatch):
    datos = {"bitcoin": {"usd": 68000.0}}
    monkeypatch.setattr(requests, "get", lambda *a, **k: RespuestaFalsa(datos))

    assert coingecko.get_prices(["bitcoin"], "eur") == {}


def test_precio_no_numerico_se_ignora(monkeypatch):
    datos = {"bitcoin": {"eur": "muchos"}}
    monkeypatch.setattr(requests, "get", lambda *a, **k: RespuestaFalsa(datos))

    assert coingecko.get_prices(["bitcoin"], "eur") == {}


def test_error_429_lo_dice_claro(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: RespuestaFalsa({}, 429))

    with pytest.raises(coingecko.CoinGeckoError, match="429"):
        coingecko.get_prices(["bitcoin"], "eur")


def test_error_500(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: RespuestaFalsa({}, 500))

    with pytest.raises(coingecko.CoinGeckoError):
        coingecko.get_prices(["bitcoin"], "eur")


def test_sin_conexion(monkeypatch):
    def falla(*a, **k):
        raise requests.ConnectionError()

    monkeypatch.setattr(requests, "get", falla)

    with pytest.raises(coingecko.CoinGeckoError, match="Sin conexion"):
        coingecko.get_prices(["bitcoin"], "eur")


def test_timeout(monkeypatch):
    def falla(*a, **k):
        raise requests.Timeout()

    monkeypatch.setattr(requests, "get", falla)

    with pytest.raises(coingecko.CoinGeckoError):
        coingecko.get_prices(["bitcoin"], "eur")


def test_respuesta_que_no_es_json(monkeypatch):
    class NoJson(RespuestaFalsa):
        def json(self):
            raise ValueError("no es json")

    monkeypatch.setattr(requests, "get", lambda *a, **k: NoJson())

    with pytest.raises(coingecko.CoinGeckoError):
        coingecko.get_prices(["bitcoin"], "eur")
