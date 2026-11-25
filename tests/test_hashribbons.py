"""Tests de /hashribbons."""

import time
from datetime import date, timedelta

import pytest

from crypto_tracker import hashribbons
from crypto_tracker.hashribbons import LARGA, MINIMO, leer

INICIO = 1_735_689_600  # 1/1/2025
PRIMERO = date(2025, 1, 1)


def _datos(potencias):
    return {
        "hashrates": [
            {"timestamp": INICIO + i * 86_400, "avgHashrate": p * 1e18}
            for i, p in enumerate(potencias)
        ]
    }


def test_plano_esta_sano():
    r = leer(_datos([100] * 100))

    assert len(r.dias) == 41
    assert r.hoy.corta == pytest.approx(100)
    assert r.hoy.larga == pytest.approx(100)
    assert r.hoy.capitula is False
    assert r.capitulaciones == []
    assert r.estado == "sano"


def test_las_medias():
    r = leer(_datos(range(1, 61)))

    # 30 días: 31..60 = 45,5. 60 días: 1..60 = 30,5.
    assert r.hoy.corta == pytest.approx(45.5)
    assert r.hoy.larga == pytest.approx(30.5)
    assert r.hoy.potencia == 60
    assert r.hoy.distancia == pytest.approx((45.5 / 30.5 - 1) * 100)


def test_con_menos_de_60_dias_no_hay():
    assert leer(_datos([100] * (LARGA - 1))) is None
    assert leer({}) is None
    assert leer([]) is None


def test_ignora_lo_roto():
    datos = _datos([100] * LARGA)
    datos["hashrates"] += [
        None,
        {},
        {"timestamp": "x", "avgHashrate": 1},
        {"timestamp": INICIO + 99 * 86_400, "avgHashrate": 0},
    ]

    assert len(leer(datos).dias) == 1


def test_capitulando():
    r = leer(_datos([100] * 100 + [80] * 20))

    c = r.capitulaciones[-1]
    assert r.estado == "capitula"
    assert c.hasta is None
    assert c.desde == PRIMERO + timedelta(days=100)
    assert c.dias(r.hoy.cuando) == 20
    assert r.pasadas == []


def test_recien_cruzadas():
    r = leer(_datos([100] * 100 + [80] * (MINIMO - 2)))

    assert r.estado == "cruzando"


def test_al_acabar_es_señal_y_luego_sano():
    bajada = [100] * 100 + [80] * 20
    r = leer(_datos(bajada + [150] * 20))

    assert r.estado == "señal"
    assert len(r.pasadas) == 1
    assert r.pasadas[0].desde == PRIMERO + timedelta(days=100)
    assert r.pasadas[0].dias(r.pasadas[0].hasta) >= 20

    assert leer(_datos(bajada + [150] * 80)).estado == "sano"


def test_junta_las_que_se_separan_poco():
    # Dos caídas con tres días buenos en medio: una sola capitulación.
    potencias = [100] * 100 + [80] * 10 + [400] * 1 + [70] * 10 + [300] * 60

    r = leer(_datos(potencias))

    assert len(r.pasadas) == 1


def test_no_cuenta_los_cruces_cortos():
    # Un bajón de dos días que se recupera enseguida.
    r = leer(_datos([100] * 100 + [60] * 2 + [200] * 60))

    assert r.pasadas == []
    assert r.estado == "sano"


# --- el comando ---

import main  # noqa: E402
from crypto_tracker import database, telegram  # noqa: E402
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


def _mempool(monkeypatch, datos):
    def pedir():
        if isinstance(datos, Exception):
            raise datos
        return datos

    monkeypatch.setattr(hashribbons, "pedir", pedir)


def test_hashribbons_sano(config, enviados, monkeypatch):
    _mempool(monkeypatch, _datos([1000] * 100))

    main.atender(config, _mensaje("/hashribbons"))

    texto = enviados[0]
    assert "⛏️ <b>Hash ribbons de bitcoin</b>" in texto
    assert "Hashrate de 30 días: 1.000 EH/s · de 60 días: 1.000 EH/s (+0,0%)" in texto
    assert "⚪ <b>Minado sano</b>" in texto
    assert "han capitulado" not in texto


def test_hashribbons_capitulando(config, enviados, monkeypatch):
    _mempool(monkeypatch, _datos([100] * 100 + [80] * 20))

    main.atender(config, _mensaje("/mineros"))

    assert "🔴 <b>Los mineros están capitulando</b>" in enviados[0]
    assert "Desde el 11/04/2025 (20 días)" in enviados[0]


def test_hashribbons_cruzando(config, enviados, monkeypatch):
    _mempool(monkeypatch, _datos([100] * 100 + [80] * 3))

    main.atender(config, _mensaje("/ribbons"))

    assert "🟡 <b>Las medias se acaban de cruzar a la baja</b>" in enviados[0]


def test_hashribbons_señal(config, enviados, monkeypatch):
    _mempool(monkeypatch, _datos([100] * 100 + [80] * 20 + [150] * 20))

    main.atender(config, _mensaje("/capitulación"))

    texto = enviados[0]
    assert "🟢 <b>Se acabó la capitulación: señal de compra</b>" in texto
    assert "Desde 2025 han capitulado una vez:" in texto
    assert "· del 11/04/2025 al " in texto


def test_hashribbons_muchas_enseña_las_ultimas(config, enviados, monkeypatch):
    potencias = [100] * 100
    for _ in range(5):
        potencias += [60] * 20 + [300] * 70
    _mempool(monkeypatch, _datos(potencias))

    main.atender(config, _mensaje("/hashribbons"))

    assert "han capitulado 5 veces. Las últimas:" in enviados[0]
    assert enviados[0].count("· del ") == 4


def test_hashribbons_sin_datos(config, enviados, monkeypatch):
    _mempool(monkeypatch, {})

    main.atender(config, _mensaje("/hashribbons"))

    assert "no me ha dado 60 días de hashrate" in enviados[0]


def test_hashribbons_mempool_caido(config, enviados, monkeypatch):
    _mempool(monkeypatch, hashribbons.HashRibbonsError("mempool.space no contesta"))

    main.atender(config, _mensaje("/hashribbons"))

    assert "No he podido mirarlo ahora mismo: mempool.space no contesta" in enviados[0]
