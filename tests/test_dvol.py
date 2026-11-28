"""Tests de /dvol."""

import time
from datetime import datetime, timezone

import pytest
import requests

from crypto_tracker import dvol
from crypto_tracker.dvol import DvolError, leer

DIA = 86_400_000
INICIO = 1_760_000_000_000


def _dias(valores):
    return [[INICIO + i * DIA, v, v, v, v] for i, v in enumerate(valores)]


def test_leer():
    d = leer("BTC", _dias([40, 50, 60]))

    assert [x.valor for x in d.dias] == [40, 50, 60]
    assert d.hoy.valor == 60
    assert d.hoy.cuando == datetime.fromtimestamp(
        (INICIO + 2 * DIA) / 1000, timezone.utc
    )


def test_ignora_lo_roto_y_ordena():
    datos = _dias([40, 50])[::-1] + [None, ["x"], [INICIO + 9 * DIA, 1, 1, 1, "nada"]]
    datos += [[INICIO + 8 * DIA, 1, 1, 1, 0], [INICIO + 7 * DIA, 1, 1, 1, float("nan")]]

    assert [x.valor for x in leer("BTC", datos).dias] == [40, 50]


def test_sin_nada_no_hay():
    assert leer("BTC", []) is None
    assert leer("BTC", {"error": 1}) is None


def test_hace_una_semana():
    assert leer("BTC", _dias([50] * 7)).hace_semana is None
    assert leer("BTC", _dias([40] + [50] * 7)).hace_semana.valor == 40


def test_maximo_minimo_y_por_debajo():
    d = leer("BTC", _dias([30, 80, 50, 60, 55]))

    assert d.maximo.valor == 80
    assert d.minimo.valor == 30
    # 30 y 50 por debajo de 55: dos de cinco.
    assert d.por_debajo == pytest.approx(40)


def test_lo_esperado_va_con_la_raiz_del_tiempo():
    d = leer("BTC", _dias([73]))

    assert d.esperado(365) == pytest.approx(73)
    assert d.esperado(1) == pytest.approx(73 / 365**0.5)
    assert d.esperado(30) == pytest.approx(73 * (30 / 365) ** 0.5)


@pytest.mark.parametrize(
    "hoy, emoji",
    [(5, "😴"), (50, "😐"), (85, "😬"), (200, "🌪️")],
)
def test_zona_segun_su_año(hoy, emoji):
    # Cien días de 1 a 100: el % que queda por debajo es casi la cifra de hoy.
    d = leer("ETH", _dias(list(range(1, 100)) + [hoy]))

    assert d.zona[0] == emoji


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
    pedidos = []

    def get(url, params, timeout):
        pedidos.append(params)
        return _Respuesta({"result": {"data": _dias([50]), "continuation": None}})

    monkeypatch.setattr(dvol.requests, "get", get)
    ahora = datetime(2026, 11, 25, tzinfo=timezone.utc)

    assert dvol.pedir("ETH", ahora) == _dias([50])
    assert pedidos[0]["currency"] == "ETH"
    assert pedidos[0]["resolution"] == "1D"
    assert pedidos[0]["end_timestamp"] - pedidos[0]["start_timestamp"] == 365 * DIA


@pytest.mark.parametrize(
    "respuesta, error",
    [
        (requests.ConnectionError("sin red"), "Deribit no contesta"),
        (_Respuesta({}, 500), "Deribit no contesta"),
        (_Respuesta(ValueError("x")), "no es JSON"),
    ],
)
def test_pedir_falla(monkeypatch, respuesta, error):
    def get(url, params, timeout):
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta

    monkeypatch.setattr(dvol.requests, "get", get)

    with pytest.raises(DvolError, match=error):
        dvol.pedir("BTC")


def test_pedir_con_algo_raro_da_vacio(monkeypatch):
    monkeypatch.setattr(
        dvol.requests, "get", lambda url, params, timeout: _Respuesta({"error": "x"})
    )

    assert dvol.pedir("BTC") == []


# --- el comando ---

import main  # noqa: E402
from crypto_tracker.nucleo import database, telegram  # noqa: E402
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


def _deribit(monkeypatch, datos):
    pedidos = []

    def pedir(moneda):
        pedidos.append(moneda)
        if isinstance(datos, Exception):
            raise datos
        return datos

    monkeypatch.setattr(dvol, "pedir", pedir)
    return pedidos


def test_dvol_a_secas_es_bitcoin(config, enviados, monkeypatch):
    pedidos = _deribit(monkeypatch, _dias([50] * 20 + [40] + [73]))

    main.atender(config, _mensaje("/dvol"))

    assert pedidos == ["BTC"]
    texto = enviados[0]
    assert "🎢 <b>DVOL de Bitcoin: 73,0</b>" in texto
    assert "<code>" in texto
    assert "🌪️ <b>De lo más alto del año" in texto
    assert "Hace una semana: 50,0 (+23,0)" in texto
    assert "el 95% de los días estuvo más bajo" in texto
    assert "se mueva ±3,8% en un día, ±10,1% en una semana o ±20,9% en un mes" in texto


def test_dvol_de_ethereum(config, enviados, monkeypatch):
    pedidos = _deribit(monkeypatch, _dias([70]))

    main.atender(config, _mensaje("/vix eth"))

    assert pedidos == ["ETH"]
    assert "DVOL de Ethereum: 70,0" in enviados[0]
    assert "Hace una semana" not in enviados[0]


def test_dvol_de_otra(config, enviados, monkeypatch):
    pedidos = _deribit(monkeypatch, [])

    main.atender(config, _mensaje("/dvol sol"))

    assert "solo tiene índice de bitcoin y de ethereum" in enviados[0]
    assert pedidos == []


def test_dvol_sin_datos(config, enviados, monkeypatch):
    _deribit(monkeypatch, [])

    main.atender(config, _mensaje("/dvol"))

    assert "Deribit no me ha dado el índice" in enviados[0]


def test_dvol_deribit_caido(config, enviados, monkeypatch):
    _deribit(monkeypatch, DvolError("Deribit no contesta: timeout"))

    main.atender(config, _mensaje("/dvol"))

    assert "No he podido mirarlo ahora mismo: Deribit no contesta" in enviados[0]
