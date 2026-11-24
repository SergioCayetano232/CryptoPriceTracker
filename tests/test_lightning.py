"""Tests de /lightning."""

import time

import pytest
import requests

import main
from crypto_tracker import database, lightning, telegram
from crypto_tracker.config import Config, Watch
from crypto_tracker.lightning import LightningError, leer

DATOS = {
    "numberofnodes": 5098,
    "numberofnodes30dchange": -13.92,
    "numberofchannels": 18527,
    "numberofchannels30dchange": -5.08,
    "networkcapacity": 218190345904,
    "networkcapacity30dchange": -11.18,
    "networkcapacityusd": 130288743.1,
    "newnodes24h": 7,
    "newchannels24h": 144,
}


def test_leer():
    ln = leer(DATOS)

    assert ln.capacidad == pytest.approx(2181.90345904)
    assert ln.dolares == pytest.approx(130288743.1)
    assert (ln.nodos, ln.canales) == (5098, 18527)
    assert ln.capacidad_mes == -11.18
    assert (ln.nodos_nuevos, ln.canales_nuevos) == (7, 144)
    assert ln.por_canal == pytest.approx(2181.90345904 / 18527)


def test_leer_sin_lo_que_no_es_imprescindible():
    ln = leer({"networkcapacity": 1e8, "numberofnodes": 10, "numberofchannels": 20})

    assert ln.dolares is None
    assert ln.capacidad_mes is None
    assert ln.nodos_nuevos is None
    assert ln.hacia == ""


@pytest.mark.parametrize(
    "cambio, hacia",
    [(8.0, "crece"), (-11.0, "encoge"), (2.0, ""), (-4.9, "")],
)
def test_hacia(cambio, hacia):
    assert leer({**DATOS, "networkcapacity30dchange": cambio}).hacia == hacia


@pytest.mark.parametrize(
    "roto",
    [
        {"networkcapacity": None},
        {"networkcapacity": 0},
        {"numberofnodes": True},
        {"numberofchannels": -3},
        {"numberofchannels": float("inf")},
    ],
)
def test_sin_lo_imprescindible_no_hay(roto):
    assert leer({**DATOS, **roto}) is None


def test_leer_basura():
    assert leer(None) is None
    assert leer([]) is None
    assert leer({**DATOS, "newnodes24h": "x", "networkcapacityusd": -1}).dolares is None


def test_pedir_caido(monkeypatch):
    def get(*a, **k):
        raise requests.ConnectionError("sin red")

    monkeypatch.setattr(requests, "get", get)

    with pytest.raises(LightningError, match="1ml.com no contesta"):
        lightning.pedir()


# --- el comando ---


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


def test_lightning(config, mandados, monkeypatch):
    monkeypatch.setattr(lightning, "pedir", lambda: DATOS)

    main.atender(config, _mensaje("/lightning"))

    texto, botones = mandados[0]
    assert "⚡ <b>Red Lightning</b>" in texto
    assert "Capacidad: <b>2.182 BTC</b>, unos 130 millones de dólares" in texto
    assert "🔻 -11,2% en 30 días" in texto
    assert "Nodos: 5.098 · 🔻 -13,9%" in texto
    assert "Canales: 18.527 · 🔻 -5,1%" in texto
    assert "En 24 h: 7 nodos y 144 canales nuevos" in texto
    assert "Cada canal tiene de media 0,118 BTC" in texto
    assert "🪫 <b>Encoge</b>" in texto
    assert botones == [[("🔄 Actualizar", "/lightning")]]


def test_lightning_sin_cambios_ni_nuevos(config, mandados, monkeypatch):
    monkeypatch.setattr(
        lightning,
        "pedir",
        lambda: {"networkcapacity": 5e10, "numberofnodes": 1, "numberofchannels": 1},
    )

    main.atender(config, _mensaje("/ln"))

    texto = mandados[0][0]
    assert "Capacidad: <b>500 BTC</b>" in texto
    assert "dólares" not in texto
    assert "30 días" not in texto
    assert "En 24 h" not in texto
    assert "😐 <b>Estable</b>" in texto


def test_lightning_sin_datos(config, mandados, monkeypatch):
    monkeypatch.setattr(lightning, "pedir", lambda: {})

    main.atender(config, _mensaje("/lightning"))

    assert "1ml.com no me ha dado" in mandados[0][0]


def test_lightning_caido(config, mandados, monkeypatch):
    def falla():
        raise LightningError("1ml.com no contesta: timeout")

    monkeypatch.setattr(lightning, "pedir", falla)

    main.atender(config, _mensaje("/lightning"))

    assert "No he podido mirarlo ahora mismo: 1ml.com" in mandados[0][0]
