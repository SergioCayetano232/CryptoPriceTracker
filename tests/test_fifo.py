"""Tests de FIFO: que lo que se vende sea lo primero que se compró."""

from datetime import datetime, timezone

import pytest

import main
from crypto_tracker import coingecko, database, fifo, impuestos, sivendo
from crypto_tracker.config import Config, Posicion, Watch
from crypto_tracker.movimientos import Movimiento

CUANDO = datetime(2026, 6, 1, tzinfo=timezone.utc)


def _pos(cantidad, invertido, coin="bitcoin"):
    return Posicion(coin, cantidad, invertido)


def _mov(id, tipo, cantidad, coste, antes, coin="bitcoin", cuando=CUANDO):
    return Movimiento(id, coin, tipo, cantidad, coste, antes, cuando)


# 1 a 100 y luego 1 a 300: el precio medio diría 200 y FIFO, 100.
HISTORIA = [
    _mov(1, "compra", 1, 100, None),
    _mov(2, "compra", 1, 300, _pos(1, 100)),
]


def _costes(movimientos):
    return [coste for _, coste in fifo.ventas(movimientos)]


def test_vende_primero_lo_mas_viejo():
    venta = _mov(3, "venta", 1, 400, _pos(2, 400))

    assert _costes([*HISTORIA, venta]) == [pytest.approx(100)]


def test_una_venta_que_coge_dos_lotes():
    venta = _mov(3, "venta", 1.5, 600, _pos(2, 400))

    assert _costes([*HISTORIA, venta]) == [pytest.approx(100 + 150)]


def test_un_lote_a_medias_sigue_con_lo_que_le_queda():
    ventas = [
        _mov(3, "venta", 0.5, 200, _pos(2, 400)),
        _mov(4, "venta", 1, 400, _pos(1.5, 300)),
    ]

    assert _costes([*HISTORIA, *ventas]) == [
        pytest.approx(50),
        pytest.approx(50 + 150),
    ]


def test_da_igual_el_orden_en_que_lleguen():
    venta = _mov(3, "venta", 1, 400, _pos(2, 400))

    # get_movimientos los da del más nuevo al más viejo
    assert _costes([venta, *reversed(HISTORIA)]) == [pytest.approx(100)]


def test_cada_cripto_lleva_sus_lotes():
    otra = _mov(3, "compra", 1, 5, None, coin="ethereum")
    venta = _mov(4, "venta", 1, 400, _pos(2, 400))

    assert _costes([*HISTORIA, otra, venta]) == [pytest.approx(100)]


def test_lo_del_env_es_el_lote_mas_viejo():
    historia = [
        _mov(1, "compra", 1, 300, _pos(1, 100)),
        _mov(2, "venta", 1, 400, _pos(2, 400)),
    ]

    assert _costes(historia) == [pytest.approx(100)]


def test_una_recompensa_entra_con_lo_que_valia():
    historia = [
        _mov(1, "recompensa", 1, 50, None),
        _mov(2, "compra", 1, 300, _pos(1, 50)),
        _mov(3, "venta", 1, 400, _pos(2, 350)),
    ]

    assert _costes(historia) == [pytest.approx(50)]


def test_una_compra_a_cero_no_es_no_saberlo():
    historia = [
        _mov(1, "compra", 1, 0, None),
        _mov(2, "venta", 1, 400, _pos(1, 0)),
    ]

    assert _costes(historia) == [0]


def test_sin_saber_lo_que_costo_lo_vendido_no_hay_coste():
    historia = [
        _mov(1, "compra", 1, None, None),
        _mov(2, "compra", 1, 300, _pos(1, None)),
        _mov(3, "venta", 1, 400, _pos(2, None)),
    ]

    assert _costes(historia) == [None]


def test_lo_que_no_se_sabe_no_mancha_el_lote_siguiente():
    historia = [
        _mov(1, "compra", 1, None, None),
        _mov(2, "compra", 1, 300, _pos(1, None)),
        _mov(3, "venta", 1, 400, _pos(2, None)),
        _mov(4, "venta", 1, 400, _pos(1, None)),
    ]

    assert _costes(historia) == [None, pytest.approx(300)]


def test_un_lote_sin_precio_a_medias_sigue_sin_precio():
    historia = [
        _mov(1, "compra", 1, None, None),
        _mov(2, "venta", 0.5, 400, _pos(1, None)),
        _mov(3, "venta", 0.5, 400, _pos(0.5, None)),
    ]

    assert _costes(historia) == [None, None]


def test_si_lo_tocaste_a_mano_manda_lo_que_habia():
    venta = _mov(3, "venta", 1, 400, _pos(5, 1000))

    assert _costes([*HISTORIA, venta]) == [pytest.approx(200)]


def test_vender_sin_tener_nada_no_tiene_coste():
    assert _costes([_mov(1, "venta", 1, 400, None)]) == [None]


def test_los_decimales_no_dejan_lotes_fantasma():
    historia = [
        _mov(1, "compra", 0.1, 10, None),
        _mov(2, "compra", 0.2, 30, _pos(0.1, 10)),
        _mov(3, "venta", 0.3, 50, _pos(0.1 + 0.2, 40)),
        _mov(4, "compra", 1, 500, None),
        _mov(5, "venta", 1, 600, _pos(1, 500)),
    ]

    assert _costes(historia) == [pytest.approx(40), pytest.approx(500)]


def test_coste_de_vender_coge_los_lotes_que_quedan():
    assert fifo.coste_de_vender(HISTORIA, _pos(2, 400), 1) == pytest.approx(100)
    assert fifo.coste_de_vender(HISTORIA, _pos(2, 400), 2) == pytest.approx(400)


def test_coste_de_vender_sin_compras_es_un_solo_lote():
    assert fifo.coste_de_vender([], _pos(2, 400), 1) == pytest.approx(200)


def test_coste_de_vender_no_toca_nada():
    historia = list(HISTORIA)

    fifo.coste_de_vender(historia, _pos(2, 400), 1)

    assert fifo.coste_de_vender(historia, _pos(2, 400), 1) == pytest.approx(100)


def test_impuestos_con_fifo():
    venta = _mov(3, "venta", 1, 400, _pos(2, 400))

    i = impuestos.calcular([*HISTORIA, venta], 2026)

    assert i.ganancia == pytest.approx(300)
    assert i.ventas == 1
    assert i.sin_datos == 0


def test_las_compras_de_otro_año_cuentan_para_el_coste():
    viejas = [
        _mov(
            1, "compra", 1, 100, None, cuando=datetime(2024, 1, 1, tzinfo=timezone.utc)
        ),
        _mov(
            2,
            "venta",
            0.5,
            100,
            _pos(1, 100),
            cuando=datetime(2025, 1, 1, tzinfo=timezone.utc),
        ),
        _mov(3, "venta", 0.5, 300, _pos(0.5, 50)),
    ]

    i = impuestos.calcular(viejas, 2026)

    assert i.ganancia == pytest.approx(250)
    assert i.ventas == 1


def test_impuestos_no_cuenta_lo_que_no_se_sabe():
    historia = [
        _mov(1, "compra", 1, None, None),
        _mov(2, "venta", 1, 400, _pos(1, None)),
        _mov(3, "compra", 1, 100, None),
        _mov(4, "venta", 1, None, _pos(1, 100)),
    ]

    i = impuestos.calcular(historia, 2026)

    assert i.ganancia == 0
    assert (i.ventas, i.sin_datos) == (2, 2)


def test_sivendo_con_fifo():
    este_año = impuestos.calcular([], 2026)

    s = sivendo.calcular(_pos(2, 400), 1, 400, _pos(1, 200), este_año, HISTORIA)

    assert s.coste == pytest.approx(100)
    assert s.ganancia == pytest.approx(300)


@pytest.fixture
def config(tmp_path, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: {"bitcoin": 200.0})
    ruta = str(tmp_path / "test.db")
    database.init_db(ruta)
    return Config(
        telegram_token="token",
        telegram_chat_id="123",
        watchlist=[Watch("bitcoin", percent=5)],
        vs_currency="eur",
        check_interval=300,
        database_path=ruta,
        history_days=0,
    )


def test_el_ciclo_entero_por_comandos(config):
    main.responder(config, "compra", "btc 1 100")
    main.responder(config, "compra", "btc 1 300")

    # con precio medio serían 200 de coste y 200 de ganancia
    simulado = main.responder(config, "sivendo", "btc 1 400")
    assert "Te costó €100,00" in simulado

    main.responder(config, "venta", "btc 1 400")
    assert "€300,00" in main.responder(config, "impuestos", "")

    # lo que queda es el lote de 300
    assert "Te costó €300,00" in main.responder(config, "sivendo", "btc 1 400")

    database.deshacer_ultimo(config.database_path)
    assert "no has vendido nada" in main.responder(config, "impuestos", "")
