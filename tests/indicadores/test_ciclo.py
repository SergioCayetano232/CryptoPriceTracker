"""Tests de /ciclo."""

import time
from datetime import date

import pytest

from crypto_tracker.indicadores import ciclo
from crypto_tracker.indicadores.ahr999 import Ahr999
from crypto_tracker.indicadores.ahr999 import Dia as DiaAhr
from crypto_tracker.indicadores.ciclo import FONDO, MEDIO, TECHO, veredicto
from crypto_tracker.indicadores.hashribbons import Dia as DiaRibbons
from crypto_tracker.indicadores.hashribbons import Ribbons
from crypto_tracker.indicadores.mayer import Dia as DiaMayer
from crypto_tracker.indicadores.mayer import Mayer
from crypto_tracker.indicadores.mvrv import Dia as DiaMvrv
from crypto_tracker.indicadores.mvrv import Mvrv
from crypto_tracker.indicadores.picycle import Dia as DiaPi
from crypto_tracker.indicadores.picycle import PiCycle
from crypto_tracker.indicadores.semaforo import Voto
from crypto_tracker.indicadores.suelo import Semana, Suelo

HOY = date(2026, 11, 25)


@pytest.mark.parametrize("multiple, valor", [(0.8, 1), (1.5, 0), (2.5, -1)])
def test_mayer(multiple, valor):
    m = Mayer("BTCUSDT", [DiaMayer(HOY, 100, multiple)], 100)

    assert ciclo.de_mayer(m).valor == valor
    assert ciclo.de_mayer(m).nombre == f"Mayer {multiple:.2f}".replace(".", ",")


class _Arcoiris:
    def __init__(self, franja):
        self.franja = franja


@pytest.mark.parametrize("franja, valor", [(0, 1), (3, 1), (4, 0), (5, 0), (6, -1)])
def test_arcoiris(franja, valor):
    assert ciclo.de_arcoiris(_Arcoiris(franja)).valor == valor


@pytest.mark.parametrize(
    "precio, valor, motivo",
    [
        (80, 1, "un 20% por debajo de la media"),
        (130, 1, "un 30% por encima de la media, cerca del suelo"),
        (200, 0, "un 100% por encima de la media"),
        (300, -1, "un 200% por encima de la media, lejos del suelo"),
    ],
)
def test_suelo(precio, valor, motivo):
    voto = ciclo.de_suelo(Suelo([Semana(HOY, precio, 100)]))

    assert (voto.valor, voto.motivo) == (valor, motivo)


@pytest.mark.parametrize("rapida, valor", [(50, 0), (89, 0), (90, -1), (120, -1)])
def test_picycle(rapida, valor):
    assert ciclo.de_picycle(PiCycle([DiaPi(HOY, 1, rapida, 100)])).valor == valor


@pytest.mark.parametrize("indice, valor", [(0.3, 1), (0.8, 0), (1.5, -1)])
def test_ahr999(indice, valor):
    # Con coste y crecimiento a 1, el índice es el precio al cuadrado.
    a = Ahr999([DiaAhr(HOY, indice**0.5, 1, 1)])

    assert ciclo.de_ahr999(a).valor == valor


@pytest.mark.parametrize("z, valor", [(-0.5, 1), (1.9, 1), (3, 0), (5, -1)])
def test_mvrv(z, valor):
    assert ciclo.de_mvrv(Mvrv([DiaMvrv(HOY, 1, 1, z)])).valor == valor


class _Ribbons:
    def __init__(self, estado):
        self.estado = estado


@pytest.mark.parametrize(
    "estado, valor", [("señal", 1), ("capitula", 0), ("cruzando", 0), ("sano", 0)]
)
def test_hashribbons(estado, valor):
    assert ciclo.de_hashribbons(_Ribbons(estado)).valor == valor


def test_hashribbons_de_verdad():
    # Que los estados que lee son los que de verdad da Ribbons.
    r = Ribbons([DiaRibbons(HOY, 1, 1, 1)])

    assert r.estado == "sano"
    assert ciclo.de_hashribbons(r).motivo == "minado sano"


def _votos(*valores):
    return [Voto(str(i), v, "") for i, v in enumerate(valores)]


@pytest.mark.parametrize(
    "valores, esperado",
    [
        ((1, 1, 0), FONDO),
        ((1, 1, -1), MEDIO),
        ((1, 1, 1, -1), FONDO),
        ((-1, -1, 0, 0), TECHO),
        ((0, 0, 0, 0), MEDIO),
        ((1, 1), MEDIO),  # con dos no hay bastantes
    ],
)
def test_veredicto(valores, esperado):
    assert veredicto(_votos(*valores)) == esperado


# --- el comando ---

import main  # noqa: E402
from crypto_tracker.indicadores import arcoiris, hashribbons, mayer, mvrv  # noqa: E402
from crypto_tracker.nucleo import database, telegram  # noqa: E402
from crypto_tracker.nucleo.config import Config, Watch  # noqa: E402

DIA = 86_400_000
INICIO = 1_500_000_000_000


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


def _velas(precios):
    return [
        [INICIO + i * DIA, "1", "1", "1", str(p), "1", 0, "1", 1, "1", "1", "0"]
        for i, p in enumerate(precios)
    ]


def _fuentes(monkeypatch, velas, de_mvrv, de_ribbons):
    def lanza_o_da(valor):
        def pedir(*a):
            if isinstance(valor, Exception):
                raise valor
            return valor

        return pedir

    monkeypatch.setattr(mayer, "pedir", lanza_o_da(velas))
    monkeypatch.setattr(mvrv, "pedir", lambda: [])
    monkeypatch.setattr(mvrv, "leer", lanza_o_da(de_mvrv))
    monkeypatch.setattr(hashribbons, "pedir", lambda: {})
    monkeypatch.setattr(hashribbons, "leer", lanza_o_da(de_ribbons))


def test_ciclo_todos(config, enviados, monkeypatch):
    # Dos años subiendo poco a poco y luego un bajón: Mayer y 200 semanas, baratos.
    precios = [10_000 + 10 * i for i in range(1500)] + [12_000] * 30
    _fuentes(
        monkeypatch,
        _velas(precios),
        Mvrv([DiaMvrv(HOY, 1, 1, 0.5)]),
        Ribbons([DiaRibbons(HOY, 1, 1, 1)]),
    )

    main.atender(config, _mensaje("/ciclo"))

    texto = enviados[0]
    assert "🟢 <b>Bitcoin, cerca de un fondo de ciclo</b>" in texto
    for nombre in ("Mayer", "Arcoíris", "200 semanas", "Pi Cycle", "ahr999"):
        assert f"<b>{nombre}" in texto
    assert "🟢 <b>MVRV Z 0,50</b>" in texto
    assert "⚪ <b>Hash ribbons</b>: minado sano" in texto
    assert "Sin datos de" not in texto


def test_ciclo_sin_binance_sigue_con_los_demas(config, enviados, monkeypatch):
    _fuentes(
        monkeypatch,
        mayer.MayerError("Binance no contesta"),
        Mvrv([DiaMvrv(HOY, 1, 1, 6)]),
        Ribbons([DiaRibbons(HOY, 1, 1, 1)]),
    )

    main.atender(config, _mensaje("/ciclos"))

    texto = enviados[0]
    assert "🟡 <b>Bitcoin, a mitad de ciclo</b>" in texto
    assert "🔴 <b>MVRV Z 6,00</b>" in texto
    assert "Sin datos de Mayer, arcoíris, 200 semanas, Pi Cycle, ahr999" in texto


def test_ciclo_con_pocas_velas_faltan_las_largas(config, enviados, monkeypatch):
    # 250 días: hay Mayer y ahr999, pero no arcoíris, 200 semanas ni Pi Cycle.
    _fuentes(
        monkeypatch,
        _velas([100] * 250),
        mvrv.MvrvError("CoinMetrics no contesta"),
        hashribbons.HashRibbonsError("mempool.space no contesta"),
    )

    main.atender(config, _mensaje("/ciclo"))

    texto = enviados[0]
    assert "<b>Mayer 1,00</b>" in texto
    assert "<b>ahr999" in texto
    assert "Sin datos de arcoíris, 200 semanas, Pi Cycle, MVRV, hash ribbons" in texto
    assert arcoiris.calcular(_velas([100] * 250)) is None


def test_ciclo_sin_nada(config, enviados, monkeypatch):
    _fuentes(
        monkeypatch,
        mayer.MayerError("x"),
        mvrv.MvrvError("x"),
        hashribbons.HashRibbonsError("x"),
    )

    main.atender(config, _mensaje("/ciclo"))

    assert "No he podido mirar ninguno ahora mismo" in enviados[0]


def test_ciclo_solo_bitcoin(config, enviados):
    main.atender(config, _mensaje("/ciclo eth"))

    assert "Los indicadores de ciclo son de bitcoin" in enviados[0]
