"""Tests de /premium."""

import pytest

from crypto_tracker import premium
from crypto_tracker.premium import PremiumError, leer

HORA = 1_795_000_000 // 3600 * 3600


def _coinbase(cierres, desde=0):
    # Coinbase va de la más nueva a la más vieja.
    velas = [[HORA + (desde + i) * 3600, 1, 1, 1, c, 1] for i, c in enumerate(cierres)]
    return velas[::-1]


def _binance(cierres, desde=0):
    return [
        [(HORA + (desde + i) * 3600) * 1000, "1", "1", "1", str(c), "1"]
        for i, c in enumerate(cierres)
    ]


def test_la_prima_contando_que_el_usdt_no_es_un_dolar():
    # En Binance 60.000 USDT, con el USDT a 0,998, son 59.880 $. En Coinbase 59.940.
    p = leer("BTC", _coinbase([59_940]), _coinbase([0.998]), _binance([60_000]))

    assert p.coinbase == 59_940
    assert p.binance == pytest.approx(59_880)
    assert p.ahora == pytest.approx(59_940 / 59_880 * 100 - 100)


def test_cruza_por_hora_y_ordena():
    p = leer(
        "BTC",
        _coinbase([101, 102, 103]),
        _coinbase([1, 1, 1]),
        # A Binance le falta la primera hora y trae una más al final.
        _binance([100, 100, 100], desde=1),
    )

    assert [round(h.prima, 2) for h in p.horas] == [2.0, 3.0]
    assert p.horas[0].cuando.timestamp() == HORA + 3600
    assert p.media == pytest.approx(2.5)
    assert p.coinbase == 103


@pytest.mark.parametrize(
    "coinbase, lado",
    [(100.2, "compran"), (99.8, "venden"), (100.05, "")],
)
def test_lado(coinbase, lado):
    p = leer("BTC", _coinbase([coinbase]), _coinbase([1]), _binance([100]))

    assert p.lado == lado


def test_sin_horas_en_comun_no_hay():
    assert leer("BTC", _coinbase([1]), _coinbase([1]), _binance([1], desde=5)) is None
    assert leer("BTC", {"message": "NotFound"}, [], []) is None


def test_ignora_velas_rotas():
    coinbase = _coinbase([101]) + [None, ["x"], [HORA + 3600, 1, 1, 1, "nada", 1]]
    binance = _binance([100]) + [[(HORA + 7200) * 1000, "1", "1", "1", "0", "1"]]

    assert len(leer("BTC", coinbase, _coinbase([1]), binance).horas) == 1


def test_pedir_pide_lo_que_toca(monkeypatch):
    pedidos = []

    def get(url, params):
        pedidos.append((url, params))
        return []

    monkeypatch.setattr(premium, "_get", get)

    premium.pedir("ETH")

    assert pedidos[0][0].endswith("/products/ETH-USD/candles")
    assert pedidos[1][0].endswith("/products/USDT-USD/candles")
    assert pedidos[2][1] == {"symbol": "ETHUSDT", "interval": "1h", "limit": 350}


def test_pedir_sin_el_par(monkeypatch):
    def get(url, params):
        raise PremiumError("sin datos")

    monkeypatch.setattr(premium, "_get", get)

    with pytest.raises(PremiumError, match="sin datos"):
        premium.pedir("NADA")


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
def mandados(monkeypatch):
    lista = []

    def enviar(token, chat, texto, botones=None, **kw):
        lista.append((texto, botones))
        return True

    monkeypatch.setattr(telegram, "send_message", enviar)
    return lista


def _mensaje(texto):
    return {"chat": {"id": 123}, "text": texto, "date": int(time.time())}


def _velas(monkeypatch, coinbase, binance=None):
    pedidos = []

    def pedir(simbolo):
        pedidos.append(simbolo)
        if isinstance(coinbase, Exception):
            raise coinbase
        uno = [1.0] * len(coinbase)
        return _coinbase(coinbase), _coinbase(uno), _binance(binance or [100] * 48)

    monkeypatch.setattr(premium, "pedir", pedir)
    return pedidos


def test_premium_a_secas_es_bitcoin(config, mandados, monkeypatch):
    pedidos = _velas(monkeypatch, [100.0] * 47 + [100.2])

    main.atender(config, _mensaje("/premium"))

    assert pedidos == ["BTC"]
    texto, botones = mandados[0]
    assert "🇺🇸 <b>Prima de Coinbase: +0,20%</b> · BTC" in texto
    assert "Coinbase: $100,20 · Binance: $100,00" in texto
    assert "En 2 días: media 0,00%, entre 0,00% y +0,20%" in texto
    assert "🟢 <b>Se paga más en Coinbase" in texto
    assert botones == [[("🔄 Actualizar", "/premium")]]


def test_premium_de_otra_vendiendo(config, mandados, monkeypatch):
    pedidos = _velas(monkeypatch, [99.8])

    main.atender(config, _mensaje("/prima eth"))

    assert pedidos == ["ETH"]
    texto, botones = mandados[0]
    assert "🔴 <b>Se paga menos en Coinbase" in texto
    # Con una hora no hay barrita ni media.
    assert "media" not in texto
    assert botones == [[("🔄 Actualizar", "/premium eth")]]


def test_premium_sin_el_par(config, mandados, monkeypatch):
    _velas(monkeypatch, PremiumError("sin datos"))

    main.atender(config, _mensaje("/premium noexiste"))

    assert "no está en Coinbase y en Binance a la vez" in mandados[0][0]


def test_premium_caido(config, mandados, monkeypatch):
    _velas(monkeypatch, PremiumError("Coinbase no contesta: timeout"))

    main.atender(config, _mensaje("/premium"))

    assert "No he podido mirarlo ahora mismo: Coinbase no contesta" in mandados[0][0]


def test_premium_sin_horas_que_cuadren(config, mandados, monkeypatch):
    monkeypatch.setattr(premium, "pedir", lambda simbolo: ([], [], []))

    main.atender(config, _mensaje("/premium"))

    assert "no me han dado precios que cuadren" in mandados[0][0]


def test_premium_de_dos_en_dos(config, mandados):
    main.atender(config, _mensaje("/premium btc eth"))

    assert "De una en una" in mandados[0][0]
