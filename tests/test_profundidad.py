"""Tests de /profundidad."""

import pytest

from crypto_tracker.profundidad import leer


def _libro(compras, ventas):
    return {
        "bids": [[str(p), str(q)] for p, q in compras],
        "asks": [[str(p), str(q)] for p, q in ventas],
    }


# Precio medio 100. Cada orden vale p * q dólares.
COMPRAS = [(99.9, 10), (99.2, 10), (98.5, 10), (97.0, 10), (90.0, 10)]
VENTAS = [(100.1, 10), (100.8, 10), (101.5, 10), (103.0, 10), (110.0, 10)]


def test_precio_medio_y_tramos():
    p = leer("BTCUSDT", _libro(COMPRAS, VENTAS))

    assert p.precio == pytest.approx(100)
    medio, uno, dos = p.tramos
    assert (medio.pct, uno.pct, dos.pct) == (0.5, 1.0, 2.0)
    assert medio.subir == pytest.approx(1001)
    assert uno.subir == pytest.approx(1001 + 1008)
    assert dos.subir == pytest.approx(1001 + 1008 + 1015)
    assert dos.bajar == pytest.approx(999 + 992 + 985)
    assert not dos.subir_corto and not dos.bajar_corto


def test_ordena_aunque_venga_desordenado():
    p = leer("BTCUSDT", _libro(COMPRAS[::-1], VENTAS[::-1]))

    assert p.precio == pytest.approx(100)
    assert p.tramos[0].subir == pytest.approx(1001)


def test_si_el_libro_se_acaba_antes_lo_marca():
    p = leer("BTCUSDT", _libro(COMPRAS[:2], VENTAS))

    dos = p.mayor
    assert dos.bajar == pytest.approx(999 + 992)
    assert dos.bajar_corto
    assert not dos.subir_corto


@pytest.mark.parametrize(
    "mas_compras, mas_ventas, lado",
    [(20, 10, "compran"), (10, 20, "venden"), (12, 10, "")],
)
def test_lado(mas_compras, mas_ventas, lado):
    compras = [(99.5, mas_compras)] + COMPRAS[-1:]
    ventas = [(100.5, mas_ventas)] + VENTAS[-1:]

    assert leer("BTCUSDT", _libro(compras, ventas)).lado == lado


def test_sin_un_lado_no_hay():
    assert leer("BTCUSDT", _libro(COMPRAS, [])) is None
    assert leer("BTCUSDT", {"code": -1121}) is None
    assert leer("BTCUSDT", None) is None


def test_ignora_ordenes_rotas():
    datos = _libro(COMPRAS, VENTAS)
    datos["bids"] += [["x", "1"], ["50"], None, ["80", "0"], ["-1", "5"]]

    assert leer("BTCUSDT", datos).tramos[0].bajar == pytest.approx(999)


# --- el comando ---

import time  # noqa: E402

import main  # noqa: E402
from crypto_tracker import database, profundidad, telegram  # noqa: E402
from crypto_tracker.config import Config, Watch  # noqa: E402
from crypto_tracker.profundidad import ProfundidadError  # noqa: E402


@pytest.fixture
def config(tmp_path):
    ruta = str(tmp_path / "test.db")
    database.init_db(ruta)
    return Config("token", "123", [Watch("solana", percent=5)], "eur", 300, ruta, 0)


@pytest.fixture
def mandados(monkeypatch):
    lista = []

    def enviar(token, chat, texto, botones=None, **kw):
        lista.append((texto, botones))
        return True

    monkeypatch.setattr(telegram, "send_message", enviar)
    return lista


def _mensaje(texto):
    return {"chat": {"id": 123}, "text": texto, "date": int(time.time())}


def _binance(monkeypatch, datos):
    pedidos = []

    def pedir(par):
        pedidos.append(par)
        if isinstance(datos, Exception):
            raise datos
        return datos

    monkeypatch.setattr(profundidad, "pedir", pedir)
    return pedidos


def test_profundidad(config, mandados, monkeypatch):
    compras = [(99.9, 50_000), (98.5, 100_000), (90.0, 1)]
    ventas = [(100.1, 20_000), (101.5, 30_000), (110.0, 1)]
    pedidos = _binance(monkeypatch, _libro(compras, ventas))

    main.atender(config, _mensaje("/profundidad btc"))

    assert pedidos == ["BTCUSDT"]
    texto, botones = mandados[0]
    assert "🧱 <b>Profundidad de Bitcoin</b> · BTCUSDT en Binance" in texto
    assert "Precio: $100,00" in texto
    assert "0,5%      2,0 M     5,0 M" in texto
    assert "2%        5,0 M    14,8 M" in texto
    assert "🛡 <b>Hay más esperando para comprar" in texto
    assert "Con +" not in texto
    assert botones == [[("🔄 Actualizar", "/profundidad btc")]]


def test_profundidad_a_secas_y_con_el_libro_corto(config, mandados, monkeypatch):
    pedidos = _binance(monkeypatch, _libro([(99.9, 3000)], [(100.1, 3000)]))

    main.atender(config, _mensaje("/liquidez"))

    assert pedidos == ["SOLUSDT"]
    texto, botones = mandados[0]
    assert "2%     +300 mil  +300 mil" in texto
    assert "Con + es que el libro se acaba antes" in texto
    assert "⚖️ <b>Parecido a los dos lados" in texto
    assert botones == [[("🔄 Actualizar", "/profundidad")]]


def test_profundidad_sin_par(config, mandados, monkeypatch):
    _binance(monkeypatch, ProfundidadError("sin datos"))

    main.atender(config, _mensaje("/profundidad noexiste"))

    assert "Binance no tiene <b>noexiste</b> contra el dólar" in mandados[0][0]


def test_profundidad_binance_caido(config, mandados, monkeypatch):
    _binance(monkeypatch, ProfundidadError("Binance no contesta: timeout"))

    main.atender(config, _mensaje("/profundidad btc"))

    assert "No he podido mirarlo ahora mismo: Binance no contesta" in mandados[0][0]


def test_profundidad_libro_vacio(config, mandados, monkeypatch):
    _binance(monkeypatch, {"bids": [], "asks": []})

    main.atender(config, _mensaje("/profundidad btc"))

    assert "no me ha dado las órdenes" in mandados[0][0]


def test_profundidad_de_dos_en_dos(config, mandados):
    main.atender(config, _mensaje("/profundidad btc eth"))

    assert "De una en una" in mandados[0][0]
