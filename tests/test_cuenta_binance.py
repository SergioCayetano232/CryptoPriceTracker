"""Tests de /binance: los saldos de verdad contra lo apuntado."""

from urllib.parse import parse_qs, urlparse

import pytest
import requests

from crypto_tracker import cuenta_binance
from crypto_tracker.cuenta_binance import CuentaError, comparar, firmar, leer
from crypto_tracker.nucleo.config import Posicion

# El ejemplo de la documentación de Binance, con su firma.
SECRETO_EJEMPLO = "NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j"
CONSULTA_EJEMPLO = (
    "symbol=LTCBTC&side=BUY&type=LIMIT&timeInForce=GTC&quantity=1&price=0.1"
    "&recvWindow=5000&timestamp=1499827319559"
)
FIRMA_EJEMPLO = "c8db56825ae71d6d79447849e617115f4a920fa2acdcab2b053c4b2838bd6b71"


def test_firma_como_la_documentacion_de_binance():
    assert firmar(CONSULTA_EJEMPLO, SECRETO_EJEMPLO) == FIRMA_EJEMPLO


def test_claves_del_env(monkeypatch):
    monkeypatch.setenv("BINANCE_API_KEY", " clave ")
    monkeypatch.setenv("BINANCE_API_SECRET", "secreto")
    assert cuenta_binance.claves() == ("clave", "secreto")

    monkeypatch.setenv("BINANCE_API_SECRET", "")
    assert cuenta_binance.claves() is None


def test_leer_suma_lo_bloqueado_y_quita_el_polvo():
    datos = {
        "balances": [
            {"asset": "BTC", "free": "0.10000000", "locked": "0.05000000"},
            {"asset": "ETH", "free": "0.000000001", "locked": "0"},
        ]
    }

    assert leer(datos) == {"BTC": pytest.approx(0.15)}


@pytest.mark.parametrize("datos", [None, {}, {"balances": [{"asset": "BTC"}]}])
def test_leer_raro(datos):
    assert leer(datos) is None


def test_comparar():
    saldos = {"BTC": 0.15, "LDBTC": 0.05, "ETH": 1.0, "EUR": 300.0, "RARO": 7.0}
    cartera = [Posicion("bitcoin", 0.2, 5000.0), Posicion("solana", 10, 1000.0)]

    c = comparar(saldos, cartera)

    por_id = {d.coin_id: d for d in c.diferencias}
    # Simple Earn (LDBTC) cuenta como bitcoin.
    assert por_id["bitcoin"].en_binance == pytest.approx(0.2)
    assert por_id["bitcoin"].cuadra
    assert por_id["ethereum"].falta == 1.0  # está en Binance y no apuntado
    assert por_id["solana"].falta == -10  # apuntado y no está en Binance
    assert "EUR" not in c.desconocidas
    assert c.desconocidas == ["RARO"]


class _Respuesta:
    def __init__(self, datos, status=200):
        self.datos, self.status_code = datos, status

    def json(self):
        if isinstance(self.datos, Exception):
            raise self.datos
        return self.datos


def test_pedir_saldos_firma_la_consulta(monkeypatch):
    pedida = {}

    def get(url, headers, **k):
        pedida["url"], pedida["headers"] = url, headers
        return _Respuesta({"balances": [{"asset": "BTC", "free": "1", "locked": "0"}]})

    monkeypatch.setattr(requests, "get", get)

    assert cuenta_binance.pedir_saldos("clave", "secreto", 1700000000000) == {"BTC": 1}
    assert pedida["headers"] == {"X-MBX-APIKEY": "clave"}
    url = urlparse(pedida["url"])
    assert url.path == "/api/v3/account"
    params = parse_qs(url.query)
    assert params["omitZeroBalances"] == ["true"]
    assert params["timestamp"] == ["1700000000000"]
    consulta = url.query.rsplit("&signature=", 1)[0]
    assert params["signature"] == [firmar(consulta, "secreto")]


@pytest.mark.parametrize(
    "respuesta, mensaje",
    [
        (
            _Respuesta({"code": -2015, "msg": "Invalid API-key"}, 401),
            "no acepta la clave",
        ),
        (_Respuesta({"code": -1021, "msg": "Timestamp"}, 400), "hora"),
        (_Respuesta(ValueError("x"), 502), "no ha querido"),
        (_Respuesta({"nada": 1}), "no entiendo"),
    ],
)
def test_pedir_saldos_falla(monkeypatch, respuesta, mensaje):
    monkeypatch.setattr(requests, "get", lambda url, **k: respuesta)

    with pytest.raises(CuentaError, match=mensaje):
        cuenta_binance.pedir_saldos("c", "s", 1)


def test_pedir_saldos_sin_red(monkeypatch):
    def get(url, **k):
        raise requests.ConnectionError("caída")

    monkeypatch.setattr(requests, "get", get)

    with pytest.raises(CuentaError, match="no contesta"):
        cuenta_binance.pedir_saldos("c", "s", 1)
