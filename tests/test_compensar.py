"""Tests de /compensar: qué vender y cuánto te ahorras."""

from datetime import date, datetime, timezone

import pytest

import main
from crypto_tracker import coingecko, database, fifo
from crypto_tracker.alerts import formatear_compensar
from crypto_tracker.compensar import Compensacion, Venta, calcular
from crypto_tracker.config import Config, Posicion, Watch
from crypto_tracker.fifo import Lote
from crypto_tracker.impuestos import Impuestos, por_tramos
from crypto_tracker.movimientos import Movimiento

HOY = date(2026, 11, 9)


def _año(ganancia, sin_datos=0):
    return Impuestos(2026, ganancia, por_tramos(ganancia), sin_datos, 1)


def test_con_una_que_llega_vende_solo_lo_justo():
    # cada una costó 100 y vale 50: para perder 300 hacen falta 6
    c = calcular(_año(300), {"solana": [Lote(10, 1000)]}, {"solana": 50.0})

    assert len(c.ventas) == 1
    assert c.ventas[0].cantidad == pytest.approx(6)
    assert c.ventas[0].perdida == pytest.approx(300)
    assert c.ventas[0].todo is False
    assert c.queda == pytest.approx(0)


def test_si_no_llega_la_vende_toda():
    c = calcular(_año(5000), {"solana": [Lote(10, 1000)]}, {"solana": 50.0})

    assert c.ventas[0].cantidad == pytest.approx(10)
    assert c.ventas[0].perdida == pytest.approx(500)
    assert c.ventas[0].todo is True
    assert c.queda == pytest.approx(4500)


def test_empieza_por_la_que_mas_pierde():
    lotes = {"solana": [Lote(1, 200)], "cardano": [Lote(1, 1000)]}
    precios = {"solana": 100.0, "cardano": 100.0}

    c = calcular(_año(950), lotes, precios)

    assert [v.coin_id for v in c.ventas] == ["cardano", "solana"]
    assert [v.perdida for v in c.ventas] == [pytest.approx(900), pytest.approx(50)]


def test_no_vende_lo_que_no_hace_falta():
    lotes = {"solana": [Lote(1, 200)], "cardano": [Lote(1, 1000)]}
    precios = {"solana": 100.0, "cardano": 100.0}

    c = calcular(_año(500), lotes, precios)

    assert [v.coin_id for v in c.ventas] == ["cardano"]


def test_las_que_ganan_no_salen():
    c = calcular(_año(300), {"bitcoin": [Lote(1, 100)]}, {"bitcoin": 500.0})

    assert c.ventas == []
    assert c.ahorro == 0


def test_para_llegar_al_lote_malo_hay_que_vender_el_bueno():
    # el viejo gana 100 y el nuevo pierde 400: en neto se pierden 300
    lotes = {"bitcoin": [Lote(1, 100), Lote(1, 600)]}

    c = calcular(_año(5000), lotes, {"bitcoin": 200.0})

    assert c.ventas[0].cantidad == pytest.approx(2)
    assert c.ventas[0].perdida == pytest.approx(300)


def test_si_el_viejo_gana_mas_de_lo_que_pierde_el_nuevo_no_compensa():
    lotes = {"bitcoin": [Lote(1, 100), Lote(1, 250)]}

    c = calcular(_año(5000), lotes, {"bitcoin": 200.0})

    assert c.ventas == []


def test_se_para_en_lo_mejor_aunque_haya_mas_lotes():
    # pierde 300 con el primero y el segundo lo devolvería todo
    lotes = {"bitcoin": [Lote(1, 600), Lote(1, 0)]}

    c = calcular(_año(5000), lotes, {"bitcoin": 300.0})

    assert c.ventas[0].cantidad == pytest.approx(1)
    assert c.ventas[0].perdida == pytest.approx(300)
    assert c.ventas[0].todo is False


def test_con_el_acumulado_a_favor_afina_dentro_del_lote():
    # el viejo gana 100; del nuevo (pierde 400) hay que sacar lo que deje -200
    lotes = {"bitcoin": [Lote(1, 100), Lote(1, 600)]}

    c = calcular(_año(200), lotes, {"bitcoin": 200.0})

    assert c.ventas[0].cantidad == pytest.approx(1.75)
    assert c.ventas[0].perdida == pytest.approx(200)


def test_un_lote_sin_precio_corta_y_se_avisa():
    lotes = {"bitcoin": [Lote(1, None), Lote(1, 600)]}

    c = calcular(_año(300), lotes, {"bitcoin": 200.0})

    assert c.ventas == []
    assert c.sin_mirar == ["bitcoin"]


def test_sin_precio_se_avisa():
    c = calcular(_año(300), {"solana": [Lote(1, 200)]}, {})

    assert c.ventas == []
    assert c.sin_mirar == ["solana"]


def test_sin_ganancia_no_propone_nada():
    c = calcular(_año(-100), {"solana": [Lote(1, 200)]}, {"solana": 100.0})

    assert c.ventas == []


def test_ahorro_entre_dos_tramos():
    # de 7.000 a 5.000: 1.000 al 21% y 1.000 al 19%
    c = calcular(_año(7000), {"solana": [Lote(1, 2100)]}, {"solana": 100.0})

    assert c.ahorro == pytest.approx(210 + 190)


def test_fifo_lotes_de_la_cartera():
    cuando = datetime(2026, 1, 1, tzinfo=timezone.utc)
    historia = [
        Movimiento(1, "bitcoin", "compra", 1, 100, None, cuando),
        Movimiento(2, "bitcoin", "compra", 1, 300, Posicion("bitcoin", 1, 100), cuando),
    ]
    cartera = (Posicion("bitcoin", 2, 400), Posicion("solana", 3, 30))

    assert fifo.lotes(historia, cartera) == {
        "bitcoin": [Lote(1, 100), Lote(1, 300)],
        "solana": [Lote(3, 30)],
    }


def _texto(ganancia, ventas, sin_mirar=(), sin_datos=0, moneda="eur"):
    c = Compensacion(2026, ganancia, list(ventas), list(sin_mirar), sin_datos)
    return formatear_compensar(c, moneda, HOY)


VENTA = Venta("solana", 6, 300, 50.0, False)


def test_el_texto_dice_cuanto_vender_y_cuanto_ahorras():
    texto = _texto(300, [VENTA])

    assert "<b>Solana</b>: vende 6" in texto
    assert "€50,00" in texto
    assert "pierdes €300,00" in texto
    assert "ahorrarías unos <b>€57,00</b>" in texto
    assert "quedan 53 días" in texto


def test_el_texto_con_todo():
    assert "vende todo" in _texto(300, [Venta("solana", 6, 300, 50.0, True)])


def test_el_texto_dice_si_sigue_quedando_que_pagar():
    assert "Seguirías tributando por +€200,00" in _texto(500, [VENTA])


def test_el_texto_sin_ganancia():
    assert "nada que compensar" in _texto(-50, [])


def test_el_texto_sin_nada_en_perdidas():
    texto = _texto(300, [])

    assert "de dónde compensar" in texto
    assert "ahorrarías" not in texto


def test_el_texto_avisa_de_lo_que_no_mira():
    texto = _texto(300, [VENTA], sin_mirar=["cardano"], sin_datos=2)

    assert "Cardano" in texto
    assert "No cuento 2 ventas" in texto


def test_el_texto_avisa_de_otra_moneda():
    assert "Hacienda lo quiere en euros" in _texto(300, [VENTA], moneda="usd")


def test_el_ultimo_dia_dice_queda_uno():
    c = Compensacion(2026, 300, [VENTA], [], 0)

    assert "queda 1 día" in formatear_compensar(c, "eur", date(2026, 12, 31))


@pytest.fixture
def config(tmp_path):
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


def _precios(monkeypatch, precios):
    llamadas = []

    def get_prices(ids, moneda):
        llamadas.append(ids)
        return precios

    monkeypatch.setattr(coingecko, "get_prices", get_prices)
    return llamadas


def test_por_comandos_propone_y_no_apunta_nada(config, monkeypatch):
    _precios(monkeypatch, {"bitcoin": 200.0, "solana": 50.0})
    main.responder(config, "compra", "btc 1 100")
    main.responder(config, "venta", "btc 1 500")  # +400
    main.responder(config, "compra", "sol 10 1000")

    texto = main.responder(config, "compensar", "")

    assert "Llevas ganado vendiendo <b>+€400,00</b>" in texto
    assert "<b>Solana</b>: vende 8" in texto
    assert len(database.get_movimientos(config.database_path, None)) == 3


def test_sin_ganancia_no_gasta_consulta(config, monkeypatch):
    llamadas = _precios(monkeypatch, {})

    texto = main.responder(config, "compensar", "")

    assert "nada que compensar" in texto
    assert llamadas == []


def test_si_no_hay_precios_lo_dice(config, monkeypatch):
    _precios(monkeypatch, {"bitcoin": 200.0, "solana": 50.0})
    main.responder(config, "compra", "btc 1 100")
    main.responder(config, "venta", "btc 0.5 500")

    def falla(*a, **k):
        raise coingecko.CoinGeckoError("sin red")

    monkeypatch.setattr(coingecko, "get_prices", falla)

    assert "No he podido" in main.responder(config, "compensar", "")
