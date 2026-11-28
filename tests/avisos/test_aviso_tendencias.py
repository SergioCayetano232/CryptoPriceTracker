"""Tests del aviso de /tendencias."""

from datetime import datetime, timedelta, timezone

import pytest

from crypto_tracker.avisos.aviso_tendencias import (
    AvisoError,
    Estado,
    Nueva,
    a_texto,
    de_texto,
    interpretar,
    mirado,
    nuevas,
    toca_mirar,
)
from crypto_tracker.indicadores.tendencias import Tendencia

AHORA = datetime(2026, 11, 23, 12, tzinfo=timezone.utc)
SOL = Tendencia("solana", "Solana", "SOL", 5, 12.3)
PEPE = Tendencia("pepe", "Pepe", "PEPE", 30, 40.0)
BTC = Tendencia("bitcoin", "Bitcoin", "BTC", 1, -1.0)


@pytest.mark.parametrize(
    "texto, sale",
    [
        ("", None),
        ("avisa", True),
        ("Avísame", True),
        ("avisa no", False),
        ("no avisa", False),
        ("no", False),
    ],
)
def test_interpretar(texto, sale):
    assert interpretar(texto) is sale


@pytest.mark.parametrize("texto", ["btc", "avisa btc", "sí"])
def test_interpretar_mal(texto):
    with pytest.raises(AvisoError, match="/tendencias avisa"):
        interpretar(texto)


def test_toca_mirar_cada_6_horas():
    assert toca_mirar(Estado(), AHORA)
    hace = Estado(mirado=AHORA - timedelta(hours=5, minutes=59))
    assert not toca_mirar(hace, AHORA)
    assert toca_mirar(Estado(mirado=AHORA - timedelta(hours=6)), AHORA)


def test_nuevas_solo_las_tuyas_con_su_lugar():
    lista = [PEPE, SOL, BTC]

    assert nuevas(lista, {"solana", "bitcoin"}, Estado(), AHORA) == [
        Nueva(SOL, 2),
        Nueva(BTC, 3),
    ]
    assert nuevas(lista, {"cardano"}, Estado(), AHORA) == []


def test_nuevas_no_repite_en_una_semana():
    e = Estado(avisadas={"solana": AHORA - timedelta(days=6)})
    assert nuevas([SOL], {"solana"}, e, AHORA) == []

    e = Estado(avisadas={"solana": AHORA - timedelta(days=7)})
    assert nuevas([SOL], {"solana"}, e, AHORA) == [Nueva(SOL, 1)]


def test_mirado_apunta_y_olvida_las_viejas():
    e = Estado(
        avisadas={
            "solana": AHORA - timedelta(days=8),
            "bitcoin": AHORA - timedelta(days=2),
        }
    )

    despues = mirado(e, AHORA, ["pepe"])

    assert despues.mirado == AHORA
    assert despues.avisadas == {
        "bitcoin": AHORA - timedelta(days=2),
        "pepe": AHORA,
    }


def test_ida_y_vuelta():
    e = Estado(AHORA, {"solana": AHORA - timedelta(days=1)})

    assert de_texto(a_texto(e)) == e
    assert de_texto(a_texto(Estado())) == Estado()


@pytest.mark.parametrize("roto", ["", "no es json", "[]", '{"mirado": "ayer"}'])
def test_de_texto_roto(roto):
    assert de_texto(roto) == Estado()


# --- de punta a punta ---

import time  # noqa: E402
from dataclasses import replace  # noqa: E402

import main  # noqa: E402
from crypto_tracker.nucleo import binance, coingecko, database, telegram  # noqa: E402
from crypto_tracker.nucleo.config import Config, Watch, parse_cartera  # noqa: E402


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
        cartera=parse_cartera("solana:10:1000"),
    )


@pytest.fixture
def enviados(monkeypatch):
    lista = []
    monkeypatch.setattr(
        telegram,
        "send_message",
        lambda token, chat, texto, **kw: lista.append(texto) or True,
    )
    return lista


@pytest.fixture
def de_moda(monkeypatch):
    pedidas = []

    def tendencias_hoy(moneda):
        pedidas.append(moneda)
        return [PEPE, SOL, BTC]

    monkeypatch.setattr(coingecko, "tendencias_hoy", tendencias_hoy)
    return pedidas


def _mensaje(texto):
    return {"chat": {"id": 123}, "text": texto, "date": int(time.time())}


def test_sin_activar_no_consulta(config, enviados, de_moda):
    main.revisar_tendencias(config, set(), ahora=AHORA)

    assert de_moda == []
    assert enviados == []


def test_activar_avisa_y_no_repite(config, enviados, de_moda):
    main.atender(config, _mensaje("/tendencias avisa"))
    assert "🔥 Hecho" in enviados[0]

    main.revisar_tendencias(config, set(), ahora=AHORA)
    # A las 7 h vuelve a mirar, pero ya las contó.
    main.revisar_tendencias(config, set(), ahora=AHORA + timedelta(hours=7))

    assert len(de_moda) == 2
    [_, aviso] = enviados
    assert aviso.startswith("🔥 <b>2 de las tuyas están de moda</b>")
    assert "2. <b>Solana</b>  🔺 +12.30% en 24 h" in aviso
    assert "3. <b>Bitcoin</b>" in aviso
    assert "Pepe" not in aviso


def test_mira_cada_6_horas(config, enviados, de_moda):
    main.atender(config, _mensaje("/tendencias avisa"))

    main.revisar_tendencias(config, set(), ahora=AHORA)
    main.revisar_tendencias(config, set(), ahora=AHORA + timedelta(hours=1))
    main.revisar_tendencias(config, set(), ahora=AHORA + timedelta(hours=5))

    assert len(de_moda) == 1


def test_una_sola_y_las_calladas_no(config, enviados, de_moda):
    main.atender(config, _mensaje("/tendencias avisa"))

    main.revisar_tendencias(config, {"bitcoin"}, ahora=AHORA)

    aviso = enviados[-1]
    assert aviso.startswith("🔥 <b>Solana está de moda</b>")
    assert "Bitcoin" not in aviso


def test_si_coingecko_falla_no_insiste(config, enviados, monkeypatch):
    llamadas = []

    def falla(moneda):
        llamadas.append(moneda)
        raise coingecko.CoinGeckoError("caído")

    monkeypatch.setattr(coingecko, "tendencias_hoy", falla)
    main.atender(config, _mensaje("/tendencias avisa"))

    main.revisar_tendencias(config, set(), ahora=AHORA)
    main.revisar_tendencias(config, set(), ahora=AHORA + timedelta(minutes=5))

    assert len(llamadas) == 1
    assert len(enviados) == 1  # solo el "Hecho"


def test_quitar(config, enviados, de_moda):
    main.atender(config, _mensaje("/tendencias avisa"))
    main.atender(config, _mensaje("/tendencias avisa no"))

    main.revisar_tendencias(config, set(), ahora=AHORA)

    assert enviados[-1] == "Hecho, ya no te aviso de las tendencias."
    assert de_moda == []
    assert database.aviso_tendencias(config.database_path) is None


def test_activar_dos_veces_no_olvida_las_avisadas(config, enviados, de_moda):
    main.atender(config, _mensaje("/tendencias avisa"))
    main.revisar_tendencias(config, set(), ahora=AHORA)
    main.atender(config, _mensaje("/tendencias avisa"))

    e = database.aviso_tendencias(config.database_path)
    assert set(e.avisadas) == {"solana", "bitcoin"}


def test_la_lista_ofrece_el_aviso_hasta_que_lo_pones(config, enviados, de_moda):
    main.atender(config, _mensaje("/tendencias"))
    main.atender(config, _mensaje("/tendencias avisa"))
    main.atender(config, _mensaje("/tendencias"))

    assert "/tendencias avisa</i>" in enviados[0]
    assert "/tendencias avisa</i>" not in enviados[2]


def test_mal_escrito(config, enviados):
    main.atender(config, _mensaje("/tendencias btc"))

    assert "No te entiendo" in enviados[0]


def test_dentro_del_ciclo(config, enviados, de_moda, monkeypatch):
    monkeypatch.setattr(binance, "precios", lambda ids, cur: {})
    monkeypatch.setattr(
        coingecko,
        "get_prices",
        lambda ids, cur: {"bitcoin": 60000.0, "solana": 150.0},
    )
    main.atender(config, _mensaje("/tendencias avisa"))

    main.ejecutar_ciclo(replace(config), {})

    assert any("están de moda" in t for t in enviados)
