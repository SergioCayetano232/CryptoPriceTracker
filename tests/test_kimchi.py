"""Tests de /kimchi."""

from datetime import date, datetime, timedelta, timezone

import pytest

from crypto_tracker import kimchi
from crypto_tracker.kimchi import KimchiError, leer

LUNES = date(2026, 11, 16)


def _upbit(precios, desde=LUNES):
    # Upbit va de la más nueva a la más vieja.
    velas = [
        {
            "market": "KRW-BTC",
            "candle_date_time_utc": f"{desde + timedelta(days=i)}T00:00:00",
            "trade_price": p,
        }
        for i, p in enumerate(precios)
    ]
    return velas[::-1]


def _binance(precios, desde=LUNES):
    velas = []
    for i, p in enumerate(precios):
        dia = datetime.combine(desde + timedelta(days=i), datetime.min.time())
        ms = int(dia.replace(tzinfo=timezone.utc).timestamp() * 1000)
        velas.append([ms, "1", "1", "1", str(p), "1"])
    return velas


def _cambio(tasas):
    return {"base": "USD", "rates": {str(d): {"KRW": t} for d, t in tasas.items()}}


def test_la_prima():
    # 60.000 $ a 1.350 wones son 81 millones; en Upbit, 82,62: un 2% más.
    k = leer("BTC", _upbit([82_620_000]), _binance([60_000]), _cambio({LUNES: 1350}))

    assert k.ahora == pytest.approx(2.0)
    assert (k.wones, k.dolares, k.cambio) == (82_620_000, 60_000, 1350)
    assert k.nivel == "ganas"


def test_el_fin_de_semana_usa_el_cambio_del_viernes():
    viernes = date(2026, 11, 20)
    k = leer(
        "BTC",
        _upbit([1350, 1377], desde=viernes + timedelta(days=1)),
        _binance([1, 1], desde=viernes + timedelta(days=1)),
        _cambio({viernes: 1350, viernes - timedelta(days=1): 1000}),
    )

    assert [d.dia.weekday() for d in k.dias] == [5, 6]
    assert [round(d.prima, 2) for d in k.dias] == [0.0, 2.0]
    assert k.media == pytest.approx(1.0)


def test_sin_cambio_de_antes_se_salta_el_dia():
    k = leer(
        "BTC",
        _upbit([1350, 1350]),
        _binance([1, 1]),
        _cambio({LUNES + timedelta(days=1): 1350}),
    )

    assert len(k.dias) == 1


@pytest.mark.parametrize(
    "corea, nivel",
    [(1060, "euforia"), (1030, "ganas"), (1005, ""), (985, "descuento")],
)
def test_nivel(corea, nivel):
    k = leer("BTC", _upbit([corea]), _binance([1]), _cambio({LUNES: 1000}))

    assert k.nivel == nivel


def test_sin_dias_en_comun_no_hay():
    otro = LUNES + timedelta(days=3)
    assert leer("BTC", _upbit([1]), _binance([1], otro), _cambio({LUNES: 1})) is None
    assert leer("BTC", {"error": {}}, [], {}) is None


def test_ignora_basura():
    upbit = _upbit([1000]) + [None, {"candle_date_time_utc": "x", "trade_price": 1}]
    upbit.append({"candle_date_time_utc": "2026-11-17T00:00:00", "trade_price": "?"})
    binance = _binance([1]) + [None, ["x"], [10**20, "1", "1", "1", "1"]]
    cambio = _cambio({LUNES: 1000})
    cambio["rates"]["mal"] = {"KRW": 1}
    cambio["rates"]["2026-11-10"] = {"KRW": "nada"}

    assert len(leer("BTC", upbit, binance, cambio).dias) == 1


def test_pedir(monkeypatch):
    pedidos = []

    def get(url, params):
        pedidos.append((url, params))
        return []

    monkeypatch.setattr(kimchi, "_get", get)

    kimchi.pedir("ETH", date(2026, 11, 24))

    assert pedidos[0][1] == {"market": "KRW-ETH", "count": 30}
    assert pedidos[1][1]["symbol"] == "ETHUSDT"
    assert pedidos[2][0].endswith("/2026-10-20..")
    assert pedidos[2][1] == {"base": "USD", "symbols": "KRW"}


def test_pedir_sin_el_par(monkeypatch):
    def get(url, params):
        raise KimchiError("sin datos")

    monkeypatch.setattr(kimchi, "_get", get)

    with pytest.raises(KimchiError, match="sin datos"):
        kimchi.pedir("NADA", LUNES)


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


def _datos(monkeypatch, corea):
    pedidos = []

    def pedir(simbolo, hoy):
        pedidos.append(simbolo)
        if isinstance(corea, Exception):
            raise corea
        return _upbit(corea), _binance([1.0] * len(corea)), _cambio({LUNES: 1000.5})

    monkeypatch.setattr(kimchi, "pedir", pedir)
    return pedidos


def test_kimchi_a_secas_es_bitcoin(config, mandados, monkeypatch):
    pedidos = _datos(monkeypatch, [1000.5] * 9 + [1030.515])

    main.atender(config, _mensaje("/kimchi"))

    assert pedidos == ["BTC"]
    texto, botones = mandados[0]
    assert "🇰🇷 <b>Prima kimchi: +3,00%</b> · BTC" in texto
    assert "Upbit: ₩1.031 · Binance: $1,00" in texto
    assert "<i>A 1.000,50 wones el dólar</i>" in texto
    assert "En 10 días: media +0,30%, entre 0,00% y +3,00%" in texto
    assert "🌶 <b>Pagan bastante más en Corea" in texto
    assert botones == [[("🔄 Actualizar", "/kimchi")]]


@pytest.mark.parametrize(
    "corea, sale",
    [(1100.0, "🔥 <b>Euforia"), (980.0, "🧊 <b>Más barato"), (1001.0, "😐")],
)
def test_kimchi_niveles(config, mandados, monkeypatch, corea, sale):
    pedidos = _datos(monkeypatch, [corea])

    main.atender(config, _mensaje("/corea eth"))

    assert pedidos == ["ETH"]
    assert sale in mandados[0][0]
    # Con un día no hay media.
    assert "media" not in mandados[0][0]


def test_kimchi_sin_el_par(config, mandados, monkeypatch):
    _datos(monkeypatch, KimchiError("sin datos"))

    main.atender(config, _mensaje("/kimchi noexiste"))

    assert "no está en Upbit y en Binance a la vez" in mandados[0][0]


def test_kimchi_caido(config, mandados, monkeypatch):
    _datos(monkeypatch, KimchiError("Upbit no contesta: timeout"))

    main.atender(config, _mensaje("/kimchi"))

    assert "No he podido mirarlo ahora mismo: Upbit no contesta" in mandados[0][0]


def test_kimchi_sin_dias_que_cuadren(config, mandados, monkeypatch):
    monkeypatch.setattr(kimchi, "pedir", lambda simbolo, hoy: ([], [], {}))

    main.atender(config, _mensaje("/kimchi"))

    assert "no me han dado días que cuadren" in mandados[0][0]


def test_kimchi_de_dos_en_dos(config, mandados):
    main.atender(config, _mensaje("/kimchi btc eth"))

    assert "De una en una" in mandados[0][0]
