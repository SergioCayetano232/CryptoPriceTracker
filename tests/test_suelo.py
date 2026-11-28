"""Tests de /suelo."""

from datetime import date, datetime, timezone

import pytest

from crypto_tracker.suelo import SEMANAS, calcular

DIA = 86_400_000
# Un lunes, para que las semanas empiecen justo con la primera vela.
LUNES = int(datetime(2018, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)


def _vela(dia, cierre):
    t = LUNES + dia * DIA
    return [t, "1", "1", "1", str(cierre), "1", t + DIA - 1, "1", 1, "1", "1", "0"]


def _por_semanas(precios):
    """Una semana entera a cada precio."""
    return [_vela(s * 7 + d, p) for s, p in enumerate(precios) for d in range(7)]


def test_plano_da_cero():
    s = calcular(_por_semanas([100] * SEMANAS))

    assert len(s.semanas) == 1
    assert s.hoy.media == pytest.approx(100)
    assert s.hoy.distancia == pytest.approx(0)


def test_la_media_va_corriendo():
    s = calcular(_por_semanas(range(1, 251)))

    assert len(s.semanas) == 51
    # La última: media de 51..250 = 150,5
    assert s.hoy.media == pytest.approx(150.5)
    assert s.hoy.distancia == pytest.approx((250 / 150.5 - 1) * 100)
    assert s.semanas[0].media == pytest.approx(100.5)


def test_la_semana_cierra_el_domingo():
    velas = _por_semanas([100] * (SEMANAS - 1))
    # La última semana va a 100 y el domingo cierra a 300.
    velas += [_vela((SEMANAS - 1) * 7 + d, 300 if d == 6 else 100) for d in range(7)]

    s = calcular(velas)

    assert s.hoy.precio == 300
    assert s.hoy.cuando == date(2021, 10, 31)
    assert s.hoy.media == pytest.approx(101)


def test_la_de_esta_semana_va_con_lo_de_hoy():
    velas = _por_semanas([100] * SEMANAS)
    # Lunes y martes de la siguiente, sin acabar.
    velas += [_vela(SEMANAS * 7, 150), _vela(SEMANAS * 7 + 1, 300)]

    s = calcular(velas)

    assert len(s.semanas) == 2
    assert s.hoy.precio == 300
    assert s.hoy.media == pytest.approx(101)


def test_con_menos_de_200_semanas_no_hay():
    assert calcular(_por_semanas([100] * (SEMANAS - 1))) is None
    assert calcular({"code": -1}) is None
    assert calcular(None) is None


def test_ignora_velas_rotas():
    velas = _por_semanas([100] * SEMANAS)
    velas += [None, ["x"], _vela(9000, "nada"), _vela(9001, 0), [None, 1, 1, 1, 5]]

    assert len(calcular(velas).semanas) == 1


def test_por_debajo_sin_contar_hoy():
    # Media ~100: dos semanas por debajo, una por encima y hoy por debajo.
    s = calcular(_por_semanas([100] * SEMANAS + [80, 90, 130, 70]))

    assert s.por_debajo == 2
    assert s.mas_lejos.precio == 130
    assert s.mas_abajo.precio == 70


def test_lo_que_sube_la_media_en_un_año():
    assert calcular(_por_semanas([100] * (SEMANAS + 51))).sube_al_año is None

    s = calcular(_por_semanas([100] * SEMANAS + [300] * 52))

    # Hace un año la media era 100; ahora 148 a 100 y 52 a 300 → 152.
    assert s.sube_al_año == pytest.approx(52)


@pytest.mark.parametrize(
    "hoy, emoji",
    [(90, "🧊"), (130, "🟢"), (200, "😐"), (350, "🔥"), (600, "🌋")],
)
def test_zona(hoy, emoji):
    # Con 199 semanas a 100, la media casi no se mueve.
    s = calcular(_por_semanas([100] * (SEMANAS - 1) + [hoy]))

    assert s.zona[0] == emoji


# --- el comando ---

import time  # noqa: E402

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


def test_suelo(config, enviados, monkeypatch):
    # 199 semanas a 20.000, luego un año subiendo hasta 60.000.
    precios = [20_000] * 199 + [20_000 + 40_000 * i / 52 for i in range(53)]
    pedidos = _binance(monkeypatch, _por_semanas(precios))

    main.atender(config, _mensaje("/suelo"))

    assert pedidos == ["BTCUSDT"]
    texto = enviados[0]
    assert "🪨 <b>Bitcoin frente a su media de 200 semanas: +" in texto
    assert "Precio: $60.000 · media: $" in texto
    assert "Para tocarla tendría que bajar a $" in texto
    assert "no ha cerrado nunca por debajo" in texto
    assert "La media ha subido un 26% en un año." in texto
    assert "<code>" in texto


def test_suelo_por_debajo(config, enviados, monkeypatch):
    _binance(monkeypatch, _por_semanas([100] * SEMANAS + [80, 90, 130, 70]))

    main.atender(config, _mensaje("/200semanas btc"))

    texto = enviados[0]
    assert "🧊 <b>Por debajo de su media" in texto
    assert "Para tocarla" not in texto
    assert "Para volver a ella tendría que subir a $100 (+" in texto
    assert "ha cerrado por debajo 2 de 4 semanas" in texto


def test_suelo_solo_bitcoin(config, enviados, monkeypatch):
    pedidos = _binance(monkeypatch, [])

    main.atender(config, _mensaje("/suelo eth"))

    assert "va con los ciclos de bitcoin" in enviados[0]
    assert pedidos == []


def test_suelo_con_pocas_semanas(config, enviados, monkeypatch):
    _binance(monkeypatch, _por_semanas([100] * 50))

    main.atender(config, _mensaje("/200w"))

    assert "no me ha dado 200 semanas" in enviados[0]


def test_suelo_binance_caido(config, enviados, monkeypatch):
    _binance(monkeypatch, mayer.MayerError("Binance no contesta: timeout"))

    main.atender(config, _mensaje("/suelo"))

    assert "No he podido mirarlo ahora mismo: Binance no contesta" in enviados[0]
