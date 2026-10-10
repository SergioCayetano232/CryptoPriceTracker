"""Tests del cliente de CoinGecko, sin red."""

import pytest
import requests

from crypto_tracker import coingecko


@pytest.fixture(autouse=True)
def sin_esperas(monkeypatch):
    """Los reintentos esperan segundos de verdad y aqui no hace falta."""
    monkeypatch.setattr(coingecko.time, "sleep", lambda s: None)
    # que la variacion de un test no se cuele en el siguiente
    monkeypatch.setattr(coingecko, "_cambios", {})


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


# --- contar las consultas ---


def test_cuenta_cada_peticion(monkeypatch):
    datos = {"bitcoin": {"eur": 63000.0}}
    monkeypatch.setattr(requests, "get", lambda *a, **k: RespuestaFalsa(datos))
    coingecko.tomar_consultas()

    coingecko.get_prices(["bitcoin"], "eur")
    coingecko.buscar("btc")

    assert coingecko.tomar_consultas() == 2
    assert coingecko.tomar_consultas() == 0  # tomarlas las pone a cero


def test_los_reintentos_tambien_cuentan(monkeypatch):
    # un 429 tambien gasta del mes
    monkeypatch.setattr(requests, "get", lambda *a, **k: RespuestaFalsa(status=429))
    coingecko.tomar_consultas()

    with pytest.raises(coingecko.CoinGeckoError):
        coingecko.get_prices(["bitcoin"], "eur")

    assert coingecko.tomar_consultas() == coingecko.INTENTOS


def test_sin_conexion_no_cuenta(monkeypatch):
    def sin_red(*a, **k):
        raise requests.ConnectionError("sin red")

    monkeypatch.setattr(requests, "get", sin_red)
    coingecko.tomar_consultas()

    with pytest.raises(coingecko.CoinGeckoError):
        coingecko.get_prices(["bitcoin"], "eur")

    assert coingecko.tomar_consultas() == 0


# --- variacion en 24 h ---


def test_pide_la_variacion_de_24h(monkeypatch):
    pedido = {}

    def get(url, params=None, headers=None, timeout=None):
        pedido.update(params)
        return RespuestaFalsa({"bitcoin": {"eur": 63000.0, "eur_24h_change": -2.5}})

    monkeypatch.setattr(requests, "get", get)

    precios = coingecko.get_prices(["bitcoin"], "eur")

    assert pedido["include_24hr_change"] == "true"
    assert precios == {"bitcoin": 63000.0}  # el precio sigue igual que antes
    assert coingecko.cambio_24h("bitcoin") == -2.5


def test_sin_variacion_no_se_inventa(monkeypatch):
    datos = {"bitcoin": {"eur": 63000.0, "eur_24h_change": None}}
    monkeypatch.setattr(requests, "get", lambda *a, **k: RespuestaFalsa(datos))

    coingecko.get_prices(["bitcoin"], "eur")

    assert coingecko.cambio_24h("bitcoin") is None


def test_si_deja_de_venir_se_olvida_la_vieja(monkeypatch):
    respuestas = [
        {"bitcoin": {"eur": 63000.0, "eur_24h_change": 4.0}},
        {"bitcoin": {"eur": 64000.0}},
    ]
    monkeypatch.setattr(
        requests, "get", lambda *a, **k: RespuestaFalsa(respuestas.pop(0))
    )

    coingecko.get_prices(["bitcoin"], "eur")
    coingecko.get_prices(["bitcoin"], "eur")

    assert coingecko.cambio_24h("bitcoin") is None


def test_maximos(monkeypatch):
    pedido = {}

    def get(url, params=None, headers=None, timeout=None):
        pedido.update(url=url, params=params)
        return RespuestaFalsa(
            [
                {
                    "id": "bitcoin",
                    "current_price": 75000,
                    "ath": 100000,
                    "ath_date": "2026-03-14T10:00:00.000Z",
                }
            ]
        )

    monkeypatch.setattr(requests, "get", get)

    maximos = coingecko.maximos(["bitcoin", "bitcion"], "eur")

    assert pedido["url"].endswith("/coins/markets")
    assert pedido["params"] == {"ids": "bitcoin,bitcion", "vs_currency": "eur"}
    assert list(maximos) == ["bitcoin"]
    assert maximos["bitcoin"].maximo == 100000


def test_maximos_vacio_no_llama(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: pytest.fail())

    assert coingecko.maximos([]) == {}


def test_tendencias_hoy(monkeypatch):
    pedido = {}

    def get(url, params=None, headers=None, timeout=None):
        pedido["url"] = url
        return RespuestaFalsa({"coins": [{"item": {"id": "pepe", "symbol": "pepe"}}]})

    monkeypatch.setattr(requests, "get", get)

    lista = coingecko.tendencias_hoy("eur")

    assert pedido["url"].endswith("/search/trending")
    assert [t.coin_id for t in lista] == ["pepe"]


def test_precios_semana(monkeypatch):
    pedido = {}

    def get(url, params=None, headers=None, timeout=None):
        pedido.update(url=url, params=params)
        return RespuestaFalsa(
            [
                {
                    "id": "bitcoin",
                    "current_price": 63000,
                    "price_change_percentage_7d_in_currency": -4.25,
                }
            ]
        )

    monkeypatch.setattr(requests, "get", get)

    precios = coingecko.precios_semana(["bitcoin", "solana"], "eur")

    assert pedido["url"].endswith("/coins/markets")
    assert pedido["params"]["ids"] == "bitcoin,solana"
    assert pedido["params"]["price_change_percentage"] == "24h,7d"
    assert precios["bitcoin"].en_7d == -4.25


def test_precios_semana_vacio_no_llama(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: pytest.fail())

    assert coingecko.precios_semana([]) == {}


def test_top_hoy(monkeypatch):
    pedido = {}

    def get(url, params=None, headers=None, timeout=None):
        pedido.update(url=url, params=params)
        return RespuestaFalsa(
            [
                {
                    "id": "solana",
                    "symbol": "sol",
                    "current_price": 150,
                    "price_change_percentage_24h": 12.5,
                }
            ]
        )

    monkeypatch.setattr(requests, "get", get)

    lista = coingecko.top_hoy("eur")

    assert pedido["url"].endswith("/coins/markets")
    assert pedido["params"]["per_page"] == 100
    assert pedido["params"]["order"] == "market_cap_desc"
    assert [(m.coin_id, m.variacion) for m in lista] == [("solana", 12.5)]


def test_mercado_global(monkeypatch):
    pedido = {}

    def get(url, params=None, headers=None, timeout=None):
        pedido["url"] = url
        return RespuestaFalsa({"data": {"total_market_cap": {"eur": 2.5e12}}})

    monkeypatch.setattr(requests, "get", get)

    mercado = coingecko.mercado_global("eur")

    assert pedido["url"].endswith("/global")
    assert mercado.total == 2.5e12
