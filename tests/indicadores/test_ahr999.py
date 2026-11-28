"""Tests de /ahr999."""

import math
import time
from datetime import date, datetime, timezone

import pytest

from crypto_tracker.indicadores.ahr999 import DIAS, calcular, crecimiento

DIA = 86_400_000
INICIO = int(datetime(2020, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)


def _vela(dia, cierre):
    t = INICIO + dia * DIA
    return [t, "1", "1", "1", str(cierre), "1", t + DIA - 1, "1", 1, "1", "1", "0"]


def _velas(precios):
    return [_vela(i, p) for i, p in enumerate(precios)]


def test_la_curva_de_crecimiento():
    # 4.000 días desde el génesis: 10^(5,84 · log10(4000) - 17,01)
    cuando = date(2019, 12, 17)
    assert (cuando - date(2009, 1, 3)).days == 4000
    assert crecimiento(cuando) == pytest.approx(10 ** (5.84 * math.log10(4000) - 17.01))


def test_plano_es_precio_entre_curva():
    a = calcular(_velas([10_000] * DIAS))

    hoy = a.hoy
    assert len(a.dias) == 1
    assert hoy.coste == pytest.approx(10_000)
    assert hoy.indice == pytest.approx(10_000 / hoy.crecimiento)


def test_el_coste_es_la_media_geometrica():
    # La mitad a 100 y la mitad a 400: la geométrica es 200, no 250.
    a = calcular(_velas([100] * 100 + [400] * 100))

    assert a.hoy.coste == pytest.approx(200)
    assert a.hoy.indice == pytest.approx(400 / 200 * 400 / a.hoy.crecimiento)


def test_la_media_va_corriendo():
    a = calcular(_velas([100] * 200 + [400] * 200))

    assert len(a.dias) == 201
    assert a.dias[0].coste == pytest.approx(100)
    assert a.hoy.coste == pytest.approx(400)


def test_precio_para_un_indice():
    hoy = calcular(_velas([10_000] * DIAS)).hoy

    precio = hoy.precio_para(0.45)
    assert (precio / hoy.coste) * (precio / hoy.crecimiento) == pytest.approx(0.45)


def test_con_menos_de_200_dias_no_hay():
    assert calcular(_velas([100] * (DIAS - 1))) is None
    assert calcular({"code": -1}) is None


def test_ignora_velas_rotas():
    velas = _velas([100] * DIAS)
    velas += [None, ["x"], _vela(900, "nada"), _vela(901, 0), _vela(902, "inf")]

    assert len(calcular(velas).dias) == 1


def test_mas_bajos_y_minimo():
    a = calcular(_velas([10_000] * DIAS + [5_000, 20_000, 8_000]))

    assert a.minimo.precio == 5_000
    assert a.mas_bajos == 1
    assert a.por_debajo == pytest.approx(25)


def _hasta(indice, dias=DIAS):
    """Velas planas al precio que da ese índice el último día."""
    cuando = datetime.fromtimestamp((INICIO + (dias - 1) * DIA) / 1000, timezone.utc)
    return [indice * crecimiento(cuando.date())] * dias


@pytest.mark.parametrize("indice, emoji", [(0.3, "🟢"), (0.8, "🔵"), (2.0, "🟠")])
def test_zona(indice, emoji):
    a = calcular(_velas(_hasta(indice)))

    assert a.hoy.indice == pytest.approx(indice, rel=0.01)
    assert a.zona[0] == emoji


def test_la_ultima_vez_salta_la_racha_de_hoy():
    precios = [100] * DIAS + [100, 1, 1, 100, 100, 1, 1]
    a = calcular(_velas(precios))

    # Hoy está en una racha baja; la anterior es la de los días 201-202.
    antes = a.ultima_vez(a.hoy.indice * 2)
    assert antes.precio == 1
    assert antes.cuando == a.dias[3].cuando
    assert calcular(_velas([100] * DIAS)).ultima_vez(0.0) is None


# --- el comando ---

import main  # noqa: E402
from crypto_tracker.indicadores import mayer  # noqa: E402
from crypto_tracker.nucleo import database, telegram  # noqa: E402
from crypto_tracker.nucleo.config import Config, Watch  # noqa: E402


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


def test_ahr999_comprar_fuerte(config, enviados, monkeypatch):
    pedidos = _binance(monkeypatch, _velas(_hasta(0.3)))

    main.atender(config, _mensaje("/ahr999"))

    assert pedidos == ["BTCUSDT"]
    texto = enviados[0]
    assert "🧮 <b>Índice ahr999 de bitcoin: 0,30</b>" in texto
    assert "🟢 <b>Zona de comprar fuerte" in texto
    assert "coste de comprar a diario 200 días: $" in texto
    assert "(+0,0%)" in texto
    assert "Pasaría a la de DCA por encima de $" in texto
    assert "nunca había estado tan bajo" in texto


def test_ahr999_dca(config, enviados, monkeypatch):
    # En zona de DCA, con un bajón hace meses que la metió en la de comprar.
    precios = _hasta(0.8, 400)
    precios[250:300] = [p / 2 for p in precios[250:300]]
    _binance(monkeypatch, _velas(precios))

    main.atender(config, _mensaje("/ahr btc"))

    texto = enviados[0]
    assert "🔵 <b>Zona de DCA" in texto
    assert "Comprar fuerte: por debajo de $" in texto
    assert "esperar: por encima de $" in texto
    assert "La última vez en zona de comprar fuerte:" in texto
    assert "<code>" in texto


def test_ahr999_esperar(config, enviados, monkeypatch):
    _binance(monkeypatch, _velas(_hasta(2.0)))

    main.atender(config, _mensaje("/ahr999"))

    assert "🟠 <b>Zona de esperar" in enviados[0]
    assert "Volvería a la de DCA por debajo de $" in enviados[0]


def test_ahr999_solo_bitcoin(config, enviados, monkeypatch):
    pedidos = _binance(monkeypatch, [])

    main.atender(config, _mensaje("/ahr999 eth"))

    assert "se pensó solo para bitcoin" in enviados[0]
    assert pedidos == []


def test_ahr999_con_pocos_dias(config, enviados, monkeypatch):
    _binance(monkeypatch, _velas([100] * 50))

    main.atender(config, _mensaje("/ahr999"))

    assert "no me ha dado 200 días" in enviados[0]


def test_ahr999_binance_caido(config, enviados, monkeypatch):
    _binance(monkeypatch, mayer.MayerError("Binance no contesta: timeout"))

    main.atender(config, _mensaje("/ahr999"))

    assert "No he podido mirarlo ahora mismo: Binance no contesta" in enviados[0]
