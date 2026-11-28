"""Tests de /gwei."""

import time

import pytest
import requests

from crypto_tracker.indicadores import gwei
from crypto_tracker.indicadores.gwei import GweiError, leer


def _hex(gweis: float) -> str:
    return hex(round(gweis * 1e9))


def _datos(base=1.0, propinas=None):
    propinas = propinas or [(0.1, 0.5, 2.0)] * 5
    return {
        "baseFeePerGas": [_hex(0.5), _hex(base)],
        "reward": [[_hex(p) for p in fila] for fila in propinas],
    }


def test_leer():
    g = leer(_datos())

    assert g.base == pytest.approx(1)
    assert [t.gwei for t in g.tarifas] == pytest.approx([1.1, 1.5, 3.0])
    assert g.normal.nombre == "Normal"


def test_la_mediana_de_los_bloques():
    propinas = [(0.1, 0.5, 2.0), (0.1, 0.5, 2.0), (50, 50, 50)]

    g = leer(_datos(propinas=propinas))

    # Un bloque suelto con propinas locas no lo mueve.
    assert [t.gwei for t in g.tarifas] == pytest.approx([1.1, 1.5, 3.0])


def test_lo_que_cuesta_en_eth():
    g = leer(_datos(base=10, propinas=[(0, 0, 0)]))

    # 21.000 de gas a 10 gwei: 0,00021 ETH.
    assert g.normal.eth(21_000) == pytest.approx(0.00021)


def test_ignora_bloques_rotos():
    datos = _datos()
    datos["reward"] += [None, ["0x1"], ["x", "0x1", "0x1"], [None, "0x1", "0x1"]]

    assert [t.gwei for t in leer(datos).tarifas] == pytest.approx([1.1, 1.5, 3.0])


@pytest.mark.parametrize(
    "datos",
    [
        {},
        None,
        {"baseFeePerGas": [], "reward": [["0x1", "0x1", "0x1"]]},
        {"baseFeePerGas": ["nada"], "reward": [["0x1", "0x1", "0x1"]]},
        {"baseFeePerGas": ["0x1"], "reward": []},
        {"baseFeePerGas": ["0x1"], "reward": [["x", "x", "x"]]},
    ],
)
def test_sin_lo_que_hace_falta_no_hay(datos):
    assert leer(datos) is None


class _Respuesta:
    def __init__(self, datos, status=200):
        self.datos, self.status_code = datos, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))

    def json(self):
        if isinstance(self.datos, Exception):
            raise self.datos
        return self.datos


def test_pedir(monkeypatch):
    cuerpos = []

    def post(url, json, timeout):
        cuerpos.append(json)
        return _Respuesta({"jsonrpc": "2.0", "result": _datos()})

    monkeypatch.setattr(gwei.requests, "post", post)

    assert gwei.pedir() == _datos()
    assert cuerpos[0]["method"] == "eth_feeHistory"
    assert cuerpos[0]["params"] == [20, "latest", [10, 50, 90]]


@pytest.mark.parametrize(
    "respuesta, error",
    [
        (requests.ConnectionError("sin red"), "no contesta"),
        (_Respuesta({}, 500), "no contesta"),
        (_Respuesta(ValueError("x")), "no es JSON"),
    ],
)
def test_pedir_falla(monkeypatch, respuesta, error):
    def post(url, json, timeout):
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta

    monkeypatch.setattr(gwei.requests, "post", post)

    with pytest.raises(GweiError, match=error):
        gwei.pedir()


def test_pedir_con_un_error_del_nodo_da_vacio(monkeypatch):
    monkeypatch.setattr(
        gwei.requests,
        "post",
        lambda url, json, timeout: _Respuesta({"error": {"code": -1}}),
    )

    assert gwei.pedir() == {}


# --- el comando ---

import main  # noqa: E402
from crypto_tracker.nucleo import coingecko, database, telegram  # noqa: E402
from crypto_tracker.nucleo.config import Config, Watch  # noqa: E402


@pytest.fixture
def config(tmp_path):
    ruta = str(tmp_path / "test.db")
    database.init_db(ruta)
    return Config("token", "123", [Watch("solana", percent=5)], "eur", 300, ruta, 0)


@pytest.fixture
def enviados(monkeypatch):
    lista = []
    monkeypatch.setattr(
        telegram, "send_message", lambda t, c, texto, **kw: lista.append(texto) or True
    )
    return lista


def _mensaje(texto):
    return {"chat": {"id": 123}, "text": texto, "date": int(time.time())}


def _nodo(monkeypatch, datos):
    def pedir():
        if isinstance(datos, Exception):
            raise datos
        return datos

    monkeypatch.setattr(gwei, "pedir", pedir)


def test_gwei_en_euros(config, enviados, monkeypatch):
    _nodo(monkeypatch, _datos(base=10, propinas=[(0, 2, 5)]))
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"ethereum": 2000.0})

    main.atender(config, _mensaje("/gwei"))

    texto = enviados[0]
    assert "⛽ <b>Gas de Ethereum: 12 gwei</b>" in texto
    # 21.000 · 12 gwei = 0,000252 ETH · 2.000 € = 0,50 €
    assert "Enviar ETH: <b>€0,50</b>" in texto
    assert "Un cambio en Uniswap: <b>€3,60</b>" in texto
    assert "🐢 Sin prisa: 10 gwei" in texto
    assert "⚡ Con prisa: 15 gwei" in texto
    assert "10 gwei se queman sí o sí" in texto


def test_gwei_barato_con_decimales(config, enviados, monkeypatch):
    _nodo(monkeypatch, _datos(base=0.1, propinas=[(0, 0.01, 1)]))
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"ethereum": 2000.0})

    main.atender(config, _mensaje("/gaseth"))

    assert "Gas de Ethereum: 0,11 gwei" in enviados[0]
    assert "Enviar ETH: <b>menos de 1 céntimo</b>" in enviados[0]


def test_gwei_sin_precio_va_en_eth(config, enviados, monkeypatch):
    _nodo(monkeypatch, _datos(base=10, propinas=[(0, 0, 0)]))

    def falla(ids, cur):
        raise coingecko.CoinGeckoError("Sin conexion")

    monkeypatch.setattr(coingecko, "get_prices", falla)

    main.atender(config, _mensaje("/gwei"))

    assert "Enviar ETH: <b>0,000210 ETH</b>" in enviados[0]


def test_gwei_usa_el_precio_guardado(config, enviados, monkeypatch):
    database.save_prices(config.database_path, {"ethereum": 1000.0}, "eur")
    _nodo(monkeypatch, _datos(base=10, propinas=[(0, 0, 0)]))

    def no_llamar(ids, cur):
        raise AssertionError("con el guardado no hace falta CoinGecko")

    monkeypatch.setattr(coingecko, "get_prices", no_llamar)

    main.atender(config, _mensaje("/gwei"))

    assert "Enviar ETH: <b>€0,21</b>" in enviados[0]


def test_gwei_sin_datos(config, enviados, monkeypatch):
    _nodo(monkeypatch, {})

    main.atender(config, _mensaje("/gwei"))

    assert "no me ha dado el gas" in enviados[0]


def test_gwei_nodo_caido(config, enviados, monkeypatch):
    _nodo(monkeypatch, GweiError("El nodo de Ethereum no contesta: timeout"))

    main.atender(config, _mensaje("/gwei"))

    assert "No he podido mirarlo ahora mismo: El nodo de Ethereum" in enviados[0]
