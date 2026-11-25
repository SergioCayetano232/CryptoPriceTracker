"""Tests de /mvrv."""

import math
import time
from datetime import date, timedelta

import pytest
import requests

from crypto_tracker import mvrv
from crypto_tracker.mvrv import CALENTAR, MvrvError, leer

PRIMERO = date(2011, 1, 1)


def _fila(dia, capitalizacion, valor, precio):
    return {
        "asset": "btc",
        "time": f"{PRIMERO + timedelta(days=dia)}T00:00:00.000000000Z",
        "CapMrktCurUSD": str(capitalizacion),
        "CapMVRVCur": str(valor),
        "PriceUSD": str(precio),
    }


def _filas(capitalizaciones, valor=2.0, precio=100.0):
    return [_fila(i, c, valor, precio) for i, c in enumerate(capitalizaciones)]


def test_el_primer_año_no_cuenta():
    assert leer(_filas([100] * CALENTAR)) is None
    m = leer(_filas([100 + i for i in range(CALENTAR + 10)]))

    assert len(m.dias) == 10
    assert m.dias[0].cuando == PRIMERO + timedelta(days=CALENTAR)


def test_el_z_con_la_desviacion_hasta_ese_dia(monkeypatch):
    monkeypatch.setattr(mvrv, "CALENTAR", 0)
    capitalizaciones = [10, 20, 30, 40]

    m = leer(_filas(capitalizaciones, valor=2.0))

    # Con MVRV 2 la realizada es la mitad: lo de arriba es capitalización / 2.
    assert len(m.dias) == 3
    for i, d in enumerate(m.dias, start=1):
        hasta = capitalizaciones[: i + 1]
        media = sum(hasta) / len(hasta)
        desviacion = math.sqrt(sum((x - media) ** 2 for x in hasta) / len(hasta))
        assert d.z == pytest.approx(capitalizaciones[i] / 2 / desviacion)


def test_sin_desviacion_no_hay_z(monkeypatch):
    monkeypatch.setattr(mvrv, "CALENTAR", 0)

    # El primero no tiene con qué compararse.
    assert len(leer(_filas([10, 20])).dias) == 1


def test_precio_realizado_y_ganancia():
    m = leer(_filas([100 + i for i in range(CALENTAR + 1)], valor=1.25, precio=50_000))

    assert m.hoy.realizado == pytest.approx(40_000)
    assert m.hoy.ganancia == pytest.approx(25)


def test_maximo_minimo_y_por_debajo(monkeypatch):
    monkeypatch.setattr(mvrv, "CALENTAR", 0)
    filas = [
        _fila(0, 10, 2, 1),
        _fila(1, 20, 4, 1),
        _fila(2, 30, 0.5, 1),
        _fila(3, 40, 1.5, 1),
    ]

    m = leer(filas)

    assert m.maximo.cuando == PRIMERO + timedelta(days=1)
    assert m.minimo.cuando == PRIMERO + timedelta(days=2)
    assert m.minimo.z < 0
    # De los tres días con Z, uno estuvo más bajo que hoy.
    assert m.por_debajo == pytest.approx(100 / 3)


def test_ignora_lo_roto_y_ordena(monkeypatch):
    monkeypatch.setattr(mvrv, "CALENTAR", 0)
    filas = _filas([10, 20, 30])[::-1] + [
        None,
        {},
        _fila(9, "nada", 1, 1),
        _fila(10, 10, 0, 1),
        _fila(11, 10, 1, float("nan")),
        {"time": "ayer", "CapMrktCurUSD": "1", "CapMVRVCur": "1", "PriceUSD": "1"},
    ]

    m = leer(filas)

    assert [d.cuando for d in m.dias] == [
        PRIMERO + timedelta(days=1),
        PRIMERO + timedelta(days=2),
    ]


@pytest.mark.parametrize("datos", [[], {}, None, {"data": "x"}])
def test_sin_nada_no_hay(datos):
    assert leer(datos) is None


@pytest.mark.parametrize(
    "z, emoji", [(-0.5, "🧊"), (1, "🟢"), (3, "😐"), (6, "🔥"), (9, "🌋")]
)
def test_zona(z, emoji):
    m = mvrv.Mvrv([mvrv.Dia(PRIMERO, 1, 1, z)])

    assert m.zona[0] == emoji


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
        return _Respuesta({"data": _filas([1, 2])})

    monkeypatch.setattr(mvrv.requests, "get", get)

    assert mvrv.pedir() == _filas([1, 2])
    assert pedidos[0]["assets"] == "btc"
    assert pedidos[0]["metrics"] == "CapMVRVCur,CapMrktCurUSD,PriceUSD"


@pytest.mark.parametrize(
    "respuesta, error",
    [
        (requests.ConnectionError("sin red"), "CoinMetrics no contesta"),
        (_Respuesta({}, 403), "CoinMetrics no contesta"),
        (_Respuesta(ValueError("x")), "no es JSON"),
    ],
)
def test_pedir_falla(monkeypatch, respuesta, error):
    def get(url, params, timeout):
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta

    monkeypatch.setattr(mvrv.requests, "get", get)

    with pytest.raises(MvrvError, match=error):
        mvrv.pedir()


# --- el comando ---

import main  # noqa: E402
from crypto_tracker import database, telegram  # noqa: E402
from crypto_tracker.config import Config, Watch  # noqa: E402


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


def _coinmetrics(monkeypatch, datos):
    def pedir():
        if isinstance(datos, Exception):
            raise datos
        return datos

    monkeypatch.setattr(mvrv, "pedir", pedir)


def test_mvrv(config, enviados, monkeypatch):
    capitalizaciones = [100 + i for i in range(CALENTAR + 30)]
    _coinmetrics(monkeypatch, _filas(capitalizaciones, valor=1.25, precio=60_000))

    main.atender(config, _mensaje("/mvrv"))

    texto = enviados[0]
    assert "🧾 <b>MVRV de bitcoin: 1,25</b>" in texto
    assert "Precio: $60.000 · precio realizado: $48.000" in texto
    assert "De media, los que tienen bitcoin van +25,0%." in texto
    assert "Z-score: " in texto
    assert "Para bajar a 0 tendría que caer a $48.000 (-20,0%)." in texto
    assert "Desde 2012, el " in texto
    assert "Datos de CoinMetrics, del 30/01." in texto


def test_mvrv_por_debajo(config, enviados, monkeypatch):
    _coinmetrics(monkeypatch, _filas([100 + i for i in range(CALENTAR + 2)], 0.8))

    main.atender(config, _mensaje("/realizado"))

    assert "🧊 <b>Fondo" in enviados[0]
    assert "Para bajar a 0" not in enviados[0]


def test_mvrv_sin_datos(config, enviados, monkeypatch):
    _coinmetrics(monkeypatch, [])

    main.atender(config, _mensaje("/mvrv"))

    assert "CoinMetrics no me ha dado el MVRV" in enviados[0]


def test_mvrv_caido(config, enviados, monkeypatch):
    _coinmetrics(monkeypatch, MvrvError("CoinMetrics no contesta: timeout"))

    main.atender(config, _mensaje("/zscore"))

    assert "No he podido mirarlo ahora mismo: CoinMetrics no contesta" in enviados[0]
