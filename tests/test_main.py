"""Tests de como contesta el bot a lo que le escriben."""

import time

import pytest

import main
from crypto_tracker import coingecko, database, grafica, telegram
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


@pytest.fixture(autouse=True)
def sin_fotos_de_verdad(monkeypatch):
    """Las imagenes que se mandarian, sin tocar la API de Telegram."""
    fotos = []
    monkeypatch.setattr(
        telegram,
        "send_photo",
        lambda token, chat, png, pie="": fotos.append((png, pie)) or True,
    )
    return fotos


@pytest.fixture(autouse=True)
def sin_cambios_de_coingecko(monkeypatch):
    """Sin esto, la variacion de 24 h de un test aparece en el siguiente."""
    monkeypatch.setattr(coingecko, "_cambios", {})


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


def test_historico(config, enviados, sin_fotos_de_verdad):
    for precio in (60000.0, 61000.0, 62000.0):
        database.save_prices(config.database_path, {"bitcoin": precio}, "eur")

    main.atender(config, _mensaje("/historico Bitcoin"))

    png, pie = sin_fotos_de_verdad[0]
    assert png.startswith(b"\x89PNG")
    assert "62.000,00" in pie
    assert "<code>" not in pie  # con la imagen, las barritas sobran
    assert enviados == []


def test_historico_sin_matplotlib_manda_texto(config, enviados, monkeypatch):
    def falla(*a):
        raise grafica.GraficaError("Falta matplotlib")

    monkeypatch.setattr(grafica, "dibujar", falla)
    for precio in (60000.0, 61000.0):
        database.save_prices(config.database_path, {"bitcoin": precio}, "eur")

    main.atender(config, _mensaje("/historico bitcoin"))

    assert "<code>" in enviados[0]  # el de siempre, con barritas


def test_historico_si_la_foto_no_pasa_manda_texto(config, enviados, monkeypatch):
    monkeypatch.setattr(telegram, "send_photo", lambda *a, **k: False)
    for precio in (60000.0, 61000.0):
        database.save_prices(config.database_path, {"bitcoin": precio}, "eur")

    main.atender(config, _mensaje("/historico bitcoin"))

    assert "61.000,00" in enviados[0]


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


# --- buscar ---


def test_buscar_por_telegram(config, enviados, monkeypatch):
    resultados = [
        {"id": "bitcoin", "name": "Bitcoin", "symbol": "btc", "market_cap_rank": 1}
    ]
    monkeypatch.setattr(coingecko, "buscar", lambda texto: resultados)

    main.atender(config, _mensaje("/buscar btc"))

    assert "<code>bitcoin</code>" in enviados[0]
    assert "BTC" in enviados[0]
    assert "bitcoin:%5" in enviados[0]


def test_buscar_sin_texto(config, enviados):
    main.atender(config, _mensaje("/buscar"))

    assert "¿Qué busco?" in enviados[0]


def test_buscar_sin_resultados(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "buscar", lambda texto: [])

    main.atender(config, _mensaje("/buscar <zzz>"))

    assert "No encuentro" in enviados[0]
    assert "<zzz>" not in enviados[0]  # escapado


def test_buscar_con_coingecko_caido(config, enviados, monkeypatch):
    def falla(texto):
        raise coingecko.CoinGeckoError("Sin conexion con CoinGecko")

    monkeypatch.setattr(coingecko, "buscar", falla)

    main.atender(config, _mensaje("/buscar btc"))

    assert "No he podido buscar" in enviados[0]


# --- cita a coingecko ---


def test_los_mensajes_con_precios_citan_a_coingecko(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 90000.0})
    monkeypatch.setattr(
        coingecko, "buscar", lambda t: [{"id": "bitcoin", "name": "Bitcoin"}]
    )

    main.ejecutar_ciclo(config, {"bitcoin": "%60000.0"})  # un aviso
    main.atender(config, _mensaje("/status"))
    main.atender(config, _mensaje("/buscar btc"))

    assert len(enviados) == 3
    for texto in enviados:
        assert 'href="https://www.coingecko.com"' in texto
        assert "Price data by" in texto


def test_el_historico_cita_a_coingecko(config, sin_fotos_de_verdad):
    for precio in (60000.0, 61000.0):
        database.save_prices(config.database_path, {"bitcoin": precio}, "eur")

    main.atender(config, _mensaje("/historico bitcoin"))

    _, pie = sin_fotos_de_verdad[0]
    assert "coingecko.com" in pie


def test_ayuda_y_estado_no_llevan_la_cita(config, enviados):
    main.atender(config, _mensaje("/ayuda"))

    assert "coingecko.com" not in enviados[0]


# --- /cartera ---


@pytest.fixture
def con_cartera(config):
    from dataclasses import replace

    from crypto_tracker.config import parse_cartera

    return replace(config, cartera=parse_cartera("bitcoin:0.016:1000,solana:7:1000"))


def test_cartera_sola(con_cartera, enviados, monkeypatch):
    pedidas = []

    def precios(ids, cur):
        pedidas.extend(ids)
        return {"bitcoin": 70000.0, "solana": 150.0}

    monkeypatch.setattr(coingecko, "get_prices", precios)

    main.atender(con_cartera, _mensaje("/cartera"))

    assert pedidas == ["bitcoin", "solana"]  # solo lo de la cartera
    assert "Tu cartera" in enviados[0]
    assert "2.170,00" in enviados[0]
    assert "Cómo van tus criptos" not in enviados[0]  # sin el resto del resumen
    assert "coingecko.com" in enviados[0]


def test_cartera_guarda_los_precios(con_cartera, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"solana": 150.0})

    main.atender(con_cartera, _mensaje("/portfolio"))  # el alias en ingles

    assert database.get_last_price(con_cartera.database_path, "solana") == 150.0


def test_cartera_sin_configurar(config, enviados, monkeypatch):
    def no_llamar(*a):
        raise AssertionError("no deberia consultar precios")

    monkeypatch.setattr(coingecko, "get_prices", no_llamar)

    main.atender(config, _mensaje("/cartera"))

    assert "PORTFOLIO" in enviados[0]


def test_cartera_con_coingecko_caido(con_cartera, enviados, monkeypatch):
    def falla(ids, cur):
        raise coingecko.CoinGeckoError("Sin conexion")

    monkeypatch.setattr(coingecko, "get_prices", falla)

    main.atender(con_cartera, _mensaje("/cartera"))

    assert "No he podido" in enviados[0]


# --- ids que coingecko no conoce ---


@pytest.fixture
def con_dedazo(config):
    from dataclasses import replace

    return replace(
        config, watchlist=[Watch("bitcoin", percent=5), Watch("bitcion", step=1000)]
    )


def test_avisa_de_un_id_que_no_existe(con_dedazo, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 63000.0})

    main.ejecutar_ciclo(con_dedazo, {})

    assert len(enviados) == 1
    assert "<b>bitcion</b>" in enviados[0]
    assert "/buscar bitcion" in enviados[0]


def test_el_id_que_no_existe_se_avisa_una_vez(con_dedazo, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 63000.0})
    avisadas = set()

    for _ in range(3):
        main.ejecutar_ciclo(con_dedazo, {}, avisadas)

    assert len(enviados) == 1
    assert avisadas == {"bitcion"}


def test_el_id_que_no_existe_se_reintenta_si_telegram_falla(con_dedazo, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 63000.0})
    monkeypatch.setattr(telegram, "send_message", lambda *a, **kw: False)
    avisadas = set()

    main.ejecutar_ciclo(con_dedazo, {}, avisadas)

    assert avisadas == set()


def test_si_no_llega_ninguna_sugiere_la_moneda(con_dedazo, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {})

    _, problema = main.ejecutar_ciclo(con_dedazo, {})

    assert "VS_CURRENCY" in enviados[0]
    assert problema is not None  # sigue contando como ciclo sin precios


def test_sin_dedazos_no_avisa_de_nada(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 63000.0})

    main.ejecutar_ciclo(config, {})

    assert enviados == []


def test_si_coingecko_falla_no_culpa_a_los_ids(con_dedazo, enviados, monkeypatch):
    def falla(ids, cur):
        raise coingecko.CoinGeckoError("Sin conexion")

    monkeypatch.setattr(coingecko, "get_prices", falla)

    main.ejecutar_ciclo(con_dedazo, {})

    assert enviados == []


# --- /alerta ---


def _precio(monkeypatch, precios):
    pedidas = []

    def get_prices(ids, cur):
        pedidas.append(list(ids))
        return {c: p for c, p in precios.items() if c in ids}

    monkeypatch.setattr(coingecko, "get_prices", get_prices)
    return pedidas


def test_crear_alerta(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 63000.0})

    main.atender(config, _mensaje("/alerta bitcoin 70.000"))

    assert "suba a <b>€70.000,00</b>" in enviados[0]
    [alerta] = database.get_puntuales(config.database_path, "eur")
    assert (alerta.coin_id, alerta.objetivo, alerta.sube) == ("bitcoin", 70000, True)


def test_crear_alerta_hacia_abajo(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 63000.0})

    main.atender(config, _mensaje("/alerta bitcoin 55000"))

    assert "baje a" in enviados[0]
    assert database.get_puntuales(config.database_path, "eur")[0].sube is False


def test_crear_alerta_de_un_id_que_no_existe(config, enviados, monkeypatch):
    _precio(monkeypatch, {})

    main.atender(config, _mensaje("/alerta bitcion 70000"))

    assert "/buscar bitcion" in enviados[0]
    assert database.get_puntuales(config.database_path, "eur") == []


def test_crear_alerta_mal_escrita(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 63000.0})

    main.atender(config, _mensaje("/alerta bitcoin <mucho>"))

    assert "&lt;mucho&gt;" in enviados[0]
    assert database.get_puntuales(config.database_path, "eur") == []


def test_crear_alerta_con_coingecko_caido(config, enviados, monkeypatch):
    def falla(ids, cur):
        raise coingecko.CoinGeckoError("Sin conexion")

    monkeypatch.setattr(coingecko, "get_prices", falla)

    main.atender(config, _mensaje("/alerta bitcoin 70000"))

    assert "No he podido" in enviados[0]
    assert database.get_puntuales(config.database_path, "eur") == []


def test_listar_y_quitar_alertas(config, enviados):
    a = database.crear_puntual(config.database_path, "bitcoin", 70000, True, "eur")

    main.atender(config, _mensaje("/alertas"))
    main.atender(config, _mensaje(f"/quitar {a.id}"))
    main.atender(config, _mensaje("/alertas"))

    assert "€70.000,00" in enviados[0]
    assert "quitada" in enviados[1]
    assert "No tienes alertas" in enviados[2]


def test_quitar_una_que_no_existe(config, enviados):
    main.atender(config, _mensaje("/quitar 42"))
    main.atender(config, _mensaje("/quitar"))

    assert "ninguna alerta con el número 42" in enviados[0]
    assert "/alertas" in enviados[1]


def test_la_alerta_salta_una_vez_y_se_borra(config, enviados, monkeypatch):
    database.crear_puntual(config.database_path, "bitcoin", 70000, True, "eur")
    estado = {"bitcoin": "%69000.0"}  # que el aviso de % no salte
    _precio(monkeypatch, {"bitcoin": 70500.0})

    estado, _ = main.ejecutar_ciclo(config, estado)
    main.ejecutar_ciclo(config, estado)

    assert len(enviados) == 1
    assert "Era tu /alerta" in enviados[0]
    assert database.get_puntuales(config.database_path, "eur") == []


def test_la_alerta_no_salta_antes_de_tiempo(config, enviados, monkeypatch):
    database.crear_puntual(config.database_path, "bitcoin", 70000, True, "eur")
    _precio(monkeypatch, {"bitcoin": 69000.0})

    main.ejecutar_ciclo(config, {"bitcoin": "%69000.0"})

    assert enviados == []
    assert len(database.get_puntuales(config.database_path, "eur")) == 1


def test_la_alerta_de_una_cripto_no_vigilada(config, enviados, monkeypatch):
    database.crear_puntual(config.database_path, "solana", 200, True, "eur")
    pedidas = _precio(monkeypatch, {"bitcoin": 63000.0, "solana": 210.0})

    main.ejecutar_ciclo(config, {"bitcoin": "%63000.0"})

    assert pedidas == [["bitcoin", "solana"]]  # en la misma consulta
    assert "Solana" in enviados[0]


def test_la_alerta_aguanta_el_mute(config, enviados, monkeypatch):
    from datetime import datetime, timedelta, timezone

    database.crear_puntual(config.database_path, "bitcoin", 70000, True, "eur")
    hasta = datetime.now(timezone.utc) + timedelta(hours=1)
    database.silenciar_hasta(config.database_path, hasta)
    _precio(monkeypatch, {"bitcoin": 70500.0})

    main.ejecutar_ciclo(config, {"bitcoin": "%70000.0"})

    assert enviados == []
    assert len(database.get_puntuales(config.database_path, "eur")) == 1


def test_la_alerta_aguanta_si_telegram_falla(config, monkeypatch):
    database.crear_puntual(config.database_path, "bitcoin", 70000, True, "eur")
    monkeypatch.setattr(telegram, "send_message", lambda *a, **kw: False)
    _precio(monkeypatch, {"bitcoin": 70500.0})

    main.ejecutar_ciclo(config, {"bitcoin": "%70000.0"})

    assert len(database.get_puntuales(config.database_path, "eur")) == 1


# --- /vigilar y /dejar ---


def test_vigilar_a_secas_lista_lo_del_env(config, enviados):
    main.atender(config, _mensaje("/vigilar"))

    assert "<b>Bitcoin</b>  cada 5 % que se mueva" in enviados[0]
    assert "desde Telegram" not in enviados[0]


def test_vigilar_una_nueva(config, enviados, monkeypatch):
    pedidas = _precio(monkeypatch, {"bitcoin": 63000.0, "solana": 150.0})

    main.atender(config, _mensaje("/vigilar solana 5%"))
    main.ejecutar_ciclo(config, {})
    main.atender(config, _mensaje("/vigilar"))

    assert "Vigilo <b>Solana</b>: cada 5 % que se mueva" in enviados[0]
    assert pedidas[-1] == ["bitcoin", "solana"]  # el ciclo ya la consulta
    assert (
        "<b>Solana</b>  cada 5 % que se mueva  <i>(desde Telegram)</i>" in enviados[1]
    )


def test_vigilar_una_que_no_existe(config, enviados, monkeypatch):
    _precio(monkeypatch, {})

    main.atender(config, _mensaje("/vigilar solanna %5"))

    assert "/buscar solanna" in enviados[0]
    assert database.get_cambios(config.database_path) == {}


def test_vigilar_mal_escrito(config, enviados):
    main.atender(config, _mensaje("/vigilar solana <%5>"))

    assert "&lt;" in enviados[0]
    assert database.get_cambios(config.database_path) == {}


def test_cambiar_la_regla_no_vuelve_a_mirar_el_id(config, enviados, monkeypatch):
    def no_llamar(*a):
        raise AssertionError("ya la vigilaba, no hace falta comprobarla")

    monkeypatch.setattr(coingecko, "get_prices", no_llamar)

    main.atender(config, _mensaje("/vigilar bitcoin 1000"))

    assert "cada €1.000,00" in enviados[0]


def test_cambiar_la_regla_no_da_avisos_falsos(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 63568.0})
    # venia por %, con la referencia muy lejos: con la regla vieja avisaria
    estado = {"bitcoin": "%50000.0"}

    main.atender(config, _mensaje("/vigilar bitcoin 1000"))
    enviados.clear()
    estado, _ = main.ejecutar_ciclo(config, estado)

    assert enviados == []
    assert estado["bitcoin"] == "63000.0"  # el nivel de partida de la regla nueva


def test_tras_empezar_de_cero_avisa_normal(config, enviados, monkeypatch):
    main.atender(config, _mensaje("/vigilar bitcoin 1000"))
    enviados.clear()
    _precio(monkeypatch, {"bitcoin": 63568.0})
    estado, _ = main.ejecutar_ciclo(config, {"bitcoin": "%50000.0"})

    _precio(monkeypatch, {"bitcoin": 64100.0})
    main.ejecutar_ciclo(config, estado)

    assert "ha subido de €64.000,00" in enviados[0]


def test_dejar_una(config, enviados, monkeypatch):
    database.guardar_cambio(config.database_path, "solana", "solana:%5.0")
    pedidas = _precio(monkeypatch, {"bitcoin": 63000.0})

    main.atender(config, _mensaje("/dejar Solana"))
    main.ejecutar_ciclo(config, {})

    assert "Dejo de vigilar <b>Solana</b>" in enviados[0]
    assert pedidas[-1] == ["bitcoin"]


def test_dejar_una_del_env(config, enviados, monkeypatch):
    database.guardar_cambio(config.database_path, "solana", "solana:%5.0")
    pedidas = _precio(monkeypatch, {"solana": 150.0})

    main.atender(config, _mensaje("/dejar bitcoin"))
    main.ejecutar_ciclo(config, {})

    assert pedidas[-1] == ["solana"]


def test_no_deja_quitar_la_ultima(config, enviados):
    main.atender(config, _mensaje("/dejar bitcoin"))

    assert "Es la única" in enviados[0]
    assert database.get_cambios(config.database_path) == {}


def test_dejar_una_que_no_vigilo(config, enviados):
    main.atender(config, _mensaje("/dejar dogecoin"))
    main.atender(config, _mensaje("/dejar"))

    assert "No estoy vigilando <b>dogecoin</b>" in enviados[0]
    assert "/dejar solana" in enviados[1]


def test_el_status_incluye_lo_de_telegram(config, enviados, monkeypatch):
    database.guardar_cambio(config.database_path, "solana", "solana:%5.0")
    _precio(monkeypatch, {"bitcoin": 63000.0, "solana": 150.0})

    main.atender(config, _mensaje("/status"))

    assert "<b>Solana</b>" in enviados[0]


def test_vigilar_un_rango_no_promete_esperar(config, enviados):
    main.atender(config, _mensaje("/vigilar bitcoin 55000 75000"))

    assert "si baja de €55.000,00 o si sube de €75.000,00" in enviados[0]
    assert "primer ciclo" not in enviados[0]


# --- /historico con tramo ---


def _con_fecha(config, precio, horas_atras):
    import sqlite3
    from datetime import datetime, timedelta, timezone

    cuando = datetime.now(timezone.utc) - timedelta(hours=horas_atras)
    conn = sqlite3.connect(config.database_path)
    conn.execute(
        "INSERT INTO prices (coin_id, price, currency, created_at) VALUES (?,?,?,?)",
        ("bitcoin", precio, "eur", cuando.isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()


def test_historico_de_una_semana(config, enviados, sin_fotos_de_verdad):
    _con_fecha(config, 50000.0, 167)
    _con_fecha(config, 70000.0, 100)  # el maximo, fuera de las ultimas 24 h
    _con_fecha(config, 60000.0, 1)

    main.atender(config, _mensaje("/historico bitcoin 7d"))

    _, pie = sin_fotos_de_verdad[0]
    assert "últimos 7 días" in pie
    assert "Máximo €70.000,00" in pie
    assert "Solo tengo" not in pie


def test_historico_sin_tramo_siguen_siendo_24h(config, sin_fotos_de_verdad):
    _con_fecha(config, 70000.0, 100)
    _con_fecha(config, 61000.0, 23)
    _con_fecha(config, 60000.0, 1)

    main.atender(config, _mensaje("/historico bitcoin"))

    _, pie = sin_fotos_de_verdad[0]
    assert "últimas 24 h" in pie
    assert "Máximo €61.000,00" in pie  # lo de hace 100 h no entra


def test_historico_avisa_si_no_hay_datos_de_todo_el_tramo(config, sin_fotos_de_verdad):
    _con_fecha(config, 60000.0, 48)
    _con_fecha(config, 61000.0, 1)

    main.atender(config, _mensaje("/historico bitcoin 30d"))

    _, pie = sin_fotos_de_verdad[0]
    assert "Solo tengo precios desde el" in pie


def test_historico_tramo_mal_escrito(config, enviados):
    main.atender(config, _mensaje("/historico bitcoin siempre"))

    assert "30m, 2h o 1d" in enviados[0]


def test_historico_sin_datos_dice_el_tramo(config, enviados):
    main.atender(config, _mensaje("/historico btc 7d"))

    assert "últimos 7 días" in enviados[0]
    assert "bitcoin, no BTC" in enviados[0]


# --- siguiente aviso en /status ---


def test_status_dice_donde_salta_el_siguiente_aviso(config, enviados, monkeypatch):
    database.save_state(config.database_path, {"bitcoin": "%60000.0"})
    _precio(monkeypatch, {"bitcoin": 61000.0})

    main.atender(config, _mensaje("/status"))

    assert "↑ €63.000,00 (+3.28%) · ↓ €57.000,00 (-6.56%)" in enviados[0]


def test_status_recien_instalado_no_inventa(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 61000.0})

    main.atender(config, _mensaje("/status"))

    assert "↑" not in enviados[0]
    assert "€61.000,00" in enviados[0]


def test_status_tras_un_ciclo_ya_lo_dice(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 61000.0})

    main.ejecutar_ciclo(config, {})
    main.atender(config, _mensaje("/status"))

    assert "↑ €64.050,00 (+5.00%)" in enviados[0]


def test_el_resumen_diario_tambien_lo_lleva(con_resumen, enviados):
    database.save_state(con_resumen.database_path, {"bitcoin": "%61000.0"})

    main.resumen_diario(con_resumen, _dia(9, 0))

    assert "Tu resumen del día" in enviados[0]
    assert "↑ €64.050,00" in enviados[0]


# --- 24 h en los avisos ---


def test_el_aviso_lleva_la_variacion_de_24h(config, enviados, monkeypatch):
    _con_fecha(config, 60000.0, 24)
    _precio(monkeypatch, {"bitcoin": 66000.0})

    main.ejecutar_ciclo(config, {"bitcoin": "%62000.0"})

    assert "ha subido un" in enviados[0]
    assert "En 24 h: 🔺 +10.00%" in enviados[0]


def test_recien_instalado_el_aviso_va_sin_24h(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 66000.0})

    main.ejecutar_ciclo(config, {"bitcoin": "%62000.0"})

    assert "ha subido un" in enviados[0]
    assert "24 h" not in enviados[0]


def test_la_variacion_de_coingecko_manda_sobre_el_historico(
    config, enviados, monkeypatch
):
    _con_fecha(config, 60000.0, 24)  # el historico diria +10%
    _precio(monkeypatch, {"bitcoin": 66000.0})
    monkeypatch.setattr(coingecko, "_cambios", {"bitcoin": 7.25})

    main.ejecutar_ciclo(config, {"bitcoin": "%62000.0"})

    assert "En 24 h: 🔺 +7.25%" in enviados[0]


def test_recien_instalado_el_resumen_ya_lleva_las_24h(config, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 66000.0})
    monkeypatch.setattr(coingecko, "_cambios", {"bitcoin": -1.5})

    texto = main.montar_resumen(config)

    assert "sin histórico" not in texto
    assert "🔻 -1.50%" in texto


def test_varios_avisos_cada_uno_con_lo_suyo(config, enviados, monkeypatch):
    from dataclasses import replace

    con_dos = replace(
        config, watchlist=[Watch("bitcoin", percent=5), Watch("solana", step=10)]
    )
    _con_fecha(config, 60000.0, 24)  # solana sin historico
    _precio(monkeypatch, {"bitcoin": 66000.0, "solana": 151.0})

    main.ejecutar_ciclo(con_dos, {"bitcoin": "%62000.0", "solana": "140.0"})

    assert "2 avisos" in enviados[0]
    assert enviados[0].count("En 24 h") == 1


# --- grafica de la cartera ---


def _cartera_con_fecha(config, coin_id, precio, horas_atras):
    import sqlite3
    from datetime import datetime, timedelta, timezone

    cuando = datetime.now(timezone.utc) - timedelta(hours=horas_atras)
    conn = sqlite3.connect(config.database_path)
    conn.execute(
        "INSERT INTO prices (coin_id, price, currency, created_at) VALUES (?,?,?,?)",
        (coin_id, precio, "eur", cuando.isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()


def test_cartera_con_grafica(con_cartera, enviados, sin_fotos_de_verdad, monkeypatch):
    for horas, precio in ((100, 50000.0), (50, 55000.0)):
        for coin_id in [p.coin_id for p in con_cartera.cartera]:
            _cartera_con_fecha(con_cartera, coin_id, precio / 20, horas)
    _precio(monkeypatch, {p.coin_id: 3000.0 for p in con_cartera.cartera})

    main.atender(con_cartera, _mensaje("/cartera"))

    png, pie = sin_fotos_de_verdad[0]
    assert png.startswith(b"\x89PNG")
    assert "Tu cartera" in pie
    assert enviados == []


def test_cartera_sin_historico_solo_texto(con_cartera, enviados, monkeypatch):
    _precio(monkeypatch, {p.coin_id: 3000.0 for p in con_cartera.cartera})

    main.atender(con_cartera, _mensaje("/cartera"))

    assert "Tu cartera" in enviados[0]


def test_cartera_tramo_mal_escrito(con_cartera, enviados):
    main.atender(con_cartera, _mensaje("/cartera siempre"))

    assert "30m, 2h o 1d" in enviados[0]


def test_el_ciclo_guarda_los_precios_de_la_cartera(con_cartera, monkeypatch):
    pedidas = _precio(monkeypatch, {"bitcoin": 63000.0, "solana": 150.0})

    main.ejecutar_ciclo(con_cartera, {})

    assert set(pedidas[0]) >= {p.coin_id for p in con_cartera.cartera}
    assert len(pedidas) == 1  # en la misma consulta


# --- consultas a coingecko ---


@pytest.fixture
def sin_cuenta_previa():
    coingecko.tomar_consultas()  # que no se cuelen las de otros tests


def _hacer(n):
    coingecko._hechas += n


def test_apuntar_consultas(config, sin_cuenta_previa):
    from datetime import datetime, timezone

    ahora = datetime(2026, 10, 10, tzinfo=timezone.utc)
    _hacer(3)
    main.apuntar_consultas(config, ahora)
    _hacer(2)
    main.apuntar_consultas(config, ahora)

    assert database.get_consultas(config.database_path, "2026-10") == 5


def test_avisa_al_pasar_del_80(config, enviados, sin_cuenta_previa):
    from datetime import datetime, timezone

    ahora = datetime(2026, 10, 20, tzinfo=timezone.utc)
    database.sumar_consultas(config.database_path, "2026-10", 7999)

    _hacer(1)
    main.apuntar_consultas(config, ahora)
    _hacer(1)
    main.apuntar_consultas(config, ahora)

    assert len(enviados) == 1
    assert "Llevas 8.000 de las 10.000" in enviados[0]


def test_el_aviso_de_cuota_no_se_calla_con_mute(config, enviados, sin_cuenta_previa):
    from datetime import datetime, timedelta, timezone

    hasta = datetime.now(timezone.utc) + timedelta(hours=1)
    database.silenciar_hasta(config.database_path, hasta)
    database.sumar_consultas(config.database_path, "2026-10", 9999)

    _hacer(1)
    main.apuntar_consultas(config, datetime(2026, 10, 25, tzinfo=timezone.utc))

    assert "hasta el día 1" in enviados[0]


def test_sin_consultas_no_toca_nada(config, enviados, sin_cuenta_previa):
    main.apuntar_consultas(config)

    assert enviados == []


def test_comando_consultas(config, enviados, sin_cuenta_previa):
    from datetime import datetime, timezone

    mes = datetime.now(timezone.utc).strftime("%Y-%m")
    database.sumar_consultas(config.database_path, mes, 1200)
    _hacer(34)  # las de esta sesion tambien salen

    main.atender(config, _mensaje("/consultas"))

    assert "Llevas 1.234 de las 10.000" in enviados[0]


def test_el_ciclo_cuenta_de_verdad(config, enviados, sin_cuenta_previa, monkeypatch):
    import requests

    class Respuesta:
        status_code = 200

        def json(self):
            return {"bitcoin": {"eur": 63000.0}}

        def raise_for_status(self):
            pass

    monkeypatch.setattr(requests, "get", lambda *a, **k: Respuesta())

    main.ejecutar_ciclo(config, {})
    main.apuntar_consultas(config)

    from datetime import datetime, timezone

    mes = datetime.now(timezone.utc).strftime("%Y-%m")
    assert database.get_consultas(config.database_path, mes) == 1
