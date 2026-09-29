"""Tests de como contesta el bot a lo que le escriben."""

import time

import pytest

import main
from crypto_tracker import coingecko, database, telegram
from crypto_tracker.config import Config, Watch


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


@pytest.fixture
def enviados(monkeypatch):
    lista = []
    monkeypatch.setattr(
        telegram,
        "send_message",
        lambda token, chat, texto, **kw: lista.append(texto) or True,
    )
    return lista


def _mensaje(texto, chat=123, hace=0):
    return {"chat": {"id": chat}, "text": texto, "date": int(time.time()) - hace}


def test_contesta_la_ayuda(config, enviados):
    main.atender(config, _mensaje("/start"))

    assert "/status" in enviados[0]


def test_ignora_otros_chats(config, enviados):
    main.atender(config, _mensaje("/status", chat=999))

    assert enviados == []


def test_ignora_comandos_viejos(config, enviados):
    # llego con el bot apagado hace una hora
    main.atender(config, _mensaje("/mute 2h", hace=3600))

    assert enviados == []
    assert database.silenciado_hasta(config.database_path) is None


def test_texto_normal_no_se_entiende(config, enviados):
    main.atender(config, _mensaje("hola"))

    assert "/ayuda" in enviados[0]


def test_comando_inventado(config, enviados):
    main.atender(config, _mensaje("/bailar"))

    assert "/ayuda" in enviados[0]


def test_mute_y_unmute(config, enviados):
    main.atender(config, _mensaje("/mute 2h"))

    assert database.silenciado_hasta(config.database_path) is not None
    assert "Callado hasta" in enviados[0]

    main.atender(config, _mensaje("/unmute"))

    assert database.silenciado_hasta(config.database_path) is None
    assert "Vuelvo a avisar" in enviados[1]


def test_mute_sin_tiempo_explica_el_formato(config, enviados):
    main.atender(config, _mensaje("/mute"))

    assert "30m" in enviados[0]
    assert database.silenciado_hasta(config.database_path) is None


def test_unmute_sin_estar_callado(config, enviados):
    main.atender(config, _mensaje("/unmute"))

    assert "No estaba" in enviados[0]


def test_status(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 63000.0})

    main.atender(config, _mensaje("/status"))

    assert "63.000,00" in enviados[0]


def test_status_sin_coingecko(config, enviados, monkeypatch):
    def falla(ids, cur):
        raise coingecko.CoinGeckoError("Sin conexion")

    monkeypatch.setattr(coingecko, "get_prices", falla)

    main.atender(config, _mensaje("/status"))

    assert "No he podido" in enviados[0]


def test_historico(config, enviados):
    for precio in (60000.0, 61000.0, 62000.0):
        database.save_prices(config.database_path, {"bitcoin": precio}, "eur")

    main.atender(config, _mensaje("/historico Bitcoin"))

    assert "62.000,00" in enviados[0]
    assert "<code>" in enviados[0]


def test_historico_sin_datos(config, enviados):
    main.atender(config, _mensaje("/historico btc"))

    assert "bitcoin, no BTC" in enviados[0]


def test_historico_sin_cripto(config, enviados):
    main.atender(config, _mensaje("/historico"))

    assert "¿De cuál?" in enviados[0]


def test_la_espera_contesta_y_avanza_el_offset(config, enviados, monkeypatch):
    llamadas = []

    def get_updates(token, offset, espera):
        llamadas.append(offset)
        if len(llamadas) == 1:
            return [{"update_id": 41, "message": _mensaje("/ayuda")}]
        return []

    monkeypatch.setattr(telegram, "get_updates", get_updates)

    offset = main.esperar_escuchando(config, 1, None)

    assert offset == 42
    assert len(enviados) == 1


def test_un_comando_que_revienta_no_tumba_el_bot(config, monkeypatch):
    llamadas = []

    def get_updates(token, offset, espera):
        llamadas.append(offset)
        return [{"update_id": 1, "message": _mensaje("/ayuda")}] if not offset else []

    def revienta(*a):
        raise ValueError("fallo raro")

    monkeypatch.setattr(telegram, "get_updates", get_updates)
    monkeypatch.setattr(main, "atender", revienta)

    # no lanza, y no se queda repitiendo el mismo mensaje
    assert main.esperar_escuchando(config, 1, None) == 2


def test_historico_recien_instalado_no_culpa_al_id(config, enviados):
    database.save_prices(config.database_path, {"bitcoin": 63000.0}, "eur")

    main.atender(config, _mensaje("/historico bitcoin"))

    assert "pocos precios" in enviados[0]
    assert "BTC" not in enviados[0]


# --- resumen diario ---


@pytest.fixture
def con_resumen(config, monkeypatch):
    from dataclasses import replace
    from datetime import time as hora

    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 63000.0})
    return replace(config, resumen_diario=hora(9, 0))


def _dia(h, m=0, dia=29):
    from datetime import datetime

    return datetime(2026, 9, dia, h, m).astimezone()


def test_resumen_diario_a_su_hora(con_resumen, enviados):
    main.resumen_diario(con_resumen, _dia(8, 55))
    assert enviados == []

    main.resumen_diario(con_resumen, _dia(9, 0))
    assert len(enviados) == 1
    assert "resumen del día" in enviados[0]
    assert "63.000,00" in enviados[0]


def test_resumen_diario_una_vez_al_dia(con_resumen, enviados):
    for minuto in (0, 5, 10, 15):
        main.resumen_diario(con_resumen, _dia(9, minuto))

    assert len(enviados) == 1

    main.resumen_diario(con_resumen, _dia(9, 0, dia=30))
    assert len(enviados) == 2


def test_resumen_diario_desactivado(config, enviados):
    # sin RESUMEN_DIARIO en el .env, como hasta ahora
    main.resumen_diario(config, _dia(9, 0))

    assert enviados == []


def test_resumen_diario_callado(con_resumen, enviados):
    main.atender(con_resumen, _mensaje("/mute 1h"))
    enviados.clear()

    main.resumen_diario(con_resumen, _dia(9, 0))

    assert enviados == []


def test_resumen_diario_reintenta_si_coingecko_falla(
    con_resumen, enviados, monkeypatch
):
    def falla(ids, cur):
        raise coingecko.CoinGeckoError("Sin conexion")

    monkeypatch.setattr(coingecko, "get_prices", falla)
    main.resumen_diario(con_resumen, _dia(9, 0))
    assert enviados == []

    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 1.0})
    main.resumen_diario(con_resumen, _dia(9, 5))
    assert len(enviados) == 1


def test_resumen_diario_reintenta_si_telegram_falla(con_resumen, monkeypatch):
    intentos = []
    monkeypatch.setattr(
        telegram,
        "send_message",
        lambda *a, **kw: intentos.append(1) or len(intentos) > 1,
    )

    main.resumen_diario(con_resumen, _dia(9, 0))
    main.resumen_diario(con_resumen, _dia(9, 5))
    main.resumen_diario(con_resumen, _dia(9, 10))

    assert len(intentos) == 2  # fallo, acierto, y ya no mas


# --- movimiento brusco ---


@pytest.fixture
def con_brusco(config):
    from dataclasses import replace

    return replace(config, brusco_porcentaje=8.0, brusco_minutos=60)


def _precio_hace(config, precio, minutos):
    import sqlite3
    from datetime import datetime, timedelta, timezone

    cuando = datetime.now(timezone.utc) - timedelta(minutes=minutos)
    conn = sqlite3.connect(config.database_path)
    conn.execute(
        "INSERT INTO prices (coin_id, price, currency, created_at) VALUES (?,?,?,?)",
        ("bitcoin", precio, "eur", cuando.isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()


def test_brusco_avisa_de_una_caida(con_brusco):
    _precio_hace(con_brusco, 60000.0, 40)

    avisos = main.revisar_bruscos(con_brusco, {"bitcoin": 55000.0})

    assert len(avisos) == 1
    assert avisos[0].minutos == 60


def test_brusco_ignora_lo_de_fuera_de_la_ventana(con_brusco):
    _precio_hace(con_brusco, 60000.0, 90)

    assert main.revisar_bruscos(con_brusco, {"bitcoin": 55000.0}) == []


def test_brusco_no_repite_el_aviso(con_brusco):
    _precio_hace(con_brusco, 60000.0, 40)
    main.revisar_bruscos(con_brusco, {"bitcoin": 55000.0})
    database.save_prices(con_brusco.database_path, {"bitcoin": 55000.0}, "eur")

    # sigue abajo, pero ya se aviso: el 60000 de antes ya no cuenta
    assert main.revisar_bruscos(con_brusco, {"bitcoin": 54500.0}) == []


def test_brusco_desactivado(config):
    _precio_hace(config, 60000.0, 40)

    assert main.revisar_bruscos(config, {"bitcoin": 30000.0}) == []


def test_brusco_llega_por_telegram(con_brusco, enviados, monkeypatch):
    _precio_hace(con_brusco, 60000.0, 40)
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 55000.0})

    main.ejecutar_ciclo(con_brusco, {"bitcoin": "%55000.0"})

    assert len(enviados) == 1
    assert "⚡" in enviados[0]


# --- horas tranquilas ---


@pytest.fixture
def ahora_tranquilo(config):
    """Un tramo tranquilo que empieza hace una hora y acaba dentro de una."""
    from dataclasses import replace
    from datetime import datetime, timedelta

    ahora = datetime.now()
    tramo = (
        (ahora - timedelta(hours=1)).time().replace(second=0, microsecond=0),
        (ahora + timedelta(hours=1)).time().replace(second=0, microsecond=0),
    )
    return replace(config, horas_tranquilas=tramo)


@pytest.fixture
def sonidos(monkeypatch):
    lista = []
    monkeypatch.setattr(
        telegram,
        "send_message",
        lambda token, chat, texto, sin_sonido=False: lista.append(sin_sonido) or True,
    )
    return lista


def test_sin_sonido_segun_la_hora(config):
    from dataclasses import replace
    from datetime import datetime, time

    noche = replace(config, horas_tranquilas=(time(23), time(8)))

    assert main._sin_sonido(noche, datetime(2026, 9, 29, 3, 0)) is True
    assert main._sin_sonido(noche, datetime(2026, 9, 29, 15, 0)) is False
    # sin HORAS_TRANQUILAS, siempre suena
    assert main._sin_sonido(config, datetime(2026, 9, 29, 3, 0)) is False


def test_avisos_sin_sonido_en_horas_tranquilas(ahora_tranquilo, sonidos, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 90000.0})

    main.ejecutar_ciclo(ahora_tranquilo, {"bitcoin": "%60000.0"})

    assert sonidos == [True]


def test_avisos_con_sonido_fuera_de_horas(config, sonidos, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 90000.0})

    main.ejecutar_ciclo(config, {"bitcoin": "%60000.0"})

    assert sonidos == [False]


def test_las_respuestas_a_comandos_siempre_suenan(ahora_tranquilo, sonidos):
    # si le escribes es que estas despierto
    main.atender(ahora_tranquilo, _mensaje("/ayuda"))

    assert sonidos == [False]


# --- cartera ---


def test_resumen_con_cartera(config, monkeypatch):
    from dataclasses import replace

    from crypto_tracker.config import parse_cartera

    pedidas = []

    def precios(ids, cur):
        pedidas.extend(ids)
        return {"bitcoin": 70000.0, "solana": 150.0}

    monkeypatch.setattr(coingecko, "get_prices", precios)
    # solana no esta en la watchlist, solo en la cartera
    con_cartera = replace(
        config, cartera=parse_cartera("bitcoin:0.016:1000,solana:7:1000")
    )

    texto = main.montar_resumen(con_cartera)

    assert pedidas == ["bitcoin", "solana"]
    assert "Tu cartera" in texto
    assert "1.120,00" in texto  # bitcoin: 0.016 * 70000
    assert "1.050,00" in texto  # solana: 7 * 150
    assert "2.170,00" in texto  # total


def test_resumen_sin_cartera_como_antes(config, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 1.0})

    assert "cartera" not in main.montar_resumen(config)
