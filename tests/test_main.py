"""Tests de como contesta el bot a lo que le escriben."""

import time
from datetime import datetime, timezone

import pytest

import main
from crypto_tracker import coingecko, database, grafica, miedo, telegram
from crypto_tracker.config import Config, Posicion, Watch


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
        lambda token, chat, png, pie="", **kw: fotos.append((png, pie)) or True,
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
    assert "(2 h)" in enviados[0]

    main.atender(config, _mensaje("/unmute"))

    assert database.silenciado_hasta(config.database_path) is None
    assert "Vuelvo a avisar" in enviados[1]


def _con_botones(monkeypatch):
    mandados = []
    monkeypatch.setattr(
        telegram,
        "send_message",
        lambda token, chat, texto, **kw: (
            mandados.append((texto, kw["botones"])) or True
        ),
    )
    return mandados


def test_mute_a_secas_pregunta_cuanto(config, monkeypatch):
    mandados = _con_botones(monkeypatch)

    main.atender(config, _mensaje("/mute"))

    texto, filas = mandados[0]
    assert database.silenciado_hasta(config.database_path) is None
    assert "¿Cuánto tiempo me callo?" in texto
    assert filas == [
        [("1 h", "/mute 1h"), ("4 h", "/mute 4h")],
        [("🌙 Hasta las 8:00", "/mute hasta 8:00")],
    ]


def test_mute_con_el_boton_y_deshacer(config, monkeypatch):
    from datetime import datetime, timedelta, timezone

    mandados = _con_botones(monkeypatch)

    main.atender_boton(config, _boton("/mute 4h"))

    falta = database.silenciado_hasta(config.database_path) - datetime.now(timezone.utc)
    assert timedelta(hours=3, minutes=59) < falta <= timedelta(hours=4)
    texto, filas = mandados[0]
    assert "🔕 Callado hasta" in texto
    assert "(4 h)" in texto
    assert filas == [[("🔔 Volver a avisar", "/unmute")]]

    main.atender_boton(config, _boton("/unmute"))

    assert database.silenciado_hasta(config.database_path) is None
    assert "Vuelvo a avisar" in mandados[1][0]


def test_mute_dice_cuanto_en_dias(config, enviados):
    main.atender(config, _mensaje("/mute 1sem"))

    assert "(7 d)" in enviados[0]


def test_mute_a_secas_si_ya_estaba_callado_no_lo_toca(config, monkeypatch):
    mandados = _con_botones(monkeypatch)
    main.atender(config, _mensaje("/mute 3h"))
    antes = database.silenciado_hasta(config.database_path)

    main.atender(config, _mensaje("/mute"))

    texto, filas = mandados[1]
    assert database.silenciado_hasta(config.database_path) == antes
    assert f"Ya estoy callado hasta las {antes.astimezone():%H:%M}" in texto
    assert filas[0] == [("🔔 Volver a avisar", "/unmute")]
    assert ("1 h", "/mute 1h") in filas[1]


def test_mute_con_tiempo_mal_escrito_explica_el_formato(config, enviados):
    main.atender(config, _mensaje("/mute mucho"))

    assert "30m" in enviados[0]
    assert database.silenciado_hasta(config.database_path) is None


def test_mute_hasta_una_hora(config, enviados):
    from datetime import datetime, timedelta

    main.atender(config, _mensaje("/mute hasta 8:00"))

    hasta = database.silenciado_hasta(config.database_path).astimezone()
    assert f"{hasta:%H:%M}" == "08:00"
    assert hasta - datetime.now().astimezone() <= timedelta(days=1)
    assert "Callado hasta las 08:00" in enviados[0]


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
    main.atender(config, _mensaje("/historico bitcion"))

    assert "/buscar bitcion" in enviados[0]


def test_historico_sin_cripto_saca_la_primera_que_vigilas(
    config, enviados, sin_fotos_de_verdad
):
    for precio in (60000.0, 61000.0):
        database.save_prices(config.database_path, {"bitcoin": precio}, "eur")

    main.atender(config, _mensaje("/historico"))

    png, pie = sin_fotos_de_verdad[0]
    assert "<b>Bitcoin</b>, últimas 24 h" in pie


def test_historico_solo_con_el_tramo(config, enviados, sin_fotos_de_verdad):
    for precio in (60000.0, 61000.0):
        database.save_prices(config.database_path, {"bitcoin": precio}, "eur")

    main.atender(config, _mensaje("/historico 7d"))

    png, pie = sin_fotos_de_verdad[0]
    assert "<b>Bitcoin</b>, últimos 7 días" in pie


def test_historico_sin_cripto_cuenta_lo_de_telegram(config, enviados):
    # Si la del .env la dejaste, la primera es la que añadiste por Telegram.
    database.guardar_cambio(config.database_path, "solana", "solana:%5.0")
    database.guardar_cambio(config.database_path, "bitcoin", None)

    main.atender(config, _mensaje("/historico"))

    assert "pocos precios de <b>solana</b>" in enviados[0]


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


# --- maximos y minimos ---


@pytest.fixture
def con_extremos(config):
    from dataclasses import replace

    config = replace(config, extremos_dias=30)
    # Un mes guardado: de 60.000 a 70.000, con el primero de hace 30 dias.
    # Un minuto dentro: justo en el borde, si cambiaba el segundo antes de
    # mirar, se quedaba fuera y el test fallaba de vez en cuando.
    _precio_hace(config, 60000.0, 30 * 24 * 60 - 1)
    _precio_hace(config, 70000.0, 10 * 24 * 60)
    _precio_hace(config, 55000.0, 5 * 24 * 60)
    return config


def _ahora():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0)


def test_extremo_maximo(con_extremos):
    avisos = main.revisar_extremos(con_extremos, {"bitcoin": 71000.0}, _ahora())

    assert len(avisos) == 1
    assert avisos[0].extremo_dias == 30
    assert avisos[0].threshold == 70000.0


def test_extremo_minimo(con_extremos):
    avisos = main.revisar_extremos(con_extremos, {"bitcoin": 54000.0}, _ahora())

    assert avisos[0].threshold == 55000.0


def test_extremo_dentro_del_rango(con_extremos):
    assert main.revisar_extremos(con_extremos, {"bitcoin": 65000.0}, _ahora()) == []


def test_extremo_una_vez_al_dia(con_extremos):
    main.revisar_extremos(con_extremos, {"bitcoin": 71000.0}, _ahora())
    database.save_prices(con_extremos.database_path, {"bitcoin": 71000.0}, "eur")

    # sigue subiendo, pero ya avisó hoy de un máximo
    assert main.revisar_extremos(con_extremos, {"bitcoin": 72000.0}, _ahora()) == []
    # un mínimo es otra cosa y sí avisa
    assert len(main.revisar_extremos(con_extremos, {"bitcoin": 50000.0}, _ahora())) == 1


def test_extremo_sin_un_mes_guardado(config):
    from dataclasses import replace

    config = replace(config, extremos_dias=30)
    _precio_hace(config, 60000.0, 3 * 24 * 60)

    assert main.revisar_extremos(config, {"bitcoin": 99000.0}, _ahora()) == []


def test_extremo_desactivado(config):
    _precio_hace(config, 60000.0, 30 * 24 * 60)

    assert main.revisar_extremos(config, {"bitcoin": 99000.0}, _ahora()) == []


def test_extremo_llega_por_telegram(con_extremos, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 71000.0})

    main.ejecutar_ciclo(con_extremos, {"bitcoin": "%71000.0"})

    assert len(enviados) == 1
    assert "🏔 <b>Bitcoin</b> marca su máximo de 30 días" in enviados[0]


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
        lambda token, chat, texto, sin_sonido=False, **kw: (
            lista.append(sin_sonido) or True
        ),
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
    assert "<code>/vigilar bitcoin %5</code>" in enviados[0]


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


def test_crear_alerta_con_nota(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 63000.0})

    main.atender(config, _mensaje("/alerta bitcoin 70000 7d vender <la mitad>"))
    main.atender(config, _mensaje("/alertas"))

    [alerta] = database.get_puntuales(config.database_path, "eur")
    assert alerta.nota == "vender <la mitad>"
    assert alerta.caduca is not None
    assert "📝 vender &lt;la mitad&gt;" in enviados[0]
    assert "📝 vender &lt;la mitad&gt;" in enviados[1]


def test_la_nota_sale_en_el_aviso(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 71000.0})
    database.crear_puntual(
        config.database_path, "bitcoin", 70000, True, "eur", nota="vender la mitad"
    )

    main.ejecutar_ciclo(config, {})

    assert "📝 vender la mitad" in enviados[0]
    assert "Era tu /alerta" in enviados[0]


def test_crear_alerta_hacia_abajo(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 63000.0})

    main.atender(config, _mensaje("/alerta bitcoin 55000"))

    assert "baje a" in enviados[0]
    assert database.get_puntuales(config.database_path, "eur")[0].sube is False


def test_crear_alerta_relativa_subiendo(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 60000.0})

    main.atender(config, _mensaje("/alerta bitcoin +10%"))

    assert "suba a <b>€66.000,00</b>" in enviados[0]
    [alerta] = database.get_puntuales(config.database_path, "eur")
    assert alerta.objetivo == pytest.approx(66000.0)
    assert alerta.sube is True


def test_crear_alerta_relativa_bajando(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 60000.0})

    main.atender(config, _mensaje("/alerta bitcoin -5%"))

    assert "baje a <b>€57.000,00</b>" in enviados[0]
    assert database.get_puntuales(config.database_path, "eur")[0].sube is False


def test_crear_alerta_relativa_sin_signo(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 60000.0})

    main.atender(config, _mensaje("/alerta bitcoin 10%"))

    assert "¿Sube o baja?" in enviados[0]
    assert database.get_puntuales(config.database_path, "eur") == []


def test_la_alerta_relativa_salta(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 60000.0})
    main.atender(config, _mensaje("/alerta bitcoin -5%"))
    enviados.clear()

    _precio(monkeypatch, {"bitcoin": 56900.0})
    main.ejecutar_ciclo(config, {"bitcoin": "%60000.0"})

    assert "Era tu /alerta" in enviados[0]
    assert database.get_puntuales(config.database_path, "eur") == []


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


def test_alerta_sin_precio_dice_a_cuanto_esta(config, enviados, monkeypatch):
    _precio(monkeypatch, {"solana": 150.0})

    main.atender(config, _mensaje("/alerta sol"))

    assert "<b>Solana</b> está a €150,00" in enviados[0]
    assert "/alerta solana 160" in enviados[0]  # el ejemplo, con sus numeros
    assert "/alerta solana +10%" in enviados[0]
    assert database.get_puntuales(config.database_path, "eur") == []


def test_alerta_sin_cripto_explica_el_formato(config, enviados, monkeypatch):
    pedidas = _precio(monkeypatch, {})

    main.atender(config, _mensaje("/alerta 70000"))
    main.atender(config, _mensaje("/alerta +10%"))

    assert "Escríbelo así" in enviados[0]
    assert "Escríbelo así" in enviados[1]
    assert pedidas == []


def test_alerta_sin_precio_de_algo_que_no_existe(config, enviados, monkeypatch):
    _precio(monkeypatch, {})

    main.atender(config, _mensaje("/alerta solanna"))

    assert "/buscar solanna" in enviados[0]


def test_crear_alerta_con_coingecko_caido(config, enviados, monkeypatch):
    def falla(ids, cur):
        raise coingecko.CoinGeckoError("Sin conexion")

    monkeypatch.setattr(coingecko, "get_prices", falla)

    main.atender(config, _mensaje("/alerta bitcoin 70000"))

    assert "No he podido" in enviados[0]
    assert database.get_puntuales(config.database_path, "eur") == []


def test_listar_y_quitar_alertas(config, enviados, monkeypatch):
    _precio(monkeypatch, {})
    a = database.crear_puntual(config.database_path, "bitcoin", 70000, True, "eur")

    main.atender(config, _mensaje("/alertas"))
    main.atender(config, _mensaje(f"/quitar {a.id}"))
    main.atender(config, _mensaje("/alertas"))

    assert "€70.000,00" in enviados[0]
    assert "quitada" in enviados[1]
    assert "No tienes alertas" in enviados[2]


def test_alertas_con_lo_que_falta(config, enviados, monkeypatch):
    pedidas = _precio(monkeypatch, {"bitcoin": 62500.0, "solana": 125.0})
    database.crear_puntual(config.database_path, "bitcoin", 70000, True, "eur")
    database.crear_puntual(config.database_path, "solana", 100, False, "eur")
    database.crear_puntual(config.database_path, "bitcoin", 60000, False, "eur")

    main.atender(config, _mensaje("/alertas"))

    assert pedidas == [["bitcoin", "solana"]]  # una consulta, sin repetir
    assert "(falta +12.00%)" in enviados[0]
    assert "(falta -20.00%)" in enviados[0]
    assert "(falta -4.00%)" in enviados[0]
    assert "CoinGecko" in enviados[0]


def test_alertas_de_la_cartera_con_lo_que_falta(config, enviados, monkeypatch):
    from dataclasses import replace

    config = replace(config, cartera=(Posicion("ethereum", 2.0, 4000.0),))
    pedidas = _precio(monkeypatch, {"ethereum": 2500.0})
    database.crear_puntual(config.database_path, "cartera", 6000, True, "eur")

    main.atender(config, _mensaje("/alertas"))

    assert pedidas == [["ethereum"]]
    assert "<b>Tu cartera</b> 🔺 €6.000,00  <i>(falta +20.00%)</i>" in enviados[0]


def test_alertas_sin_conexion_sale_la_lista_igual(config, enviados, monkeypatch):
    def falla(ids, cur):
        raise coingecko.CoinGeckoError("Sin conexion con CoinGecko")

    monkeypatch.setattr(coingecko, "get_prices", falla)
    database.crear_puntual(config.database_path, "bitcoin", 70000, True, "eur")

    main.atender(config, _mensaje("/alertas"))

    assert "€70.000,00" in enviados[0]
    assert "falta" not in enviados[0]
    assert "CoinGecko" not in enviados[0]


def test_alertas_sin_ninguna_no_gasta_consultas(config, enviados, monkeypatch):
    pedidas = _precio(monkeypatch, {})

    main.atender(config, _mensaje("/alertas"))

    assert pedidas == []
    assert "No tienes alertas" in enviados[0]


def test_quitar_todas(config, enviados):
    database.crear_puntual(config.database_path, "bitcoin", 70000, True, "eur")
    database.crear_puntual(config.database_path, "solana", 100, False, "eur")

    main.atender(config, _mensaje("/quitar Todas"))
    main.atender(config, _mensaje("/quitar todas"))

    assert enviados[0] == "🗑 2 alertas quitadas."
    assert enviados[1] == "No tenías ninguna alerta puesta."
    assert database.get_puntuales(config.database_path, "eur") == []


def test_quitar_todas_con_una_sola(config, enviados):
    database.crear_puntual(config.database_path, "bitcoin", 70000, True, "eur")

    main.atender(config, _mensaje("/quitar todas"))

    assert enviados[0] == "🗑 Alerta quitada."


def test_quitar_una_que_no_existe(config, enviados):
    main.atender(config, _mensaje("/quitar 42"))

    assert "ninguna alerta con el número 42" in enviados[0]


def test_quitar_a_secas_sin_alertas(config, enviados):
    main.atender(config, _mensaje("/quitar"))

    assert "No tienes alertas puestas" in enviados[0]


def test_quitar_a_secas_ensena_las_alertas_con_botones(config, monkeypatch):
    mandados = []
    monkeypatch.setattr(
        telegram,
        "send_message",
        lambda token, chat, texto, **kw: mandados.append((texto, kw)) or True,
    )
    _precio(monkeypatch, {})
    a = database.crear_puntual(config.database_path, "bitcoin", 70000, True, "eur")

    main.atender(config, _mensaje("/quitar"))

    texto, kw = mandados[0]
    assert "Tus alertas" in texto
    assert (f"🗑 {a.id} Bitcoin", f"/quitar {a.id}") in kw["botones"][0]


def test_quitar_varias(config, enviados):
    ids = [
        database.crear_puntual(config.database_path, "bitcoin", p, True, "eur").id
        for p in (70000, 80000, 90000)
    ]

    main.atender(config, _mensaje(f"/quitar {ids[0]}, #{ids[2]}"))

    assert enviados[0] == "🗑 2 alertas quitadas."
    [queda] = database.get_puntuales(config.database_path, "eur")
    assert queda.id == ids[1]


def test_quitar_varias_con_alguna_que_no_existe(config, enviados):
    a = database.crear_puntual(config.database_path, "bitcoin", 70000, True, "eur")

    main.atender(config, _mensaje(f"/quitar {a.id} 41 42"))

    assert enviados[0] == (
        "🗑 Alerta quitada.\n"
        "No tengo ninguna alerta con los números 41 y 42. Mira /alertas"
    )
    assert database.get_puntuales(config.database_path, "eur") == []


def test_quitar_con_algo_que_no_es_numero_no_borra_nada(config, enviados):
    a = database.crear_puntual(config.database_path, "bitcoin", 70000, True, "eur")

    main.atender(config, _mensaje(f"/quitar {a.id} bitcoin"))

    assert "/quitar 2 5" in enviados[0]
    assert database.get_puntuales(config.database_path, "eur") == [a]


# --- caducidad de /alerta ---


def test_alerta_con_caducidad(config, enviados, monkeypatch):
    from datetime import timedelta

    _precio(monkeypatch, {"bitcoin": 60000.0})

    main.atender(config, _mensaje("/alerta btc 70000 7d"))
    main.atender(config, _mensaje("/alerta btc +10% 12h"))
    main.atender(config, _mensaje("/alertas"))

    a, b = database.get_puntuales(config.database_path, "eur")
    falta = a.caduca - datetime.now(timezone.utc)
    assert timedelta(days=6, hours=23) < falta <= timedelta(days=7)
    assert b.objetivo == pytest.approx(66000)
    assert b.caduca - a.caduca < timedelta(days=7)
    assert f"se borra el {a.caduca.astimezone():%d/%m a las %H:%M}" in enviados[0]
    assert f"⌛ {a.caduca.astimezone():%d/%m}" in enviados[2]


def test_alerta_sin_caducidad_como_siempre(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 60000.0})

    main.atender(config, _mensaje("/alerta btc 70000"))

    assert database.get_puntuales(config.database_path, "eur")[0].caduca is None
    assert "Solo te aviso una vez." in enviados[0]


def test_alerta_con_caducidad_mal_escrita(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 60000.0})

    main.atender(config, _mensaje("/alerta btc 70000 500d"))

    assert "Como mucho un año" in enviados[0]
    assert database.get_puntuales(config.database_path, "eur") == []


def _caducada(config, coin_id="bitcoin", objetivo=70000):
    from datetime import timedelta

    hace_rato = datetime.now(timezone.utc) - timedelta(minutes=1)
    return database.crear_puntual(
        config.database_path, coin_id, objetivo, True, "eur", hace_rato
    )


def test_el_ciclo_borra_las_caducadas_y_avisa_sin_sonido(config, monkeypatch):
    mandados = []
    monkeypatch.setattr(
        telegram,
        "send_message",
        lambda token, chat, texto, **kw: mandados.append((texto, kw)) or True,
    )
    _caducada(config)
    viva = database.crear_puntual(config.database_path, "bitcoin", 80000, True, "eur")
    _precio(monkeypatch, {"bitcoin": 69000.0})

    main.ejecutar_ciclo(config, {"bitcoin": "%69000.0"})

    texto, kw = mandados[0]
    assert "⌛ <b>Ha caducado sin llegar</b>" in texto
    assert "<b>Bitcoin</b> 🔺 €70.000,00" in texto
    assert kw["sin_sonido"] is True
    assert database.get_puntuales(config.database_path, "eur") == [viva]


def test_la_caducada_no_salta_aunque_llegue(config, enviados, monkeypatch):
    _caducada(config)
    _precio(monkeypatch, {"bitcoin": 70500.0})

    main.ejecutar_ciclo(config, {"bitcoin": "%70000.0"})

    assert len(enviados) == 1
    assert "caducado" in enviados[0]
    assert "Era tu /alerta" not in enviados[0]


def test_callado_no_caduca_hasta_que_vuelves(config, enviados, monkeypatch):
    from datetime import timedelta

    _caducada(config)
    _precio(monkeypatch, {"bitcoin": 69000.0})
    database.silenciar_hasta(
        config.database_path, datetime.now(timezone.utc) + timedelta(hours=1)
    )

    main.ejecutar_ciclo(config, {"bitcoin": "%69000.0"})

    assert enviados == []
    assert len(database.get_puntuales(config.database_path, "eur")) == 1

    database.silenciar_hasta(config.database_path, None)
    main.ejecutar_ciclo(config, {"bitcoin": "%69000.0"})

    assert "caducado" in enviados[0]
    assert database.get_puntuales(config.database_path, "eur") == []


def test_si_no_llega_el_aviso_de_caducada_no_la_borra(config, monkeypatch):
    monkeypatch.setattr(telegram, "send_message", lambda *a, **k: False)
    _caducada(config)
    _precio(monkeypatch, {"bitcoin": 69000.0})

    main.ejecutar_ciclo(config, {"bitcoin": "%69000.0"})

    assert len(database.get_puntuales(config.database_path, "eur")) == 1


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


def test_dejar_con_el_simbolo(config, enviados, monkeypatch):
    database.guardar_cambio(config.database_path, "solana", "solana:%5.0")

    main.atender(config, _mensaje("/dejar sol"))

    assert "Dejo de vigilar <b>Solana</b>" in enviados[0]
    assert database.get_cambios(config.database_path)["solana"] is None


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


def test_dejar_varias(config, enviados):
    for coin_id in ("solana", "ethereum", "cardano"):
        database.guardar_cambio(config.database_path, coin_id, f"{coin_id}:%5.0")

    main.atender(config, _mensaje("/dejar sol, eth ada"))

    esperado = "Dejo de vigilar <b>Solana</b>, <b>Ethereum</b> y <b>Cardano</b>"
    assert esperado in enviados[0]
    cambios = database.get_cambios(config.database_path)
    assert cambios["solana"] is cambios["ethereum"] is cambios["cardano"] is None


def test_dejar_varias_con_alguna_que_no_vigilo(config, enviados):
    database.guardar_cambio(config.database_path, "solana", "solana:%5.0")

    main.atender(config, _mensaje("/dejar solana dogecoin"))

    assert "Dejo de vigilar <b>Solana</b>." in enviados[0]
    assert "No estaba vigilando <b>dogecoin</b>" in enviados[0]
    assert database.get_cambios(config.database_path)["solana"] is None


def test_dejar_varias_sin_ninguna_vigilada(config, enviados):
    main.atender(config, _mensaje("/dejar dogecoin pepe"))

    assert "No estoy vigilando <b>dogecoin</b> ni <b>pepe</b>" in enviados[0]


def test_dejar_todas_no_quita_ninguna(config, enviados):
    database.guardar_cambio(config.database_path, "solana", "solana:%5.0")

    main.atender(config, _mensaje("/dejar btc sol"))

    assert "Son todas las que vigilo" in enviados[0]
    assert database.get_cambios(config.database_path)["solana"] == "solana:%5.0"
    assert "bitcoin" not in database.get_cambios(config.database_path)


def test_el_status_incluye_lo_de_telegram(config, enviados, monkeypatch):
    database.guardar_cambio(config.database_path, "solana", "solana:%5.0")
    _precio(monkeypatch, {"bitcoin": 63000.0, "solana": 150.0})

    main.atender(config, _mensaje("/status"))

    assert "<b>Solana</b>" in enviados[0]


def test_vigilar_un_rango_no_promete_esperar(config, enviados):
    main.atender(config, _mensaje("/vigilar bitcoin 55000 75000"))

    assert "si baja de €55.000,00 o si sube de €75.000,00" in enviados[0]
    assert "primer ciclo" not in enviados[0]


# --- /compra y /venta ---


def _con_cartera(config, *posiciones):
    from dataclasses import replace

    return replace(config, cartera=posiciones)


def test_comprar_algo_nuevo(config, enviados, monkeypatch):
    pedidas = _precio(monkeypatch, {"bitcoin": 63000.0, "solana": 150.0})

    main.atender(config, _mensaje("/compra solana 5 700"))
    main.ejecutar_ciclo(config, {})

    assert "Apunto <b>5</b> de Solana por €700,00" in enviados[0]
    assert "Ahora tienes 5, que te costaron €700,00" in enviados[0]
    assert database.get_cambios_cartera(config.database_path) == {
        "solana": Posicion("solana", 5, 700)
    }
    assert pedidas[-1] == ["bitcoin", "solana"]  # el ciclo ya la consulta


def test_comprar_sin_coste_va_al_precio_de_ahora(config, enviados, monkeypatch):
    _precio(monkeypatch, {"solana": 150.0})

    main.atender(config, _mensaje("/compra solana 2"))

    assert "por €300,00" in enviados[0]


def test_comprar_algo_que_no_existe(config, enviados, monkeypatch):
    _precio(monkeypatch, {})

    main.atender(config, _mensaje("/compra solanna 5 700"))

    assert "/buscar solanna" in enviados[0]
    assert database.get_cambios_cartera(config.database_path) == {}


def test_comprar_mas_de_lo_del_env(config, enviados, monkeypatch):
    def no_llamar(*a):
        raise AssertionError("ya la tenia y dice el coste, no hace falta el precio")

    monkeypatch.setattr(coingecko, "get_prices", no_llamar)
    config = _con_cartera(config, Posicion("bitcoin", 0.016, 1000))

    main.atender(config, _mensaje("/compra bitcoin 0,01 600"))

    assert "Ahora tienes 0,026, que te costaron €1.600,00" in enviados[0]


def test_comprar_mal_escrito(config, enviados):
    main.atender(config, _mensaje("/compra bitcoin"))

    assert "/compra bitcoin 0.01 600" in enviados[0]
    assert database.get_cambios_cartera(config.database_path) == {}


def test_vender_una_parte(config, enviados):
    config = _con_cartera(config, Posicion("bitcoin", 0.02, 1000))

    main.atender(config, _mensaje("/venta bitcoin 0.005"))

    assert "venta de <b>0,005</b> de Bitcoin" in enviados[0]
    assert "Te quedan 0,015, que te costaron €750,00" in enviados[0]


def test_vender_todo_la_quita_de_la_cartera(config, enviados, monkeypatch):
    config = _con_cartera(
        config,
        Posicion("bitcoin", 0.02, 1000),
        Posicion("ethereum", 0.4, 1000),
    )
    _precio(monkeypatch, {"bitcoin": 50000.0, "ethereum": 2000.0})

    main.atender(config, _mensaje("/venta ethereum todo"))
    main.atender(config, _mensaje("/cartera"))

    assert "venta de <b>0,4</b> de Ethereum" in enviados[0]
    assert "Ya no te queda nada de Ethereum" in enviados[0]
    assert "Ethereum" not in enviados[1]
    assert "Total <b>€1.000,00</b>" in enviados[1]


def test_vender_mas_de_lo_que_tienes(config, enviados):
    config = _con_cartera(config, Posicion("bitcoin", 0.02, 1000))

    main.atender(config, _mensaje("/venta bitcoin 1"))
    main.atender(config, _mensaje("/venta solana todo"))

    assert "Solo tienes 0,02 de bitcoin" in enviados[0]
    assert "No tienes solana" in enviados[1]
    assert database.get_cambios_cartera(config.database_path) == {}


def test_compra_lleva_boton_para_deshacerla(config, monkeypatch):
    mandados = _con_botones(monkeypatch)
    _precio(monkeypatch, {"solana": 150.0})

    main.atender(config, _mensaje("/compra solana 5 700"))

    [m] = database.get_movimientos(config.database_path)
    assert mandados[0][1] == [[("↩️ Deshacer", f"/deshacer {m.id}")]]


def test_deshacer_una_compra_mal_apuntada(config, enviados, monkeypatch):
    def no_llamar(*a):
        raise AssertionError("no hace falta el precio")

    monkeypatch.setattr(coingecko, "get_prices", no_llamar)
    config = _con_cartera(config, Posicion("bitcoin", 0.016, 1000))

    main.atender(config, _mensaje("/compra bitcoin 10 600"))
    main.atender(config, _mensaje("/deshacer"))

    assert "Quito la compra de <b>10</b> de Bitcoin" in enviados[1]
    assert "Vuelves a tener 0,016, que te costaron €1.000,00" in enviados[1]
    assert database.get_cambios_cartera(config.database_path) == {
        "bitcoin": Posicion("bitcoin", 0.016, 1000)
    }


def test_deshacer_una_venta_de_todo_la_devuelve(config, enviados, monkeypatch):
    config = _con_cartera(config, Posicion("ethereum", 0.4, 1000))
    _precio(monkeypatch, {"ethereum": 2000.0})

    main.atender(config, _mensaje("/venta ethereum todo"))
    main.atender(config, _mensaje("/deshacer"))
    main.atender(config, _mensaje("/cartera"))

    assert "Quito la venta de <b>0,4</b> de Ethereum" in enviados[1]
    assert "Ethereum" in enviados[2]


def test_un_boton_viejo_no_deshace_la_nueva(config, enviados, monkeypatch):
    _precio(monkeypatch, {"solana": 150.0})
    main.atender(config, _mensaje("/compra solana 5 700"))
    main.atender(config, _mensaje("/compra solana 1 150"))
    viejo, nuevo = sorted(m.id for m in database.get_movimientos(config.database_path))

    main.atender(config, _mensaje(f"/deshacer {viejo}"))

    assert "ya no es la última" in enviados[2]
    assert len(database.get_movimientos(config.database_path)) == 2


def test_pulsar_dos_veces_el_mismo_boton(config, enviados, monkeypatch):
    _precio(monkeypatch, {"solana": 150.0})
    main.atender(config, _mensaje("/compra solana 5 700"))
    main.atender(config, _mensaje("/compra solana 1 150"))
    nuevo = database.get_movimientos(config.database_path)[0].id

    main.atender(config, _mensaje(f"/deshacer {nuevo}"))
    main.atender(config, _mensaje(f"/deshacer {nuevo}"))

    assert "ya está deshecha" in enviados[3]
    assert len(database.get_movimientos(config.database_path)) == 1


def test_deshacer_sin_nada(config, enviados):
    main.atender(config, _mensaje("/deshacer"))

    assert "No hay ninguna compra ni venta" in enviados[0]


def test_movimientos_lista_y_boton_de_la_ultima(config, monkeypatch):
    mandados = _con_botones(monkeypatch)
    _precio(monkeypatch, {"solana": 150.0})
    config = _con_cartera(config, Posicion("solana", 5, 700))
    main.atender(config, _mensaje("/compra solana 1 150"))
    main.atender(config, _mensaje("/venta solana 2"))

    main.atender(config, _mensaje("/movimientos"))

    texto, teclado = mandados[2]
    assert texto.index("Venta de 2 de Solana") < texto.index(
        "Compra de 1 de Solana por €150,00"
    )
    ultima = database.get_movimientos(config.database_path)[0]
    assert teclado == [[("↩️ Deshacer la última", f"/deshacer {ultima.id}")]]


def test_movimientos_sin_nada(config, enviados):
    main.atender(config, _mensaje("/movimientos"))

    assert "No has apuntado ninguna compra ni venta" in enviados[0]


def test_cartera_sin_nada_explica_compra(config, enviados):
    main.atender(config, _mensaje("/cartera"))

    assert "/compra bitcoin 0.016 1000" in enviados[0]


def test_cartera_solo_desde_telegram(config, enviados, monkeypatch):
    _precio(monkeypatch, {"solana": 150.0})

    main.atender(config, _mensaje("/compra solana 2 200"))
    main.atender(config, _mensaje("/cartera"))

    assert "<b>Solana</b>  €300,00" in enviados[1]


# --- /alerta cartera ---


def test_alerta_de_la_cartera(config, enviados, monkeypatch):
    config = _con_cartera(
        config, Posicion("bitcoin", 0.02, 1000), Posicion("ethereum", 0.5)
    )
    _precio(monkeypatch, {"bitcoin": 50000.0, "ethereum": 2000.0})

    main.atender(config, _mensaje("/alerta cartera 2500"))

    assert "cuando <b>tu cartera</b> suba a <b>€2.500,00</b>" in enviados[0]
    assert "Ahora vale €2.000,00" in enviados[0]


def test_alerta_de_la_cartera_en_porcentaje(config, enviados, monkeypatch):
    config = _con_cartera(config, Posicion("bitcoin", 0.02, 1000))
    _precio(monkeypatch, {"bitcoin": 50000.0})

    main.atender(config, _mensaje("/alerta cartera -10%"))

    assert "baje a <b>€900,00</b>" in enviados[0]


def test_alerta_de_la_cartera_salta(config, enviados, monkeypatch):
    config = _con_cartera(
        config, Posicion("bitcoin", 0.02, 1000), Posicion("ethereum", 0.5)
    )
    _precio(monkeypatch, {"bitcoin": 50000.0, "ethereum": 2000.0})
    main.atender(config, _mensaje("/alerta cartera 2500"))
    enviados.clear()

    pedidas = _precio(monkeypatch, {"bitcoin": 70000.0, "ethereum": 2300.0})
    main.ejecutar_ciclo(config, {})

    assert "<b>Tu cartera</b> ha subido de €2.500,00" in enviados[0]
    assert "Ahora vale <b>€2.550,00</b>" in enviados[0]
    assert "cartera" not in pedidas[-1]  # no es una cripto, no se le pide a CoinGecko
    assert database.get_puntuales(config.database_path, "eur") == []


def test_alerta_de_la_cartera_no_salta_sin_todos_los_precios(
    config, enviados, monkeypatch
):
    config = _con_cartera(
        config, Posicion("bitcoin", 0.02, 1000), Posicion("ethereum", 0.5)
    )
    _precio(monkeypatch, {"bitcoin": 50000.0, "ethereum": 2000.0})
    main.atender(config, _mensaje("/alerta cartera 1500"))
    enviados.clear()

    # Sin ethereum la cartera parece valer 1000 y bajaria de 1500, pero no es verdad
    _precio(monkeypatch, {"bitcoin": 50000.0})
    main.ejecutar_ciclo(config, {})

    assert not any("Tu cartera" in t for t in enviados)
    assert len(database.get_puntuales(config.database_path, "eur")) == 1


def test_alerta_de_la_cartera_con_lo_comprado_por_telegram(
    config, enviados, monkeypatch
):
    _precio(monkeypatch, {"solana": 150.0})
    main.atender(config, _mensaje("/compra solana 10 1000"))

    main.atender(config, _mensaje("/alerta cartera 2000"))

    assert "Ahora vale €1.500,00" in enviados[1]


def test_alerta_de_la_cartera_sin_precio(config, enviados, monkeypatch):
    config = _con_cartera(config, Posicion("bitcoin", 0.02, 1000))
    _precio(monkeypatch, {"bitcoin": 50000.0})

    main.atender(config, _mensaje("/alerta cartera"))

    assert "<b>Tu cartera</b> vale €1.000,00" in enviados[0]
    assert "/alerta cartera 1100" in enviados[0]
    assert database.get_puntuales(config.database_path, "eur") == []


def test_alerta_de_la_cartera_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/alerta cartera 5000"))

    assert "No tienes cartera" in enviados[0]
    assert database.get_puntuales(config.database_path, "eur") == []


# --- /bot ---


def test_bot_fuera_del_bucle(config, enviados, monkeypatch):
    monkeypatch.setattr(main, "_pulso", None)

    main.atender(config, _mensaje("/bot"))

    assert "--loop" in enviados[0]


def test_bot_con_el_bucle_en_marcha(config, enviados, monkeypatch):
    from datetime import datetime, timedelta, timezone

    from crypto_tracker import salud

    ahora = datetime.now(timezone.utc)
    pulso = salud.Pulso(ahora=ahora - timedelta(hours=2))
    pulso.exito(ahora - timedelta(minutes=4))
    monkeypatch.setattr(main, "_pulso", pulso)
    database.crear_puntual(config.database_path, "solana", 200.0, True, "eur")

    main.atender(config, _mensaje("/bot"))

    assert "Encendido desde hace 2 h" in enviados[0]
    assert "Último ciclo bueno: hace 4 min" in enviados[0]
    assert "Vigilo 1 cripto · 1 alerta puesta" in enviados[0]


def test_bot_cuenta_las_consultas_del_mes(config, enviados, monkeypatch):
    from datetime import datetime, timezone

    from crypto_tracker import cuota, salud

    ahora = datetime.now(timezone.utc)
    database.sumar_consultas(config.database_path, cuota.mes(ahora), 812)
    monkeypatch.setattr(main, "_pulso", salud.Pulso(ahora=ahora))

    main.atender(config, _mensaje("/bot"))

    assert "📡 812 de 10.000 consultas" in enviados[0]


def test_el_bucle_deja_su_pulso_para_bot(config, enviados, monkeypatch):
    monkeypatch.setattr(main, "_pulso", None)
    monkeypatch.setattr(telegram, "set_commands", lambda *a: True)
    monkeypatch.setattr(main, "ejecutar_ciclo", lambda c, e, s: (e, None))
    monkeypatch.setattr(main, "apuntar_consultas", lambda c: None)

    def corta(*a):
        raise KeyboardInterrupt

    monkeypatch.setattr(main, "esperar_escuchando", corta)

    with pytest.raises(KeyboardInterrupt):
        main.ejecutar_bucle(config, {})

    assert main._pulso is not None
    assert main._pulso.ultimo_bien is not None


def _arrancar_bucle(config, monkeypatch):
    """Arranca --loop y lo corta tras el primer ciclo."""
    monkeypatch.setattr(telegram, "set_commands", lambda *a: True)
    monkeypatch.setattr(main, "ejecutar_ciclo", lambda c, e, s: (e, None))
    monkeypatch.setattr(main, "apuntar_consultas", lambda c: None)

    def corta(*a):
        raise KeyboardInterrupt

    monkeypatch.setattr(main, "esperar_escuchando", corta)
    with pytest.raises(KeyboardInterrupt):
        main.ejecutar_bucle(config, {})


def test_avisa_al_encenderse(config, enviados, monkeypatch):
    _arrancar_bucle(config, monkeypatch)

    assert "Encendido: vigilo 1 cripto cada 5 min." in enviados[0]
    assert "apagado" not in enviados[0]  # nunca habia guardado nada


def test_al_encenderse_dice_cuanto_estuvo_apagado(config, enviados, monkeypatch):
    _precio_hace(config, 60000.0, 3 * 60)

    _arrancar_bucle(config, monkeypatch)

    assert "Llevaba apagado desde el" in enviados[0]
    assert "(3 h)" in enviados[0]


def test_al_encenderse_cuenta_lo_de_telegram(config, enviados, monkeypatch):
    database.guardar_cambio(config.database_path, "solana", "solana:%5.0")

    _arrancar_bucle(config, monkeypatch)

    assert "vigilo 2 criptos" in enviados[0]


def test_el_aviso_de_encendido_suena_bajito_de_noche(config, monkeypatch):
    mandados = []
    monkeypatch.setattr(
        telegram,
        "send_message",
        lambda token, chat, texto, **kw: mandados.append(kw) or True,
    )
    monkeypatch.setattr(main, "_sin_sonido", lambda c: True)

    _arrancar_bucle(config, monkeypatch)

    assert mandados[0]["sin_sonido"] is True


# --- /precio ---


def test_precio_de_una_que_no_vigilas(config, enviados, monkeypatch):
    pedidas = _precio(monkeypatch, {"solana": 150.0})
    monkeypatch.setattr(coingecko, "_cambios", {"solana": 2.5})

    main.atender(config, _mensaje("/precio Solana"))

    assert pedidas == [["solana"]]  # una sola consulta, sin lo vigilado
    assert "💰 <b>Solana</b>  €150,00\n🔺 +2.50% en 24 h" in enviados[0]
    assert "CoinGecko" in enviados[0]


def test_precio_con_el_simbolo(config, enviados, monkeypatch):
    pedidas = _precio(monkeypatch, {"bitcoin": 63000.0})

    main.atender(config, _mensaje("/precio BTC"))

    assert pedidas == [["bitcoin"]]
    assert "💰 <b>Bitcoin</b>  €63.000,00" in enviados[0]


def test_precio_tira_del_historico_si_coingecko_no_da_el_24h(
    config, enviados, monkeypatch
):
    _precio(monkeypatch, {"bitcoin": 66000.0})
    _precio_hace(config, 60000.0, 24 * 60 + 5)

    main.atender(config, _mensaje("/price bitcoin"))

    assert "🔺 +10.00% en 24 h" in enviados[0]


def test_precio_de_algo_que_no_existe(config, enviados, monkeypatch):
    _precio(monkeypatch, {})

    main.atender(config, _mensaje("/precio solanna"))

    assert "/buscar solanna" in enviados[0]


def test_precio_a_secas_saca_las_que_vigilas(config, enviados, monkeypatch):
    from dataclasses import replace

    con_dos = replace(
        config, watchlist=[Watch("bitcoin", percent=5), Watch("solana", step=10)]
    )
    pedidas = _precio(monkeypatch, {"bitcoin": 63000.0, "solana": 150.0})

    main.atender(con_dos, _mensaje("/precio"))

    assert pedidas == [["bitcoin", "solana"]]
    assert "<b>Bitcoin</b>  €63.000,00" in enviados[0]
    assert "<b>Solana</b>  €150,00" in enviados[0]


def test_precio_a_secas_cuenta_lo_de_telegram(config, enviados, monkeypatch):
    database.guardar_cambio(config.database_path, "solana", "solana:10.0")
    pedidas = _precio(monkeypatch, {"bitcoin": 63000.0, "solana": 150.0})

    main.atender(config, _mensaje("/precio"))

    assert pedidas == [["bitcoin", "solana"]]


def test_precio_a_secas_no_pasa_del_maximo(config, enviados, monkeypatch):
    from dataclasses import replace

    muchas = replace(config, watchlist=[Watch(f"c{i}", step=1) for i in range(12)])
    pedidas = _precio(monkeypatch, {})

    main.atender(muchas, _mensaje("/precio"))

    assert pedidas == [[f"c{i}" for i in range(10)]]


def test_precio_de_varias(config, enviados, monkeypatch):
    pedidas = _precio(monkeypatch, {"bitcoin": 63000.0, "solana": 150.0})
    monkeypatch.setattr(coingecko, "_cambios", {"bitcoin": -1.5, "solana": 2.5})

    main.atender(config, _mensaje("/precio btc, sol"))

    assert pedidas == [["bitcoin", "solana"]]  # en una sola consulta
    assert "<b>Bitcoin</b>  €63.000,00  🔻 -1.50%" in enviados[0]
    assert "<b>Solana</b>  €150,00  🔺 +2.50%" in enviados[0]
    assert enviados[0].index("Bitcoin") < enviados[0].index("Solana")  # en tu orden
    assert "CoinGecko" in enviados[0]


def test_precio_de_varias_con_alguna_mal(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 63000.0})

    main.atender(config, _mensaje("/precio bitcoin solanna"))

    assert "<b>Bitcoin</b>  €63.000,00" in enviados[0]
    assert "No encuentro <b>solanna</b>" in enviados[0]


def test_precio_de_varias_todas_mal(config, enviados, monkeypatch):
    _precio(monkeypatch, {})

    main.atender(config, _mensaje("/precio bitcion solanna"))

    assert "No encuentro <b>bitcion</b>, <b>solanna</b>" in enviados[0]
    assert "/buscar bitcion" in enviados[0]


def test_precio_repetida_cuenta_una(config, enviados, monkeypatch):
    pedidas = _precio(monkeypatch, {"bitcoin": 63000.0})

    main.atender(config, _mensaje("/precio btc bitcoin"))

    assert pedidas == [["bitcoin"]]
    assert "💰 <b>Bitcoin</b>  €63.000,00" in enviados[0]  # como con una sola


def test_precio_de_demasiadas(config, enviados, monkeypatch):
    pedidas = _precio(monkeypatch, {})

    main.atender(config, _mensaje("/precio " + " ".join(f"c{i}" for i in range(11))))

    assert "Como mucho 10" in enviados[0]
    assert pedidas == []


def test_precio_sin_conexion(config, enviados, monkeypatch):
    def falla(ids, cur):
        raise coingecko.CoinGeckoError("Sin conexion con CoinGecko")

    monkeypatch.setattr(coingecko, "get_prices", falla)

    main.atender(config, _mensaje("/precio solana"))

    assert "No he podido mirar el precio" in enviados[0]


# --- /convertir ---


def test_convertir_cripto_a_dinero(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 62000.0})

    main.atender(config, _mensaje("/convertir 0.05 bitcoin"))

    assert "💱 0,05 Bitcoin = <b>€3.100,00</b>" in enviados[0]
    assert "<i>1 Bitcoin = €62.000,00</i>" in enviados[0]
    assert "CoinGecko" in enviados[0]


def test_convertir_dinero_a_cripto(config, enviados, monkeypatch):
    _precio(monkeypatch, {"solana": 150.0})

    main.atender(config, _mensaje("/convertir 500€ solana"))

    assert "💱 €500,00 = <b>3,33333333 Solana</b>" in enviados[0]


def test_convertir_algo_que_no_existe(config, enviados, monkeypatch):
    _precio(monkeypatch, {})

    main.atender(config, _mensaje("/convertir 1 solanna"))

    assert "/buscar solanna" in enviados[0]


def test_convertir_mal_escrito(config, enviados, monkeypatch):
    pedidas = _precio(monkeypatch, {"solana": 150.0})

    main.atender(config, _mensaje("/convertir"))
    main.atender(config, _mensaje("/convertir 500 usd solana"))

    assert "/convertir 0.05 bitcoin" in enviados[0]
    assert "en EUR, no en USD" in enviados[1]
    assert pedidas == []  # no gasta consultas en lo que no entiende


# --- /exportar ---


@pytest.fixture
def archivos(monkeypatch):
    lista = []
    monkeypatch.setattr(
        telegram,
        "send_document",
        lambda token, chat, contenido, nombre, pie="": (
            lista.append((contenido, nombre, pie)) or True
        ),
    )
    return lista


def test_exportar(config, enviados, archivos):
    _precio_hace(config, 60000.0, 60)
    _precio_hace(config, 61000.5, 30)
    _precio_hace(config, 99999.0, 40 * 24 * 60)  # fuera de los 30 dias

    main.atender(config, _mensaje("/exportar bitcoin"))

    contenido, nombre, pie = archivos[0]
    lineas = contenido.decode("utf-8-sig").splitlines()
    assert lineas[0] == "fecha;precio_eur"
    assert [linea.split(";")[1] for linea in lineas[1:]] == ["60000", "61000,5"]
    assert nombre.startswith("bitcoin-30d-") and nombre.endswith(".csv")
    assert "2 precios de <b>bitcoin</b>, últimos 30 días" in pie
    assert "Solo los tengo desde" in pie  # hay una hora, no un mes
    assert enviados == []


def test_exportar_con_tramo(config, archivos):
    _precio_hace(config, 60000.0, 60)
    _precio_hace(config, 61000.0, 3 * 60)

    main.atender(config, _mensaje("/exportar bitcoin 2h"))

    assert archivos[0][0].decode("utf-8-sig").count("\r\n") == 2  # cabecera y uno


def test_exportar_sin_precios(config, enviados, archivos):
    main.atender(config, _mensaje("/exportar Bitcion"))

    assert "No tengo precios de <b>bitcion</b>" in enviados[0]
    assert archivos == []


def test_exportar_mal_escrito(config, enviados, archivos):
    main.atender(config, _mensaje("/exportar"))

    assert "/exportar bitcoin 30d" in enviados[0]


def test_exportar_si_falla_el_archivo_lo_dice(config, enviados, monkeypatch):
    _precio_hace(config, 60000.0, 60)
    monkeypatch.setattr(telegram, "send_document", lambda *a, **k: False)

    main.atender(config, _mensaje("/exportar bitcoin"))

    assert "No he podido mandarte el archivo" in enviados[0]


# --- /ath ---


def _maximos(monkeypatch, maximos):
    from crypto_tracker.maximo import Maximo

    pedidas = []

    def maximos_falsos(coin_ids, currency):
        pedidas.append(coin_ids)
        return {
            c: Maximo(c, precio, maximo, datetime(2026, 3, 14, tzinfo=timezone.utc))
            for c, (precio, maximo) in maximos.items()
            if c in coin_ids
        }

    monkeypatch.setattr(coingecko, "maximos", maximos_falsos)
    return pedidas


def test_ath(config, enviados, monkeypatch):
    pedidas = _maximos(monkeypatch, {"bitcoin": (75000.0, 100000.0)})

    main.atender(config, _mensaje("/ath btc"))

    assert pedidas == [["bitcoin"]]
    assert "🏔 <b>Bitcoin</b>  máximo histórico €100.000,00" in enviados[0]
    assert "El 14/03/2026, hace" in enviados[0]
    assert "Ahora €75.000,00 · le falta +33.33% para volver" in enviados[0]
    assert "CoinGecko" in enviados[0]


def test_ath_en_maximos(config, enviados, monkeypatch):
    _maximos(monkeypatch, {"bitcoin": (100000.0, 100000.0)})

    main.atender(config, _mensaje("/maximo bitcoin"))

    assert "🎉 está en máximos" in enviados[0]


def test_ath_de_varias(config, enviados, monkeypatch):
    _maximos(monkeypatch, {"bitcoin": (75000.0, 100000.0), "solana": (250.0, 250.0)})

    main.atender(config, _mensaje("/ath btc sol bitcion"))

    assert "<b>Bitcoin</b>  €100.000,00 <i>(03/2026)</i>  +33.33%" in enviados[0]
    assert "<b>Solana</b>  €250,00 <i>(03/2026)</i>  🎉 en máximos" in enviados[0]
    assert "No encuentro <b>bitcion</b>" in enviados[0]


def test_ath_a_secas_las_que_vigilas(config, enviados, monkeypatch):
    pedidas = _maximos(monkeypatch, {"bitcoin": (75000.0, 100000.0)})

    main.atender(config, _mensaje("/ath"))

    assert pedidas == [["bitcoin"]]
    assert "máximo histórico" in enviados[0]


def test_ath_que_no_existe(config, enviados, monkeypatch):
    _maximos(monkeypatch, {})

    main.atender(config, _mensaje("/ath bitcion"))

    assert "No encuentro <b>bitcion</b>" in enviados[0]


def test_ath_sin_conexion(config, enviados, monkeypatch):
    def falla(*a, **k):
        raise coingecko.CoinGeckoError("Sin conexion con CoinGecko")

    monkeypatch.setattr(coingecko, "maximos", falla)

    main.atender(config, _mensaje("/ath bitcoin"))

    assert "No he podido mirarlo ahora mismo: Sin conexion" in enviados[0]


# --- /tendencias ---


def test_tendencias(config, monkeypatch):
    from crypto_tracker.tendencias import Tendencia

    mandados = []
    monkeypatch.setattr(
        telegram,
        "send_message",
        lambda token, chat, texto, **kw: mandados.append((texto, kw)) or True,
    )
    monkeypatch.setattr(
        coingecko,
        "tendencias_hoy",
        lambda currency: [
            Tendencia("pepe", "Pepe", "PEPE", 30, 12.5),
            Tendencia("nueva", "Nueva <3", "", None, None),
        ],
    )

    main.atender(config, _mensaje("/trending"))

    texto, kw = mandados[0]
    assert "1. <b>Pepe</b> PEPE <i>#30</i>  🔺 +12.50%" in texto
    assert "2. <b>Nueva &lt;3</b>\n" in texto
    assert "CoinGecko" in texto
    assert kw["botones"] == [
        [("🎯 PEPE", "/alerta pepe"), ("🎯 Nueva <3", "/alerta nueva")]
    ]


def test_tendencias_vacias(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "tendencias_hoy", lambda currency: [])

    main.atender(config, _mensaje("/tendencias"))

    assert "no me ha dado tendencias" in enviados[0]


def test_tendencias_sin_conexion(config, enviados, monkeypatch):
    def falla(*a, **k):
        raise coingecko.CoinGeckoError("Sin conexion con CoinGecko")

    monkeypatch.setattr(coingecko, "tendencias_hoy", falla)

    main.atender(config, _mensaje("/tendencias"))

    assert "No he podido mirarlo ahora mismo: Sin conexion" in enviados[0]


# --- /top ---


def test_top(config, monkeypatch):
    from crypto_tracker.top import Movida

    mandados = _con_botones(monkeypatch)
    monkeypatch.setattr(
        coingecko,
        "top_hoy",
        lambda currency: [
            Movida("solana", "Solana", "SOL", 150.0, 12.5),
            Movida("pepe", "Pepe <3", "", 0.00001, -9.1),
            Movida("tether", "Tether", "USDT", 0.92, 0.0),
        ],
    )

    main.atender(config, _mensaje("/top"))

    texto, teclado = mandados[0]
    assert texto.index("Suben") < texto.index("SOL") < texto.index("Bajan")
    assert "<b>SOL</b>  +12.50%" in texto
    assert "Pepe &lt;3" in texto  # sin simbolo, el nombre, escapado
    assert "USDT" not in texto
    assert teclado == [[("🔄 Actualizar", "/top")]]


def test_top_todo_en_verde(config, enviados, monkeypatch):
    from crypto_tracker.top import Movida

    monkeypatch.setattr(
        coingecko,
        "top_hoy",
        lambda currency: [Movida("solana", "Solana", "SOL", 150.0, 2.0)],
    )

    main.atender(config, _mensaje("/top"))

    assert "Hoy no baja ninguna" in enviados[0]


def test_top_sin_datos(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "top_hoy", lambda currency: [])

    main.atender(config, _mensaje("/top"))

    assert "no me ha dado los precios" in enviados[0]


def test_top_sin_conexion(config, enviados, monkeypatch):
    def falla(*a, **k):
        raise coingecko.CoinGeckoError("Sin conexion con CoinGecko")

    monkeypatch.setattr(coingecko, "top_hoy", falla)

    main.atender(config, _mensaje("/top"))

    assert "No he podido mirarlo ahora mismo: Sin conexion" in enviados[0]


# --- /miedo ---


def test_miedo(config, monkeypatch):
    from datetime import date

    from crypto_tracker.miedo import Indice

    mandados = _con_botones(monkeypatch)
    monkeypatch.setattr(
        miedo,
        "pedir",
        lambda: [
            Indice(64, "Greed", date(2026, 10, 10)),
            Indice(59, "Greed", date(2026, 10, 9)),
            Indice(20, "Extreme Fear", date(2026, 10, 3)),
        ],
    )

    main.atender(config, _mensaje("/miedo"))

    texto, teclado = mandados[0]
    assert "😏 <b>Miedo y codicia: 64</b> · Codicia" in texto
    assert "▰▰▰▰▰▰▱▱▱▱" in texto
    assert "Ayer 59 😏 · Hace una semana 20 😱" in texto
    assert "alternative.me" in texto
    assert teclado == [[("🔄 Actualizar", "/miedo")]]


def test_miedo_sin_ayer(config, enviados, monkeypatch):
    from datetime import date

    from crypto_tracker.miedo import Indice

    monkeypatch.setattr(
        miedo, "pedir", lambda: [Indice(8, "Extreme Fear", date(2026, 10, 10))]
    )

    main.atender(config, _mensaje("/miedo"))

    assert "▰▱▱▱▱▱▱▱▱▱" in enviados[0]
    assert "Ayer" not in enviados[0]


def test_miedo_sin_conexion(config, enviados, monkeypatch):
    def falla():
        raise miedo.MiedoError("alternative.me no contesta")

    monkeypatch.setattr(miedo, "pedir", falla)

    main.atender(config, _mensaje("/miedo"))

    assert "No he podido mirarlo ahora mismo: alternative.me" in enviados[0]


# --- /mercado ---


def test_mercado(config, monkeypatch):
    from crypto_tracker.mercado import Mercado

    mandados = []
    monkeypatch.setattr(
        telegram,
        "send_message",
        lambda token, chat, texto, **kw: mandados.append((texto, kw)) or True,
    )
    monkeypatch.setattr(
        coingecko,
        "mercado_global",
        lambda currency: Mercado(2.51e12, -4.31, 58.83, 11.0, 9.16),
    )

    main.atender(config, _mensaje("/mercado"))

    texto, kw = mandados[0]
    assert "🌍 <b>Mercado cripto</b>  €2,51 billones\n🔻 -4.31% en 24 h" in texto
    assert "<b>Bitcoin</b>  58.8% del total" in texto
    assert "<b>Ethereum</b>  11.0% del total" in texto
    assert "<b>Estables</b>  9.2% del total" in texto
    assert "CoinGecko" in texto
    assert kw["botones"] == [[("🔄 Actualizar", "/mercado")]]


def test_mercado_a_medias(config, enviados, monkeypatch):
    from crypto_tracker.mercado import Mercado

    monkeypatch.setattr(
        coingecko,
        "mercado_global",
        lambda currency: Mercado(None, None, 58.83, None, None),
    )

    main.atender(config, _mensaje("/global"))

    assert "<b>Bitcoin</b>  58.8% del total" in enviados[0]
    assert "Ethereum" not in enviados[0]
    assert "en 24 h" not in enviados[0]
    assert "USDT" not in enviados[0]


def test_mercado_sin_datos(config, enviados, monkeypatch):
    from crypto_tracker.mercado import Mercado

    monkeypatch.setattr(
        coingecko,
        "mercado_global",
        lambda currency: Mercado(None, None, None, None, None),
    )

    main.atender(config, _mensaje("/mercado"))

    assert "no me ha dado los datos del mercado" in enviados[0]


def test_mercado_sin_conexion(config, enviados, monkeypatch):
    def falla(*a, **k):
        raise coingecko.CoinGeckoError("Sin conexion con CoinGecko")

    monkeypatch.setattr(coingecko, "mercado_global", falla)

    main.atender(config, _mensaje("/mercado"))

    assert "No he podido mirarlo ahora mismo: Sin conexion" in enviados[0]


# --- /comparar ---


def _precio_de(config, coin_id, precio, minutos):
    import sqlite3
    from datetime import timedelta

    cuando = datetime.now(timezone.utc) - timedelta(minutes=minutos)
    conn = sqlite3.connect(config.database_path)
    conn.execute(
        "INSERT INTO prices (coin_id, price, currency, created_at) VALUES (?,?,?,?)",
        (coin_id, precio, "eur", cuando.isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()


def test_comparar(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    for coin_id, antes, ahora in [
        ("bitcoin", 100.0, 110.0),
        ("ethereum", 100.0, 80.0),
        ("solana", 100.0, 150.0),
        ("cardano", 100.0, 100.0),
    ]:
        _precio_de(config, coin_id, antes, 6 * 24 * 60 + 23 * 60)
        _precio_de(config, coin_id, ahora, 5)

    main.atender(config, _mensaje("/comparar btc eth sol ada pepe"))

    texto = enviados[0]
    assert "📊 <b>Cómo les ha ido</b> · <i>últimos 7 días</i>" in texto
    assert texto.index("Solana") < texto.index("Bitcoin") < texto.index("Ethereum")
    assert "🥇 <b>Solana</b>  🔺 +50.00%" in texto
    assert "🥈 <b>Bitcoin</b>  🔺 +10.00%" in texto
    assert "🥉 <b>Cardano</b>  ➖ +0.00%" in texto
    assert "4. <b>Ethereum</b>  🔻 -20.00%" in texto
    assert "No tengo precios guardados de <b>pepe</b>" in texto
    assert "desde el" not in texto


def test_comparar_a_secas_las_que_vigilas(config, enviados):
    _precio_de(config, "bitcoin", 100.0, 2 * 24 * 60)
    _precio_de(config, "bitcoin", 120.0, 5)
    _precio_de(config, "solana", 100.0, 2 * 24 * 60)  # no la vigila
    _precio_de(config, "solana", 200.0, 5)

    main.atender(config, _mensaje("/comparar 30d"))

    assert "últimos 30 días" in enviados[0]
    assert "🥇 <b>Bitcoin</b>  🔺 +20.00% <i>(desde el" in enviados[0]
    assert "Solana" not in enviados[0]


def test_comparar_con_precios_viejos(config, enviados):
    _precio_de(config, "bitcoin", 100.0, 20 * 24 * 60)
    _precio_de(config, "bitcoin", 120.0, 3 * 24 * 60)
    _precio_de(config, "solana", 100.0, 29 * 24 * 60)  # todo el tramo
    _precio_de(config, "solana", 90.0, 3 * 24 * 60)

    main.atender(config, _mensaje("/comparar btc sol 30d"))

    assert "+20.00% <i>(del " in enviados[0]
    assert "-10.00% <i>(hasta el " in enviados[0]


def test_comparar_sin_precios(config, enviados):
    main.atender(config, _mensaje("/comparar btc eth"))

    assert "No tengo precios guardados de ninguna (últimos 7 días)" in enviados[0]


def test_comparar_mal_escrito(config, enviados):
    main.atender(config, _mensaje("/comparar btc 500d"))

    assert "Como mucho un año" in enviados[0]


# --- /volatilidad ---


def test_volatilidad(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    # Un precio al dia: +3%, +2,91%, -4,72%, -0,99%, de media 2,90%
    for dias, precio in [(4, 100.0), (3, 103.0), (2, 106.0), (1, 101.0), (0, 100.0)]:
        _precio_de(config, "bitcoin", precio, dias * 24 * 60 + 5)

    main.atender(config, _mensaje("/volatilidad btc 7d"))

    texto = enviados[0]
    assert "〰️ <b>Bitcoin</b> · <i>últimos 7 días</i>" in texto
    assert "Se mueve de media un <b>2.90%</b> al día <i>(4 días)</i>" in texto
    assert "El día que más: 🔻 -4.72% el" in texto
    assert "%2 → 3 veces" in texto
    assert "%5 → 2 veces" in texto
    assert "%10 → ninguna" in texto
    assert "Solo tengo precios desde el" in texto


def test_volatilidad_a_secas_la_primera_que_vigilas(config, enviados):
    _precio_de(config, "bitcoin", 100.0, 24 * 60 + 5)
    _precio_de(config, "bitcoin", 101.0, 5)

    main.atender(config, _mensaje("/volatilidad"))

    assert "<b>Bitcoin</b> · <i>últimos 30 días</i>" in enviados[0]
    assert "<i>(1 día)</i>" in enviados[0]
    assert "%2 → ninguna" in enviados[0]


def test_volatilidad_sin_precios(config, enviados):
    _precio_de(config, "solana", 100.0, 5)

    main.atender(config, _mensaje("/volatilidad sol"))

    assert "No tengo precios guardados de <b>solana</b> de al menos" in enviados[0]


def test_volatilidad_tramo_corto(config, enviados):
    main.atender(config, _mensaje("/volatilidad btc 12h"))

    assert "Necesito al menos 2 días" in enviados[0]


# --- /si ---


def test_si(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    _precio_hace(config, 50000.0, 29 * 24 * 60)
    _precio_hace(config, 55000.0, 10 * 24 * 60)
    _precio_hace(config, 60000.0, 5)

    main.atender(config, _mensaje("/si 1000 btc"))

    assert "€1.000,00 en <b>Bitcoin</b> hace 30 días" in enviados[0]
    assert "<b>€1.200,00</b>" in enviados[0]
    assert "Solo tengo" not in enviados[0]


def test_si_con_menos_historico(config, enviados):
    _precio_hace(config, 50000.0, 3 * 24 * 60)
    _precio_hace(config, 40000.0, 5)

    main.atender(config, _mensaje("/si 1000 bitcoin 30d"))

    assert "<b>€800,00</b>" in enviados[0]
    assert "Solo tengo precios desde entonces, no de hace 30 días" in enviados[0]


def test_si_sin_precios(config, enviados):
    _precio_hace(config, 50000.0, 5)  # con uno solo no hay nada que comparar

    main.atender(config, _mensaje("/si 1000 bitcoin"))
    main.atender(config, _mensaje("/si 1000 solana"))

    assert "No tengo precios guardados de <b>bitcoin</b>" in enviados[0]
    assert "No tengo precios guardados de <b>solana</b>" in enviados[1]


def test_si_mal_escrito(config, enviados):
    main.atender(config, _mensaje("/si"))
    main.atender(config, _mensaje("/si mucho bitcoin"))

    assert "/si 1000 bitcoin 30d" in enviados[0]
    assert "no es una cantidad" in enviados[1]


def test_si_con_el_ultimo_precio_viejo(config, enviados):
    _precio_hace(config, 50000.0, 6 * 24 * 60)
    _precio_hace(config, 60000.0, 3 * 24 * 60)

    main.atender(config, _mensaje("/si 1000 bitcoin 7d"))

    assert "El último precio que tengo es del" in enviados[0]


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
    main.atender(config, _mensaje("/historico bitcion 7d"))

    assert "últimos 7 días" in enviados[0]
    assert "/buscar bitcion" in enviados[0]


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


# --- botones de los avisos ---


@pytest.fixture
def contestados(monkeypatch):
    lista = []
    monkeypatch.setattr(
        telegram, "answer_callback", lambda token, cid: lista.append(cid) or True
    )
    return lista


def _boton(datos, chat=123):
    return {"id": "q1", "data": datos, "message": {"chat": {"id": chat}}}


def test_el_aviso_lleva_botones(config, monkeypatch):
    mandados = []
    monkeypatch.setattr(
        telegram,
        "send_message",
        lambda token, chat, texto, **kw: mandados.append(kw) or True,
    )
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 90000.0})

    main.ejecutar_ciclo(config, {"bitcoin": "%60000.0"})

    filas = mandados[0]["botones"]
    assert ("📈 Gráfica", "/historico bitcoin") in filas[0]
    assert filas[-1] == [("🔕 Callar 1 h", "/mute 1h")]


def test_boton_de_callar(config, enviados, contestados):
    main.atender_boton(config, _boton("/mute 1h"))

    assert contestados == ["q1"]
    assert database.silenciado_hasta(config.database_path) is not None
    assert "Callado" in enviados[0]


def test_boton_si_vuelve_crea_la_alerta(config, enviados, contestados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 64100.0})

    main.atender_boton(config, _boton("/alerta bitcoin 64000,0"))

    pendientes = database.get_puntuales(config.database_path, "eur")
    assert [(p.coin_id, p.objetivo, p.sube) for p in pendientes] == [
        ("bitcoin", 64000.0, False)
    ]


def test_boton_de_grafica(config, contestados, sin_fotos_de_verdad):
    _con_fecha(config, 60000.0, 2)
    _con_fecha(config, 61000.0, 1)

    main.atender_boton(config, _boton("/historico bitcoin"))

    assert len(sin_fotos_de_verdad) == 1


def test_alertas_lleva_botones_para_quitarlas(config, monkeypatch):
    mandados = []
    monkeypatch.setattr(
        telegram,
        "send_message",
        lambda token, chat, texto, **kw: mandados.append((texto, kw)) or True,
    )
    _precio(monkeypatch, {})
    a = database.crear_puntual(config.database_path, "bitcoin", 70000, True, "eur")
    b = database.crear_puntual(config.database_path, "solana", 100, False, "eur")

    main.atender(config, _mensaje("/alertas"))

    texto, kw = mandados[0]
    assert "Tus alertas" in texto
    assert kw["botones"] == [
        [
            (f"🗑 {a.id} Bitcoin", f"/quitar {a.id}"),
            (f"🗑 {b.id} Solana", f"/quitar {b.id}"),
        ],
        [("🔄 Actualizar", "/alertas"), ("🗑 Quitar todas", "/quitar todas")],
    ]


def test_alertas_sin_ninguna_no_lleva_botones(config, monkeypatch):
    mandados = []
    monkeypatch.setattr(
        telegram,
        "send_message",
        lambda token, chat, texto, **kw: mandados.append(kw) or True,
    )

    main.atender(config, _mensaje("/alertas"))

    assert mandados[0]["botones"] is None


def test_boton_de_quitar_alerta(config, enviados, contestados):
    a = database.crear_puntual(config.database_path, "bitcoin", 70000, True, "eur")
    b = database.crear_puntual(config.database_path, "solana", 100, False, "eur")

    main.atender_boton(config, _boton(f"/quitar {a.id}"))
    main.atender_boton(config, _boton(f"/quitar {a.id}"))  # el mensaje viejo sigue ahi

    assert enviados[0] == "🗑 Alerta quitada."
    assert f"ninguna alerta con el número {a.id}" in enviados[1]
    assert database.get_puntuales(config.database_path, "eur") == [b]


def test_boton_de_otro_chat(config, enviados, contestados):
    main.atender_boton(config, _boton("/mute 1h", chat=999))

    # se contesta para que no se quede cargando, pero no hace nada
    assert contestados == ["q1"]
    assert enviados == []
    assert database.silenciado_hasta(config.database_path) is None


def test_la_espera_atiende_los_botones(config, enviados, contestados, monkeypatch):
    llamadas = []

    def get_updates(token, offset, espera):
        llamadas.append(offset)
        if len(llamadas) == 1:
            return [{"update_id": 9, "callback_query": _boton("/ayuda")}]
        return []

    monkeypatch.setattr(telegram, "get_updates", get_updates)

    assert main.esperar_escuchando(config, 1, None) == 10
    assert contestados == ["q1"]
    assert len(enviados) == 1


# --- resumen semanal ---


@pytest.fixture
def con_semana(config):
    from dataclasses import replace
    from datetime import time as hora

    from crypto_tracker.config import parse_cartera

    return replace(
        config,
        resumen_diario=hora(9, 0),
        cartera=parse_cartera("bitcoin:0.1:5000,solana:10:1000"),
    )


def _guardar(config, coin_id, precio, horas_atras):
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


def _semana_guardada(config):
    for coin_id, antes, ahora in (("bitcoin", 60000.0, 63000.0), ("solana", 100, 95)):
        _guardar(config, coin_id, antes, 7 * 24 - 1)
        _guardar(config, coin_id, ahora, 0)


DOMINGO = _dia(9, 30, dia=27)
LUNES = _dia(9, 30, dia=28)


def test_semanal_el_domingo(con_semana, enviados, sin_fotos_de_verdad):
    _semana_guardada(con_semana)

    main.resumen_semanal(con_semana, DOMINGO)

    [(png, pie)] = sin_fotos_de_verdad
    assert png
    assert "Tu semana" in pie
    assert "+3.57% (+€250,00) en la semana" in pie
    assert pie.index("Bitcoin") < pie.index("Solana")
    assert "Solo tengo precios" not in pie
    assert enviados == []


def test_semanal_una_vez(con_semana, sin_fotos_de_verdad):
    _semana_guardada(con_semana)

    main.resumen_semanal(con_semana, DOMINGO)
    main.resumen_semanal(con_semana, DOMINGO)

    assert len(sin_fotos_de_verdad) == 1


def test_semanal_solo_los_domingos(con_semana, sin_fotos_de_verdad):
    _semana_guardada(con_semana)

    main.resumen_semanal(con_semana, LUNES)

    assert sin_fotos_de_verdad == []


def test_semanal_sin_cartera(con_resumen, enviados, sin_fotos_de_verdad):
    main.resumen_semanal(con_resumen, DOMINGO)

    assert enviados == [] and sin_fotos_de_verdad == []


def test_semanal_sin_precios_no_manda_ni_insiste(con_semana, enviados):
    main.resumen_semanal(con_semana, DOMINGO)

    assert enviados == []
    ultimo = database.ultimo_resumen(con_semana.database_path, database.ULTIMO_SEMANAL)
    assert ultimo == DOMINGO.date()


def test_semanal_callado(con_semana, sin_fotos_de_verdad):
    from datetime import datetime, timedelta, timezone

    _semana_guardada(con_semana)
    hasta = datetime.now(timezone.utc) + timedelta(hours=1)
    database.silenciar_hasta(con_semana.database_path, hasta)

    main.resumen_semanal(con_semana, DOMINGO)

    assert sin_fotos_de_verdad == []
    # al quitar el mute, si sigue en hora, llega
    assert (
        database.ultimo_resumen(con_semana.database_path, database.ULTIMO_SEMANAL)
        is None
    )


def test_semanal_sin_imagen_manda_texto(con_semana, enviados, monkeypatch):
    def falla(*a, **k):
        raise grafica.GraficaError("Falta matplotlib")

    monkeypatch.setattr(grafica, "dibujar", falla)
    _semana_guardada(con_semana)

    main.resumen_semanal(con_semana, DOMINGO)

    assert "Tu semana" in enviados[0]


def test_semanal_reintenta_si_telegram_falla(con_semana, monkeypatch):
    monkeypatch.setattr(telegram, "send_photo", lambda *a, **k: False)
    monkeypatch.setattr(telegram, "send_message", lambda *a, **k: False)
    _semana_guardada(con_semana)

    main.resumen_semanal(con_semana, DOMINGO)

    assert (
        database.ultimo_resumen(con_semana.database_path, database.ULTIMO_SEMANAL)
        is None
    )


def test_semanal_avisa_si_no_hay_semana_entera(con_semana, sin_fotos_de_verdad):
    for coin_id, antes, ahora in (("bitcoin", 60000.0, 63000.0), ("solana", 100, 95)):
        _guardar(con_semana, coin_id, antes, 30)
        _guardar(con_semana, coin_id, ahora, 0)

    main.resumen_semanal(con_semana, DOMINGO)

    assert "Solo tengo precios desde" in sin_fotos_de_verdad[0][1]


# --- boton de actualizar ---


@pytest.fixture
def con_teclado(monkeypatch):
    """Lo que se manda junto con los botones, sea texto o foto."""
    mandados = []
    monkeypatch.setattr(
        telegram,
        "send_message",
        lambda token, chat, texto, **kw: mandados.append((texto, kw)) or True,
    )
    monkeypatch.setattr(
        telegram,
        "send_photo",
        lambda token, chat, png, pie="", **kw: mandados.append((pie, kw)) or True,
    )
    return mandados


def test_status_lleva_boton_de_actualizar(config, con_teclado, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 63000.0})

    main.atender(config, _mensaje("/status"))

    texto, kw = con_teclado[0]
    assert "63.000,00" in texto
    assert kw["botones"] == [[("🔄 Actualizar", "/status")]]


def test_pulsar_actualizar_vuelve_a_consultar(config, con_teclado, monkeypatch):
    pedidas = _precio(monkeypatch, {"bitcoin": 63000.0})

    main.atender_boton(config, _boton("/status"))

    assert len(pedidas) == 1
    assert "63.000,00" in con_teclado[0][0]


def test_pulsar_actualizar_en_alertas_mira_el_precio_de_ahora(
    config, con_teclado, monkeypatch
):
    database.crear_puntual(config.database_path, "bitcoin", 70000, True, "eur")
    pedidas = _precio(monkeypatch, {"bitcoin": 63000.0})

    main.atender_boton(config, _boton("/alertas"))

    assert pedidas == [["bitcoin"]]
    assert "Tus alertas" in con_teclado[0][0]
    assert ("🔄 Actualizar", "/alertas") in con_teclado[0][1]["botones"][-1]


def test_status_sin_precios_no_lleva_boton(config, con_teclado, monkeypatch):
    def falla(ids, cur):
        raise coingecko.CoinGeckoError("Sin conexion")

    monkeypatch.setattr(coingecko, "get_prices", falla)

    main.atender(config, _mensaje("/status"))

    assert con_teclado[0][1]["botones"] is None


def test_cartera_sin_grafica_lleva_boton(con_cartera, con_teclado, monkeypatch):
    _precio(monkeypatch, {p.coin_id: 3000.0 for p in con_cartera.cartera})

    main.atender(con_cartera, _mensaje("/cartera"))

    assert con_teclado[0][1]["botones"] == [[("🔄 Actualizar", "/cartera")]]


def test_la_grafica_de_cartera_lleva_boton_con_su_tramo(
    con_cartera, con_teclado, monkeypatch
):
    for horas, precio in ((100, 50000.0), (50, 55000.0)):
        for coin_id in [p.coin_id for p in con_cartera.cartera]:
            _cartera_con_fecha(con_cartera, coin_id, precio / 20, horas)
    _precio(monkeypatch, {p.coin_id: 3000.0 for p in con_cartera.cartera})

    main.atender(con_cartera, _mensaje("/cartera 7d"))

    pie, kw = con_teclado[0]
    assert "Tu cartera" in pie
    assert kw["botones"] == [[("🔄 Actualizar", "/cartera 7d")]]


def test_si_la_foto_no_pasa_el_texto_lleva_el_boton(
    con_cartera, con_teclado, monkeypatch
):
    for horas, precio in ((100, 50000.0), (50, 55000.0)):
        for coin_id in [p.coin_id for p in con_cartera.cartera]:
            _cartera_con_fecha(con_cartera, coin_id, precio / 20, horas)
    _precio(monkeypatch, {p.coin_id: 3000.0 for p in con_cartera.cartera})
    monkeypatch.setattr(telegram, "send_photo", lambda *a, **kw: False)

    main.atender(con_cartera, _mensaje("/cartera"))

    texto, kw = con_teclado[0]
    assert "Tu cartera" in texto
    assert kw["botones"] == [[("🔄 Actualizar", "/cartera")]]
