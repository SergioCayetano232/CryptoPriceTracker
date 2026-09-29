"""Tests del cliente de CoinGecko, sin red."""

import pytest
import requests

from crypto_tracker import coingecko


@pytest.fixture(autouse=True)
def sin_esperas(monkeypatch):
    """Los reintentos esperan segundos de verdad y aqui no hace falta."""
    monkeypatch.setattr(coingecko.time, "sleep", lambda s: None)


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


def test_reintenta_y_acaba_bien(monkeypatch):
    intentos = []

    def a_la_tercera(*a, **k):
        intentos.append(1)
        if len(intentos) < 3:
            raise requests.ConnectionError()
        return RespuestaFalsa({"bitcoin": {"eur": 63000.0}})

    monkeypatch.setattr(requests, "get", a_la_tercera)

    assert coingecko.get_prices(["bitcoin"], "eur") == {"bitcoin": 63000.0}
    assert len(intentos) == 3


def test_reintenta_el_429(monkeypatch):
    intentos = []

    def limitado(*a, **k):
        intentos.append(1)
        return RespuestaFalsa({}, 429)

    monkeypatch.setattr(requests, "get", limitado)

    with pytest.raises(coingecko.CoinGeckoError, match="429"):
        coingecko.get_prices(["bitcoin"], "eur")

    assert len(intentos) == coingecko.INTENTOS


def test_el_404_no_se_reintenta(monkeypatch):
    intentos = []

    def no_encontrado(*a, **k):
        intentos.append(1)
        return RespuestaFalsa({}, 404)

    monkeypatch.setattr(requests, "get", no_encontrado)

    with pytest.raises(coingecko.CoinGeckoError):
        coingecko.get_prices(["bitcoin"], "eur")

    assert len(intentos) == 1


def test_la_espera_se_dobla(monkeypatch):
    esperas = []

    monkeypatch.setattr(requests, "get", lambda *a, **k: RespuestaFalsa({}, 503))
    monkeypatch.setattr(coingecko.time, "sleep", esperas.append)  # pisa el fixture

    with pytest.raises(coingecko.CoinGeckoError):
        coingecko.get_prices(["bitcoin"], "eur")

    assert esperas == [2, 4]


# --- buscar ---

# Recortado de lo que devuelve /search?query=btc
BUSQUEDA_BTC = {
    "coins": [
        {
            "id": "wrapped-bitcoin",
            "name": "Wrapped Bitcoin",
            "symbol": "WBTC",
            "market_cap_rank": 16,
        },
        {
            "id": "bitcoin-avalanche-bridged-btc-b",
            "name": "Bitcoin Avalanche",
            "symbol": "BTC.B",
            "market_cap_rank": None,
        },
        {"id": "bitcoin", "name": "Bitcoin", "symbol": "BTC", "market_cap_rank": 1},
        {"id": "copia-btc", "name": "Copia", "symbol": "BTC", "market_cap_rank": None},
    ]
}


def test_buscar_pone_primero_la_buena(monkeypatch):
    pedido = {}

    def get(url, params=None, headers=None, timeout=None):
        pedido.update(params)
        return RespuestaFalsa(BUSQUEDA_BTC)

    monkeypatch.setattr(requests, "get", get)

    resultados = coingecko.buscar("  btc ")

    assert pedido["query"] == "btc"
    assert [m["id"] for m in resultados][:3] == [
        "bitcoin",  # simbolo exacto y la mas grande
        "copia-btc",  # simbolo exacto pero sin rango
        "wrapped-bitcoin",  # no es exacta, pero es grande
    ]


def test_buscar_por_nombre():
    resultados = coingecko.mejores(BUSQUEDA_BTC["coins"], "Bitcoin")

    assert resultados[0]["id"] == "bitcoin"


def test_buscar_limita_los_resultados():
    assert len(coingecko.mejores(BUSQUEDA_BTC["coins"], "btc", maximo=2)) == 2


def test_buscar_vacio_no_llama(monkeypatch):
    def no_llamar(*a, **k):
        raise AssertionError("no deberia llamar a la API")

    monkeypatch.setattr(requests, "get", no_llamar)

    assert coingecko.buscar("  ") == []


def test_buscar_sin_resultados(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: RespuestaFalsa({"coins": []}))

    assert coingecko.buscar("zzzz") == []


def test_buscar_ignora_basura():
    raras = [{"name": "sin id"}, "texto", {"id": "bitcoin", "symbol": "btc"}]

    assert [m["id"] for m in coingecko.mejores(raras, "btc")] == ["bitcoin"]


def test_buscar_reintenta_como_los_precios(monkeypatch):
    intentos = []

    def a_la_segunda(*a, **k):
        intentos.append(1)
        if len(intentos) < 2:
            raise requests.ConnectionError()
        return RespuestaFalsa(BUSQUEDA_BTC)

    monkeypatch.setattr(requests, "get", a_la_segunda)

    assert coingecko.buscar("btc")[0]["id"] == "bitcoin"
    assert len(intentos) == 2


# --- clave de la API ---


def test_sin_clave_no_manda_cabecera(monkeypatch):
    monkeypatch.delenv("COINGECKO_API_KEY", raising=False)
    cabeceras = {}

    def get(url, params=None, headers=None, timeout=None):
        cabeceras.update(headers or {})
        return RespuestaFalsa({"bitcoin": {"eur": 1.0}})

    monkeypatch.setattr(requests, "get", get)
    coingecko.get_prices(["bitcoin"], "eur")

    assert cabeceras == {}


def test_con_clave_la_manda(monkeypatch):
    monkeypatch.setenv("COINGECKO_API_KEY", "  CG-abc123  ")
    cabeceras = {}

    def get(url, params=None, headers=None, timeout=None):
        cabeceras.update(headers or {})
        return RespuestaFalsa({"coins": []})

    monkeypatch.setattr(requests, "get", get)
    coingecko.buscar("btc")  # tambien la busqueda

    assert cabeceras == {"x-cg-demo-api-key": "CG-abc123"}


def test_el_403_dice_como_arreglarlo(monkeypatch):
    intentos = []

    def bloqueado(*a, **k):
        intentos.append(1)
        return RespuestaFalsa({}, 403)

    monkeypatch.setattr(requests, "get", bloqueado)

    with pytest.raises(coingecko.CoinGeckoError, match="COINGECKO_API_KEY"):
        coingecko.get_prices(["bitcoin"], "eur")

    assert len(intentos) == 1  # reintentar no lo arregla
