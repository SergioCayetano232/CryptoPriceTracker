"""Tests de /arcoiris."""

import math
from datetime import datetime, timedelta, timezone

import pytest

from crypto_tracker.arcoiris import FRANJAS, GENESIS, MINIMO, calcular

INICIO = datetime(2017, 8, 17, tzinfo=timezone.utc)


def _vela(cuando, precio):
    ms = int(cuando.timestamp() * 1000)
    return [ms, "1", "1", "1", str(precio), "1", ms + 1, "1", 1, "1", "1", "0"]


def _ley(cuando, a=-12.0, b=4.5):
    dias = (cuando - GENESIS) / timedelta(days=1)
    return 10 ** (a + b * math.log10(dias))


def _velas(n, ruido=lambda i: 0.0, hoy=None):
    velas = []
    for i in range(n):
        cuando = INICIO + timedelta(days=i)
        velas.append(_vela(cuando, _ley(cuando) * 10 ** ruido(i)))
    if hoy is not None:
        velas[-1] = _vela(INICIO + timedelta(days=n - 1), hoy)
    return velas


def _onda(i):
    # Un día arriba y otro abajo: se compensa y la curva sale la de verdad.
    return 0.3 if i % 2 else -0.3


def test_encuentra_la_ley_de_potencias():
    a = calcular(_velas(1500, _onda))

    assert a.b == pytest.approx(4.5, abs=0.05)
    assert a.a == pytest.approx(-12.0, abs=0.2)
    cuando = INICIO + timedelta(days=1000)
    assert a.curva(cuando) == pytest.approx(_ley(cuando), rel=0.02)


def test_nueve_franjas_entre_lo_mas_bajo_y_lo_mas_alto():
    a = calcular(_velas(1500, _onda))

    assert len(a.bordes) == len(FRANJAS) + 1
    pasos = {round(a.bordes[i + 1] - a.bordes[i], 9) for i in range(len(FRANJAS))}
    assert len(pasos) == 1
    assert a.bordes[0] == pytest.approx(-0.3, abs=0.05)
    assert a.bordes[-1] == pytest.approx(0.3, abs=0.05)


def test_la_franja_de_hoy():
    abajo = calcular(_velas(1500, lambda i: -0.3 if i == 1499 else _onda(i)))
    arriba = calcular(_velas(1500, lambda i: 0.3 if i == 1499 else _onda(i)))
    medio = calcular(_velas(1500, lambda i: 0.0 if i == 1499 else _onda(i)))

    assert abajo.franja == 0
    assert arriba.franja == len(FRANJAS) - 1
    assert medio.franja == 4
    assert abajo.sobre_curva < 0 < arriba.sobre_curva


def test_precio_de_los_bordes():
    a = calcular(_velas(1500, _onda))
    cuando = a.hoy[0]

    assert a.precio_borde(cuando, 0) < a.curva(cuando) < a.precio_borde(cuando, 9)


def test_con_poca_historia_no_hay():
    assert calcular(_velas(MINIMO - 1)) is None
    assert calcular({"code": -1}) is None


def test_ignora_velas_rotas():
    velas = _velas(MINIMO, _onda)
    velas += [None, ["x"], [10**20, "1", "1", "1", "1"], _vela(INICIO, 0)]

    assert len(calcular(velas).dias) == MINIMO


def test_dibuja_un_png():
    from crypto_tracker.informes.grafica import dibujar_arcoiris

    assert dibujar_arcoiris(calcular(_velas(MINIMO, _onda))).startswith(b"\x89PNG")


# --- el comando ---

import time  # noqa: E402

import main  # noqa: E402
from crypto_tracker import mayer  # noqa: E402
from crypto_tracker.informes import grafica  # noqa: E402
from crypto_tracker.nucleo import database, telegram  # noqa: E402
from crypto_tracker.nucleo.config import Config, Watch  # noqa: E402


@pytest.fixture
def config(tmp_path):
    ruta = str(tmp_path / "test.db")
    database.init_db(ruta)
    return Config("token", "123", [Watch("solana", percent=5)], "eur", 300, ruta, 0)


@pytest.fixture
def fotos(monkeypatch):
    lista = []
    monkeypatch.setattr(
        telegram, "send_photo", lambda t, c, png, pie, **kw: lista.append(pie) or True
    )
    return lista


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

    def pedir(par):
        pedidos.append(par)
        if isinstance(velas, Exception):
            raise velas
        return velas

    monkeypatch.setattr(mayer, "pedir", pedir)
    return pedidos


def test_arcoiris(config, fotos, enviados, monkeypatch):
    # Hoy justo en la curva: la franja de en medio.
    pedidos = _binance(
        monkeypatch, _velas(1500, lambda i: 0 if i == 1499 else _onda(i))
    )

    main.atender(config, _mensaje("/arcoiris"))

    assert pedidos == ["BTCUSDT"]
    pie = fotos[0]
    assert "🌈 <b>Bitcoin en el arcoíris: HODL</b>" in pie
    assert "(+0,0%)" in pie or "(-0,0%)" in pie
    assert "Franja 5 de 9, contando desde abajo." in pie
    assert "Sube a «¿Es una burbuja?» desde $" in pie
    assert "Baja a «Todavía barato» por debajo de $" in pie
    assert "desde 2017" in pie
    assert enviados == []


def test_arcoiris_en_la_de_abajo_no_dice_bajar(config, fotos, monkeypatch):
    _binance(monkeypatch, _velas(1500, lambda i: -0.3 if i == 1499 else _onda(i)))

    main.atender(config, _mensaje("/rainbow btc"))

    assert "Saldo: casi regalado</b>" in fotos[0]
    assert "Baja a" not in fotos[0]


def test_arcoiris_sin_imagen_manda_texto(config, enviados, monkeypatch):
    _binance(monkeypatch, _velas(MINIMO, _onda))

    def falla(*a, **k):
        raise grafica.GraficaError("Falta matplotlib")

    monkeypatch.setattr(grafica, "dibujar_arcoiris", falla)

    main.atender(config, _mensaje("/arcoiris"))

    assert "Bitcoin en el arcoíris" in enviados[0]


def test_arcoiris_solo_bitcoin(config, enviados):
    main.atender(config, _mensaje("/arcoiris eth"))

    assert "solo tiene sentido con bitcoin" in enviados[0]


def test_arcoiris_con_pocos_dias(config, enviados, monkeypatch):
    _binance(monkeypatch, _velas(100))

    main.atender(config, _mensaje("/arcoiris"))

    assert "no me ha dado bastantes días" in enviados[0]


def test_arcoiris_binance_caido(config, enviados, monkeypatch):
    _binance(monkeypatch, mayer.MayerError("Binance no contesta: timeout"))

    main.atender(config, _mensaje("/arcoiris"))

    assert "No he podido mirarlo ahora mismo: Binance no contesta" in enviados[0]
