"""Tests de /mayer."""

import pytest

from crypto_tracker import mayer
from crypto_tracker.mayer import DIAS, MayerError, calcular

DIA = 86_400_000
INICIO = 1_500_000_000_000


def _vela(dia, cierre):
    t = INICIO + dia * DIA
    return [t, "1", "1", "1", str(cierre), "1", t + DIA - 1, "1", 1, "1", "1", "0"]


def _velas(precios):
    return [_vela(i, p) for i, p in enumerate(precios)]


def test_plano_da_uno():
    m = calcular("BTCUSDT", _velas([100] * 250))

    assert len(m.dias) == 51
    assert m.hoy.multiple == pytest.approx(1)
    assert m.media == pytest.approx(100)


def test_el_multiple_de_hoy():
    # 199 días a 100 y hoy a 300: la media es 101 y el múltiplo, 300 / 101.
    m = calcular("BTCUSDT", _velas([100] * 199 + [300]))

    assert m.media == pytest.approx(101)
    assert m.hoy.multiple == pytest.approx(300 / 101)
    assert m.hoy.precio == 300


def test_la_media_va_corriendo():
    precios = [float(i) for i in range(1, 401)]
    m = calcular("BTCUSDT", _velas(precios))

    # El último: media de 201..400 = 300,5
    assert m.media == pytest.approx(300.5)
    assert m.hoy.multiple == pytest.approx(400 / 300.5)
    assert m.dias[0].multiple == pytest.approx(200 / 100.5)


def test_con_menos_de_200_dias_no_hay():
    assert calcular("BTCUSDT", _velas([100] * (DIAS - 1))) is None
    assert calcular("BTCUSDT", {"code": -1}) is None


def test_ignora_velas_rotas_y_repetidas():
    velas = _velas([100] * 200)
    velas += [None, ["x"], _vela(300, "nada"), _vela(301, 0), _vela(199, 100)]

    assert len(calcular("BTCUSDT", velas).dias) == 1


def test_por_debajo_maximo_y_minimo():
    precios = [100] * 199 + [50, 300, 120]
    m = calcular("BTCUSDT", _velas(precios))

    assert m.maximo.precio == 300
    assert m.minimo.precio == 50
    # De los tres días, uno estaba más bajo que hoy.
    assert m.por_debajo == pytest.approx(100 / 3)


@pytest.mark.parametrize(
    "hoy, emoji",
    [(70, "🧊"), (90, "🟢"), (120, "😐"), (200, "🔥"), (400, "🌋")],
)
def test_zona(hoy, emoji):
    # Con 199 días a 100, la media casi no se mueve y el múltiplo es ~hoy/100.
    assert calcular("BTCUSDT", _velas([100] * 199 + [hoy])).zona[0] == emoji


def test_pedir_va_hacia_atras_hasta_que_se_acaba(monkeypatch):
    pedidos = []
    tandas = [
        [_vela(i, 1) for i in range(2000, 3000)],
        [_vela(i, 1) for i in range(1000, 2000)],
        [_vela(i, 1) for i in range(600, 1000)],
    ]

    def get(params):
        pedidos.append(params)
        return tandas[len(pedidos) - 1]

    monkeypatch.setattr(mayer, "_get", get)

    velas = mayer.pedir("BTCUSDT")

    assert len(velas) == 2400
    assert velas[0][0] < velas[-1][0]
    assert "endTime" not in pedidos[0]
    assert pedidos[1]["endTime"] == INICIO + 2000 * DIA - 1
    assert len(pedidos) == 3


def test_pedir_no_pasa_de_cuatro(monkeypatch):
    pedidos = []

    def get(params):
        pedidos.append(params)
        return [_vela(i, 1) for i in range(1000)]

    monkeypatch.setattr(mayer, "_get", get)

    mayer.pedir("BTCUSDT")

    assert len(pedidos) == mayer.PEDIDOS


def test_pedir_sin_par(monkeypatch):
    def get(params):
        raise MayerError("sin datos")

    monkeypatch.setattr(mayer, "_get", get)

    with pytest.raises(MayerError, match="sin datos"):
        mayer.pedir("NADAUSDT")


# --- el comando ---

import time  # noqa: E402

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


def _binance(monkeypatch, velas):
    pedidos = []

    def get(params):
        pedidos.append(params)
        if isinstance(velas, Exception):
            raise velas
        return velas if len(pedidos) == 1 else []

    monkeypatch.setattr(mayer, "_get", get)
    return pedidos


def test_mayer_a_secas_es_bitcoin(config, enviados, monkeypatch):
    # 299 días a 50.000, hoy a 40.000: media 49.950 y múltiplo 0,80.
    pedidos = _binance(monkeypatch, _velas([50_000] * 299 + [40_000]))

    main.atender(config, _mensaje("/mayer"))

    assert pedidos[0]["symbol"] == "BTCUSDT"
    texto = enviados[0]
    assert "Múltiplo de Mayer de Bitcoin: 0,80</b>" in texto
    assert "Precio: $40.000 · media de 200 días: $49.950" in texto
    assert "🟢 <b>Por debajo de su media de 200 días" in texto
    assert "el 0% de los días estuvo más bajo que hoy" in texto
    assert "subir a $49.950 (+24,9%)" in texto
    assert "a partir de $119.880" in texto


def test_mayer_de_otra_y_de_centimos(config, enviados, monkeypatch):
    pedidos = _binance(monkeypatch, _velas([0.5] * 199 + [2.0]))

    main.atender(config, _mensaje("/multiplo ada"))

    assert pedidos[0]["symbol"] == "ADAUSDT"
    texto = enviados[0]
    assert "Precio: $2,00" in texto
    assert "🌋" in texto
    # Ya está por encima de su media y de la burbuja: no dice a qué precio llega.
    assert "Para volver" not in texto
    assert "Zona de burbuja" not in texto


def test_mayer_con_pocos_dias(config, enviados, monkeypatch):
    _binance(monkeypatch, _velas([1] * 50))

    main.atender(config, _mensaje("/mayer btc"))

    assert "lleva menos de 200 días en Binance" in enviados[0]


def test_mayer_sin_par(config, enviados, monkeypatch):
    _binance(monkeypatch, MayerError("sin datos"))

    main.atender(config, _mensaje("/mayer noexiste"))

    assert "Binance no tiene <b>noexiste</b> contra el dólar" in enviados[0]


def test_mayer_binance_caido(config, enviados, monkeypatch):
    _binance(monkeypatch, MayerError("Binance no contesta: timeout"))

    main.atender(config, _mensaje("/mayer"))

    assert "No he podido mirarlo ahora mismo: Binance no contesta" in enviados[0]


def test_mayer_de_dos_en_dos(config, enviados):
    main.atender(config, _mensaje("/mayer btc eth"))

    assert "De una en una" in enviados[0]
