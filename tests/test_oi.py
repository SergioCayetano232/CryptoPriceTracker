"""Tests de /oi."""

from datetime import datetime, timedelta, timezone

import pytest

from crypto_tracker.oi import Dia, lectura, leer

HOY = datetime(2026, 11, 23, tzinfo=timezone.utc)


def _dato(dias_atras, contratos, precio):
    cuando = HOY - timedelta(days=dias_atras)
    return {
        "symbol": "BTCUSDT",
        "sumOpenInterest": str(contratos),
        "sumOpenInterestValue": str(contratos * precio),
        "timestamp": int(cuando.timestamp() * 1000),
    }


def _interes(*pares):
    """(contratos, precio) del más viejo a hoy, uno por día."""
    n = len(pares)
    return leer("BTCUSDT", [_dato(n - 1 - i, c, p) for i, (c, p) in enumerate(pares)])


def test_leer():
    i = leer("BTCUSDT", [_dato(1, 90000, 60000), _dato(0, 99000, 66000)])

    assert i.par == "BTCUSDT"
    assert i.hoy == Dia(HOY, 99000, 99000 * 66000)
    assert i.hoy.precio == pytest.approx(66000)
    assert i.cambio(1) == pytest.approx(10)
    assert i.cambio_precio(1) == pytest.approx(10)
    assert i.cambio(7) is None


def test_leer_ordena_y_salta_lo_roto():
    datos = [
        _dato(0, 99000, 66000),
        {"sumOpenInterest": "x", "timestamp": 1},
        "basura",
        {"sumOpenInterest": "1", "sumOpenInterestValue": "0", "timestamp": 2},
        _dato(1, 90000, 60000),
    ]

    i = leer("BTCUSDT", datos)

    assert [d.contratos for d in i.dias] == [90000, 99000]


@pytest.mark.parametrize("datos", [None, {}, [], [_dato(0, 1, 1)]])
def test_leer_sin_dos_dias(datos):
    assert leer("BTCUSDT", datos) is None


def test_maximo():
    assert _interes((100, 1), (90, 1), (110, 1)).maximo
    assert not _interes((100, 1), (120, 1), (110, 1)).maximo


@pytest.mark.parametrize(
    "hace_7, hoy, emoji",
    [
        ((100, 100), (110, 105), "🐂"),
        ((100, 100), (110, 95), "🐻"),
        ((100, 100), (110, 100), "⚡"),
        ((100, 100), (90, 105), "🩳"),
        ((100, 100), (90, 95), "🎈"),
        ((100, 100), (90, 100), "🧹"),
        ((100, 100), (102, 110), "😐"),
    ],
)
def test_lectura_con_la_semana(hace_7, hoy, emoji):
    # Ocho días: el de hace 7 y seis de relleno que no cuentan.
    i = _interes(hace_7, *[(1, 1)] * 6, hoy)

    assert lectura(i)[0] == emoji


def test_lectura_con_menos_de_una_semana_usa_lo_que_hay():
    assert lectura(_interes((100, 100), (110, 105)))[0] == "🐂"


def test_pedir_sin_futuros_es_la_lista_vacia(monkeypatch):
    from crypto_tracker import oi
    from crypto_tracker.funding import FundingError

    monkeypatch.setattr(oi, "_get", lambda url, params: [])

    with pytest.raises(FundingError, match="sin futuros"):
        oi.pedir("NOEXISTEUSDT")


# --- de punta a punta ---

import time  # noqa: E402

import main  # noqa: E402
from crypto_tracker import database, oi, telegram  # noqa: E402
from crypto_tracker.config import Config, Watch  # noqa: E402
from crypto_tracker.funding import FundingError  # noqa: E402


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


def _binance(monkeypatch, datos):
    pedidos = []

    def get(url, params):
        pedidos.append(params)
        if isinstance(datos, Exception):
            raise datos
        return datos

    monkeypatch.setattr(oi, "_get", get)
    return pedidos


def test_oi(config, enviados, monkeypatch):
    # 8 días: lo apostado cae un 12% y el precio un 3%.
    datos = [_dato(7, 1000, 100)] + [_dato(d, 950, 99) for d in range(6, 0, -1)]
    pedidos = _binance(monkeypatch, datos + [_dato(0, 880, 97)])

    main.atender(config, _mensaje("/oi sol"))

    assert pedidos == [{"symbol": "SOLUSDT", "period": "1d", "limit": 31}]
    texto = enviados[0]
    assert texto.startswith("📊 <b>Futuros de Solana</b> · SOLUSDT en Binance")
    assert "Apostado ahora: <b>880,00 SOL</b>" in texto
    assert "24 h: -7,4% · 7 días: -12,0%" in texto
    assert "🎈 <b>Se cierran posiciones mientras baja" in texto
    assert "En la semana, lo apostado -12,0% y el precio -3,0%." in texto
    assert "/funding sol</i>" in texto


def test_oi_a_secas_usa_la_primera_que_vigilas(config, enviados, monkeypatch):
    pedidos = _binance(monkeypatch, [_dato(1, 100, 1), _dato(0, 120, 1)])

    main.atender(config, _mensaje("/oi"))

    assert pedidos[0]["symbol"] == "SOLUSDT"
    assert "En 1 día, lo apostado +20,0%" in enviados[0]


def test_oi_sin_futuros(config, enviados, monkeypatch):
    _binance(monkeypatch, FundingError("sin futuros"))

    main.atender(config, _mensaje("/oi noexiste"))

    assert "<b>noexiste</b> no tiene futuros en Binance" in enviados[0]


def test_oi_binance_caido(config, enviados, monkeypatch):
    _binance(monkeypatch, FundingError("Binance no contesta: timeout"))

    main.atender(config, _mensaje("/oi btc"))

    assert "No he podido mirarlo ahora mismo: Binance no contesta" in enviados[0]


def test_oi_de_dos_en_dos(config, enviados):
    main.atender(config, _mensaje("/oi btc eth"))

    assert "De una en una" in enviados[0]
