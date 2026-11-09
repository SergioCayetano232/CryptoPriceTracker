"""Tests de /rellenar: qué se entiende y qué precios entran."""

from datetime import datetime, timedelta, timezone

import pytest
import requests

import main
from crypto_tracker import coingecko, database
from crypto_tracker.config import Config, Watch
from crypto_tracker.rellenar import RellenarError, faltan, interpretar, leer

BASE = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)


def _cada_hora(n, desde=BASE):
    return [(desde + timedelta(hours=i), 100.0 + i) for i in range(n)]


def test_sin_tramo_pide_todo_lo_que_se_guarda():
    assert interpretar("btc", 90) == (["bitcoin"], 90)


def test_con_varias_y_tramo():
    assert interpretar("btc eth 30d", 90) == (["bitcoin", "ethereum"], 30)


def test_a_secas_no_dice_ninguna():
    assert interpretar("", 90) == ([], 90)


def test_solo_el_tramo():
    assert interpretar("30d", 90) == ([], 30)


def test_sin_limite_de_historico_se_queda_en_un_año():
    assert interpretar("btc", 0) == (["bitcoin"], 365)
    assert interpretar("btc", 1000) == (["bitcoin"], 365)


def test_no_pide_mas_de_lo_que_se_guarda():
    with pytest.raises(RellenarError, match="HISTORY_DAYS"):
        interpretar("btc 120d", 90)


def test_ni_menos_de_dos_dias():
    with pytest.raises(RellenarError, match="mínimo"):
        interpretar("btc 12h", 90)


def test_ni_mas_de_un_año():
    with pytest.raises(RellenarError):
        interpretar("btc 500d", 0)


def test_lee_la_respuesta_ordenada_y_en_utc():
    ms = int(BASE.timestamp() * 1000)
    data = {"prices": [[ms + 3_600_000, 2], [ms, 1.5]]}

    assert leer(data) == [
        (BASE, 1.5),
        (BASE + timedelta(hours=1), 2.0),
    ]


@pytest.mark.parametrize(
    "fila", [[1000, None], [1000, 0], [1000, -5], [1000], "raro", [None, 3]]
)
def test_se_salta_las_filas_malas(fila):
    assert leer({"prices": [fila]}) == []


@pytest.mark.parametrize("data", [{}, [], None, {"error": "coin not found"}])
def test_una_respuesta_rara_no_trae_nada(data):
    assert leer(data) == []


def test_sin_nada_guardado_entra_todo():
    bajados = _cada_hora(5)

    assert faltan(bajados, []) == bajados


def test_lo_que_ya_estaba_no_se_duplica():
    # cada 5 min y medio hasta las 13:55, así que las 14:00 también están cubiertas
    guardados = [BASE + timedelta(seconds=330 * i) for i in range(22)]

    assert faltan(_cada_hora(5), guardados) == _cada_hora(5)[3:]


def test_rellena_un_hueco_en_medio():
    guardados = [BASE, BASE + timedelta(hours=1), BASE + timedelta(hours=4)]

    assert [p[0] for p in faltan(_cada_hora(5), guardados)] == [
        BASE + timedelta(hours=2),
        BASE + timedelta(hours=3),
    ]


def test_repetirlo_no_mete_nada_aunque_las_horas_no_caigan_igual():
    primera = _cada_hora(48)
    # la segunda vez CoinGecko da las mismas horas pero desplazadas media hora
    segunda = _cada_hora(47, BASE + timedelta(minutes=30))

    assert faltan(segunda, [p[0] for p in primera]) == []


def test_con_precios_diarios_el_margen_es_de_dias():
    bajados = [(BASE + timedelta(days=i), 100.0) for i in range(4)]
    # el segundo día tiene un precio guardado a seis horas
    guardados = [BASE + timedelta(days=1, hours=6)]

    assert [p[0] for p in faltan(bajados, guardados)] == [
        BASE,
        BASE + timedelta(days=2),
        BASE + timedelta(days=3),
    ]


def test_un_solo_punto_entra_tal_cual():
    assert faltan([(BASE, 5.0)], [BASE]) == [(BASE, 5.0)]


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
        history_days=90,
    )


def _serie(dias_atras, n):
    inicio = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(
        days=dias_atras
    )
    return _cada_hora(n, inicio)


def _api(monkeypatch, series):
    pedidas = []

    def historico(coin_id, dias, moneda):
        pedidas.append((coin_id, dias, moneda))
        resultado = series[coin_id]
        if isinstance(resultado, Exception):
            raise resultado
        return resultado

    monkeypatch.setattr(coingecko, "historico", historico)
    return pedidas


def test_guarda_lo_bajado(config, monkeypatch):
    pedidas = _api(monkeypatch, {"bitcoin": _serie(10, 24)})

    texto = main.responder(config, "rellenar", "btc 30d")

    assert pedidas == [("bitcoin", 30, "eur")]
    assert "<b>24</b> precios nuevos" in texto
    assert (
        len(database.get_serie(config.database_path, "bitcoin", 24 * 30, "eur")) == 24
    )


def test_repetirlo_no_duplica(config, monkeypatch):
    _api(monkeypatch, {"bitcoin": _serie(10, 24)})

    main.responder(config, "rellenar", "btc")
    texto = main.responder(config, "rellenar", "btc")

    assert "ya lo tenía todo" in texto
    assert (
        len(database.get_serie(config.database_path, "bitcoin", 24 * 30, "eur")) == 24
    )


def test_el_ultimo_precio_sigue_siendo_el_de_ahora(config, monkeypatch):
    database.save_prices(config.database_path, {"bitcoin": 999.0}, "eur")
    _api(monkeypatch, {"bitcoin": _serie(10, 24)})

    main.responder(config, "rellenar", "btc")

    assert database.get_last_price(config.database_path, "bitcoin") == 999.0


def test_a_secas_van_las_que_vigila(config, monkeypatch):
    pedidas = _api(monkeypatch, {"bitcoin": _serie(10, 24)})

    main.responder(config, "rellenar", "")

    assert pedidas == [("bitcoin", 90, "eur")]


def test_una_que_falla_no_para_las_demas(config, monkeypatch):
    error = coingecko.CoinGeckoError("CoinGecko no la conoce, búscala con /buscar")
    _api(monkeypatch, {"bitcion": error, "ethereum": _serie(10, 24)})

    texto = main.responder(config, "rellenar", "bitcion eth")

    assert "bitcion: no he podido" in texto
    assert "/buscar" in texto
    assert "Ethereum: <b>24</b>" in texto


def test_si_no_viene_nada_no_dice_que_lo_tenia_todo(config, monkeypatch):
    _api(monkeypatch, {"bitcoin": []})

    texto = main.responder(config, "rellenar", "btc")

    assert "no tiene precios" in texto
    assert "ya lo tenía" not in texto


def test_con_esto_ya_sale_el_rsi(config, monkeypatch):
    assert "Necesito" in main.responder(config, "rsi", "btc")
    _api(monkeypatch, {"bitcoin": _serie(30, 30 * 24)})

    main.responder(config, "rellenar", "btc")

    assert "Necesito" not in main.responder(config, "rsi", "btc")


def test_pide_el_market_chart_con_el_id_en_la_ruta(monkeypatch):
    urls = []

    class Respuesta:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"prices": [[1_000_000, 5.0]]}

    def get(url, params, **kw):
        urls.append((url, params))
        return Respuesta()

    monkeypatch.setattr(requests, "get", get)

    puntos = coingecko.historico("a/b", 30, "eur")

    assert len(puntos) == 1
    assert urls == [
        (
            "https://api.coingecko.com/api/v3/coins/a%2Fb/market_chart",
            {"vs_currency": "eur", "days": 30},
        )
    ]
