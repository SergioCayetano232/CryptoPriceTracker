"""Tests de /paciencia."""

import statistics
import time
from datetime import date, datetime, timedelta, timezone

import pytest

from crypto_tracker.paciencia import MINIMO, calcular

DIA = 86_400_000
INICIO = int(datetime(2018, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
PRIMERO = date(2018, 1, 1)


def _vela(dia, cierre):
    t = INICIO + dia * DIA
    return [t, "1", "1", "1", str(cierre), "1", t + DIA - 1, "1", 1, "1", "1", "0"]


def _velas(precios):
    return [_vela(i, p) for i, p in enumerate(precios)]


def test_subiendo_siempre_se_gana():
    p = calcular(_velas([100 + i for i in range(400)]))

    assert [x.nombre for x in p.plazos] == ["1 mes", "6 meses", "1 año"]
    for plazo in p.plazos:
        assert plazo.ganaba == 100
    un_mes = p.plazos[0]
    assert len(un_mes.compras) == 370
    assert un_mes.compras[0].cuando == PRIMERO
    assert un_mes.compras[0].cambio == pytest.approx(30)


def test_plano_no_gana_nunca():
    p = calcular(_velas([100] * 100))

    assert p.plazos[0].ganaba == 0
    assert p.plazos[0].mediana == 0


def test_mediana_y_peor():
    # Sube 30 días, baja 30 y vuelve a subir: a un mes hay de todo.
    precios = [100 + i for i in range(30)] + [130 - i for i in range(30)]
    precios += [100 + i for i in range(40)]
    un_mes = calcular(_velas(precios)).plazos[0]

    cambios = sorted(c.cambio for c in un_mes.compras)
    assert un_mes.mediana == pytest.approx(statistics.median(cambios))
    assert un_mes.peor.cambio == cambios[0]
    assert un_mes.peor.cuando == PRIMERO + timedelta(days=30)
    assert 0 < un_mes.ganaba < 100


def test_sin_bastantes_compras_no_sale_el_plazo():
    # 30 compras a un mes justas: 60 días. Con uno menos no hay ninguno.
    assert calcular(_velas([100] * (30 + MINIMO))).plazos[0].nombre == "1 mes"
    assert calcular(_velas([100] * (29 + MINIMO))) is None
    assert calcular([]) is None
    assert calcular({"code": -1}) is None


def test_salta_los_huecos_y_lo_roto():
    velas = _velas([100] * 80)
    del velas[40]
    velas += [None, ["x"], _vela(500, "nada"), _vela(501, 0)]

    un_mes = calcular(velas).plazos[0]

    # Sin el día 40 no se puede comprar ese día ni el 10 (que acabaría en él).
    assert len(un_mes.compras) == 48


def test_lo_de_hace_el_plazo_mas_largo():
    p = calcular(_velas([100] * 300 + [300] * 100))

    plazo, compra = p.hace
    assert plazo.nombre == "1 año"
    assert compra.cuando == p.hoy - timedelta(days=365)
    assert compra.cambio == pytest.approx(200)
    assert p.precio == 300


# --- el comando ---

import main  # noqa: E402
from crypto_tracker import mayer  # noqa: E402
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


def test_paciencia_a_secas_es_bitcoin(config, enviados, monkeypatch):
    pedidos = _binance(monkeypatch, _velas([10_000 + 10 * i for i in range(400)]))

    main.atender(config, _mensaje("/paciencia"))

    assert pedidos == ["BTCUSDT"]
    texto = enviados[0]
    assert "⏳ <b>Comprar Bitcoin un día cualquiera y aguantar</b>" in texto
    assert "Cada día desde el 01/01/2018 como día de compra:" in texto
    assert "· 1 mes: ganabas el 100% de las veces (lo típico: +" in texto
    assert "· 1 año: ganabas el 100%" in texto
    assert "2 años" not in texto
    assert "Nadie que aguantara 1 año ha perdido: lo peor fue comprar el " in texto
    assert "Si compraste hace 1 año (" in texto


def test_paciencia_con_perdidas(config, enviados, monkeypatch):
    # Baja todo el rato: aguantar siempre salía mal.
    _binance(monkeypatch, _velas([1000 - i for i in range(100)]))

    main.atender(config, _mensaje("/aguante eth"))

    texto = enviados[0]
    assert "Comprar Ethereum" in texto
    assert "ganabas el 0% de las veces" in texto
    assert "Aguantando 1 mes, lo peor fue comprar el " in texto
    assert ": -" in texto


def test_paciencia_casi_siempre_no_es_100(config, enviados, monkeypatch):
    # Una sola compra perdedora entre más de 200.
    precios = [100] + [50] * 30 + [51 + i for i in range(250)]
    _binance(monkeypatch, _velas(precios))

    main.atender(config, _mensaje("/paciencia"))

    assert "1 mes: ganabas más del 99% de las veces" in enviados[0]


def test_paciencia_de_dos_en_dos(config, enviados):
    main.atender(config, _mensaje("/paciencia btc eth"))

    assert "De una en una" in enviados[0]


def test_paciencia_con_poco(config, enviados, monkeypatch):
    _binance(monkeypatch, _velas([100] * 20))

    main.atender(config, _mensaje("/paciencia"))

    assert "lleva muy poco en Binance" in enviados[0]


def test_paciencia_sin_par(config, enviados, monkeypatch):
    _binance(monkeypatch, mayer.MayerError("sin datos"))

    main.atender(config, _mensaje("/paciencia nada"))

    assert "Binance no tiene <b>nada</b> contra el dólar" in enviados[0]


def test_paciencia_binance_caido(config, enviados, monkeypatch):
    _binance(monkeypatch, mayer.MayerError("Binance no contesta: timeout"))

    main.atender(config, _mensaje("/paciencia"))

    assert "No he podido mirarlo ahora mismo: Binance no contesta" in enviados[0]
