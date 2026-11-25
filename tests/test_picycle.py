"""Tests de /picycle."""

import time

import pytest

from crypto_tracker.picycle import LENTA, calcular

DIA = 86_400_000
INICIO = 1_500_000_000_000


def _vela(dia, cierre):
    t = INICIO + dia * DIA
    return [t, "1", "1", "1", str(cierre), "1", t + DIA - 1, "1", 1, "1", "1", "0"]


def _velas(precios):
    return [_vela(i, p) for i, p in enumerate(precios)]


def _cruce():
    """Plano a 100 y luego una subida que mete la rápida por encima."""
    return [100.0] * 400 + [100.0 * 1.04**i for i in range(80)]


def test_plano_esta_a_la_mitad():
    p = calcular(_velas([100] * 400))

    assert len(p.dias) == 51
    assert p.hoy.rapida == pytest.approx(100)
    assert p.hoy.lenta == pytest.approx(200)
    assert p.hoy.ratio == pytest.approx(0.5)
    assert p.falta == pytest.approx(100)


def test_las_medias_van_corriendo():
    precios = [float(i) for i in range(1, 501)]
    p = calcular(_velas(precios))

    # La de 111: media de 390..500 = 445. La de 350: 151..500 = 325,5, por dos.
    assert p.hoy.rapida == pytest.approx(445)
    assert p.hoy.lenta == pytest.approx(651)
    assert p.dias[0].rapida == pytest.approx(295)
    assert p.dias[0].lenta == pytest.approx(351)


def test_con_menos_de_350_dias_no_hay():
    assert calcular(_velas([100] * (LENTA - 1))) is None
    assert calcular({"code": -1}) is None


def test_ignora_velas_rotas_y_repetidas():
    velas = _velas([100] * LENTA)
    velas += [None, ["x"], _vela(900, "nada"), _vela(901, 0), _vela(10, 100)]

    assert len(calcular(velas).dias) == 1


def test_sin_cruces():
    assert calcular(_velas([100] * 400)).cruces == []


def test_el_cruce_y_su_maximo():
    precios = _cruce() + [50.0] * 40
    p = calcular(_velas(precios))

    cruces = p.cruces
    assert len(cruces) == 1
    assert cruces[0].dia.ratio >= 1
    # El máximo es el último día de la subida, si cae en los 30 de después.
    dias = (cruces[0].maximo.cuando - cruces[0].dia.cuando).days
    assert 0 <= dias <= 30
    assert cruces[0].maximo.precio == max(
        d.precio for d in p.dias[p.dias.index(cruces[0].dia) :][:31]
    )


def test_volver_a_bajar_no_es_otro_cruce():
    p = calcular(_velas(_cruce() + [50.0] * 200))

    assert len(p.cruces) == 1
    assert p.hoy.ratio < 1


@pytest.mark.parametrize(
    "ratio, emoji",
    [(0.5, "🧊"), (0.8, "🟡"), (0.95, "🔥"), (1.2, "🚨")],
)
def test_zona(ratio, emoji):
    # 349 días a 100 y el último justo al precio que deja las medias en ese ratio.
    ultimo = (2 * ratio * 34_900 / 350 - 11_000 / 111) / (1 / 111 - 2 * ratio / 350)
    p = calcular(_velas([100] * 349 + [ultimo]))

    assert p.hoy.ratio == pytest.approx(ratio, rel=0.01)
    assert p.zona[0] == emoji


# --- el comando ---

import main  # noqa: E402
from crypto_tracker import database, mayer, telegram  # noqa: E402
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

    def pedir(par):
        pedidos.append(par)
        if isinstance(velas, Exception):
            raise velas
        return velas

    monkeypatch.setattr(mayer, "pedir", pedir)
    return pedidos


def test_picycle_lejos(config, enviados, monkeypatch):
    pedidos = _binance(monkeypatch, _velas([100] * 400))

    main.atender(config, _mensaje("/picycle"))

    assert pedidos == ["BTCUSDT"]
    texto = enviados[0]
    assert "🥧 <b>Pi Cycle Top de bitcoin</b>" in texto
    assert "Media de 111 días: $100 · el doble de la de 350: $200" in texto
    assert "🧊 <b>Lejos del techo" in texto
    assert "La rápida está al 50% de la otra: le falta subir un 100%" in texto
    assert "no se han cruzado nunca" in texto


def test_picycle_con_cruce(config, enviados, monkeypatch):
    _binance(monkeypatch, _velas(_cruce() + [50.0] * 200))

    main.atender(config, _mensaje("/techo btc"))

    texto = enviados[0]
    assert "se han cruzado una vez:" in texto
    assert "con bitcoin a $" in texto
    assert "el máximo llegó" in texto or "ahí fue el máximo" in texto


def test_picycle_cruzadas_hoy(config, enviados, monkeypatch):
    _binance(monkeypatch, _velas(_cruce()))

    main.atender(config, _mensaje("/pi"))

    assert "🚨 <b>Cruzadas" in enviados[0]
    assert "le falta subir" not in enviados[0]


def test_picycle_solo_bitcoin(config, enviados, monkeypatch):
    pedidos = _binance(monkeypatch, [])

    main.atender(config, _mensaje("/picycle eth"))

    assert "se pensó para los techos de bitcoin" in enviados[0]
    assert pedidos == []


def test_picycle_con_pocos_dias(config, enviados, monkeypatch):
    _binance(monkeypatch, _velas([100] * 100))

    main.atender(config, _mensaje("/picycle"))

    assert "no me ha dado 350 días" in enviados[0]


def test_picycle_binance_caido(config, enviados, monkeypatch):
    _binance(monkeypatch, mayer.MayerError("Binance no contesta: timeout"))

    main.atender(config, _mensaje("/picycle"))

    assert "No he podido mirarlo ahora mismo: Binance no contesta" in enviados[0]
