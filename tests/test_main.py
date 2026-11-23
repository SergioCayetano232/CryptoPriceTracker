"""Tests de como contesta el bot a lo que le escriben."""

import contextlib
import time
from datetime import datetime, timedelta, timezone

import pytest

import main
from crypto_tracker import (
    binance,
    bola,
    caraocruz,
    coingecko,
    comandos,
    comisionred,
    condicion,
    consejo,
    dado,
    database,
    direccion,
    estacional,
    excusa,
    frase,
    funding,
    grafica,
    inflacion,
    miedo,
    refran,
    tarot,
    telegram,
    vsbolsa,
)
from crypto_tracker.config import Config, Posicion, Watch
from crypto_tracker.precio import Precio
from crypto_tracker.respuestas import cartera as respuestas_cartera
from crypto_tracker.respuestas import resumenes, revisiones


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
def sin_dominancia_de_verdad(monkeypatch):
    """El bucle saca una foto al día del mercado; sin esto iría a CoinGecko."""

    def sin_red(cur):
        raise coingecko.CoinGeckoError("sin red en los tests")

    monkeypatch.setattr(coingecko, "mercado_global", sin_red)


@pytest.fixture(autouse=True)
def sin_miedo_de_verdad(monkeypatch):
    """El resumen diario lo pide; sin esto los tests irian a alternative.me."""
    monkeypatch.setattr(miedo, "pedir", lambda: [])
    monkeypatch.setattr(miedo, "historico", lambda dias: [])


@pytest.fixture(autouse=True)
def sin_cambios_de_coingecko(monkeypatch):
    """Sin esto, la variacion de 24 h de un test aparece en el siguiente."""
    monkeypatch.setattr(coingecko, "_cambios", {})
    monkeypatch.setattr(coingecko, "_usd", {})


@pytest.fixture(autouse=True)
def sin_maximos_de_verdad(monkeypatch):
    """Cada aviso los pide; sin esto los tests de avisos irian a CoinGecko."""
    monkeypatch.setattr(coingecko, "maximos", lambda ids, cur: {})


@pytest.fixture(autouse=True)
def sin_binance_de_verdad(monkeypatch):
    """Si CoinGecko falla en un test, el ciclo tiraria de Binance por internet."""
    monkeypatch.setattr(binance, "precios", lambda ids, cur: {})


def _mensaje(texto, chat=123, hace=0):
    return {"chat": {"id": chat}, "text": texto, "date": int(time.time()) - hace}


def test_contesta_la_ayuda(config, enviados):
    main.atender(config, _mensaje("/start"))

    assert "/status" in enviados[0]


@pytest.mark.parametrize("nombre", list(comandos.COMANDOS))
def test_todos_los_comandos_del_menu_tienen_respuesta(config, monkeypatch, nombre):
    import requests

    def sin_red(*a, **k):
        raise requests.ConnectionError("sin red en los tests")

    monkeypatch.setattr(requests.Session, "request", sin_red)
    monkeypatch.setattr(coingecko.time, "sleep", lambda s: None)  # sin esperas
    no_entendidos = []
    monkeypatch.setattr(
        comandos, "no_entiendo", lambda n, *a: no_entendidos.append(n) or ""
    )

    # Que falle por no tener red da igual: lo que miro es que llegue a su sitio.
    with contextlib.suppress(Exception):
        main.responder(config, nombre, "")

    assert no_entendidos == []


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


def test_mute_a_secas_dice_las_criptos_calladas(config, monkeypatch):
    mandados = _con_botones(monkeypatch)
    main.atender(config, _mensaje("/mute bitcoin 2h"))

    main.atender(config, _mensaje("/mute"))

    texto, filas = mandados[1]
    hasta = database.criptos_calladas(config.database_path)["bitcoin"]
    assert f"<b>Bitcoin</b> hasta las {hasta.astimezone():%H:%M}" in texto
    assert "/unmute bitcoin" in texto
    assert "¿Cuánto tiempo me callo con todas?" in texto
    assert filas[0] == [("🔔 Volver a avisar", "/unmute")]


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


def test_btc_a_secas_da_el_precio(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 63000.0})

    main.atender(config, _mensaje("btc"))

    assert "63.000,00" in enviados[0]


def test_hola_a_secas_no_pide_precios(config, enviados, monkeypatch):
    pedidas = _precio(monkeypatch, {"bitcoin": 63000.0})

    main.atender(config, _mensaje("hola"))

    assert pedidas == []
    assert enviados[0] == comandos.NO_ENTIENDO


@pytest.mark.parametrize(
    "ejemplo",
    [e for ejemplos in comandos.EJEMPLOS.values() for e, _ in ejemplos],
)
def test_los_ejemplos_de_la_ayuda_se_entienden(
    config, enviados, sin_fotos_de_verdad, monkeypatch, ejemplo
):
    from dataclasses import replace

    from crypto_tracker.config import parse_cartera

    _precio(monkeypatch, {"bitcoin": 63000.0, "solana": 150.0, "ethereum": 3000.0})
    con_cartera = replace(config, cartera=parse_cartera("bitcoin:0.1:5000"))

    main.contestar(con_cartera, ejemplo)

    [respuesta] = enviados + [pie for _, pie in sin_fotos_de_verdad]
    for error in ("Escríbelo así", "No entiendo", "no es un", "No te entiendo"):
        assert error not in respuesta


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


def test_resumen_diario_lleva_el_miedo(con_resumen, enviados, monkeypatch):
    from datetime import date

    from crypto_tracker.miedo import Indice

    monkeypatch.setattr(
        miedo,
        "pedir",
        lambda: [
            Indice(20, "Extreme Fear", date(2026, 9, 29)),
            Indice(31, "Fear", date(2026, 9, 28)),
        ],
    )

    main.resumen_diario(con_resumen, _dia(9, 0))

    linea = "😱 Miedo y codicia: <b>20</b> · Miedo extremo  <i>(ayer 31)</i>"
    assert linea in enviados[0]
    assert enviados[0].index(linea) < enviados[0].index("CoinGecko")


def test_resumen_diario_sale_aunque_falle_el_miedo(con_resumen, enviados, monkeypatch):
    def falla():
        raise miedo.MiedoError("alternative.me no contesta")

    monkeypatch.setattr(miedo, "pedir", falla)

    main.resumen_diario(con_resumen, _dia(9, 0))

    assert "resumen del día" in enviados[0]
    assert "Miedo y codicia" not in enviados[0]


def _compra_de(config, cuando, coin_id="bitcoin"):
    import sqlite3

    from crypto_tracker.config import Posicion

    database.init_db(config.database_path)
    numero = database.apuntar_movimiento(
        config.database_path,
        coin_id,
        "compra",
        0.01,
        600.0,
        None,
        Posicion(coin_id, 0.01, 600.0),
    )
    with sqlite3.connect(config.database_path) as conn:
        conn.execute(
            "UPDATE movimientos SET created_at = ? WHERE id = ?",
            (cuando.isoformat(), numero),
        )


def test_resumen_diario_con_aniversario(con_resumen, enviados, monkeypatch):
    pedidas = []

    def precios(ids, cur):
        pedidas.extend(ids)
        return {"bitcoin": 63000.0, "solana": 150.0}

    monkeypatch.setattr(coingecko, "get_prices", precios)
    _compra_de(con_resumen, _dia(12).replace(year=2025))
    _compra_de(con_resumen, _dia(12).replace(year=2024), "solana")
    _compra_de(con_resumen, _dia(12, dia=28).replace(year=2025))  # ayer no

    main.resumen_diario(con_resumen, _dia(9, 0))

    texto = enviados[0]
    assert "🎂 <b>Hoy cumplen años 2 de tus compras</b>" in texto
    assert "Hace 1 año compraste 0,01 de Bitcoin por €600,00" in texto
    assert "Hace 2 años compraste 0,01 de Solana" in texto
    assert texto.index("🎂") < texto.index("CoinGecko")
    # Solana no se vigila, pero su precio viene en la misma consulta.
    assert "solana" in pedidas


def test_resumen_diario_sin_aniversario(con_resumen, enviados):
    _compra_de(con_resumen, _dia(12, dia=28).replace(year=2025))

    main.resumen_diario(con_resumen, _dia(9, 0))

    assert "🎂" not in enviados[0]


def test_status_no_lleva_aniversario(con_resumen, enviados):
    from datetime import datetime

    ahora = datetime.now().astimezone()
    # Cuatro años atrás, que hasta un 29 de febrero tiene su igual.
    _compra_de(con_resumen, ahora.replace(year=ahora.year - 4))

    main.atender(con_resumen, _mensaje("/status"))

    assert "🎂" not in enviados[0]


def test_resumen_cuando_lo_pides(con_resumen, enviados, monkeypatch):
    from datetime import date

    from crypto_tracker.miedo import Indice

    monkeypatch.setattr(
        miedo, "pedir", lambda: [Indice(20, "Extreme Fear", date(2026, 9, 29))]
    )

    main.atender(con_resumen, _mensaje("/resumen"))

    assert "resumen del día" in enviados[0]
    assert "63.000,00" in enviados[0]
    assert "Miedo y codicia: <b>20</b>" in enviados[0]


def test_resumen_a_mano_no_quita_el_de_las_9(con_resumen, enviados, monkeypatch):
    monkeypatch.setattr(miedo, "pedir", lambda: [])

    main.atender(con_resumen, _mensaje("/resumen"))
    main.resumen_diario(con_resumen, _dia(9, 0))

    assert len(enviados) == 2
    assert "resumen del día" in enviados[1]


def test_resumen_sin_coingecko(config, enviados, monkeypatch):
    def falla(ids, cur):
        raise coingecko.CoinGeckoError("Sin conexion")

    monkeypatch.setattr(coingecko, "get_prices", falla)
    monkeypatch.setattr(miedo, "pedir", lambda: [])

    main.atender(config, _mensaje("/resumen"))

    assert "No he podido" in enviados[0]


def test_horario_cambia_la_hora_del_resumen(con_resumen, enviados):
    main.atender(con_resumen, _mensaje("/horario 8:30"))

    assert "a las <b>08:30</b>" in enviados[0]
    main.resumen_diario(con_resumen, _dia(8, 35))
    assert "resumen del día" in enviados[1]


def test_horario_a_las_9_ya_no_toca(con_resumen, enviados):
    main.atender(con_resumen, _mensaje("/horario 20:00"))

    main.resumen_diario(con_resumen, _dia(9, 0))

    assert len(enviados) == 1


def test_horario_no_quita_el_resumen(con_resumen, enviados):
    main.atender(con_resumen, _mensaje("/horario no"))
    main.resumen_diario(con_resumen, _dia(9, 0))

    assert "Ya no te mando el resumen" in enviados[0]
    assert len(enviados) == 1


def test_horario_lo_pone_aunque_el_env_no_lo_tenga(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 63000.0})
    main.atender(config, _mensaje("/horario"))
    main.atender(config, _mensaje("/horario 7"))
    main.resumen_diario(config, _dia(7, 0))

    assert "Ahora no te mando resumen" in enviados[0]
    assert "resumen del día" in enviados[2]


def test_horario_a_secas_dice_la_hora(con_resumen, enviados):
    main.atender(con_resumen, _mensaje("/horario"))

    assert "a las <b>09:00</b>" in enviados[0]


def test_horario_mal_escrito(con_resumen, enviados):
    main.atender(con_resumen, _mensaje("/horario mañana"))

    assert "No entiendo 'mañana'" in enviados[0]
    assert database.hora_resumen(con_resumen.database_path) == (False, None)


def test_el_status_no_lleva_el_miedo(con_resumen, enviados, monkeypatch):
    def no_llamar():
        raise AssertionError("/status no tiene que esperar a alternative.me")

    monkeypatch.setattr(miedo, "pedir", no_llamar)

    main.atender(con_resumen, _mensaje("/status"))

    assert "Miedo y codicia" not in enviados[0]


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


# --- caida de la cartera desde su record ---


@pytest.fixture
def con_bajon(config):
    from dataclasses import replace

    config = replace(config, caida_cartera=20.0, cartera=(Posicion("bitcoin", 0.01),))
    # Récord de 1.000 € hace tres días; luego baja a 900.
    _precio_hace(config, 80000.0, 5 * 24 * 60)
    _precio_hace(config, 100000.0, 3 * 24 * 60)
    _precio_hace(config, 90000.0, 60)
    return config


def test_bajon_avisa(con_bajon, enviados):
    main.revisar_bajon(con_bajon, 750.0, set())

    assert len(enviados) == 1
    assert "caído un 25,0% desde su récord" in enviados[0]


def test_bajon_no_repite(con_bajon, enviados):
    main.revisar_bajon(con_bajon, 750.0, set())
    main.revisar_bajon(con_bajon, 700.0, set())

    assert len(enviados) == 1


def test_bajon_otro_escalon(con_bajon, enviados):
    main.revisar_bajon(con_bajon, 750.0, set())
    main.revisar_bajon(con_bajon, 590.0, set())

    assert len(enviados) == 2
    assert "Ya pasa del 40%" in enviados[1]


def test_bajon_poca_caida(con_bajon, enviados):
    main.revisar_bajon(con_bajon, 850.0, set())

    assert enviados == []


def test_bajon_desactivado(con_bajon, enviados):
    from dataclasses import replace

    main.revisar_bajon(replace(con_bajon, caida_cartera=None), 500.0, set())

    assert enviados == []


def test_bajon_callado_avisa_al_volver(con_bajon, enviados):
    main.revisar_bajon(con_bajon, 750.0, {"cartera"})
    assert enviados == []

    main.revisar_bajon(con_bajon, 750.0, set())
    assert len(enviados) == 1


def test_bajon_si_falla_telegram_lo_intenta_luego(con_bajon, monkeypatch):
    lista = []
    monkeypatch.setattr(telegram, "send_message", lambda *a, **kw: False)
    main.revisar_bajon(con_bajon, 750.0, set())

    monkeypatch.setattr(
        telegram, "send_message", lambda t, c, texto, **kw: lista.append(texto) or True
    )
    main.revisar_bajon(con_bajon, 750.0, set())
    assert len(lista) == 1


def test_bajon_record_nuevo_vuelve_a_empezar(con_bajon, enviados):
    main.revisar_bajon(con_bajon, 750.0, set())
    _precio_hace(con_bajon, 120000.0, 30)

    main.revisar_bajon(con_bajon, 900.0, set())

    assert len(enviados) == 2
    assert "€1.200,00" in enviados[1]


def test_bajon_llega_en_el_ciclo(con_bajon, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 75000.0})

    main.ejecutar_ciclo(con_bajon, {"bitcoin": "%75000.0"})

    assert any("desde su récord" in t for t in enviados)


# --- estables ---


def test_estable_avisa_una_vez_y_al_volver(config, enviados, monkeypatch):
    monkeypatch.setattr(
        coingecko, "get_prices", lambda ids, cur: {"bitcoin": 60000.0, "tether": 0.9}
    )
    monkeypatch.setitem(coingecko._usd, "tether", 0.97)

    main.revisar_estables(config, ["bitcoin", "tether"], set())
    main.revisar_estables(config, ["bitcoin", "tether"], set())

    assert len(enviados) == 1
    assert "USDT se sale de su dólar" in enviados[0]

    monkeypatch.setitem(coingecko._usd, "tether", 0.999)
    main.revisar_estables(config, ["bitcoin", "tether"], set())
    main.revisar_estables(config, ["bitcoin", "tether"], set())

    assert len(enviados) == 2
    assert "USDT</b> vuelve a su dólar" in enviados[1]


def test_estable_llega_en_el_ciclo(config, enviados, monkeypatch):
    from dataclasses import replace

    from crypto_tracker.config import parse_cartera

    def precios(ids, cur):
        coingecko._usd["usd-coin"] = 0.95
        return {"bitcoin": 60000.0, "usd-coin": 0.87}

    monkeypatch.setattr(coingecko, "get_prices", precios)
    con_usdc = replace(config, cartera=parse_cartera("usd-coin:500"))

    main.ejecutar_ciclo(con_usdc, {"bitcoin": "%60000.0"})

    assert any("USDC se sale de su dólar" in t for t in enviados)


def test_estable_callada_espera(config, enviados, monkeypatch):
    monkeypatch.setitem(coingecko._usd, "tether", 0.97)

    main.revisar_estables(config, ["tether"], {"tether"})
    assert enviados == []

    # Al volver a hablar, si sigue fuera, avisa.
    main.revisar_estables(config, ["tether"], set())
    assert len(enviados) == 1


def test_estable_si_no_llega_lo_reintenta(config, monkeypatch):
    mandados = []
    monkeypatch.setattr(
        telegram, "send_message", lambda *a, **k: mandados.append(a[2]) and False
    )
    monkeypatch.setitem(coingecko._usd, "tether", 0.97)

    main.revisar_estables(config, ["tether"], set())
    main.revisar_estables(config, ["tether"], set())

    assert len(mandados) == 2
    assert database.estables_avisadas(config.database_path) == set()


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


def test_el_aviso_dice_lo_que_falta_para_el_maximo(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 90000.0})
    pedidas = _maximos(monkeypatch, {"bitcoin": (89000.0, 108000.0)})

    main.ejecutar_ciclo(config, {"bitcoin": "%60000.0"})

    assert pedidas == [["bitcoin"]]
    # con los 90.000 del aviso, no con los 89.000 de la consulta de máximos
    assert "Le falta +20.00% para su máximo histórico" in enviados[0]


def test_sin_avisos_no_pide_maximos(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 60100.0})
    pedidas = _maximos(monkeypatch, {"bitcoin": (60100.0, 108000.0)})

    main.ejecutar_ciclo(config, {"bitcoin": "%60000.0"})

    assert enviados == []
    assert pedidas == []


def test_si_fallan_los_maximos_el_aviso_sale_igual(config, enviados, monkeypatch):
    def falla(ids, cur):
        raise coingecko.CoinGeckoError("Sin conexion con CoinGecko")

    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 90000.0})
    monkeypatch.setattr(coingecko, "maximos", falla)

    main.ejecutar_ciclo(config, {"bitcoin": "%60000.0"})

    assert "ha subido" in enviados[0]
    assert "histórico" not in enviados[0]


def test_el_aviso_de_la_cartera_no_pide_maximos(config, enviados, monkeypatch):
    from dataclasses import replace

    config = replace(config, cartera=(Posicion("bitcoin", 0.1, 5000.0),))
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 61000.0})
    pedidas = _maximos(monkeypatch, {})
    database.crear_puntual(config.database_path, "cartera", 6000, True, "eur")

    main.ejecutar_ciclo(config, {"bitcoin": "%60000.0"})

    assert "Tu cartera" in enviados[0]
    assert pedidas == []


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

    texto = resumenes.montar_resumen(con_cartera)

    assert pedidas == ["bitcoin", "solana"]
    assert "Tu cartera" in texto
    assert "1.120,00" in texto  # bitcoin: 0.016 * 70000
    assert "1.050,00" in texto  # solana: 7 * 150
    assert "2.170,00" in texto  # total


def test_resumen_sin_cartera_como_antes(config, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 1.0})

    assert "cartera" not in resumenes.montar_resumen(config)


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


def test_cartera_con_el_total_en_sats(con_cartera, enviados, monkeypatch):
    monkeypatch.setattr(
        coingecko, "get_prices", lambda ids, cur: {"bitcoin": 70000.0, "solana": 150.0}
    )

    main.atender(con_cartera, _mensaje("/cartera"))

    assert "<i>En sats: 3.100.000</i>" in enviados[0]


def test_cartera_sin_bitcoin_lo_pide_para_los_sats(config, enviados, monkeypatch):
    from dataclasses import replace

    from crypto_tracker.config import parse_cartera

    config = replace(config, cartera=parse_cartera("solana:7:1000"))
    pedidas = _precio(monkeypatch, {"solana": 150.0, "bitcoin": 70000.0})

    main.atender(config, _mensaje("/cartera"))

    assert pedidas == [["solana", "bitcoin"]]  # en la misma consulta
    assert "<i>En sats: 1.500.000</i>" in enviados[0]
    assert "Bitcoin" not in enviados[0]  # no se cuela en la cartera


def test_cartera_solo_de_bitcoin_sin_sats(config, enviados, monkeypatch):
    from dataclasses import replace

    from crypto_tracker.config import parse_cartera

    config = replace(config, cartera=parse_cartera("bitcoin:0.016:1000"))
    _precio(monkeypatch, {"bitcoin": 70000.0})

    main.atender(config, _mensaje("/cartera"))

    assert "sats" not in enviados[0]


def test_cartera_en_otra_moneda(con_cartera, monkeypatch):
    mandados = _con_botones(monkeypatch)
    pedidas = []

    def precios(ids, cur):
        pedidas.append(cur)
        return {"bitcoin": 80000.0, "solana": 170.0}

    monkeypatch.setattr(coingecko, "get_prices", precios)

    main.atender(con_cartera, _mensaje("/cartera usd"))
    main.atender(con_cartera, _mensaje("/cartera $"))

    texto, teclado = mandados[0]
    assert pedidas == ["usd", "usd"]
    assert "Total <b>$2.470,00</b>\n" in texto  # sin lo que ganas detras
    assert "te salió" not in texto
    assert "solo te lo sé decir en EUR" in texto
    assert teclado == [[("🔄 Actualizar", "/cartera usd")]]
    # En otra moneda no se guarda: el historico va en la del .env.
    assert database.get_last_price(con_cartera.database_path, "bitcoin") is None


def test_cartera_en_la_misma_moneda_como_siempre(con_cartera, enviados, monkeypatch):
    monkeypatch.setattr(
        coingecko, "get_prices", lambda ids, cur: {"bitcoin": 70000.0, "solana": 150.0}
    )

    main.atender(con_cartera, _mensaje("/cartera eur"))

    assert "2.170,00" in enviados[0]
    assert "solo te lo sé decir" not in enviados[0]


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

    # /precio va por /coins/markets; sin variaciones, como si no vinieran.
    def precios_semana(ids, cur):
        pedidas.append(list(ids))
        return {c: Precio(c, p, None, None) for c, p in precios.items() if c in ids}

    monkeypatch.setattr(coingecko, "get_prices", get_prices)
    monkeypatch.setattr(coingecko, "precios_semana", precios_semana)
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


def test_no_crea_dos_veces_la_misma_alerta(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 63000.0})

    main.atender(config, _mensaje("/alerta bitcoin 70.000"))
    main.atender(config, _mensaje("/alerta btc 70000,0"))  # como la manda el boton
    main.atender(config, _mensaje("/alerta bitcoin 70500"))

    [primera, otra] = database.get_puntuales(config.database_path, "eur")
    assert f"Ya tienes esa alerta, es la número {primera.id}" in enviados[1]
    assert otra.objetivo == 70500


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


def test_alertas_la_mas_cerca_primero(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 62500.0, "solana": 125.0})
    database.crear_puntual(config.database_path, "bitcoin", 70000, True, "eur")
    database.crear_puntual(config.database_path, "solana", 100, False, "eur")
    cerca = database.crear_puntual(config.database_path, "bitcoin", 60000, False, "eur")

    main.atender(config, _mensaje("/alertas"))

    texto = enviados[0]
    assert texto.index("-4.00%") < texto.index("+12.00%") < texto.index("-20.00%")
    assert f"Para quitar una: /quitar {cerca.id}" in texto


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


def test_quitar_las_de_una_cripto(config, enviados):
    database.crear_puntual(config.database_path, "bitcoin", 70000, True, "eur")
    sol = database.crear_puntual(config.database_path, "solana", 100, False, "eur")
    database.crear_puntual(config.database_path, "bitcoin", 60000, False, "eur")

    main.atender(config, _mensaje("/quitar BTC"))
    main.atender(config, _mensaje("/quitar bitcoin"))

    assert enviados[0] == "🗑 2 alertas quitadas."
    assert enviados[1] == "No tienes ninguna alerta de bitcoin. Mira /alertas"
    assert database.get_puntuales(config.database_path, "eur") == [sol]


def test_quitar_las_de_la_cartera(config, enviados):
    database.crear_puntual(config.database_path, "cartera", 5000, True, "eur")

    main.atender(config, _mensaje("/quitar cartera"))

    assert enviados[0] == "🗑 Alerta quitada."
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


# --- /mute de una sola cripto ---


@pytest.fixture
def dos_vigiladas(config):
    from dataclasses import replace

    return replace(
        config, watchlist=[Watch("bitcoin", percent=5), Watch("solana", percent=5)]
    )


def _callar(config, coin_id, horas=1):
    from datetime import timedelta

    hasta = datetime.now(timezone.utc) + timedelta(hours=horas)
    database.callar_cripto(config.database_path, coin_id, hasta)


def test_la_callada_no_avisa_y_las_demas_si(dos_vigiladas, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 90000.0, "solana": 300.0})
    _callar(dos_vigiladas, "bitcoin")

    main.ejecutar_ciclo(dos_vigiladas, {"bitcoin": "%60000.0", "solana": "%150.0"})

    assert "Solana" in enviados[0]
    assert "Bitcoin" not in enviados[0]


def test_solo_la_callada_no_manda_nada(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 90000.0})
    _callar(config, "bitcoin")

    estado, _ = main.ejecutar_ciclo(config, {"bitcoin": "%60000.0"})

    assert enviados == []
    # Como el mute de todas: al volver no llega de golpe lo que paso mientras
    assert estado == {"bitcoin": "%90000.0"}


def test_la_alerta_de_una_callada_espera(config, enviados, monkeypatch):
    database.crear_puntual(config.database_path, "bitcoin", 70000, True, "eur")
    _caducada(config, objetivo=95000)
    _precio(monkeypatch, {"bitcoin": 71000.0})
    _callar(config, "bitcoin")

    main.ejecutar_ciclo(config, {"bitcoin": "%71000.0"})

    assert enviados == []
    assert len(database.get_puntuales(config.database_path, "eur")) == 2

    database.callar_cripto(config.database_path, "bitcoin", None)
    main.ejecutar_ciclo(config, {"bitcoin": "%71000.0"})

    assert any("Era tu /alerta" in t for t in enviados)
    assert database.get_puntuales(config.database_path, "eur") == []


def test_mute_de_una_cripto(config, enviados):
    main.atender(config, _mensaje("/mute btc 2h"))

    assert "No te aviso de <b>bitcoin</b> hasta las" in enviados[0]
    assert "/unmute bitcoin" in enviados[0]
    assert set(database.criptos_calladas(config.database_path)) == {"bitcoin"}
    assert database.silenciado_hasta(config.database_path) is None


def test_mute_de_una_cripto_sin_tiempo(config, enviados):
    main.atender(config, _mensaje("/mute btc"))

    assert "¿Cuánto tiempo?" in enviados[0]
    assert database.criptos_calladas(config.database_path) == {}


def test_unmute_de_una_cripto(config, enviados):
    _callar(config, "bitcoin")
    _callar(config, "solana")

    main.atender(config, _mensaje("/unmute btc"))
    main.atender(config, _mensaje("/unmute btc"))

    assert "Vuelvo a avisar de <b>bitcoin</b>" in enviados[0]
    assert "No tenía callada <b>bitcoin</b>" in enviados[1]
    assert set(database.criptos_calladas(config.database_path)) == {"solana"}


def test_unmute_a_secas_quita_tambien_las_de_una_cripto(config, enviados):
    _callar(config, "bitcoin")

    main.atender(config, _mensaje("/unmute"))

    assert enviados[0] == "🔔 Vuelvo a avisar."
    assert database.criptos_calladas(config.database_path) == {}


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


def test_crear_alerta_en_pareja(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 70000.0})

    main.atender(config, _mensaje("/alerta bitcoin 80k o 60.000 7d salir"))

    assert "suba a <b>€80.000,00</b> o baje a <b>€60.000,00</b>" in enviados[0]
    assert "quito la otra" in enviados[0]
    assert "📝 salir" in enviados[0]
    abajo, arriba = database.get_puntuales(config.database_path, "eur")
    assert (abajo.objetivo, abajo.sube, arriba.objetivo, arriba.sube) == (
        60000,
        False,
        80000,
        True,
    )
    assert abajo.caduca == arriba.caduca is not None
    assert abajo.nota == arriba.nota == "salir"
    assert database.parejas(config.database_path) == {
        abajo.id: arriba.id,
        arriba.id: abajo.id,
    }


@pytest.mark.parametrize(
    "texto, error",
    [
        ("/alerta bitcoin 75000 o 80000", "uno por encima y otro por debajo"),
        ("/alerta bitcoin +10% o -5%", "no %"),
        ("/alerta bitcoin 60000 o mucho", "no es un precio"),
    ],
)
def test_crear_alerta_en_pareja_mal(config, enviados, monkeypatch, texto, error):
    _precio(monkeypatch, {"bitcoin": 70000.0})

    main.atender(config, _mensaje(texto))

    assert error in enviados[0]
    assert database.get_puntuales(config.database_path, "eur") == []


@pytest.mark.parametrize("precio, otra", [(59000.0, "80.000"), (81000.0, "60.000")])
def test_la_pareja_salta_y_quita_la_otra(config, enviados, monkeypatch, precio, otra):
    _precio(monkeypatch, {"bitcoin": 70000.0})
    main.atender(config, _mensaje("/alerta bitcoin 60000 o 80000"))
    _precio(monkeypatch, {"bitcoin": precio})

    estado, _ = main.ejecutar_ciclo(config, {"bitcoin": f"%{precio}"})
    main.ejecutar_ciclo(config, estado)

    assert len(enviados) == 2  # el de crearla y un solo aviso
    assert "Era tu /alerta" in enviados[1]
    assert f"Quito la otra de la pareja, la de €{otra},00." in enviados[1]
    assert database.get_puntuales(config.database_path, "eur") == []


def test_la_pareja_sin_saltar_se_quedan_las_dos(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 70000.0})
    main.atender(config, _mensaje("/alerta bitcoin 60000 o 80000"))

    main.ejecutar_ciclo(config, {"bitcoin": "%70000.0"})

    assert len(enviados) == 1
    assert len(database.get_puntuales(config.database_path, "eur")) == 2


def test_alertas_dice_cuales_van_en_pareja(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 70000.0})
    main.atender(config, _mensaje("/alerta bitcoin 60000 o 80000"))
    main.atender(config, _mensaje("/alerta bitcoin 90000"))
    main.atender(config, _mensaje("/alertas"))

    assert enviados[-1].count("🔗") == 2
    assert "va con la 2: si salta una, quito la otra" in enviados[-1]
    assert "va con la 1:" in enviados[-1]

    main.atender(config, _mensaje("/quitar 1"))
    main.atender(config, _mensaje("/alertas"))

    assert "🔗" not in enviados[-1]


def test_quitar_una_de_la_pareja_deja_la_otra_normal(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 70000.0})
    main.atender(config, _mensaje("/alerta bitcoin 60000 o 80000"))
    abajo, arriba = database.get_puntuales(config.database_path, "eur")
    main.atender(config, _mensaje(f"/quitar {abajo.id}"))
    _precio(monkeypatch, {"bitcoin": 81000.0})

    main.ejecutar_ciclo(config, {"bitcoin": "%81000.0"})

    assert "Era tu /alerta" in enviados[-1]
    assert "pareja" not in enviados[-1]
    assert database.get_puntuales(config.database_path, "eur") == []


def test_avisa_una_vez_al_volver_a_lo_que_costo(config, enviados, monkeypatch):
    from dataclasses import replace

    config = replace(config, cartera=(Posicion("solana", 5.0, 1000.0),))  # a 200
    estado = {"bitcoin": "%63000.0"}
    for precio in (150.0, 190.0, 205.0, 210.0):
        _precio(monkeypatch, {"bitcoin": 63000.0, "solana": precio})
        estado, _ = main.ejecutar_ciclo(config, estado)

    assert len(enviados) == 1
    assert "<b>Solana</b> vuelve a lo que te costó, €200,00" in enviados[0]


def test_no_avisa_si_nunca_estuvo_en_perdidas(config, enviados, monkeypatch):
    from dataclasses import replace

    config = replace(config, cartera=(Posicion("solana", 5.0, 1000.0),))
    _precio(monkeypatch, {"bitcoin": 63000.0, "solana": 205.0})

    main.ejecutar_ciclo(config, {"bitcoin": "%63000.0"})

    assert enviados == []


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


def test_vigilar_a_secas_lleva_botones_para_dejarlas(config, monkeypatch):
    mandados = _con_botones(monkeypatch)
    database.guardar_cambio(config.database_path, "solana", "solana:%5.0")

    main.atender(config, _mensaje("/vigilar"))
    main.atender_boton(config, _boton("/dejar solana"))
    main.atender(config, _mensaje("/vigilar"))

    assert mandados[0][1] == [
        [("✖ Bitcoin", "/dejar bitcoin"), ("✖ Solana", "/dejar solana")]
    ]
    assert "Dejo de vigilar <b>Solana</b>" in mandados[1][0]
    assert mandados[2][1] is None  # con una sola no hay nada que dejar


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


def test_comprar_mas_de_lo_del_env_sin_conexion(config, enviados, monkeypatch):
    def falla(*a):
        raise coingecko.CoinGeckoError("Sin conexion con CoinGecko")

    # Ya la tenia y dice el coste: el precio solo es para pillar erratas.
    monkeypatch.setattr(coingecko, "get_prices", falla)
    config = _con_cartera(config, Posicion("bitcoin", 0.016, 1000))

    main.atender(config, _mensaje("/compra bitcoin 0,01 600"))

    assert "Ahora tienes 0,026, que te costaron €1.600,00" in enviados[0]


def test_comprar_a_un_precio_normal_no_avisa(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 60000.0})

    main.atender(config, _mensaje("/compra bitcoin 0.01 620"))

    assert "⚠️" not in enviados[0]


def test_comprar_con_un_cero_de_mas_avisa(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 60000.0})

    main.atender(config, _mensaje("/compra bitcoin 0.01 6000"))

    assert "Esta la pagas a €600.000,00 cada una" in enviados[0]
    assert "ahora está a €60.000,00 (+900%)" in enviados[0]
    assert "Si es una errata, dale a Deshacer." in enviados[0]
    # Avisa, pero la apunta: puede ser de verdad.
    assert len(database.get_movimientos(config.database_path)) == 1


def test_comprar_mal_escrito(config, enviados):
    main.atender(config, _mensaje("/compra bitcoin"))

    assert "/compra bitcoin 0.01 600" in enviados[0]
    assert database.get_cambios_cartera(config.database_path) == {}


def test_vender_una_parte(config, enviados, monkeypatch):
    config = _con_cartera(config, Posicion("bitcoin", 0.02, 1000))
    _precio(monkeypatch, {"bitcoin": 60000.0})

    main.atender(config, _mensaje("/venta bitcoin 0.005"))

    assert "venta de <b>0,005</b> de Bitcoin por €300,00" in enviados[0]
    assert "🔺 Le sacas +€50,00 (+20.00%)." in enviados[0]
    assert "Te quedan 0,015, que te costaron €750,00" in enviados[0]


def test_vender_diciendo_a_cuanto_no_consulta_el_precio(config, enviados, monkeypatch):
    config = _con_cartera(config, Posicion("bitcoin", 0.02, 1000))
    pedidas = _precio(monkeypatch, {"bitcoin": 60000.0})

    main.atender(config, _mensaje("/venta bitcoin 0.005 200"))
    main.atender(config, _mensaje("/venta bitcoin todo @70000"))

    assert pedidas == []
    assert "por €200,00" in enviados[0]
    assert "🔻 Le sacas -€50,00 (-20.00%)." in enviados[0]
    assert "por €1.050,00" in enviados[1]  # las 0,015 que quedaban
    assert "Le sacas +€300,00 (+40.00%)." in enviados[1]


def test_vender_sin_conexion_la_apunta_igual(config, enviados, monkeypatch):
    def falla(ids, cur):
        raise coingecko.CoinGeckoError("Sin conexion con CoinGecko")

    monkeypatch.setattr(coingecko, "get_prices", falla)
    config = _con_cartera(config, Posicion("bitcoin", 0.02, 1000))

    main.atender(config, _mensaje("/venta bitcoin 0.005"))

    assert "Apunto la venta de <b>0,005</b> de Bitcoin.\n" in enviados[0]
    assert "Le sacas" not in enviados[0]
    [venta] = database.get_ventas(config.database_path)
    assert venta.coste is None


def test_ganancias_de_lo_vendido(config, enviados, monkeypatch):
    config = _con_cartera(
        config, Posicion("bitcoin", 0.02, 1000), Posicion("solana", 10, 2000)
    )
    _precio(monkeypatch, {})

    main.atender(config, _mensaje("/venta bitcoin 0.01 700"))
    main.atender(config, _mensaje("/venta solana todo 1500"))
    main.atender(config, _mensaje("/ganancias"))

    texto = enviados[2]
    assert "🔺 <b>Bitcoin</b>  +€200,00" in texto
    assert "🔻 <b>Solana</b>  -€500,00" in texto
    assert texto.index("Bitcoin") < texto.index("Solana")
    assert "Total <b>-€300,00</b>" in texto
    assert "No cuento" not in texto


def test_ganancias_sin_ventas(config, enviados):
    main.atender(config, _mensaje("/ganancias"))

    assert "Todavía no has vendido nada" in enviados[0]


def test_pelotazo(config, enviados, monkeypatch):
    pedidas = _precio(monkeypatch, {"bitcoin": 100000.0, "solana": 100.0})

    main.atender(config, _mensaje("/compra bitcoin 0.01 500"))
    main.atender(config, _mensaje("/compra solana 10 2000"))
    main.atender(config, _mensaje("/pelotazo"))

    texto = enviados[2]
    assert sorted(pedidas[-1]) == ["bitcoin", "solana"]
    assert "🎯 <b>Tu pelotazo: Bitcoin +100.00%</b>" in texto
    assert "🤦 <b>Tu peor compra: Solana -50.00%</b>" in texto


def test_apodo_manos_de_papel(config, enviados, monkeypatch):
    config = _con_cartera(
        config, Posicion("bitcoin", 0.05, 1000), Posicion("solana", 10, 1000)
    )
    _precio(monkeypatch, {"bitcoin": 20000.0, "solana": 100.0})

    main.atender(config, _mensaje("/venta bitcoin 0.01 200"))
    main.atender(config, _mensaje("/venta solana 1 100"))
    main.atender(config, _mensaje("/mote"))

    assert "🧻 Te llamaremos <b>Manos de papel</b>" in enviados[2]
    assert "Has vendido 2 veces y comprado 0" in enviados[2]


def test_apodo_comprador_de_picos(config, enviados, monkeypatch):
    config = _con_cartera(config, Posicion("bitcoin", 0.01, 1000))
    _precio(monkeypatch, {"bitcoin": 30000.0})

    main.atender(config, _mensaje("/apodo"))

    assert "<b>Comprador de picos</b>" in enviados[0]
    assert "Tu cartera va -70%" in enviados[0]


def test_apodo_sin_cartera(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())

    main.atender(config, _mensaje("/apodo"))

    assert "<b>El Mirón</b>" in enviados[0]


def test_pelotazo_sin_compras(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())

    main.atender(config, _mensaje("/pelotazo"))

    assert "No tengo compras" in enviados[0]


def test_arrepentido(config, enviados, monkeypatch):
    config = _con_cartera(
        config, Posicion("bitcoin", 0.02, 1000), Posicion("solana", 10, 2000)
    )
    pedidas = _precio(monkeypatch, {"bitcoin": 100000.0, "solana": 100.0})

    main.atender(config, _mensaje("/venta bitcoin 0.01 700"))
    main.atender(config, _mensaje("/venta solana todo 1500"))
    main.atender(config, _mensaje("/arrepentido"))

    texto = enviados[2]
    assert pedidas[-1] == ["bitcoin", "solana"]
    assert "😩 <b>Bitcoin</b>  +€300,00" in texto
    assert "😌 <b>Solana</b>  -€500,00" in texto
    assert "Bien vendido: hoy te darían <b>€200,00 menos</b>" in texto


def test_arrepentido_sin_ventas(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())

    main.atender(config, _mensaje("/arrepentido"))

    assert "No tengo ventas con las que comparar" in enviados[0]


def test_arrepentido_sin_precios(config, enviados, monkeypatch):
    config = _con_cartera(config, Posicion("bitcoin", 0.02, 1000))
    _precio(monkeypatch, {})

    main.atender(config, _mensaje("/venta bitcoin 0.01 700"))
    main.atender(config, _mensaje("/arrepentido"))

    assert "No he podido consultar los precios" in enviados[1]


def test_impuestos_de_lo_vendido(config, enviados, monkeypatch):
    config = _con_cartera(
        config, Posicion("bitcoin", 0.02, 1000), Posicion("solana", 10, 2000)
    )
    _precio(monkeypatch, {})

    main.atender(config, _mensaje("/venta bitcoin 0.01 7500"))
    main.atender(config, _mensaje("/venta solana todo 1500"))
    main.atender(config, _mensaje("/impuestos"))

    # +7.000 con bitcoin y -500 con solana: 6.500, que pasa del primer tramo.
    texto = enviados[2]
    assert "Has ganado vendiendo <b>+€6.500,00</b>" in texto
    assert "Al 19%: €6.000,00 → €1.140,00" in texto
    assert "Al 21%: €500,00 → €105,00" in texto
    assert "A Hacienda, unos <b>€1.245,00</b>" in texto


def _tres_movimientos(config, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 2000.0})
    main.atender(config, _mensaje("/compra bitcoin 1 1000"))
    main.atender(config, _mensaje("/compra bitcoin 1 3000"))
    main.atender(config, _mensaje("/venta bitcoin 1 3000"))


def test_corregir_una_antigua_rehace_todo(config, enviados, monkeypatch):
    _tres_movimientos(config, monkeypatch)

    main.atender(config, _mensaje("/corregir 1 importe 2000"))

    texto = enviados[-1]
    assert "Corrijo la compra <b>#1</b> de Bitcoin" in texto
    assert "Importe: €1.000,00 → <b>€2.000,00</b>" in texto
    assert "los 2 movimientos que van detrás" in texto
    assert "Ahora tienes 1, que te costaron €2.500,00" in texto
    posicion = main._con_cambios(config).cartera[0]
    assert (posicion.cantidad, posicion.invertido) == (1, 2500)

    main.atender(config, _mensaje("/ganancias"))
    assert "+€500,00" in enviados[-1]


def test_corregir_y_luego_deshacer(config, enviados, monkeypatch):
    _tres_movimientos(config, monkeypatch)
    main.atender(config, _mensaje("/corregir 1 importe 2000"))

    main.atender(config, _mensaje("/deshacer"))

    # La venta deshecha devuelve lo de después de corregir, no lo de antes
    posicion = main._con_cambios(config).cartera[0]
    assert (posicion.cantidad, posicion.invertido) == (2, 5000)


def test_corregir_otra_cripto_no_la_toca(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 2000.0, "solana": 100.0})
    main.atender(config, _mensaje("/compra bitcoin 1 1000"))
    main.atender(config, _mensaje("/compra solana 1 100"))

    main.atender(config, _mensaje("/corregir 1 importe 2000"))

    cartera = {p.coin_id: p.invertido for p in main._con_cambios(config).cartera}
    assert cartera == {"bitcoin": 2000, "solana": 100}
    assert "movimiento que va detrás" not in enviados[-1]


def test_corregir_que_deja_una_venta_sin_saldo_no_cambia_nada(
    config, enviados, monkeypatch
):
    _precio(monkeypatch, {"bitcoin": 2000.0})
    main.atender(config, _mensaje("/compra bitcoin 1 1000"))
    main.atender(config, _mensaje("/venta bitcoin 0.8 1500"))
    antes = database.get_movimientos(config.database_path, None)

    main.atender(config, _mensaje("/corregir 1 cantidad 0.5"))

    assert "Así no cuadra" in enviados[-1]
    assert database.get_movimientos(config.database_path, None) == antes
    assert main._con_cambios(config).cartera[0].cantidad == pytest.approx(0.2)


def test_corregir_que_lo_deja_a_cero(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 2000.0})
    main.atender(config, _mensaje("/compra bitcoin 1 1000"))
    main.atender(config, _mensaje("/venta bitcoin todo 1500"))

    main.atender(config, _mensaje("/corregir 2 importe 1800"))

    assert "Ya no te queda nada de Bitcoin" in enviados[-1]


def test_corregir_si_no_cuadra_no_cambia_nada(config, enviados, monkeypatch):
    _tres_movimientos(config, monkeypatch)
    database.guardar_posicion(
        config.database_path, "bitcoin", Posicion("bitcoin", 7, 100)
    )
    antes = database.get_movimientos(config.database_path, None)

    main.atender(config, _mensaje("/corregir 1 importe 2000"))

    assert "no cuadra con lo que tienes" in enviados[-1]
    assert database.get_movimientos(config.database_path, None) == antes
    assert main._con_cambios(config).cartera[0].cantidad == 7


def test_corregir_uno_que_no_existe(config, enviados):
    main.atender(config, _mensaje("/editar 99 importe 2000"))

    assert "No tengo el movimiento #99" in enviados[0]


def test_corregir_mal_escrito(config, enviados):
    main.atender(config, _mensaje("/corregir"))

    assert "/corregir 12 cantidad 0.02" in enviados[0]


def test_movimientos_enseña_el_numero(config, enviados, monkeypatch):
    _tres_movimientos(config, monkeypatch)

    main.atender(config, _mensaje("/movimientos"))

    assert "· #1</i>" in enviados[-1]
    assert "· #3</i>" in enviados[-1]


def test_recompensa_al_precio_de_ahora(config, enviados, monkeypatch):
    config = _con_cartera(config, Posicion("ethereum", 1, 2000))
    _precio(monkeypatch, {"ethereum": 2500.0})

    main.atender(config, _mensaje("/recompensa eth 0.02 staking de octubre"))

    assert "<b>0,02</b> de Ethereum de recompensa, valorada en €50,00" in enviados[0]
    assert "Ahora tienes 1,02" in enviados[0]
    assert "📝 staking de octubre" in enviados[0]
    posicion = main._con_cambios(config).cartera[0]
    assert posicion.cantidad == pytest.approx(1.02)
    assert posicion.invertido == pytest.approx(2050)


def test_recompensa_con_valor_no_consulta(config, enviados, monkeypatch):
    config = _con_cartera(config, Posicion("ethereum", 1, 2000))
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())

    main.atender(config, _mensaje("/staking eth 0.02 50"))

    assert "valorada en €50,00" in enviados[0]


def test_recompensa_de_algo_que_no_tenias(config, enviados, monkeypatch):
    _precio(monkeypatch, {"solana": 100.0})

    main.atender(config, _mensaje("/airdrop solana 3"))

    posicion = main._con_cambios(config).cartera[0]
    assert (posicion.coin_id, posicion.cantidad, posicion.invertido) == (
        "solana",
        3,
        300,
    )


def test_recompensa_al_vender_solo_cuenta_lo_que_subio(config, enviados, monkeypatch):
    _precio(monkeypatch, {"solana": 100.0})
    main.atender(config, _mensaje("/recompensa solana 3"))

    main.atender(config, _mensaje("/venta solana todo 360"))

    assert "Le sacas +€60,00" in enviados[1]


def test_recompensa_se_deshace(config, enviados, monkeypatch):
    config = _con_cartera(config, Posicion("ethereum", 1, 2000))
    _precio(monkeypatch, {"ethereum": 2500.0})
    main.atender(config, _mensaje("/recompensa eth 0.02"))

    main.atender(config, _mensaje("/deshacer"))

    assert "Quito la recompensa de <b>0,02</b> de Ethereum" in enviados[1]
    assert main._con_cambios(config).cartera[0].cantidad == 1
    assert main._con_cambios(config).cartera[0].invertido == 2000


def test_recompensa_sin_precio_no_apunta(config, enviados, monkeypatch):
    def falla(*a, **k):
        raise coingecko.CoinGeckoError("sin red")

    monkeypatch.setattr(coingecko, "get_prices", falla)

    main.atender(config, _mensaje("/recompensa eth 0.02"))

    assert "No he podido consultar el precio" in enviados[0]
    assert database.get_movimientos(config.database_path) == []


def test_recompensa_que_no_existe(config, enviados, monkeypatch):
    _precio(monkeypatch, {})

    main.atender(config, _mensaje("/recompensa noexiste 1"))

    assert database.get_movimientos(config.database_path) == []


def test_recompensa_mal_escrita(config, enviados):
    main.atender(config, _mensaje("/recompensa eth"))

    assert "/recompensa eth 0.02" in enviados[0]


def test_impuestos_con_recompensas(config, enviados, monkeypatch):
    _precio(monkeypatch, {"solana": 100.0})
    main.atender(config, _mensaje("/recompensa solana 3"))

    main.atender(config, _mensaje("/impuestos"))

    assert "Recibiste €300,00 en recompensas" in enviados[1]


def test_sivendo_no_apunta_nada(config, enviados, monkeypatch):
    config = _con_cartera(config, Posicion("bitcoin", 0.02, 1000))
    _precio(monkeypatch, {"bitcoin": 70000.0})

    main.atender(config, _mensaje("/sivendo btc 0.01"))

    texto = enviados[0]
    assert "<b>Si vendes 0,01 de Bitcoin</b>" in texto
    assert "Te darían €700,00" in texto
    assert "Te costó €500,00" in texto
    assert "<b>+€200,00</b> (+40.00%)" in texto
    assert "A Hacienda, unos <b>€38,00</b>" in texto
    assert "Te quedarían 0,01" in texto
    assert database.get_movimientos(config.database_path) == []


def test_sivendo_suma_lo_que_ya_llevas(config, enviados, monkeypatch):
    config = _con_cartera(config, Posicion("bitcoin", 0.02, 1000))
    _precio(monkeypatch, {})

    main.atender(config, _mensaje("/venta bitcoin 0.01 6400"))  # +5.900
    main.atender(config, _mensaje("/sivendo btc todo 700"))  # +200

    texto = enviados[1]
    assert "Este año ya llevas +€5.900,00 vendiendo" in texto
    assert "A Hacienda, unos <b>€40,00</b>" in texto
    assert "No te quedaría nada de Bitcoin" in texto


def test_sivendo_a_un_precio_no_consulta(config, enviados, monkeypatch):
    config = _con_cartera(config, Posicion("bitcoin", 0.02, 1000))
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())

    main.atender(config, _mensaje("/sivendo btc 0.01 @80000"))

    assert "Te darían €800,00" in enviados[0]


def test_sivendo_con_perdida_que_ahorra(config, enviados, monkeypatch):
    config = _con_cartera(config, Posicion("bitcoin", 0.02, 1000))
    _precio(monkeypatch, {})

    main.atender(config, _mensaje("/venta bitcoin 0.01 1500"))  # +1.000
    main.atender(config, _mensaje("/sivendo btc todo 300"))  # -200

    assert "Te ahorrarías unos <b>€38,00</b> de Hacienda" in enviados[1]


def test_sivendo_sin_saber_lo_que_costo(config, enviados, monkeypatch):
    config = _con_cartera(config, Posicion("bitcoin", 0.02, None))

    main.atender(config, _mensaje("/sivendo btc 0.01 700"))

    assert "No sé lo que te costó" in enviados[0]
    assert "Hacienda" not in enviados[0]


def test_sivendo_mas_de_lo_que_tienes(config, enviados):
    config = _con_cartera(config, Posicion("bitcoin", 0.02, 1000))

    main.atender(config, _mensaje("/sivendo btc 1 700"))

    assert "Solo tienes 0,02 de bitcoin" in enviados[0]


def test_sivendo_lo_que_no_tienes(config, enviados):
    main.atender(config, _mensaje("/sivendo solana 1 700"))

    assert "No tienes solana en la cartera" in enviados[0]


# --- /permuta ---


def test_permuta_no_apunta_nada(config, enviados, monkeypatch):
    config = _con_cartera(config, Posicion("bitcoin", 0.02, 1000))
    _precio(monkeypatch, {"bitcoin": 70000.0, "ethereum": 2000.0})

    main.atender(config, _mensaje("/permuta btc eth 0.01"))

    texto = enviados[0]
    assert "<b>Si cambias 0,01 de Bitcoin por Ethereum</b>" in texto
    assert "Te darían <b>0,35</b> de Ethereum" in texto
    assert "Te costó €500,00" in texto
    assert "<b>+€200,00</b> (+40.00%)" in texto
    assert "A Hacienda, unos <b>€38,00</b>" in texto
    assert "cuenta como venderla" in texto
    assert "contará como comprado a €700,00" in texto
    assert "Te quedarían 0,01 de Bitcoin" in texto
    assert database.get_movimientos(config.database_path) == []


def test_permuta_con_comision(config, enviados, monkeypatch):
    config = _con_cartera(config, Posicion("bitcoin", 0.02, 1000))
    _precio(monkeypatch, {"bitcoin": 70000.0, "ethereum": 2000.0})

    main.atender(config, _mensaje("/permuta btc eth todo com 1%"))

    texto = enviados[0]
    assert "(con €14,00 de comisión)" in texto
    assert "<b>+€386,00</b>" in texto
    assert "Te quedarían" not in texto


def test_permuta_con_perdida(config, enviados, monkeypatch):
    config = _con_cartera(config, Posicion("bitcoin", 0.02, 1000))
    _precio(monkeypatch, {"bitcoin": 30000.0, "ethereum": 2000.0})

    main.atender(config, _mensaje("/venta bitcoin 0.01 1500"))  # +1.000
    main.atender(config, _mensaje("/permuta btc eth todo"))  # -200

    assert "Te ahorrarías unos <b>€38,00</b> de Hacienda" in enviados[1]
    assert "cuenta como venderla" not in enviados[1]


def test_permuta_sin_precio_de_la_otra(config, enviados, monkeypatch):
    config = _con_cartera(config, Posicion("bitcoin", 0.02, 1000))
    _precio(monkeypatch, {"bitcoin": 70000.0})

    main.atender(config, _mensaje("/permuta btc noexiste 0.01"))

    assert "Te darían" not in enviados[0]


def test_permuta_lo_que_no_tienes(config, enviados):
    main.atender(config, _mensaje("/permuta solana btc 1"))

    assert "No tienes solana en la cartera" in enviados[0]


def test_permuta_mal_escrita(config, enviados):
    main.atender(config, _mensaje("/permuta btc"))

    assert "Escríbelo así" in enviados[0]


def test_sivendo_sin_precio_posible(config, enviados, monkeypatch):
    config = _con_cartera(config, Posicion("bitcoin", 0.02, 1000))

    def falla(*a, **k):
        raise coingecko.CoinGeckoError("sin red")

    monkeypatch.setattr(coingecko, "get_prices", falla)

    main.atender(config, _mensaje("/sivendo btc 0.01"))

    assert "No he podido mirar el precio" in enviados[0]


def test_impuestos_de_otro_año_sin_ventas(config, enviados):
    main.atender(config, _mensaje("/hacienda 2020"))

    assert enviados[0] == (
        "En 2020 no has vendido nada, así que no hay nada que declarar."
    )


def test_impuestos_año_que_no_vale(config, enviados):
    main.atender(config, _mensaje("/impuestos mañana"))

    assert "Dime un año" in enviados[0]


def test_ganancias_con_ventas_de_antes_sin_precio(config, enviados):
    btc = Posicion("bitcoin", 0.02, 1000)
    database.apuntar_movimiento(
        config.database_path, "bitcoin", "venta", 0.01, None, btc, btc
    )

    main.atender(config, _mensaje("/ganancias"))

    assert "son de antes de guardar a cuánto vendías" in enviados[0]


def test_ganancias_deshaciendo_la_venta_se_va(config, enviados, monkeypatch):
    config = _con_cartera(config, Posicion("bitcoin", 0.02, 1000))
    _precio(monkeypatch, {})

    main.atender(config, _mensaje("/venta bitcoin 0.01 700"))
    main.atender(config, _mensaje("/deshacer"))
    main.atender(config, _mensaje("/ganancias"))

    assert "Todavía no has vendido nada" in enviados[2]


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
    assert mandados[0][1][0] == [("↩️ Deshacer", f"/deshacer {m.id}")]
    # Debajo, los del ánimo con el que la hiciste.
    assert ("😱 Miedo", f"/emocion {m.id} miedo") in mandados[0][1][1]


def test_deshacer_una_compra_mal_apuntada(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 60000.0})
    config = _con_cartera(config, Posicion("bitcoin", 0.016, 1000))

    main.atender(config, _mensaje("/compra bitcoin 10 600"))
    main.atender(config, _mensaje("/deshacer"))

    assert "⚠️ Esta la pagas a €60,00 cada una" in enviados[0]
    assert "ahora está a €60.000,00 (-100%)" in enviados[0]

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


def test_movimientos_de_una_cripto(config, monkeypatch):
    mandados = _con_botones(monkeypatch)
    _precio(monkeypatch, {"solana": 150.0, "bitcoin": 60000.0})
    main.atender(config, _mensaje("/compra solana 1 150"))
    main.atender(config, _mensaje("/compra bitcoin 0.01 600"))

    main.atender(config, _mensaje("/movimientos sol"))
    main.atender(config, _mensaje("/movimientos btc"))

    texto, teclado = mandados[2]
    assert "compras y ventas de Solana" in texto
    assert "Compra de 1 de Solana por €150,00 <i>(a €150,00)</i>" in texto
    assert "0,01 de Bitcoin por €600,00 <i>(a €60.000,00)</i>" in mandados[3][0]
    assert "Bitcoin" not in texto
    # La ultima es la de bitcoin: el boton desharía otra que no sale aqui.
    assert teclado is None
    ultima = database.get_movimientos(config.database_path)[0]
    assert mandados[3][1] == [[("↩️ Deshacer la última", f"/deshacer {ultima.id}")]]


def test_primera(config, enviados, monkeypatch):
    _precio(monkeypatch, {"solana": 150.0, "bitcoin": 60000.0})
    main.atender(config, _mensaje("/compra solana 1 100"))
    main.atender(config, _mensaje("/compra bitcoin 0.01 600"))

    main.atender(config, _mensaje("/primera"))
    main.atender(config, _mensaje("/primera btc"))

    assert "1 de Solana por €100,00" in enviados[2]
    assert "<b>+50.00%</b> desde entonces" in enviados[2]
    assert "Lo que compraste vale hoy €150,00 (+€50,00)" in enviados[2]
    assert "0,01 de Bitcoin" in enviados[3]


def test_primera_sin_compras(config, enviados):
    main.atender(config, _mensaje("/primera"))
    main.atender(config, _mensaje("/primera eth"))

    assert "No has apuntado ninguna compra por aquí" in enviados[0]
    assert "ninguna compra de <b>ethereum</b>" in enviados[1]


def test_primera_sin_precio(config, enviados, monkeypatch):
    _precio(monkeypatch, {"solana": 150.0})
    main.atender(config, _mensaje("/compra solana 1 100"))

    def falla(*a, **k):
        raise coingecko.CoinGeckoError("caído")

    monkeypatch.setattr(coingecko, "get_prices", falla)
    main.atender(config, _mensaje("/primera"))

    assert "1 de Solana por €100,00" in enviados[1]
    assert "Ahora está" not in enviados[1]


def test_movimientos_de_una_sin_nada(config, enviados):
    main.atender(config, _mensaje("/movimientos eth"))

    assert "ninguna compra ni venta de Ethereum" in enviados[0]


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


def test_bot_dice_los_precios_guardados(config, enviados, monkeypatch):
    from datetime import datetime, timezone

    from crypto_tracker import salud

    monkeypatch.setattr(main, "_pulso", salud.Pulso(ahora=datetime.now(timezone.utc)))
    database.save_prices(config.database_path, {"bitcoin": 63000.0}, "eur")

    main.atender(config, _mensaje("/bot"))

    assert "💾 1 precio guardado, desde el" in enviados[0]


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
    monkeypatch.setattr(main, "ejecutar_ciclo", lambda c, e, s, p=None: (e, None))
    monkeypatch.setattr(main, "pedir_precios", lambda *a: main.Pedidos({}))
    monkeypatch.setattr(main, "apuntar_consultas", lambda c: None)

    def corta(*a):
        raise KeyboardInterrupt

    monkeypatch.setattr(main, "esperar_escuchando", corta)

    with pytest.raises(KeyboardInterrupt):
        main.ejecutar_bucle(config, {})

    assert main._pulso is not None
    assert main._pulso.ultimo_bien is not None


def test_el_bucle_pone_el_menu_corto(config, enviados, monkeypatch):
    puestos = []
    monkeypatch.setattr(telegram, "set_commands", lambda t, c: puestos.append(c))
    monkeypatch.setattr(main, "ejecutar_ciclo", lambda c, e, s, p=None: (e, None))
    monkeypatch.setattr(main, "pedir_precios", lambda *a: main.Pedidos({}))
    monkeypatch.setattr(main, "apuntar_consultas", lambda c: None)

    def corta(*a):
        raise KeyboardInterrupt

    monkeypatch.setattr(main, "esperar_escuchando", corta)
    with pytest.raises(KeyboardInterrupt):
        main.ejecutar_bucle(config, {})

    assert puestos == [comandos.MENU]


def _arrancar_bucle(config, monkeypatch):
    """Arranca --loop y lo corta tras el primer ciclo."""
    monkeypatch.setattr(telegram, "set_commands", lambda *a: True)
    monkeypatch.setattr(main, "ejecutar_ciclo", lambda c, e, s, p=None: (e, None))
    monkeypatch.setattr(main, "pedir_precios", lambda *a: main.Pedidos({}))
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


def test_al_encenderse_dice_las_alertas_puestas(config, enviados, monkeypatch):
    database.crear_puntual(config.database_path, "bitcoin", 70000, True, "eur")
    database.crear_puntual(config.database_path, "solana", 100, False, "eur")
    database.crear_puntual(config.database_path, "bitcoin", 60000, False, "usd")

    _arrancar_bucle(config, monkeypatch)

    # La de dolares no cuenta: con EUR en el .env no saltaria.
    assert "\nTienes 2 alertas puestas esperando." in enviados[0]


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

    # una sola consulta, sin lo vigilado; bitcoin, para los sats
    assert pedidas == [["solana", "bitcoin"]]
    assert "💰 <b>Solana</b>  €150,00\n🔺 +2.50% en 24 h" in enviados[0]
    assert "CoinGecko" in enviados[0]


def test_precio_con_la_semana(config, enviados, monkeypatch):
    monkeypatch.setattr(
        coingecko,
        "precios_semana",
        lambda ids, cur: {"bitcoin": Precio("bitcoin", 63000.0, 2.5, -4.25)},
    )

    main.atender(config, _mensaje("/precio btc"))

    assert "🔺 +2.50% en 24 h\n🔻 -4.25% en 7 días" in enviados[0]
    assert "en 1 h" not in enviados[0]  # si CoinGecko no lo da, no sale


def test_precio_con_el_puesto_y_el_volumen(config, enviados, monkeypatch):
    btc = Precio("bitcoin", 63000.0, 2.5, -4.25, volumen=32_512_000_000, puesto=1)
    monkeypatch.setattr(coingecko, "precios_semana", lambda ids, cur: {"bitcoin": btc})

    main.atender(config, _mensaje("/precio btc"))

    assert (
        "en 7 días\n<i>Puesto #1 · volumen en 24 h: €32.512 millones</i>" in enviados[0]
    )


def test_precio_con_minimo_y_maximo_de_24h(config, enviados, monkeypatch):
    btc = Precio(
        "bitcoin", 63000.0, 2.5, -4.25, puesto=1, minimo_24h=61800, maximo_24h=64250
    )
    monkeypatch.setattr(coingecko, "precios_semana", lambda ids, cur: {"bitcoin": btc})

    main.atender(config, _mensaje("/precio btc"))

    assert (
        "en 7 días\n<i>Mínimo €61.800,00 · máximo €64.250,00 en 24 h</i>\n"
        "<i>Puesto #1</i>" in enviados[0]
    )


def test_precio_con_lo_emitido(config, enviados, monkeypatch):
    btc = Precio("bitcoin", 63000.0, 2.5, -4.25, emitido=95.7, tope=21_000_000)
    monkeypatch.setattr(coingecko, "precios_semana", lambda ids, cur: {"bitcoin": btc})

    main.atender(config, _mensaje("/precio btc"))

    assert "en 7 días\n<i>Emitido el 95.7% de 21 millones</i>" in enviados[0]


def test_precio_con_el_maximo_historico(config, enviados, monkeypatch):
    from crypto_tracker.maximo import Maximo

    m = Maximo("bitcoin", 63000.0, 98000.0, datetime(2024, 12, 17, tzinfo=timezone.utc))
    btc = Precio("bitcoin", 63000.0, 2.5, -4.25, maximo=m)
    monkeypatch.setattr(coingecko, "precios_semana", lambda ids, cur: {"bitcoin": btc})

    main.atender(config, _mensaje("/precio btc"))

    assert "\n<i>Máximo histórico €98.000,00 hace " in enviados[0]
    assert "le falta +55.56%</i>" in enviados[0]


def test_precio_con_30_dias(config, enviados, monkeypatch):
    btc = Precio("bitcoin", 63000.0, 2.5, -4.25, en_30d=8.1)
    monkeypatch.setattr(coingecko, "precios_semana", lambda ids, cur: {"bitcoin": btc})

    main.atender(config, _mensaje("/precio btc"))

    assert "🔻 -4.25% en 7 días\n🔺 +8.10% en 30 días" in enviados[0]


def test_precio_volumen_con_lo_que_es_de_lo_que_vale(config, enviados, monkeypatch):
    btc = Precio("bitcoin", 63000.0, 2.5, -4.25, volumen=32e9, capitalizacion=1.25e12)
    monkeypatch.setattr(coingecko, "precios_semana", lambda ids, cur: {"bitcoin": btc})

    main.atender(config, _mensaje("/precio btc"))

    assert "<i>Volumen en 24 h: €32.000 millones (3% de lo que vale)</i>" in enviados[0]


def test_precio_en_sats(config, enviados, monkeypatch):
    pedidas = _precio(monkeypatch, {"solana": 150.0, "bitcoin": 75000.0})

    main.atender(config, _mensaje("/precio sol"))
    main.atender(config, _mensaje("/precio btc"))
    main.atender(config, _mensaje("/precio sol eth"))

    assert "💰 <b>Solana</b>  €150,00  <i>(200.000 sats)</i>" in enviados[0]
    assert pedidas[1] == ["bitcoin"]  # sin repetirlo
    assert "sats" not in enviados[1]
    assert pedidas[2] == ["solana", "ethereum"]  # con varias no sale


def test_precio_de_varias_sin_volumen(config, enviados, monkeypatch):
    precios = {
        c: Precio(c, 100.0, 1.0, 2.0, volumen=5e9) for c in ("bitcoin", "solana")
    }
    monkeypatch.setattr(coingecko, "precios_semana", lambda ids, cur: precios)

    main.atender(config, _mensaje("/precio btc sol"))

    assert "Volumen" not in enviados[0]  # una por línea, no cabe


def test_precio_con_la_ultima_hora(config, enviados, monkeypatch):
    monkeypatch.setattr(
        coingecko,
        "precios_semana",
        lambda ids, cur: {"bitcoin": Precio("bitcoin", 63000.0, 2.5, -4.25, -0.4)},
    )

    main.atender(config, _mensaje("/precio btc"))

    assert "€63.000,00\n🔻 -0.40% en 1 h\n🔺 +2.50% en 24 h" in enviados[0]


def test_precio_con_las_barritas_de_lo_guardado(config, enviados, monkeypatch):
    monkeypatch.setattr(
        coingecko,
        "precios_semana",
        lambda ids, cur: {"bitcoin": Precio("bitcoin", 63000.0, 2.5, -4.25)},
    )
    for i in range(8):
        _precio_de(config, "bitcoin", 60000.0 + i * 100, (8 - i) * 60)
    _precio_de(config, "bitcoin", 1.0, 25 * 60)  # de antes de ayer, no cuenta

    main.atender(config, _mensaje("/precio btc"))

    assert "en 7 días\n<code>▁▂▃▄▅▆▇█</code> <i>24 h</i>" in enviados[0]


def test_precio_con_lo_que_tienes(con_cartera, enviados, monkeypatch):
    monkeypatch.setattr(
        coingecko,
        "precios_semana",
        lambda ids, cur: {"bitcoin": Precio("bitcoin", 70000.0, 2.5, -4.25)},
    )

    main.atender(con_cartera, _mensaje("/precio btc"))

    assert "💼 Tienes 0,016, que valen <b>€1.120,00</b>" in enviados[0]
    assert "+€120,00" in enviados[0]


def test_precio_de_una_que_no_tienes(con_cartera, enviados, monkeypatch):
    monkeypatch.setattr(
        coingecko,
        "precios_semana",
        lambda ids, cur: {"ethereum": Precio("ethereum", 2500.0, 2.5, -4.25)},
    )

    main.atender(con_cartera, _mensaje("/precio eth"))

    assert "Tienes" not in enviados[0]


def test_precio_de_varias_con_la_semana(config, enviados, monkeypatch):
    monkeypatch.setattr(
        coingecko,
        "precios_semana",
        lambda ids, cur: {
            "bitcoin": Precio("bitcoin", 63000.0, 2.5, -4.25),
            "solana": Precio("solana", 150.0, None, 8.0),
        },
    )
    monkeypatch.setattr(coingecko, "_cambios", {})

    main.atender(config, _mensaje("/precio btc sol"))

    assert "<b>Bitcoin</b>  €63.000,00  🔺 +2.50% · -4.25%" in enviados[0]
    assert "<b>Solana</b>  €150,00 · +8.00% 7d" in enviados[0]


def test_precio_con_el_simbolo(config, enviados, monkeypatch):
    pedidas = _precio(monkeypatch, {"bitcoin": 63000.0})

    main.atender(config, _mensaje("/precio BTC"))

    assert pedidas == [["bitcoin"]]
    assert "💰 <b>Bitcoin</b>  €63.000,00" in enviados[0]


def test_precio_en_otra_moneda(con_cartera, enviados, monkeypatch):
    monedas = []

    def semana(ids, cur):
        monedas.append(cur)
        return {"bitcoin": Precio("bitcoin", 75000.0, None, -4.25)}

    monkeypatch.setattr(coingecko, "precios_semana", semana)
    _precio_hace(con_cartera, 60000.0, 24 * 60 + 5)

    main.atender(con_cartera, _mensaje("/precio btc usd"))

    assert monedas == ["usd"]
    assert "💰 <b>Bitcoin</b>  $75.000,00" in enviados[0]
    # lo guardado y la cartera van en euros: mezclarlos daría cuentas falsas
    assert "Sin datos de las últimas 24 h" in enviados[0]
    assert "Tienes" not in enviados[0]


def test_precio_de_varias_en_otra_moneda(config, enviados, monkeypatch):
    monkeypatch.setattr(
        coingecko,
        "precios_semana",
        lambda ids, cur: {
            "bitcoin": Precio("bitcoin", 50000.0, 2.5, -4.25),
            "ethereum": Precio("ethereum", 2000.0, 1.0, 3.0),
        },
    )

    main.atender(config, _mensaje("/precio btc eth £"))

    assert "<b>Bitcoin</b>  £50.000,00" in enviados[0]
    assert "<b>Ethereum</b>  £2.000,00" in enviados[0]


def test_precio_en_la_moneda_del_env_es_lo_de_siempre(
    con_cartera, enviados, monkeypatch
):
    monkeypatch.setattr(
        coingecko,
        "precios_semana",
        lambda ids, cur: {"bitcoin": Precio("bitcoin", 70000.0, 2.5, -4.25)},
    )

    main.atender(con_cartera, _mensaje("/precio btc euros"))

    assert "💼 Tienes 0,016" in enviados[0]


def test_precio_de_una_lleva_botones_de_alerta(config, monkeypatch):
    mandados = _con_botones(monkeypatch)
    _precio(monkeypatch, {"bitcoin": 63000.0})

    main.atender(config, _mensaje("/precio btc"))

    texto, filas = mandados[0]
    assert "💰 <b>Bitcoin</b>  €63.000,00" in texto
    assert filas == [
        [
            ("🔔 Si sube un 5%", "/alerta bitcoin +5%"),
            ("🔔 Si baja un 5%", "/alerta bitcoin -5%"),
        ]
    ]


def test_precio_de_una_con_precios_guardados_lleva_grafica(config, monkeypatch):
    mandados = _con_botones(monkeypatch)
    _precio(monkeypatch, {"bitcoin": 63000.0})
    _precio_hace(config, 62000.0, 120)
    _precio_hace(config, 62500.0, 60)

    main.atender(config, _mensaje("/precio btc"))

    _, filas = mandados[0]
    assert filas[-1] == [("📈 Gráfica", "/historico bitcoin")]


def test_precio_de_varias_lleva_actualizar(config, monkeypatch):
    mandados = _con_botones(monkeypatch)
    _precio(monkeypatch, {"bitcoin": 63000.0, "ethereum": 2500.0})

    main.atender(config, _mensaje("/precio btc eth usd"))
    main.atender_boton(config, _boton(mandados[0][1][0][0][1]))

    assert mandados[0][1] == [[("🔄 Actualizar", "/precio btc eth usd")]]
    assert mandados[1][0] == mandados[0][0]


def test_precio_a_secas_lleva_actualizar(config, monkeypatch):
    from dataclasses import replace

    config = replace(
        config, watchlist=[Watch("bitcoin", percent=5), Watch("solana", step=10)]
    )
    mandados = _con_botones(monkeypatch)
    _precio(monkeypatch, {"bitcoin": 63000.0, "solana": 150.0})

    main.atender(config, _mensaje("/precio"))

    assert mandados[0][1] == [[("🔄 Actualizar", "/precio")]]


def test_precio_de_muchas_con_ids_largos_sin_actualizar(config, monkeypatch):
    mandados = _con_botones(monkeypatch)
    ids = [f"una-cripto-larga-{i}" for i in range(4)]
    _precio(monkeypatch, {c: 1.0 for c in ids})

    main.atender(config, _mensaje("/precio " + " ".join(ids)))

    assert mandados[0][1] is None


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

    monkeypatch.setattr(coingecko, "precios_semana", falla)

    main.atender(config, _mensaje("/precio solana"))

    assert "No he podido mirar el precio" in enviados[0]


# --- /convertir ---


def test_convertir_cripto_a_dinero(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 62000.0})

    main.atender(config, _mensaje("/convertir 0.05 bitcoin"))

    assert "💱 0,05 Bitcoin = <b>€3.100,00</b>" in enviados[0]
    assert "<i>1 Bitcoin = €62.000,00</i>" in enviados[0]
    assert "CoinGecko" in enviados[0]


def test_convertir_dice_lo_que_valia_hace_24h(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 62000.0})
    monkeypatch.setattr(coingecko, "_cambios", {"bitcoin": 2.5})

    main.atender(config, _mensaje("/convertir 0.05 bitcoin"))

    assert "Hace 24 h valía €3.024,39  🔺 +2.50%" in enviados[0]


def test_convertir_sin_cambio_no_dice_nada_de_ayer(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 62000.0})

    main.atender(config, _mensaje("/convertir 0.05 bitcoin"))

    assert "Hace 24 h" not in enviados[0]


def test_convertir_desde_dinero_no_dice_lo_de_ayer(config, enviados, monkeypatch):
    _precio(monkeypatch, {"solana": 150.0})
    monkeypatch.setattr(coingecko, "_cambios", {"solana": -3.0})

    main.atender(config, _mensaje("/convertir 500€ solana"))

    assert "Hace 24 h" not in enviados[0]


def test_convertir_dinero_a_cripto(config, enviados, monkeypatch):
    _precio(monkeypatch, {"solana": 150.0})

    main.atender(config, _mensaje("/convertir 500€ solana"))

    assert "💱 €500,00 = <b>3,33333333 Solana</b>" in enviados[0]


def test_convertir_entre_criptos(config, enviados, monkeypatch):
    pedidas = _precio(monkeypatch, {"ethereum": 3000.0, "bitcoin": 60000.0})

    main.atender(config, _mensaje("/convertir 2 eth btc"))

    assert "💱 2 Ethereum = <b>0,1 Bitcoin</b>" in enviados[0]
    assert "1 Bitcoin = 20 Ethereum" in enviados[0]
    assert "1 Ethereum = €3.000,00 · 1 Bitcoin = €60.000,00" in enviados[0]
    assert len(pedidas) == 1  # una sola consulta para las dos


def test_convertir_sats_a_dinero(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 60000.0})

    main.atender(config, _mensaje("/convertir 100000 sats"))

    assert "💱 100.000 sats = <b>€60,00</b>" in enviados[0]
    assert "1 sat = €0,0006" in enviados[0]
    assert "0,001 Bitcoin</i>" in enviados[0]


def test_convertir_dinero_a_sats(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 60000.0})

    main.atender(config, _mensaje("/convertir 50€ sats"))

    assert "💱 €50,00 = <b>83.333 sats</b>" in enviados[0]


def test_convertir_cripto_a_sats(config, enviados, monkeypatch):
    _precio(monkeypatch, {"ethereum": 3000.0, "bitcoin": 60000.0})

    main.atender(config, _mensaje("/convertir 1 eth sats"))

    assert "💱 1 Ethereum = <b>5.000.000 sats</b>" in enviados[0]


def test_convertir_entre_criptos_si_una_no_existe(config, enviados, monkeypatch):
    _precio(monkeypatch, {"ethereum": 3000.0})

    main.atender(config, _mensaje("/convertir 1 eth bitcion"))

    assert "/buscar bitcion" in enviados[0]


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


def test_exportar_movimientos(config, enviados, archivos, monkeypatch):
    config = _con_cartera(config, Posicion("bitcoin", 0.02, 1000))
    _precio(monkeypatch, {})
    main.atender(config, _mensaje("/compra bitcoin 0.01 800 por si acaso"))
    main.atender(config, _mensaje("/venta bitcoin 0.01 900"))
    enviados.clear()

    main.atender(config, _mensaje("/exportar movimientos"))

    contenido, nombre, pie = archivos[0]
    lineas = contenido.decode("utf-8-sig").splitlines()
    assert len(lineas) == 3
    assert lineas[1].split(";")[1:5] == ["compra", "bitcoin", "0,01", "800"]
    assert lineas[1].endswith(";por si acaso;1")
    assert lineas[2].split(";")[1:5] == ["venta", "bitcoin", "0,01", "900"]
    assert nombre.startswith("movimientos-") and nombre.endswith(".csv")
    assert "2 movimientos" in pie
    assert enviados == []


def test_exportar_movimientos_mas_de_diez(config, archivos, monkeypatch):
    config = _con_cartera(config, Posicion("bitcoin", 1, 1000))
    _precio(monkeypatch, {})
    for _ in range(12):
        main.atender(config, _mensaje("/compra bitcoin 0.01 800"))

    main.atender(config, _mensaje("/exportar movimientos"))

    assert archivos[0][0].decode("utf-8-sig").count("\r\n") == 13


def test_exportar_movimientos_uno_en_singular(config, archivos, monkeypatch):
    config = _con_cartera(config, Posicion("bitcoin", 1, 1000))
    _precio(monkeypatch, {})
    main.atender(config, _mensaje("/compra bitcoin 0.01 800"))

    main.atender(config, _mensaje("/exportar movimientos"))

    assert "1 movimiento," in archivos[0][2]


def test_exportar_movimientos_sin_ninguno(config, enviados, archivos):
    main.atender(config, _mensaje("/exportar movimientos"))

    assert "Todavía no has apuntado" in enviados[0]
    assert archivos == []


def test_exportar_movimientos_de_mas(config, enviados, archivos):
    main.atender(config, _mensaje("/exportar movimientos 2025"))

    assert "/exportar movimientos" in enviados[0]
    assert archivos == []


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


def test_ath_con_el_minimo(config, enviados, monkeypatch):
    from crypto_tracker.maximo import Maximo

    m = Maximo(
        "bitcoin",
        75000.0,
        100000.0,
        datetime(2026, 3, 14, tzinfo=timezone.utc),
        50.0,
        datetime(2013, 7, 6, tzinfo=timezone.utc),
    )
    monkeypatch.setattr(coingecko, "maximos", lambda ids, cur: {"bitcoin": m})

    main.atender(config, _mensaje("/ath btc"))

    assert "le falta +33.33% para volver\n\n🕳 Mínimo histórico €50,00" in enviados[0]
    assert "El 06/07/2013, hace" in enviados[0]
    assert "ha subido +149900.00% desde ahí" in enviados[0]


def test_ath_en_maximos(config, enviados, monkeypatch):
    _maximos(monkeypatch, {"bitcoin": (100000.0, 100000.0)})

    main.atender(config, _mensaje("/maximo bitcoin"))

    assert "🎉 está en máximos" in enviados[0]


def test_ath_de_varias(config, enviados, monkeypatch):
    _maximos(monkeypatch, {"bitcoin": (75000.0, 100000.0), "solana": (250.0, 250.0)})

    main.atender(config, _mensaje("/ath btc sol bitcion"))

    assert "<b>Bitcoin</b>  €100.000,00 <i>(hace " in enviados[0]
    assert "</i>  +33.33%" in enviados[0]
    assert "</i>  🎉 en máximos" in enviados[0]
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


BC1 = "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"


def _saldo(monkeypatch, sats, txs):
    pedidas = []

    def pedir(d):
        pedidas.append(d)
        return direccion.Saldo(sats, txs)

    monkeypatch.setattr(direccion, "pedir", pedir)
    return pedidas


def test_direccion_añadir_ver_y_quitar(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 80000.0})
    _saldo(monkeypatch, 50_000_000, 3)

    main.atender(config, _mensaje(f"/direccion {BC1} frío"))
    main.atender(config, _mensaje(f"/monedero {BC1}"))
    main.atender(config, _mensaje("/direccion"))
    main.atender(config, _mensaje("/direccion quitar FRÍO"))
    main.atender(config, _mensaje("/direccion"))

    assert "👀 Vigilo <b>frío</b>: ahora tiene 0,5 BTC (€40.000,00)" in enviados[0]
    assert "Ya la vigilo como <b>frío</b>" in enviados[1]
    assert "• <b>frío</b>: 0,5 BTC" in enviados[2]
    assert "Ya no vigilo <b>frío</b>" in enviados[3]
    assert "No vigilo ninguna" in enviados[4]


def test_direccion_que_no_existe(config, enviados, monkeypatch):
    def pedir(d):
        raise direccion.DireccionError("mempool.space dice que esa dirección no existe")

    monkeypatch.setattr(direccion, "pedir", pedir)

    main.atender(config, _mensaje(f"/direccion {BC1}"))

    assert "No he podido mirarla" in enviados[0]
    assert database.direcciones(config.database_path) == {}


def test_direccion_mal_escrita(config, enviados):
    main.atender(config, _mensaje("/direccion hola"))

    assert "no parece una dirección de bitcoin" in enviados[0]


def test_direccion_maximo(config, enviados, monkeypatch):
    _saldo(monkeypatch, 0, 0)
    for i in range(direccion.MAXIMO):
        v = direccion.Vigilada(f"bc1q{'a' * 30}{i}", f"n{i}", 0, 0)
        database.guardar_direccion(config.database_path, v.direccion, v.guardar())

    main.atender(config, _mensaje(f"/direccion {BC1}"))

    assert "Como mucho vigilo 10" in enviados[0]


def _vigilando(config):
    v = direccion.Vigilada(BC1, "frío", 50_000_000, 3)
    database.guardar_direccion(config.database_path, BC1, v.guardar())


def test_revisar_direcciones_avisa_una_vez(config, enviados, monkeypatch):
    _vigilando(config)
    _saldo(monkeypatch, 40_000_000, 4)

    main.revisar_direcciones(config, {"bitcoin": 80000.0})
    main.revisar_direcciones(config, {"bitcoin": 80000.0})

    assert len(enviados) == 1
    assert "🔔 <b>Se ha movido frío</b>" in enviados[0]
    assert "📤 Han salido <b>0,1 BTC (€8.000,00)</b>" in enviados[0]


def test_revisar_direcciones_quieta(config, enviados, monkeypatch):
    _vigilando(config)
    _saldo(monkeypatch, 50_000_000, 3)

    main.revisar_direcciones(config, {"bitcoin": 80000.0})

    assert enviados == []


def test_revisar_direcciones_si_falla_telegram_lo_reintenta(config, monkeypatch):
    _vigilando(config)
    _saldo(monkeypatch, 60_000_000, 4)
    monkeypatch.setattr(telegram, "send_message", lambda *a, **kw: False)

    main.revisar_direcciones(config, {"bitcoin": 80000.0})

    guardada = database.direcciones(config.database_path)[BC1]
    assert direccion.cargar(BC1, guardada).txs == 3


def test_revisar_direcciones_callado_espera(config, enviados, monkeypatch):
    _vigilando(config)
    _saldo(monkeypatch, 60_000_000, 4)
    monkeypatch.setattr(
        revisiones,
        "_silenciado",
        lambda c: datetime.now(timezone.utc) + timedelta(hours=1),
    )

    main.revisar_direcciones(config, {"bitcoin": 80000.0})

    assert enviados == []
    guardada = database.direcciones(config.database_path)[BC1]
    assert direccion.cargar(BC1, guardada).txs == 3


def test_revisar_direcciones_sin_mempool_sigue(config, enviados, monkeypatch):
    _vigilando(config)

    def pedir(d):
        raise direccion.DireccionError("mempool.space no contesta")

    monkeypatch.setattr(direccion, "pedir", pedir)

    main.revisar_direcciones(config, {"bitcoin": 80000.0})

    assert enviados == []


def test_estacional(config, enviados, monkeypatch):
    pedidos = []

    def pedir(par):
        pedidos.append(par)
        return [
            [1, "1", "0", "0", "1", "0", 2],
            [1735689600000, "100", "0", "0", "110", "0", 1738367999999],
        ]

    monkeypatch.setattr(estacional, "pedir", pedir)

    main.atender(config, _mensaje("/meses eth"))

    assert pedidos == ["ETHUSDT"]
    assert "📅 <b>Ethereum</b> mes a mes, desde 2025" in enviados[0]
    assert "🔺 Ene: <b>+10,0%</b> · subió 1 de 1" in enviados[0]


def test_estacional_sin_datos(config, enviados, monkeypatch):
    def pedir(par):
        raise estacional.EstacionalError("sin datos")

    monkeypatch.setattr(estacional, "pedir", pedir)

    main.atender(config, _mensaje("/estacional noexiste"))

    assert "Binance no tiene <b>noexiste</b> contra el dólar" in enviados[0]


def test_estacional_recien_salida(config, enviados, monkeypatch):
    monkeypatch.setattr(estacional, "pedir", lambda par: [])

    main.atender(config, _mensaje("/estacional btc"))

    assert "aún no tiene ningún mes entero" in enviados[0]


def test_funding(config, monkeypatch):
    mandados = _con_botones(monkeypatch)
    pedidos = []

    def pedir(par):
        pedidos.append(par)
        return {"lastFundingRate": "0.0001"}, [{"fundingRate": "0.0001"}]

    monkeypatch.setattr(funding, "pedir", pedir)

    main.atender(config, _mensaje("/funding sol"))

    texto, teclado = mandados[0]
    assert pedidos == ["SOLUSDT"]
    assert "😐 <b>Funding de SOL: +0,0100%</b>" in texto
    assert teclado == [[("🔄 Actualizar", "/funding solana")]]


def test_funding_sin_futuros(config, enviados, monkeypatch):
    def pedir(par):
        raise funding.FundingError("sin futuros")

    monkeypatch.setattr(funding, "pedir", pedir)

    main.atender(config, _mensaje("/funding usdc"))

    assert "<b>usd-coin</b> no tiene futuros en Binance" in enviados[0]


def test_funding_de_una_en_una(config, enviados):
    main.atender(config, _mensaje("/funding btc eth"))

    assert "De una en una" in enviados[0]


def test_comisionred(config, monkeypatch):
    mandados = _con_botones(monkeypatch)
    monkeypatch.setattr(
        comisionred,
        "pedir",
        lambda: ({"halfHourFee": 30}, [{"avgFee_50": 10}]),
    )
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: {"bitcoin": 80000.0})

    main.atender(config, _mensaje("/mempool"))

    texto, teclado = mandados[0]
    assert "🚶 En media hora: <b>€3,38</b> · 30 sat/vB" in texto
    assert "🔴 Cara" in texto
    assert teclado == [[("🔄 Actualizar", "/comisionred")]]


def test_comisionred_sin_conexion(config, enviados, monkeypatch):
    def falla():
        raise comisionred.ComisionRedError("mempool.space no contesta")

    monkeypatch.setattr(comisionred, "pedir", falla)

    main.atender(config, _mensaje("/comisionred"))

    assert "No he podido mirarlo ahora mismo" in enviados[0]


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
            Indice(48, "Neutral", date(2026, 9, 10)),
        ],
    )

    main.atender(config, _mensaje("/miedo"))

    texto, teclado = mandados[0]
    assert "😏 <b>Miedo y codicia: 64</b> · Codicia" in texto
    assert "▰▰▰▰▰▰▱▱▱▱" in texto
    assert "Ayer 59 😏 · Hace una semana 20 😱 · Hace un mes 48 😐" in texto
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
    assert "<b>El resto</b>  21.0% del total" in texto
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
    assert "El resto" not in enviados[0]


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


def _mercado_global(monkeypatch, bitcoin):
    from crypto_tracker.mercado import Mercado

    llamadas = []

    def mercado_global(cur):
        llamadas.append(cur)
        return Mercado(2.4e12, 1.0, bitcoin, 12.0, 6.0)

    monkeypatch.setattr(coingecko, "mercado_global", mercado_global)
    return llamadas


def test_dominancia(config, enviados, monkeypatch):
    from crypto_tracker.dominancia import Foto

    hace_semana = datetime.now(timezone.utc) - timedelta(days=7)
    database.guardar_dominancia(config.database_path, Foto(hace_semana, 56.0, 13, 6))
    _mercado_global(monkeypatch, 58.0)

    main.atender(config, _mensaje("/dominancia"))

    assert "👑 <b>Dominancia de Bitcoin: 58,0%</b>" in enviados[0]
    assert "🔺 +2,0 puntos en 7 días" in enviados[0]
    assert "El dinero vuelve a bitcoin" in enviados[0]
    # Ya que ha consultado, se queda como la foto de hoy.
    assert len(database.get_dominancia(config.database_path, 1)) == 1


def test_foto_dominancia_una_al_dia(config, monkeypatch):
    llamadas = _mercado_global(monkeypatch, 58.0)

    main.foto_dominancia(config)
    main.foto_dominancia(config)

    assert len(llamadas) == 1
    assert len(database.get_dominancia(config.database_path, 1)) == 1


def test_foto_dominancia_sin_conexion(config, monkeypatch):
    def falla(cur):
        raise coingecko.CoinGeckoError("sin red")

    monkeypatch.setattr(coingecko, "mercado_global", falla)

    main.foto_dominancia(config)

    assert database.get_dominancia(config.database_path, 1) == []


def test_sharpe(con_cartera, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    for dias in range(1, 45):
        bitcoin = 70000.0 if dias % 2 else 71400.0
        _precio_de(con_cartera, "bitcoin", bitcoin, dias * 24 * 60)
        _precio_de(con_cartera, "solana", 120.0 + dias, dias * 24 * 60)

    main.atender(con_cartera, _mensaje("/sharpe 40d"))

    assert "📐 <b>Tu Sharpe de los últimos 40 días:" in enviados[0]
    assert "₿ Bitcoin:" in enviados[0]


def test_sharpe_sin_historia(con_cartera, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 70000.0, "solana": 120.0})

    main.atender(con_cartera, _mensaje("/sharpe"))

    assert "Necesito 31 días seguidos" in enviados[0]


def test_sharpe_mal_escrito(config, enviados):
    main.atender(config, _mensaje("/sharpe 7d"))

    assert "Dime de 30 a 365 días" in enviados[0]


def test_futuro(con_cartera, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    for dias in range(1, 30):
        bitcoin = 70000.0 if dias % 2 else 71400.0
        _precio_de(con_cartera, "bitcoin", bitcoin, dias * 24 * 60)
        _precio_de(con_cartera, "solana", 120.0, dias * 24 * 60)
    _precio_de(con_cartera, "bitcoin", 70000.0, 5)
    _precio_de(con_cartera, "solana", 120.0, 5)

    main.atender(con_cartera, _mensaje("/futuro 7d"))

    assert "🔮 <b>Tu cartera dentro de 7 días</b>" in enviados[0]
    assert "2 de cada 3 veces: entre" in enviados[0]


def test_futuro_sin_historia(con_cartera, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 70000.0, "solana": 120.0})

    main.atender(con_cartera, _mensaje("/proyeccion"))

    assert "Necesito 15 días seguidos" in enviados[0]


def test_futuro_mal_escrito(config, enviados):
    main.atender(config, _mensaje("/futuro mañana"))

    assert "Dime de 1 a 365 días" in enviados[0]


def test_fibonacci(config, enviados):
    for horas, precio in [(72, 100.0), (48, 200.0), (24, 150.0), (1, 150.0)]:
        _precio_de(config, "bitcoin", precio, horas * 60)

    main.atender(config, _mensaje("/fibo btc 7d"))

    assert "🌀 <b>Bitcoin</b>: Fibonacci, últimos 7 días" in enviados[0]
    assert "🛟 Por debajo, el 61,8%" in enviados[0]


def test_fibonacci_quieta(config, enviados):
    _precio_de(config, "bitcoin", 100.0, 120)
    _precio_de(config, "bitcoin", 100.1, 60)

    main.atender(config, _mensaje("/fibonacci"))

    assert "apenas se ha movido" in enviados[0]


def test_fibonacci_sin_precios(config, enviados):
    main.atender(config, _mensaje("/fibonacci solana"))

    assert "No tengo precios guardados de <b>solana</b>" in enviados[0]


def test_macd(config, enviados):
    for dias in range(1, 61):
        _precio_de(config, "bitcoin", 100.0 + (60 - dias) ** 2, dias * 24 * 60)

    main.atender(config, _mensaje("/macd btc"))

    assert "📶 <b>Bitcoin</b>: MACD de 12 y 26 días" in enviados[0]
    assert "🐂 <b>Empuje al alza</b>" in enviados[0]


def test_macd_sin_historia(config, enviados):
    main.atender(config, _mensaje("/empuje"))

    assert "Necesito 35 días seguidos" in enviados[0]


def test_bollinger(config, enviados):
    for dias in range(1, 25):
        _precio_de(config, "bitcoin", 95.0 if dias % 2 else 105.0, dias * 24 * 60)
    _precio_de(config, "bitcoin", 130.0, 5)

    main.atender(config, _mensaje("/bandas"))

    assert "📏 <b>Bitcoin</b>: bandas de Bollinger de 20 días" in enviados[0]
    assert "por encima de la banda alta" in enviados[0]


def test_bollinger_pocos_dias(config, enviados):
    _precio_de(config, "bitcoin", 100.0, 60)

    main.atender(config, _mensaje("/bollinger btc"))

    assert "Necesito 20 días seguidos de precios de <b>bitcoin</b>" in enviados[0]


def test_soporte(config, enviados):
    precios = [100, 95, 90, 95, 100, 105, 110, 105, 100, 95, 91, 95, 100, 105, 109, 104]
    for i, precio in enumerate(precios):
        _precio_de(config, "bitcoin", precio, (len(precios) - i) * 24 * 60)
    _precio_de(config, "bitcoin", 100, 60)

    main.atender(config, _mensaje("/soporte"))

    assert "🧱 <b>Bitcoin</b>: soportes y resistencias" in enviados[0]
    assert "🔴 €109,50 · 2 toques" in enviados[0]
    assert "🟢 €90,50 · 2 toques" in enviados[0]


def test_soporte_pocos_dias(config, enviados):
    _precio_de(config, "bitcoin", 100, 60)

    main.atender(config, _mensaje("/resistencia btc"))

    assert "Necesito al menos 5 días guardados de <b>bitcoin</b>" in enviados[0]


def test_diames(config, enviados):
    from datetime import timedelta

    for dias in range(1, 80):
        cuando = datetime.now(timezone.utc) - timedelta(days=dias)
        precio = 90.0 if cuando.astimezone().day == 15 else 100.0
        _precio_de(config, "bitcoin", precio, dias * 24 * 60)

    main.atender(config, _mensaje("/diames"))

    assert "📆 <b>Bitcoin</b> por días del mes" in enviados[0]
    assert "🟢 Más barata, el día <b>15</b>" in enviados[0]
    assert "← el mejor para comprar" in enviados[0]


def test_diames_sin_meses_enteros(config, enviados):
    _precio_de(config, "bitcoin", 100.0, 60)

    main.atender(config, _mensaje("/diames btc"))

    assert "No tengo un mes seguido de precios de <b>bitcoin</b>" in enviados[0]


def test_diames_mal_escrito(config, enviados):
    main.atender(config, _mensaje("/diames btc eth"))

    assert "/diames bitcoin 365d" in enviados[0]


def test_comparar(config, sin_fotos_de_verdad, monkeypatch):
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

    png, texto = sin_fotos_de_verdad[0]
    assert png.startswith(b"\x89PNG")
    assert "📊 <b>Cómo les ha ido</b> · <i>últimos 7 días</i>" in texto
    assert texto.index("Solana") < texto.index("Bitcoin") < texto.index("Ethereum")
    assert "🥇 <b>Solana</b>  🔺 +50.00%" in texto
    assert "🥈 <b>Bitcoin</b>  🔺 +10.00%" in texto
    assert "🥉 <b>Cardano</b>  ➖ +0.00%" in texto
    assert "4. <b>Ethereum</b>  🔻 -20.00%" in texto
    assert "De media 🔺 <b>+10.00%</b>" in texto
    assert "No tengo precios guardados de <b>pepe</b>" in texto
    assert "desde el" not in texto


def test_comparar_a_secas_las_que_vigilas(config, sin_fotos_de_verdad):
    _precio_de(config, "bitcoin", 100.0, 2 * 24 * 60)
    _precio_de(config, "bitcoin", 120.0, 5)
    _precio_de(config, "solana", 100.0, 2 * 24 * 60)  # no la vigila
    _precio_de(config, "solana", 200.0, 5)

    main.atender(config, _mensaje("/comparar 30d"))

    _, texto = sin_fotos_de_verdad[0]
    assert "últimos 30 días" in texto
    assert "🥇 <b>Bitcoin</b>  🔺 +20.00% <i>(desde el" in texto
    assert "Solana" not in texto
    assert "De media" not in texto  # con una sola no tiene sentido


def test_comparar_con_precios_viejos(config, sin_fotos_de_verdad):
    _precio_de(config, "bitcoin", 100.0, 20 * 24 * 60)
    _precio_de(config, "bitcoin", 120.0, 3 * 24 * 60)
    _precio_de(config, "solana", 100.0, 29 * 24 * 60)  # todo el tramo
    _precio_de(config, "solana", 90.0, 3 * 24 * 60)

    main.atender(config, _mensaje("/comparar btc sol 30d"))

    _, texto = sin_fotos_de_verdad[0]
    assert "+20.00% <i>(del " in texto
    assert "-10.00% <i>(hasta el " in texto


def test_comparar_con_muchas_va_sin_grafica(config, enviados, sin_fotos_de_verdad):
    nombres = ["bitcoin", "ethereum", "solana", "cardano", "ripple", "tron", "litecoin"]
    for coin_id in nombres:
        _precio_de(config, coin_id, 100.0, 2 * 24 * 60)
        _precio_de(config, coin_id, 110.0, 5)

    main.atender(config, _mensaje("/comparar btc eth sol ada xrp trx ltc"))

    assert sin_fotos_de_verdad == []
    assert "7. <b>" in enviados[0]


def test_comparar_si_falla_la_grafica_manda_el_texto(config, enviados, monkeypatch):
    def rota(*a):
        raise grafica.GraficaError("Falta matplotlib")

    monkeypatch.setattr(grafica, "dibujar_comparar", rota)
    _precio_de(config, "bitcoin", 100.0, 2 * 24 * 60)
    _precio_de(config, "bitcoin", 120.0, 5)

    main.atender(config, _mensaje("/comparar btc"))

    assert "🥇 <b>Bitcoin</b>" in enviados[0]


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
    # %5 son 2 avisos en 4 días, 3,5 a la semana: demasiados
    assert "<code>/vigilar bitcoin %10</code>" in texto
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


# --- /dca ---


def test_dca(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    # Compra a 50.000 y a 25.000, y ahora esta a 60.000
    _precio_hace(config, 50000.0, 14 * 24 * 60 - 10)
    _precio_hace(config, 25000.0, 6 * 24 * 60)
    _precio_hace(config, 60000.0, 5)

    main.atender(config, _mensaje("/dca 100 btc 14d"))

    assert "€100,00 en <b>Bitcoin</b> cada semana hace 14 días" in enviados[0]
    assert "<b>€360,00</b>" in enviados[0]
    assert "2 compras, €200,00 en total" in enviados[0]
    # Los 200 a 50.000 son 0,004, que ahora valen 240
    assert "Todo de golpe en la primera: €240,00 (+20.00%)" in enviados[0]
    assert "Mejor poco a poco, por €120,00" in enviados[0]


def test_dca_sin_precios(config, enviados):
    main.atender(config, _mensaje("/dca 50 solana"))

    assert "No tengo precios guardados de <b>solana</b>" in enviados[0]


def test_dca_mal_escrito(config, enviados):
    main.atender(config, _mensaje("/dca"))

    assert "/dca 50 bitcoin semanal 90d" in enviados[0]


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

    texto = resumenes.montar_resumen(config)

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


# --- /reparto ---


def test_reparto(con_cartera, enviados, sin_fotos_de_verdad, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 70000.0, "solana": 160.0})

    main.atender(con_cartera, _mensaje("/reparto"))

    png, pie = sin_fotos_de_verdad[0]
    assert png.startswith(b"\x89PNG")
    # 0,016 BTC = 1.120 € y 7 SOL = 1.120 €: mitad y mitad
    assert "🥧 <b>Tu cartera</b>: €2.240,00" in pie
    assert "<b>Bitcoin</b> 50% · €1.120,00" in pie
    assert "<b>Solana</b> 50% · €1.120,00" in pie
    assert enviados == []


def test_reparto_sin_un_precio(con_cartera, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 70000.0})

    main.atender(con_cartera, _mensaje("/reparto"))

    assert "No tengo el precio de <b>solana</b>" in enviados[0]


def test_reparto_sin_imagen_manda_texto(con_cartera, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 70000.0, "solana": 160.0})

    def falla(*a, **k):
        raise grafica.GraficaError("Falta matplotlib")

    monkeypatch.setattr(grafica, "dibujar_reparto", falla)

    main.atender(con_cartera, _mensaje("/reparto"))

    assert "<b>Bitcoin</b> 50%" in enviados[0]


def test_reparto_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/reparto"))

    assert "PORTFOLIO" in enviados[0]


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


def test_boton_del_precio_crea_la_alerta(config, enviados, contestados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 60000.0})

    main.atender_boton(config, _boton("/alerta bitcoin -5%"))

    [alerta] = database.get_puntuales(config.database_path, "eur")
    assert alerta.objetivo == pytest.approx(57000.0)
    assert alerta.sube is False
    assert "baje a <b>€57.000,00</b>" in enviados[0]


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


def _semana_guardada(config, horas_atras=7 * 24 - 1):
    for coin_id, antes, ahora in (("bitcoin", 60000.0, 63000.0), ("solana", 100, 95)):
        _guardar(config, coin_id, antes, horas_atras)
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


def test_semanal_a_la_hora_de_horario(con_semana, sin_fotos_de_verdad):
    from datetime import time

    _semana_guardada(con_semana)
    database.guardar_hora_resumen(con_semana.database_path, time(20, 0))

    main.resumen_semanal(con_semana, DOMINGO)  # a las 9:30 ya no toca
    assert sin_fotos_de_verdad == []

    main.resumen_semanal(con_semana, _dia(20, 0, dia=27))
    assert len(sin_fotos_de_verdad) == 1


def test_semanal_avisa_si_no_hay_semana_entera(con_semana, sin_fotos_de_verdad):
    for coin_id, antes, ahora in (("bitcoin", 60000.0, 63000.0), ("solana", 100, 95)):
        _guardar(con_semana, coin_id, antes, 30)
        _guardar(con_semana, coin_id, ahora, 0)

    main.resumen_semanal(con_semana, DOMINGO)

    assert "Solo tengo precios desde" in sin_fotos_de_verdad[0][1]


# --- resumen mensual ---


def _dia_1():
    """El día 1 de este mes a las 9:30: el mes pasado es el que acaba de cerrar."""
    from datetime import datetime

    hoy = datetime.now().astimezone()
    return datetime(hoy.year, hoy.month, 1, 9, 30).astimezone()


def _mes_pasado_guardado(config):
    from datetime import datetime

    # Horas desde el 1 a las 00:00: lo de más atrás es del mes pasado.
    van = (datetime.now().astimezone() - _dia_1()).total_seconds() / 3600 + 9.5
    for coin_id, antes, despues in (("bitcoin", 60000.0, 63000.0), ("solana", 100, 95)):
        _guardar(config, coin_id, antes, van + 48)
        _guardar(config, coin_id, despues, van + 2)
        # esto ya es del mes nuevo y no tiene que contar
        _guardar(config, coin_id, despues * 10, 0)


def _nombre_mes_pasado():
    from datetime import timedelta

    from crypto_tracker import mes

    return mes.nombre(_dia_1() - timedelta(days=1))


def test_mensual_el_dia_1(con_semana, enviados, sin_fotos_de_verdad):
    _mes_pasado_guardado(con_semana)

    main.resumen_mensual(con_semana, _dia_1())

    [(png, pie)] = sin_fotos_de_verdad
    nombre = _nombre_mes_pasado()
    assert png
    assert f"🗓 <b>Tu {nombre}</b>" in pie
    assert f"+3.57% (+€250,00) en {nombre}" in pie
    assert enviados == []


def test_mensual_una_vez(con_semana, sin_fotos_de_verdad):
    _mes_pasado_guardado(con_semana)

    main.resumen_mensual(con_semana, _dia_1())
    main.resumen_mensual(con_semana, _dia_1())

    assert len(sin_fotos_de_verdad) == 1


def test_mensual_solo_el_dia_1(con_semana, sin_fotos_de_verdad):
    from datetime import timedelta

    _mes_pasado_guardado(con_semana)

    main.resumen_mensual(con_semana, _dia_1() + timedelta(days=1))

    assert sin_fotos_de_verdad == []


def test_mensual_sin_cartera(con_resumen, enviados, sin_fotos_de_verdad):
    main.resumen_mensual(con_resumen, _dia_1())

    assert enviados == [] and sin_fotos_de_verdad == []


def test_mensual_sin_precios_no_insiste(con_semana, enviados, sin_fotos_de_verdad):
    main.resumen_mensual(con_semana, _dia_1())

    assert enviados == [] and sin_fotos_de_verdad == []
    ultimo = database.ultimo_resumen(con_semana.database_path, database.ULTIMO_MENSUAL)
    assert ultimo == _dia_1().date()


def test_mensual_callado_llega_al_volver(con_semana, sin_fotos_de_verdad):
    from datetime import datetime, timedelta, timezone

    _mes_pasado_guardado(con_semana)
    database.silenciar_hasta(
        con_semana.database_path, datetime.now(timezone.utc) + timedelta(hours=1)
    )

    main.resumen_mensual(con_semana, _dia_1())
    assert sin_fotos_de_verdad == []

    database.silenciar_hasta(con_semana.database_path, None)
    main.resumen_mensual(con_semana, _dia_1())
    assert len(sin_fotos_de_verdad) == 1


def test_mensual_reintenta_si_telegram_falla(con_semana, monkeypatch):
    monkeypatch.setattr(telegram, "send_photo", lambda *a, **k: False)
    monkeypatch.setattr(telegram, "send_message", lambda *a, **k: False)
    _mes_pasado_guardado(con_semana)

    main.resumen_mensual(con_semana, _dia_1())

    assert (
        database.ultimo_resumen(con_semana.database_path, database.ULTIMO_MENSUAL)
        is None
    )


def test_mensual_y_semanal_no_se_pisan(con_semana, sin_fotos_de_verdad):
    _mes_pasado_guardado(con_semana)

    main.resumen_mensual(con_semana, _dia_1())

    assert (
        database.ultimo_resumen(con_semana.database_path, database.ULTIMO_SEMANAL)
        is None
    )


def test_semana_cuando_la_pides(con_semana, enviados, sin_fotos_de_verdad):
    _semana_guardada(con_semana)

    main.atender(con_semana, _mensaje("/semana"))

    [(png, pie)] = sin_fotos_de_verdad
    assert png
    assert "+3.57% (+€250,00) en la semana" in pie
    assert enviados == []


def test_semana_a_mano_no_quita_la_del_domingo(con_semana, sin_fotos_de_verdad):
    _semana_guardada(con_semana)

    main.atender(con_semana, _mensaje("/semana"))
    main.resumen_semanal(con_semana, DOMINGO)

    assert len(sin_fotos_de_verdad) == 2


def test_semana_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/semana"))

    assert enviados[0] == main.SIN_CARTERA


def test_semana_de_una_es_su_historico(config, enviados, sin_fotos_de_verdad):
    for precio in (60000.0, 62000.0):
        database.save_prices(config.database_path, {"bitcoin": precio}, "eur")

    main.atender(config, _mensaje("/semana btc"))

    _, pie = sin_fotos_de_verdad[0]
    assert "📈 <b>Bitcoin</b>, últimos 7 días" in pie
    assert "62.000,00" in pie


def test_semana_de_varias(config, enviados):
    main.atender(config, _mensaje("/semana btc eth"))

    assert "De una en una" in enviados[0]


def test_semana_sin_precios(con_semana, enviados):
    main.atender(con_semana, _mensaje("/semana"))

    assert "Aún no tengo precios" in enviados[0]


def test_semana_sin_imagen_manda_texto(con_semana, enviados, monkeypatch):
    def falla(*a, **k):
        raise grafica.GraficaError("Falta matplotlib")

    monkeypatch.setattr(grafica, "dibujar", falla)
    _semana_guardada(con_semana)

    main.atender(con_semana, _mensaje("/semana"))

    assert "Tu semana" in enviados[0]


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


def test_resumen_lleva_boton_de_actualizar(config, con_teclado, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 63000.0})
    monkeypatch.setattr(miedo, "pedir", lambda: [])

    main.atender(config, _mensaje("/resumen"))

    assert con_teclado[0][1]["botones"] == [[("🔄 Actualizar", "/resumen")]]


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


# --- /objetivo ---


def test_equilibrio(con_cartera, enviados, monkeypatch):
    monkeypatch.setattr(
        coingecko, "get_prices", lambda ids, cur: {"bitcoin": 70000.0, "solana": 120.0}
    )

    main.atender(con_cartera, _mensaje("/equilibrio"))

    # Solana te salió a 142,86: le falta. Bitcoin a 62.500: ya ganas.
    assert enviados[0].index("<b>Solana</b>") < enviados[0].index("<b>Bitcoin</b>")
    assert "<b>Solana</b> a €142,86 · falta <b>+19.05%</b>" in enviados[0]
    assert "<b>Bitcoin</b> a €62.500,00 · ya ganas" in enviados[0]
    assert "coingecko.com" in enviados[0]


def test_equilibrio_lleva_boton_de_actualizar(con_cartera, con_teclado, monkeypatch):
    monkeypatch.setattr(
        coingecko, "get_prices", lambda ids, cur: {"bitcoin": 70000.0, "solana": 120.0}
    )

    main.atender(con_cartera, _mensaje("/equilibrio"))

    assert con_teclado[0][1]["botones"] == [[("🔄 Actualizar", "/equilibrio")]]


def test_promediar(con_cartera, enviados, monkeypatch):
    pedidas = []

    def precios(ids, cur):
        pedidas.extend(ids)
        return {"bitcoin": 40000.0}

    monkeypatch.setattr(coingecko, "get_prices", precios)

    main.atender(con_cartera, _mensaje("/promediar btc 50k"))

    assert pedidas == ["bitcoin"]  # solo esa, no toda la cartera
    assert "Compra <b>0,02 Bitcoin</b> por <b>€800,00</b>" in enviados[0]
    assert "coingecko.com" in enviados[0]


def test_promediar_sin_tenerla_no_consulta(con_cartera, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: pytest.fail())

    main.atender(con_cartera, _mensaje("/promedio eth 2000"))

    assert "No tienes <b>ethereum</b> en la cartera" in enviados[0]


def test_promediar_mal_escrito(con_cartera, enviados):
    main.atender(con_cartera, _mensaje("/promediar bitcoin"))

    assert "/promediar bitcoin 50000" in enviados[0]


def test_promediar_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/promediar btc 50000"))

    assert enviados[0] == main.SIN_CARTERA


def test_posicion_sin_cripto_no_consulta(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: pytest.fail())

    main.atender(config, _mensaje("/posicion 1000 2% -10%"))

    assert "mete <b>€200,00</b>" in enviados[0]
    assert "coingecko.com" not in enviados[0]


def test_posicion_con_cripto(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 50000.0})

    main.atender(config, _mensaje("/tamaño btc 1000 2% 40000"))

    assert "mete <b>€100,00</b>" in enviados[0]
    assert "Son <b>0,002 Bitcoin</b> a €50.000,00" in enviados[0]
    assert "coingecko.com" in enviados[0]


def test_posicion_stop_por_encima(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 50000.0})

    main.atender(config, _mensaje("/posicion btc 1000 2% 60000"))

    assert "por debajo del precio de ahora" in enviados[0]


def test_posicion_sin_precio(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {})

    main.atender(config, _mensaje("/posicion bitcion 1000 2% -10%"))

    assert "No he podido consultar los precios" in enviados[0]


def test_posicion_mal_escrito(config, enviados):
    main.atender(config, _mensaje("/posicion 1000"))

    assert "/posicion 1000 2% -10%" in enviados[0]


def test_plan_sin_cartera_empieza_de_cero(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: pytest.fail())

    main.atender(config, _mensaje("/plan 10000 50"))

    assert "llegas en <b>3 años y 10 meses</b>" in enviados[0]
    assert "cartera" not in enviados[0]


def test_plan_cuenta_la_cartera(con_cartera, enviados, monkeypatch):
    monkeypatch.setattr(
        coingecko, "get_prices", lambda ids, cur: {"bitcoin": 50000.0, "solana": 0.0}
    )

    main.atender(con_cartera, _mensaje("/ahorro 10000 50"))

    # 0,016 bitcoin a 50.000 son 800: faltan 9.200, 184 semanas.
    assert "Habrás metido €9.200,00" in enviados[0]
    assert "Contando los €800,00 que ya tienes en cartera" in enviados[0]


def test_plan_mal_escrito(config, enviados):
    main.atender(config, _mensaje("/plan 10000"))

    assert "/plan 10000 50 semanal" in enviados[0]


def test_apy_de_la_cartera(con_cartera, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"solana": 100.0})

    main.atender(con_cartera, _mensaje("/apy sol 10% 1a"))

    assert "🌱 <b>7 SOL al 10% al año</b> (lo de tu cartera)" in enviados[0]
    assert "En 1 año: <b>7,7 SOL</b> (+0,7) · €770,00" in enviados[0]


def test_apy_con_cantidad(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"ethereum": 2000.0})

    main.atender(config, _mensaje("/interés 2 eth 4%"))

    assert "🌱 <b>2 ETH al 4% al año</b>\n" in enviados[0]
    assert "En 10 años" in enviados[0]


def test_apy_sin_tenerla(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: pytest.fail())

    main.atender(config, _mensaje("/apy eth 4%"))

    assert "No tienes <b>ethereum</b> en la cartera" in enviados[0]


def test_staking_sigue_siendo_recompensa():
    from crypto_tracker import comandos

    assert comandos.interpretar("/staking eth 0.02") == ("recompensa", "eth 0.02")


def test_limite_ponerlo_verlo_y_quitarlo(config, enviados):
    main.atender(config, _mensaje("/limite"))
    assert "No tienes límite de compras" in enviados[-1]

    main.atender(config, _mensaje("/limite 300"))
    assert enviados[-1].startswith("✅ Hecho")
    assert "Tu límite: €300,00 al mes" in enviados[-1]

    main.atender(config, _mensaje("/presupuesto no"))
    assert database.limite_compras(config.database_path) is None


def test_compra_avisa_al_pasarte_del_limite(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 60000.0})
    database.guardar_limite_compras(config.database_path, 300)

    main.atender(config, _mensaje("/compra btc 0.001 100"))
    assert "límite" not in enviados[-1]

    main.atender(config, _mensaje("/compra btc 0.002 150"))
    assert "🧮 Llevas €250,00 de tus €300,00" in enviados[-1]

    main.atender(config, _mensaje("/compra btc 0.002 120"))
    assert "⚠️ Con esta, este mes llevas <b>€370,00</b>" in enviados[-1]
    # Debajo de lo de siempre, no en su lugar.
    assert enviados[-1].index("⚠️") > enviados[-1].index("Bitcoin")


def test_compra_sin_limite_no_dice_nada(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 60000.0})

    main.atender(config, _mensaje("/compra btc 0.01 600"))

    assert "límite" not in enviados[-1]
    assert "🧮" not in enviados[-1]


def test_doble(con_cartera, enviados, monkeypatch):
    monkeypatch.setattr(
        coingecko, "get_prices", lambda ids, cur: {"bitcoin": 70000.0, "solana": 120.0}
    )

    main.atender(con_cartera, _mensaje("/doble"))

    # Bitcoin te salió a 62.500 y Solana a 142,86: el doble, 125.000 y 285,71.
    assert "<b>Bitcoin</b> a €125.000,00 · falta <b>+78.57%</b>" in enviados[0]
    assert "<b>Solana</b> a €285,71 · falta <b>+138.10%</b>" in enviados[0]
    assert "coingecko.com" in enviados[0]


def test_doble_lleva_boton_de_actualizar(con_cartera, con_teclado, monkeypatch):
    monkeypatch.setattr(
        coingecko, "get_prices", lambda ids, cur: {"bitcoin": 70000.0, "solana": 120.0}
    )

    main.atender(con_cartera, _mensaje("/x2"))

    assert con_teclado[0][1]["botones"] == [[("🔄 Actualizar", "/doble")]]


def test_doble_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/doble"))

    assert "PORTFOLIO" in enviados[0]


def test_mitad(con_cartera, enviados, monkeypatch):
    monkeypatch.setattr(
        coingecko, "get_prices", lambda ids, cur: {"bitcoin": 70000.0, "solana": 120.0}
    )

    main.atender(con_cartera, _mensaje("/mitad"))

    # Bitcoin te salió a 62.500 y Solana a 142,86: la mitad, 31.250 y 71,43.
    assert "<b>Bitcoin</b> a €31.250,00 · aguanta <b>-55.36%</b>" in enviados[0]
    assert "<b>Solana</b> a €71,43 · aguanta <b>-40.48%</b>" in enviados[0]
    assert enviados[0].index("Solana") < enviados[0].index("Bitcoin")
    assert "coingecko.com" in enviados[0]


def test_mitad_lleva_boton_de_actualizar(con_cartera, con_teclado, monkeypatch):
    monkeypatch.setattr(
        coingecko, "get_prices", lambda ids, cur: {"bitcoin": 70000.0, "solana": 120.0}
    )

    main.atender(con_cartera, _mensaje("/mitad"))

    assert con_teclado[0][1]["botones"] == [[("🔄 Actualizar", "/mitad")]]


def test_mitad_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/mitad"))

    assert "PORTFOLIO" in enviados[0]


def test_equilibrio_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/equilibrio"))

    assert "PORTFOLIO" in enviados[0]


def test_equilibrio_si_falta_un_precio(con_cartera, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 70000.0})

    main.atender(con_cartera, _mensaje("/equilibrio"))

    assert "no tengo el precio de todo" in enviados[0]


def test_objetivo(con_cartera, enviados, monkeypatch):
    monkeypatch.setattr(
        coingecko, "get_prices", lambda ids, cur: {"bitcoin": 70000.0, "solana": 150.0}
    )

    main.atender(con_cartera, _mensaje("/objetivo btc 100k"))

    assert "valdría <b>€2.650,00</b>" in enviados[0]
    assert "+€480,00 respecto a hoy" in enviados[0]
    assert "coingecko.com" in enviados[0]


def test_objetivo_de_una_que_no_tienes_no_gasta_consulta(
    con_cartera, enviados, monkeypatch
):
    def no_llamar(*a):
        raise AssertionError("no deberia consultar precios")

    monkeypatch.setattr(coingecko, "get_prices", no_llamar)

    main.atender(con_cartera, _mensaje("/objetivo eth 3000"))

    assert "No tienes <b>ethereum</b>" in enviados[0]


def test_objetivo_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/objetivo btc 100000"))

    assert "PORTFOLIO" in enviados[0]


def test_objetivo_si_falta_un_precio(con_cartera, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 70000.0})

    main.atender(con_cartera, _mensaje("/objetivo btc 100000"))

    assert "no tengo el precio de todo" in enviados[0]


def test_objetivo_mal_escrito(con_cartera, enviados):
    main.atender(con_cartera, _mensaje("/objetivo bitcoin"))

    assert "/objetivo bitcoin 100000" in enviados[0]


# --- alertas a punto en el resumen ---


def test_resumen_lleva_las_alertas_a_punto(con_resumen, enviados, monkeypatch):
    pedidas = []

    def precios(ids, cur):
        pedidas.extend(ids)
        return {"bitcoin": 63000.0, "solana": 150.0}

    monkeypatch.setattr(coingecko, "get_prices", precios)
    ruta = con_resumen.database_path
    database.crear_puntual(ruta, "bitcoin", 64000, True, "eur")  # +1,59%
    database.crear_puntual(ruta, "bitcoin", 80000, True, "eur")  # lejos
    database.crear_puntual(ruta, "solana", 146, False, "eur")  # no la vigila

    main.atender(con_resumen, _mensaje("/resumen"))

    assert pedidas == ["bitcoin", "solana"]  # todo en una consulta
    assert "A punto de saltar" in enviados[0]
    assert "€64.000,00  <i>(falta +1.59%)</i>" in enviados[0]
    assert "€146,00  <i>(falta -2.67%)</i>" in enviados[0]
    assert "80.000" not in enviados[0]


def test_resumen_sin_alertas_a_punto_dice_la_mas_cerca(con_resumen, enviados):
    database.crear_puntual(con_resumen.database_path, "bitcoin", 80000, True, "eur")

    database.crear_puntual(con_resumen.database_path, "bitcoin", 90000, True, "eur")

    main.resumen_diario(con_resumen, _dia(9, 5))

    assert "resumen del día" in enviados[0]
    assert "A punto de saltar" not in enviados[0]
    assert (
        "🎯 Tienes 2 alertas, la más cerca: <b>Bitcoin</b> 🔺 €80.000,00"
        in (enviados[0])
    )
    assert "90.000" not in enviados[0]


def test_resumen_diario_lleva_las_alertas_a_punto(con_resumen, enviados):
    database.crear_puntual(con_resumen.database_path, "bitcoin", 62000, False, "eur")

    main.resumen_diario(con_resumen, _dia(9, 5))

    assert "A punto de saltar" in enviados[0]


def test_resumen_con_alerta_de_la_cartera_a_punto(con_cartera, enviados, monkeypatch):
    monkeypatch.setattr(
        coingecko, "get_prices", lambda ids, cur: {"bitcoin": 70000.0, "solana": 150.0}
    )
    database.crear_puntual(con_cartera.database_path, "cartera", 2200, True, "eur")

    main.atender(con_cartera, _mensaje("/resumen"))

    assert "<b>Tu cartera</b> 🔺 €2.200,00  <i>(falta +1.38%)</i>" in enviados[0]


def test_resumen_sin_alertas_no_dice_nada_de_ellas(con_resumen, enviados):
    main.resumen_diario(con_resumen, _dia(9, 5))

    assert "🎯" not in enviados[0]


def test_el_status_no_lleva_las_alertas_a_punto(con_resumen, enviados):
    database.crear_puntual(con_resumen.database_path, "bitcoin", 64000, True, "eur")

    main.atender(con_resumen, _mensaje("/status"))

    assert "A punto de saltar" not in enviados[0]


# --- /rango ---


def test_rango(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    for horas, precio in [(167, 100.0), (100, 120.0), (50, 80.0), (1, 110.0)]:
        _precio_de(config, "bitcoin", precio, horas * 60)

    main.atender(config, _mensaje("/rango btc"))

    texto = enviados[0]
    assert "📏 <b>Bitcoin</b>, últimos 7 días" in texto
    assert "Máximo €120,00" in texto
    assert "Mínimo €80,00" in texto
    assert "Ahora <b>€110,00</b>, al 75% del rango" in texto
    assert "Solo tengo precios desde el" not in texto


def test_rango_a_secas_la_primera_que_vigilas(config, enviados):
    _precio_de(config, "bitcoin", 100.0, 60)
    _precio_de(config, "bitcoin", 101.0, 5)

    main.atender(config, _mensaje("/rango"))

    assert "<b>Bitcoin</b>, últimos 7 días" in enviados[0]
    assert "Solo tengo precios desde el" in enviados[0]


def test_rango_sin_precios(config, enviados):
    main.atender(config, _mensaje("/rango sol 30d"))

    assert "No tengo precios guardados de <b>solana</b>" in enviados[0]


def test_rango_mal_escrito(config, enviados):
    main.atender(config, _mensaje("/rango btc eth"))

    assert "/rango bitcoin 7d" in enviados[0]


# --- /sube ---


def test_sube(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    for dias, precio in [(29, 100.0), (20, 80.0), (10, 120.0), (1, 96.0)]:
        _precio_de(config, "bitcoin", precio, dias * 24 * 60)

    main.atender(config, _mensaje("/sube btc"))

    texto = enviados[0]
    assert "🚀 <b>Bitcoin</b>, últimos 30 días" in texto
    assert "<b>+20.00%</b> desde el mínimo" in texto
    assert "Mejor subida <b>+50.00%</b>" in texto


def test_sube_con_el_alias(config, enviados):
    _precio_de(config, "bitcoin", 100.0, 60)
    _precio_de(config, "bitcoin", 99.0, 5)

    main.atender(config, _mensaje("/subida"))

    assert "está en su mínimo del tramo" in enviados[0]


def test_minimo_es_sube(config, enviados):
    _precio_de(config, "bitcoin", 90.0, 60)
    _precio_de(config, "bitcoin", 99.0, 5)

    main.atender(config, _mensaje("/mínimo btc 7d"))

    assert "<b>+10.00%</b> desde el mínimo" in enviados[0]


def test_sube_sin_precios(config, enviados):
    main.atender(config, _mensaje("/sube sol 7d"))

    assert "No tengo precios guardados de <b>solana</b>" in enviados[0]


# --- /caida ---


def test_caida(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    for dias, precio in [(29, 100.0), (20, 120.0), (10, 90.0), (1, 108.0)]:
        _precio_de(config, "bitcoin", precio, dias * 24 * 60)

    main.atender(config, _mensaje("/caida btc"))

    texto = enviados[0]
    assert "📉 <b>Bitcoin</b>, últimos 30 días" in texto
    assert "<b>-10.00%</b> desde el máximo" in texto
    assert "Peor caída <b>-25.00%</b>" in texto
    assert "Solo tengo precios desde el" not in texto


def test_caida_a_secas_y_con_tilde(config, enviados):
    _precio_de(config, "bitcoin", 100.0, 60)
    _precio_de(config, "bitcoin", 101.0, 5)

    main.atender(config, _mensaje("/caída"))

    assert "<b>Bitcoin</b>, últimos 30 días" in enviados[0]
    assert "está en su máximo del tramo" in enviados[0]
    assert "Solo tengo precios desde el" in enviados[0]


def test_caida_sin_precios(config, enviados):
    main.atender(config, _mensaje("/caida sol 7d"))

    assert "No tengo precios guardados de <b>solana</b>" in enviados[0]


# --- /correlacion ---


def test_correlacion(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    for dias, precio in enumerate([100, 110, 99, 105, 120, 108, 112, 101, 115]):
        _precio_de(config, "bitcoin", float(precio), (8 - dias) * 24 * 60)
        _precio_de(config, "ethereum", precio / 20, (8 - dias) * 24 * 60)

    main.atender(config, _mensaje("/correlacion btc eth"))

    assert "🔗 <b>Bitcoin</b> y <b>Ethereum</b>, últimos 30 días" in enviados[0]
    assert "Correlación <b>+1,00</b>: van muy juntas" in enviados[0]


def test_correlacion_a_secas_con_una_sola_vigilada(config, enviados):
    main.atender(config, _mensaje("/correlacion"))

    assert "¿Cuáles?" in enviados[0]


def test_correlacion_sin_precios(config, enviados):
    main.atender(config, _mensaje("/correlación btc sol"))

    assert "al menos 7 días seguidos con precios de <b>bitcoin</b> y" in enviados[0]


# --- /copia ---


def test_copia_con_lo_de_telegram(config, enviados, monkeypatch):
    _precio(monkeypatch, {"solana": 150.0, "bitcoin": 60000.0})
    main.atender(config, _mensaje("/vigilar solana 10"))
    main.atender(config, _mensaje("/compra bitcoin 0.01 600"))
    main.atender(config, _mensaje("/horario 8:30"))

    main.atender(config, _mensaje("/copia"))

    texto = enviados[-1]
    assert "WATCHLIST=bitcoin:%5,solana:10\n" in texto
    assert "PORTFOLIO=bitcoin:0.01:600\n" in texto
    assert "RESUMEN_DIARIO=08:30</code>" in texto


# --- /dia ---


def test_dia(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    _precio_de(config, "bitcoin", 100.0, 3 * 24 * 60)
    _precio_de(config, "bitcoin", 110.0, 0)
    hace_tres = (datetime.now(timezone.utc) - timedelta(days=3)).astimezone()

    main.atender(config, _mensaje(f"/dia btc {hace_tres:%d/%m/%Y}"))

    assert "📅 <b>Bitcoin</b> el " in enviados[0]
    assert "Cerró a <b>€100,00</b>" in enviados[0]
    assert "Desde entonces +10.00%: ahora €110,00" in enviados[0]


def test_dia_sin_ese_dia_sugiere_otro(config, enviados):
    _precio_de(config, "bitcoin", 100.0, 0)
    hoy = datetime.now(timezone.utc).astimezone()

    main.atender(config, _mensaje("/dia anteayer"))

    assert "No tengo precios de <b>bitcoin</b> del" in enviados[0]
    assert f"/dia bitcoin {hoy:%d/%m/%Y}" in enviados[0]


def test_dia_sin_precios_y_mal_escrito(config, enviados):
    main.atender(config, _mensaje("/dia sol ayer"))
    main.atender(config, _mensaje("/dia btc"))

    assert "No tengo precios guardados de <b>solana</b>" in enviados[0]
    assert "/dia bitcoin 01/09" in enviados[1]


# --- /cuando ---


def test_cuando(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    for dias, precio in [(30, 55000.0), (20, 59000.0), (10, 70000.0), (0, 80000.0)]:
        _precio_de(config, "bitcoin", precio, dias * 24 * 60)

    main.atender(config, _mensaje("/cuando btc 60k"))

    assert "estuvo a <b>€60.000,00</b> o menos" in enviados[0]
    assert "hace 20 días" in enviados[0]
    assert "Entonces €59.000,00, ahora €80.000,00" in enviados[0]


def test_cuando_sin_precios(config, enviados):
    main.atender(config, _mensaje("/cuando sol 100"))

    assert "No tengo precios guardados de <b>solana</b>" in enviados[0]


def test_cuando_mal_escrito(config, enviados):
    main.atender(config, _mensaje("/cuando btc"))

    assert "/cuando bitcoin 60000" in enviados[0]


# --- /ajustes ---


def test_ajustes_con_el_horario_cambiado(config, enviados):
    main.atender(config, _mensaje("/horario 7:45"))
    enviados.clear()

    main.atender(config, _mensaje("/ajustes"))

    assert "⚙️ <b>Tus ajustes</b>" in enviados[0]
    assert "📰 Resumen cada día a las 07:45" in enviados[0]


# --- /redondo ---


def test_redondo(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    _precio_de(config, "bitcoin", 60000.0, 60)
    _precio_de(config, "bitcoin", 64000.0, 5)

    main.atender(config, _mensaje("/redondo btc"))

    assert "🎯 <b>Bitcoin</b>  ahora €64.000,00" in enviados[0]
    assert "⬆️ €70.000,00  a <b>+9.38%</b>" in enviados[0]


def test_redondo_a_secas_las_que_vigilas(config, enviados):
    _precio_de(config, "bitcoin", 64000.0, 5)
    _precio_de(config, "ethereum", 2500.0, 5)

    main.atender(config, _mensaje("/redondo"))

    # Ethereum tiene precios, pero no la vigilas.
    assert "<b>Bitcoin</b>" in enviados[0]
    assert "Ethereum" not in enviados[0]


def test_redondo_sin_precios(config, enviados):
    main.atender(config, _mensaje("/redondo sol"))

    assert "No tengo precios guardados de <b>solana</b>" in enviados[0]


# --- /rsi ---


def test_rsi(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    # 20 días subiendo: RSI 100
    for dias in range(20):
        _precio_de(config, "bitcoin", 100.0 - dias, dias * 24 * 60)

    main.atender(config, _mensaje("/rsi btc"))

    assert "📊 <b>Bitcoin</b>, RSI de 14 días: <b>100</b>" in enviados[0]
    assert "Sobrecomprada" in enviados[0]


def test_rsi_sin_dias_suficientes(config, enviados):
    _precio_de(config, "bitcoin", 100.0, 60)

    main.atender(config, _mensaje("/rsi"))

    assert "Necesito 15 días seguidos de precios de <b>bitcoin</b>" in enviados[0]


def test_rsi_de_varias(config, enviados):
    main.atender(config, _mensaje("/rsi btc eth"))

    assert "De una en una" in enviados[0]


# --- /extremo ---


def test_extremo(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    for dias, precio in [(3, 100.0), (2, 110.0), (1, 99.0), (0, 100.0)]:
        _precio_de(config, "bitcoin", precio, dias * 24 * 60 + 5)

    main.atender(config, _mensaje("/mejor btc"))

    assert "Mejor día: <b>+10.00%</b>" in enviados[0]
    assert "Peor día: <b>-10.00%</b>" in enviados[0]
    assert "Solo tengo precios desde el" in enviados[0]


def test_extremo_sin_precios(config, enviados):
    main.atender(config, _mensaje("/extremo sol"))

    assert "No tengo precios guardados de <b>solana</b>" in enviados[0]


def test_extremo_de_varias(config, enviados):
    main.atender(config, _mensaje("/extremo btc eth"))

    assert "Escríbelo así: /extremo bitcoin 30d" in enviados[0]


# --- /verdes ---


def test_verdes(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    for dias, precio in [(3, 100.0), (2, 105.0), (1, 103.0), (0, 110.0)]:
        _precio_de(config, "bitcoin", precio, dias * 24 * 60 + 5)

    main.atender(config, _mensaje("/verdes btc 30d"))

    assert "<b>2</b> en verde y <b>1</b> en rojo" in enviados[0]
    assert "Solo tengo precios desde el" in enviados[0]


def test_verdes_sin_cripto_usa_la_primera(config, enviados):
    main.atender(config, _mensaje("/verdes"))

    assert "No tengo precios guardados de <b>bitcoin</b>" in enviados[0]


def test_verdes_de_varias(config, enviados):
    main.atender(config, _mensaje("/verdes btc eth"))

    assert "Escríbelo así: /verdes bitcoin 30d" in enviados[0]


# --- /diasemana ---


def test_diasemana(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    for dias, precio in [(3, 100.0), (2, 105.0), (1, 103.0), (0, 110.0)]:
        _precio_de(config, "bitcoin", precio, dias * 24 * 60 + 5)

    main.atender(config, _mensaje("/diasemana btc 30d"))

    assert "<b>Bitcoin</b> por días de la semana, últimos 30 días" in enviados[0]
    assert "Mejor:" in enviados[0]
    assert "Solo tengo precios desde el" in enviados[0]


def test_diasemana_sin_cripto_usa_la_primera(config, enviados):
    main.atender(config, _mensaje("/diasemana"))

    assert "No tengo precios guardados de <b>bitcoin</b>" in enviados[0]


def test_diasemana_de_varias(config, enviados):
    main.atender(config, _mensaje("/diasemana btc eth"))

    assert "Escríbelo así: /diasemana bitcoin 90d" in enviados[0]


# --- /horas ---


def test_horas(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    # Dos días y pico de un precio cada hora: al menos uno sale entero.
    for horas in range(60):
        _precio_de(config, "bitcoin", 100.0 + horas % 24, horas * 60 + 5)

    main.atender(config, _mensaje("/horas btc 7d"))

    assert "<b>Bitcoin</b> por horas, últimos 7 días" in enviados[0]
    assert "Más barata sobre las" in enviados[0]


def test_horas_sin_precios(config, enviados):
    main.atender(config, _mensaje("/horas"))

    assert "No tengo ningún día entero de precios de <b>bitcoin</b>" in enviados[0]


def test_horas_de_varias(config, enviados):
    main.atender(config, _mensaje("/horas btc eth"))

    assert "Escríbelo así: /horas bitcoin 30d" in enviados[0]


# --- /ratio ---


def test_ratio(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    for dias, eth, btc in [(2, 3000.0, 100000.0), (0, 3300.0, 100000.0)]:
        _precio_de(config, "ethereum", eth, dias * 24 * 60 + 5)
        _precio_de(config, "bitcoin", btc, dias * 24 * 60 + 5)

    main.atender(config, _mensaje("/ratio eth btc 7d"))

    assert "1 Ethereum = <b>0,0330</b> Bitcoin" in enviados[0]
    assert "🔺 +10.00%" in enviados[0]


def test_ratio_sin_precios(config, enviados):
    main.atender(config, _mensaje("/ratio eth sol"))

    assert "Necesito precios de <b>ethereum</b> y <b>solana</b>" in enviados[0]


def test_ratio_de_una(config, enviados):
    main.atender(config, _mensaje("/ratio eth"))

    assert "De dos en dos. Escríbelo así: /ratio eth btc 30d" in enviados[0]


# --- /hoy ---


def test_hoy(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    _precio_de(config, "bitcoin", 100.0, 0)  # con 0, de hoy aunque sean las 00:00

    main.atender(config, _mensaje("/hoy"))

    assert "☀️ <b>Hoy</b>, desde las 00:00" in enviados[0]
    assert "<b>Bitcoin</b>  €100,00" in enviados[0]


def test_hoy_lleva_boton_de_actualizar(config, con_teclado):
    _precio_de(config, "bitcoin", 100.0, 0)

    main.atender(config, _mensaje("/hoy btc"))

    assert con_teclado[0][1]["botones"] == [[("🔄 Actualizar", "/hoy btc")]]


def test_hoy_sin_precios(config, enviados):
    main.atender(config, _mensaje("/hoy btc eth"))

    assert "No tengo precios guardados de hoy" in enviados[0]


# --- /racha ---


def test_racha(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    for dias, precio in [(3, 120.0), (2, 100.0), (1, 105.0), (0, 110.0)]:
        _precio_de(config, "bitcoin", precio, dias * 24 * 60 + 5)

    main.atender(config, _mensaje("/racha btc"))

    assert "lleva <b>2 días</b> seguidos subiendo" in enviados[0]
    assert "+10.00%" in enviados[0]


def test_racha_sin_precios(config, enviados):
    main.atender(config, _mensaje("/racha sol"))

    assert "No tengo precios guardados de <b>solana</b>" in enviados[0]


def test_racha_de_varias(config, enviados):
    main.atender(config, _mensaje("/racha btc eth"))

    assert "De una en una" in enviados[0]


# --- /media ---


def test_media(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    for dias in range(7):
        _precio_de(config, "bitcoin", 100.0 + dias * 10, (6 - dias) * 24 * 60 + 5)

    main.atender(config, _mensaje("/media btc"))

    texto = enviados[0]
    assert "ahora €160,00" in texto
    assert "Media de 7 días  €130,00  🔺 +23.08% por encima" in texto
    assert "Media de 30 días  <i>no tengo tantos días guardados</i>" in texto


def test_media_con_tramo(config, enviados):
    _precio_de(config, "bitcoin", 100.0, 24 * 60 + 5)
    _precio_de(config, "bitcoin", 110.0, 5)

    main.atender(config, _mensaje("/media 2d"))

    assert "Media de 2 días  €105,00" in enviados[0]
    assert "30 días" not in enviados[0]


def test_media_sin_precios(config, enviados):
    main.atender(config, _mensaje("/media sol"))

    assert "No tengo precios guardados de <b>solana</b>" in enviados[0]


# --- /halving ---


def test_halving(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())

    main.atender(config, _mensaje("/halving"))

    assert "⛏️ <b>Próximo halving de Bitcoin</b>" in enviados[0]
    assert "BTC" in enviados[0]


# --- /mundo ---


def test_mundo_con_lo_guardado(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    _precio_de(config, "bitcoin", 83000.0, 5)

    main.atender(config, _mensaje("/mundo"))

    assert "Hoy serían unos <b>€210,00</b>" in enviados[0]


def test_mundo_sin_red(config, enviados, monkeypatch):
    def falla(*a, **k):
        raise coingecko.CoinGeckoError("sin conexión")

    monkeypatch.setattr(coingecko, "get_prices", falla)

    main.atender(config, _mensaje("/mundo"))

    assert "No he podido mirar el precio ahora mismo: sin conexión" in enviados[0]


# --- /pizza ---


def test_pizza_con_lo_guardado(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    _precio_de(config, "bitcoin", 80000.0, 5)

    main.atender(config, _mensaje("/pizza"))

    assert "Hoy serían <b>€800 millones</b>, €400 millones cada una" in enviados[0]


def test_pizza_sin_guardar_lo_pide(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: {"bitcoin": 90000.0})

    main.atender(config, _mensaje("/pizza"))

    assert "Hoy serían <b>€900 millones</b>" in enviados[0]


def test_pizza_sin_red(config, enviados, monkeypatch):
    def falla(*a, **k):
        raise coingecko.CoinGeckoError("sin conexión")

    monkeypatch.setattr(coingecko, "get_prices", falla)

    main.atender(config, _mensaje("/pizza"))

    assert "No he podido mirar el precio ahora mismo: sin conexión" in enviados[0]


# --- /aleatoria ---


def test_aleatoria(config, monkeypatch):
    from crypto_tracker.top import Movida

    mandados = _con_botones(monkeypatch)
    # bitcoin la vigilas y tether es estable: solo puede salir solana.
    monkeypatch.setattr(
        coingecko,
        "top_hoy",
        lambda *a, **k: [
            Movida("bitcoin", "Bitcoin", "BTC", 80000.0, 1.0),
            Movida("tether", "Tether", "USDT", 1.0, 0.0),
            Movida("solana", "Solana", "SOL", 105.0, 3.0),
        ],
    )

    main.atender(config, _mensaje("/aleatoria"))

    texto, filas = mandados[0]
    assert "🎲 <b>Solana (SOL)</b>" in texto
    assert "Es la número 3 por tamaño" in texto
    assert filas == [[("🎲 Otra", "/aleatoria"), ("📈 Su precio", "/precio solana")]]


def test_aleatoria_sin_red(config, enviados, monkeypatch):
    def falla(*a, **k):
        raise coingecko.CoinGeckoError("sin conexión")

    monkeypatch.setattr(coingecko, "top_hoy", falla)

    main.atender(config, _mensaje("/aleatoria"))

    assert "No he podido mirarlo ahora mismo: sin conexión" in enviados[0]


# --- /ultimo ---


def test_ultimo_apunta_el_aviso_y_lo_enseña(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 90000.0})

    main.ejecutar_ciclo(config, {"bitcoin": "%60000.0"})
    enviados.clear()
    main.atender(config, _mensaje("/ultimo"))

    assert "<b>Bitcoin</b>  hoy a las" in enviados[0]
    assert "🔺 Subió a €90.000,00  ·  desde entonces +0.00%" in enviados[0]


def test_ultimo_sin_avisos(config, enviados):
    main.atender(config, _mensaje("/ultimo"))

    assert "<b>Bitcoin</b>  <i>aún no ha avisado</i>" in enviados[0]


def test_ultimo_no_apunta_lo_que_no_llega(config, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 90000.0})
    monkeypatch.setattr(telegram, "send_message", lambda *a, **k: False)

    main.ejecutar_ciclo(config, {"bitcoin": "%60000.0"})

    assert database.ultimos_avisos(config.database_path) == {}


def test_ultimo_no_apunta_lo_callado(config, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 90000.0})
    main.atender(config, _mensaje("/mute 2h"))

    main.ejecutar_ciclo(config, {"bitcoin": "%60000.0"})

    assert database.ultimos_avisos(config.database_path) == {}


# --- /millonario ---


def test_millonario_con_tu_cartera(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.5, 5000.0),))
    _precio_de(config, "bitcoin", 80000.0, 5)

    main.atender(config, _mensaje("/millonario"))

    assert "Necesitas <b>12,5 BTC</b>, a €80.000,00 cada uno" in enviados[0]
    assert "Con lo que tienes (0,5 BTC) llevas el <b>4.00%</b>" in enviados[0]


def test_millonario_de_una_que_no_vigilas(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: {"pepe": 0.00001})

    main.atender(config, _mensaje("/millonario pepe"))

    assert "Necesitas <b>100.000.000.000 Pepe</b>" in enviados[0]
    assert "Con lo que tienes" not in enviados[0]


def test_millonario_no_existe(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: {})

    main.atender(config, _mensaje("/millonario bitcion"))

    assert "No encuentro <b>bitcion</b>" in enviados[0]


def test_millonario_de_una_en_una(config, enviados):
    main.atender(config, _mensaje("/millonario btc eth"))

    assert "De una en una" in enviados[0]


# --- /cumple ---


def test_cumple(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())

    main.atender(config, _mensaje("/cumple"))

    assert "🎂 <b>Bitcoin tiene" in enviados[0]


# --- /whitepaper ---


def test_whitepaper(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())

    main.atender(config, _mensaje("/whitepaper"))

    assert "📄 <b>El whitepaper de Bitcoin tiene" in enviados[0]


def test_paper_es_whitepaper(config, enviados):
    main.atender(config, _mensaje("/paper"))

    assert "whitepaper de Bitcoin" in enviados[0]


# --- /merge ---


def test_merge(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())

    main.atender(config, _mensaje("/merge"))

    assert "🐼 <b>The Merge cumple" in enviados[0]


# --- /ethereum ---


def test_ethereum(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())

    main.atender(config, _mensaje("/ethereum"))

    assert "⟠ <b>Ethereum cumple" in enviados[0]


# --- /adios ---


def test_adios(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())

    main.atender(config, _mensaje("/adios"))

    assert "👻 <b>Satoshi lleva" in enviados[0]


# --- /sat ---


def test_sat(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    _precio_de(config, "bitcoin", 70000.0, 5)

    main.atender(config, _mensaje("/sats"))

    assert "1 sat vale €0,0007" in enviados[0]
    assert "€100 → 142.857 sats" in enviados[0]


def test_sat_sin_precio_guardado_lo_pide(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 100000.0})

    main.atender(config, _mensaje("/sat"))

    assert "1 sat vale €0,001" in enviados[0]


# --- /caraocruz ---


def test_caraocruz(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    monkeypatch.setattr(caraocruz, "lanzar", lambda: "cruz")

    main.atender(config, _mensaje("/caraocruz btc"))
    main.atender(config, _mensaje("/moneda"))

    assert "🪙 Ha salido <b>cruz</b>: vende <b>Bitcoin</b>" in enviados[0]
    assert "<b>cruz</b>: vende\n" in enviados[1]


# --- /dado ---


def test_dado(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    monkeypatch.setattr(dado, "tirar", lambda: 2)

    main.atender(config, _mensaje("/dado sol"))
    main.atender(config, _mensaje("/dado"))

    assert "<b>2</b> ⚁: vende un poco de <b>Solana</b>" in enviados[0]
    assert "<b>2</b> ⚁: vende un poco\n" in enviados[1]


# --- /frase ---


def test_frase(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    monkeypatch.setattr(frase, "elegir", lambda: frase.FRASES[5])

    main.atender(config, _mensaje("/cita"))

    assert "💬 <i>«Running bitcoin»</i>\n— Hal Finney, 2009" in enviados[0]


# --- /consejo ---


def test_consejo(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    monkeypatch.setattr(consejo, "elegir", lambda: consejo.CONSEJOS[4])

    main.atender(config, _mensaje("/consejos"))

    assert "<i>«No vendas nunca. Ni siquiera cuando" in enviados[0]


# --- /glosario ---


def test_glosario(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())

    main.atender(config, _mensaje("/diccionario fomo"))
    main.atender(config, _mensaje("/glosario"))

    assert enviados[0].startswith("📖 <b>FOMO</b>")
    assert "Las palabras que sé" in enviados[1]


# --- /lambo ---


def test_lambo(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(
        config, cartera=(Posicion("bitcoin", 2.0), Posicion("solana", 1000.0))
    )
    _precio_de(config, "bitcoin", 100000.0, 5)
    _precio_de(config, "solana", 100.0, 5)

    main.atender(config, _mensaje("/lambo"))

    assert "Vale €300.000,00" in enviados[0]
    assert "<b>1 Lamborghini</b>" in enviados[0]


def test_lambo_pide_lo_que_no_tiene_guardado(config, enviados, monkeypatch):
    from dataclasses import replace

    pedidas = []
    monkeypatch.setattr(
        coingecko,
        "get_prices",
        lambda ids, cur: pedidas.append(ids) or {"solana": 100.0},
    )
    config = replace(
        config, cartera=(Posicion("bitcoin", 0.01), Posicion("solana", 10.0))
    )
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/lambo"))

    assert pedidas == [["solana"]]
    assert "Vale €2.000,00" in enviados[0]


def test_ballena(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(
        config, cartera=(Posicion("bitcoin", 12.5), Posicion("solana", 1000.0))
    )

    main.atender(config, _mensaje("/ballena"))

    assert "🐙 <b>Eres un pulpo</b>" in enviados[0]
    assert "te faltan 37,5 BTC" in enviados[0]


def test_ballena_cuenta_lo_comprado(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: {"bitcoin": 80000.0})

    main.atender(config, _mensaje("/compra bitcoin 2 100000"))
    main.atender(config, _mensaje("/whale"))

    assert "🦀 <b>Eres un cangrejo</b>" in enviados[-1]


def test_ballena_sin_bitcoin(config, enviados):
    main.atender(config, _mensaje("/ballena"))

    assert "no tienes bitcoin" in enviados[0]


def test_cafe(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.02),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/café"))

    assert "Vale €2.000,00" in enviados[0]
    assert "<b>1.333 cafés</b>" in enviados[0]


def test_sueldo(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.12),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/smi"))

    assert "Vale €12.000,00" in enviados[0]
    assert "<b>8,4 meses</b>" in enviados[0]


def test_gasolina(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.02),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/gas"))

    assert "Vale €2.000,00" in enviados[0]
    assert "<b>1.111 litros</b>" in enviados[0]


def test_bigmac(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.02),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/hamburguesa"))

    assert "<b>363 Big Macs</b>" in enviados[0]


def test_iphone(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.04),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/iphone"))

    assert "<b>2 iPhones</b>" in enviados[0]


def test_iphone_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/iphone"))

    assert "PORTFOLIO" in enviados[0]


def test_alquiler(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.04),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/alquiler"))

    assert "Te paga <b>3 meses</b>" in enviados[0]


def test_alquiler_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/alquiler"))

    assert "PORTFOLIO" in enviados[0]


def test_oro(config, enviados, monkeypatch):
    from dataclasses import replace

    config = replace(config, cartera=(Posicion("bitcoin", 0.07),))
    _precio_de(config, "bitcoin", 100000.0, 5)
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: {"pax-gold": 3110.35})

    main.atender(config, _mensaje("/oro"))

    assert "Son <b>70 gramos</b>" in enviados[0]


def test_oro_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/oro"))

    assert "PORTFOLIO" in enviados[0]


def test_netflix(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.001),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/netflix"))

    assert "Te paga <b>7 meses</b>" in enviados[0]


def test_netflix_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/netflix"))

    assert "PORTFOLIO" in enviados[0]


def test_ps5(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.02),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/playstation"))

    assert "Te da para <b>2 PS5</b>" in enviados[0]


def test_ps5_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/ps5"))

    assert "PORTFOLIO" in enviados[0]


def test_tesla(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 1.0),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/tesla"))

    assert "Te da para <b>2 Teslas</b>" in enviados[0]


def test_tesla_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/tesla"))

    assert "PORTFOLIO" in enviados[0]


def test_spotify(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.001),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/spotify"))

    assert "Te paga <b>8 meses</b>" in enviados[0]


def test_spotify_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/spotify"))

    assert "PORTFOLIO" in enviados[0]


def test_cana(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.02),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/caña"))

    assert "Te da para <b>666 cañas</b>" in enviados[0]


def test_cana_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/cerveza"))

    assert "PORTFOLIO" in enviados[0]


def test_switch(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.01),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/nintendo"))

    assert "Te da para <b>2 Switch 2</b>" in enviados[0]


def test_switch_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/switch"))

    assert "PORTFOLIO" in enviados[0]


def test_cine(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.01),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/peli"))

    assert "Te da para <b>111 entradas</b>" in enviados[0]


def test_cine_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/cine"))

    assert "PORTFOLIO" in enviados[0]


def test_gimnasio(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.01),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/gym"))

    assert "Te paga <b>25 meses</b>" in enviados[0]


def test_gimnasio_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/gimnasio"))

    assert "PORTFOLIO" in enviados[0]


def test_vuelo(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.02),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/viaje"))

    assert "Te da para <b>3 viajes</b>" in enviados[0]


def test_vuelo_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/vuelo"))

    assert "PORTFOLIO" in enviados[0]


def test_super(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.02),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/supermercado"))

    assert "Te da para <b>20 carros</b>" in enviados[0]


def test_super_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/super"))

    assert "PORTFOLIO" in enviados[0]


def test_kebab(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.01),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/doner"))

    assert "Te da para <b>166 kebabs</b>" in enviados[0]


def test_kebab_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/kebab"))

    assert "PORTFOLIO" in enviados[0]


def test_metro(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.01),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/abono"))

    assert "Te paga <b>33 meses</b>, más de 2 años" in enviados[0]


def test_metro_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/metro"))

    assert "PORTFOLIO" in enviados[0]


def test_luz(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.01),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/factura"))

    assert "Te paga <b>16 meses</b>, más de 1 año" in enviados[0]


def test_luz_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/luz"))

    assert "PORTFOLIO" in enviados[0]


def test_libro(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.01),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/leer"))

    assert "Te da para <b>50 libros</b>" in enviados[0]


def test_libro_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/libro"))

    assert "PORTFOLIO" in enviados[0]


def test_concierto(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.01),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/musica"))

    assert "Te da para <b>20 entradas</b>" in enviados[0]


def test_concierto_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/concierto"))

    assert "PORTFOLIO" in enviados[0]


def test_airpods(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.01),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/cascos"))

    assert "Te da para <b>4 AirPods Pro</b>" in enviados[0]


def test_airpods_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/airpods"))

    assert "PORTFOLIO" in enviados[0]


def test_zapatillas(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.01),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/zapas"))

    assert "Te da para <b>8 pares</b>" in enviados[0]


def test_zapatillas_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/zapatillas"))

    assert "PORTFOLIO" in enviados[0]


def test_ave(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.01),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/tren"))

    assert "Te da para <b>12 viajes</b>" in enviados[0]


def test_ave_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/ave"))

    assert "PORTFOLIO" in enviados[0]


def test_menu(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.01),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/menú"))

    assert "Te da para <b>76 menús</b>" in enviados[0]


def test_menu_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/menu"))

    assert "PORTFOLIO" in enviados[0]


def test_hotel(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.01),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/noches"))

    assert "Te da para <b>10 noches</b>" in enviados[0]


def test_hotel_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/hotel"))

    assert "PORTFOLIO" in enviados[0]


def test_peluqueria(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.01),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/pelo"))

    assert "Te da para <b>66 cortes</b>" in enviados[0]


def test_peluqueria_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/peluquería"))

    assert "PORTFOLIO" in enviados[0]


def test_macbook(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.03),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/portátil"))

    assert "Te da para <b>2 MacBook Air</b>" in enviados[0]


def test_macbook_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/macbook"))

    assert "PORTFOLIO" in enviados[0]


def test_bici(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.02),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/bicicleta"))

    assert "Te da para <b>2 bicis de carretera</b>" in enviados[0]


def test_bici_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/bici"))

    assert "PORTFOLIO" in enviados[0]


def test_churros(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.01),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/chocolate"))

    assert "Te da para <b>250 chocolates con churros</b>" in enviados[0]


def test_churros_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/churros"))

    assert "PORTFOLIO" in enviados[0]


def test_loteria(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.01),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/lotería"))

    assert "Te da para <b>50 décimos</b>" in enviados[0]


def test_loteria_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/loteria"))

    assert "PORTFOLIO" in enviados[0]


def test_piso(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.01),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/casa"))

    assert "Te da para <b>0,2 m²</b> en Madrid" in enviados[0]


def test_piso_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/piso"))

    assert "PORTFOLIO" in enviados[0]


def test_futbol(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.01),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/fútbol"))

    assert "Te da para <b>16 entradas</b>" in enviados[0]


def test_futbol_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/futbol"))

    assert "PORTFOLIO" in enviados[0]


def test_taxi(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.01),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/aeropuerto"))

    assert "Te da para <b>30 viajes</b>" in enviados[0]


def test_taxi_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/taxi"))

    assert "PORTFOLIO" in enviados[0]


def test_tortilla(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.01),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/pincho"))

    assert "Te da para <b>333 pinchos</b>" in enviados[0]


def test_tortilla_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/tortilla"))

    assert "PORTFOLIO" in enviados[0]


def test_videojuego(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.01),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/juegos"))

    assert "Te da para <b>12 juegos</b>" in enviados[0]


def test_videojuego_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/videojuego"))

    assert "PORTFOLIO" in enviados[0]


def test_sofa(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.01),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/sofá"))

    assert "Te da para <b>2 sofás</b>" in enviados[0]


def test_sofa_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/sofa"))

    assert "PORTFOLIO" in enviados[0]


def test_navidad(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.01),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/xmas"))

    assert "Te da para <b>10 cestas navideñas</b>" in enviados[0]


def test_navidad_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/navidad"))

    assert "PORTFOLIO" in enviados[0]


def test_bigmac_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/bigmac"))

    assert "PORTFOLIO" in enviados[0]


def test_gasolina_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/gasolina"))

    assert "PORTFOLIO" in enviados[0]


def test_sueldo_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/sueldo"))

    assert "PORTFOLIO" in enviados[0]


def test_sueldo_en_dolares(config, enviados):
    from dataclasses import replace

    main.atender(replace(config, vs_currency="usd"), _mensaje("/sueldo"))

    assert "Solo funciona con <code>VS_CURRENCY=eur</code>" in enviados[0]


def test_cafe_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/cafe"))

    assert "PORTFOLIO" in enviados[0]


def test_enletras(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.0123),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/cheque"))

    assert "Mil doscientos treinta euros" in enviados[0]
    assert "<i>€1.230,00</i>" in enviados[0]


def test_enletras_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/enletras"))

    assert "No tienes cartera puesta" in enviados[0]


def test_lambo_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/lambo"))

    assert "No tienes cartera puesta" in enviados[0]


# --- /quieta ---


def test_quieta(dos_vigiladas, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    _guardar(dos_vigiladas, "bitcoin", 100.0, 10)
    _guardar(dos_vigiladas, "bitcoin", 101.0, 1)
    # Solana acaba igual que empezó, pero por el camino ha subido un 10%
    _guardar(dos_vigiladas, "solana", 100.0, 10)
    _guardar(dos_vigiladas, "solana", 110.0, 5)
    _guardar(dos_vigiladas, "solana", 100.0, 1)

    main.atender(dos_vigiladas, _mensaje("/quieta"))

    assert "La más quieta en 24 h: Bitcoin" in enviados[0]
    assert "un <b>1.00%</b>" in enviados[0]
    assert "· Solana  10.00%" in enviados[0]


def test_quieta_no_cuenta_lo_de_hace_mas_de_un_dia(config, enviados):
    _guardar(config, "bitcoin", 50.0, 30)
    _guardar(config, "bitcoin", 100.0, 2)
    _guardar(config, "bitcoin", 100.0, 1)

    main.atender(config, _mensaje("/calma"))

    assert "un <b>0.00%</b>" in enviados[0]


def test_quieta_lleva_boton_de_actualizar(config, con_teclado):
    _guardar(config, "bitcoin", 100.0, 2)
    _guardar(config, "bitcoin", 101.0, 1)

    main.atender(config, _mensaje("/quieta"))

    assert con_teclado[0][1]["botones"] == [[("🔄 Actualizar", "/quieta")]]


def test_quieta_sin_precios(config, enviados):
    main.atender(config, _mensaje("/quieta"))

    assert "No tengo precios guardados" in enviados[0]


# --- /jamon ---


def test_jamon(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.02),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/jamón"))

    assert "Vale €2.000,00" in enviados[0]
    assert "<b>4 jamones</b>" in enviados[0]


def test_jamon_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/jamon"))

    assert "No tienes cartera puesta" in enviados[0]


# --- /rolex ---


def test_rolex(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.5),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/rolex"))

    assert "Vale €50.000,00" in enviados[0]
    assert "<b>5 Rolex</b>" in enviados[0]


def test_rolex_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/rolex"))

    assert "No tienes cartera puesta" in enviados[0]


# --- /emoji ---


def test_emoji(con_cartera, enviados, monkeypatch):
    monkeypatch.setattr(
        coingecko, "get_prices", lambda ids, cur: {"bitcoin": 70000.0, "solana": 150.0}
    )
    monkeypatch.setattr(
        coingecko, "cambio_24h", lambda c: {"bitcoin": 8.0, "solana": 6.0}[c]
    )

    main.atender(con_cartera, _mensaje("/emoji"))

    assert enviados[0].startswith("🤑")
    assert "Tu cartera va <b>+7.02%</b> en 24 h" in enviados[0]


def test_emoji_lleva_boton_de_actualizar(con_cartera, con_teclado, monkeypatch):
    monkeypatch.setattr(
        coingecko, "get_prices", lambda ids, cur: {"bitcoin": 70000.0, "solana": 150.0}
    )
    monkeypatch.setattr(coingecko, "cambio_24h", lambda c: 0.0)

    main.atender(con_cartera, _mensaje("/emoji"))

    assert con_teclado[0][1]["botones"] == [[("🔄 Actualizar", "/emoji")]]


def test_emoji_sin_el_cambio_de_una(con_cartera, enviados, monkeypatch):
    monkeypatch.setattr(
        coingecko, "get_prices", lambda ids, cur: {"bitcoin": 70000.0, "solana": 150.0}
    )
    monkeypatch.setattr(
        coingecko, "cambio_24h", lambda c: 3.0 if c == "bitcoin" else None
    )

    main.atender(con_cartera, _mensaje("/emoji"))

    assert enviados[0] == "No sé cómo iba Solana hace 24 h. Prueba en un rato."


def test_emoji_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/emoji"))

    assert "PORTFOLIO" in enviados[0]


# --- /tiempo ---


def test_tiempo(con_cartera, enviados, monkeypatch):
    monkeypatch.setattr(
        coingecko, "get_prices", lambda ids, cur: {"bitcoin": 70000.0, "solana": 150.0}
    )
    monkeypatch.setattr(
        coingecko, "cambio_24h", lambda c: {"bitcoin": -3.0, "solana": -4.0}[c]
    )

    main.atender(con_cartera, _mensaje("/tiempo"))

    assert enviados[0].startswith("🌧️ <b>Lluvia</b>")
    assert "en 24 h" in enviados[0]


def test_tiempo_lleva_boton_de_actualizar(con_cartera, con_teclado, monkeypatch):
    monkeypatch.setattr(
        coingecko, "get_prices", lambda ids, cur: {"bitcoin": 70000.0, "solana": 150.0}
    )
    monkeypatch.setattr(coingecko, "cambio_24h", lambda c: 0.0)

    main.atender(con_cartera, _mensaje("/clima"))

    assert con_teclado[0][0].startswith("☁️ <b>Nublado</b>")
    assert con_teclado[0][1]["botones"] == [[("🔄 Actualizar", "/tiempo")]]


def test_tiempo_sin_el_cambio_de_una(con_cartera, enviados, monkeypatch):
    monkeypatch.setattr(
        coingecko, "get_prices", lambda ids, cur: {"bitcoin": 70000.0, "solana": 150.0}
    )
    monkeypatch.setattr(
        coingecko, "cambio_24h", lambda c: 3.0 if c == "bitcoin" else None
    )

    main.atender(con_cartera, _mensaje("/tiempo"))

    assert enviados[0] == "No sé cómo iba Solana hace 24 h. Prueba en un rato."


def test_tiempo_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/tiempo"))

    assert "PORTFOLIO" in enviados[0]


# --- /dato ---


def test_dato(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())

    main.atender(config, _mensaje("/dato"))

    assert enviados[0].startswith("🤓 <b>¿Sabías que…?</b>")


# --- /quiz ---


def test_quiz_pregunta_y_responde_con_botones(
    config, con_teclado, contestados, monkeypatch
):
    from crypto_tracker import quiz

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    monkeypatch.setattr(quiz, "sacar", lambda: 1)

    main.atender(config, _mensaje("/quiz"))
    texto, kw = con_teclado[0]
    assert texto == "❓ <b>¿Cuántos bitcoin habrá como mucho?</b>"
    [[(_, buena)], *_] = kw["botones"]

    main.atender_boton(config, _boton(buena))
    assert contestados == ["q1"]
    texto, kw = con_teclado[1]
    assert texto.startswith("✅ <b>¡Bien!</b>")
    assert kw["botones"] == [[("🎲 Otra pregunta", "/quiz")]]


def test_quiz_con_lo_que_sea_saca_otra(config, con_teclado):
    main.atender(config, _mensaje("/quiz hola"))

    assert con_teclado[0][0].startswith("❓")


# --- /excusa ---


def test_excusa(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    monkeypatch.setattr(excusa, "elegir", lambda: excusa.EXCUSAS[0])

    main.atender(config, _mensaje("/excusa"))

    assert "<i>«Es culpa de la Fed." in enviados[0]


# --- /horoscopo ---


def test_horoscopo(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())

    main.atender(config, _mensaje("/horoscopo Géminis"))

    assert enviados[0].startswith("🔮 <b>♊ Géminis</b>")
    assert "Cripto de la suerte" in enviados[0]


def test_horoscopo_sin_signo(config, enviados):
    main.atender(config, _mensaje("/horoscopo"))

    assert enviados[0] == "¿De qué signo? Por ejemplo: /horoscopo aries"


# --- /aceite ---


def test_aceite(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.02),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/aove"))

    assert "Vale €2.000,00" in enviados[0]
    assert "<b>250 litros</b>" in enviados[0]


def test_aceite_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/aceite"))

    assert "No tienes cartera puesta" in enviados[0]


# --- /bola ---


def test_bola(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    monkeypatch.setattr(bola, "agitar", lambda: "Mejor no.")

    main.atender(config, _mensaje("/bola ¿Vendo ya?"))

    assert "<b>¿Vendo ya?</b>" in enviados[0]
    assert "<i>«Mejor no.»</i>" in enviados[0]


def test_bola_sin_pregunta(config, enviados):
    main.atender(config, _mensaje("/bola"))

    assert "Pregúntame algo" in enviados[0]


# --- /refran ---


def test_refran(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    monkeypatch.setattr(refran, "elegir", lambda: refran.REFRANES[0])

    main.atender(config, _mensaje("/refrán"))

    assert "<i>«A quien madruga, el halving le ayuda.»</i>" in enviados[0]


# --- /galleta ---


def test_galleta(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())

    main.atender(config, _mensaje("/fortuna"))
    main.atender(config, _mensaje("/galleta"))

    assert "🥠 <b>Tu galleta de la suerte</b>" in enviados[0]
    assert enviados[0] == enviados[1]


# --- /tarot ---


def test_tarot(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    monkeypatch.setattr(tarot, "sacar", lambda: tarot.CARTAS[0])

    main.atender(config, _mensaje("/carta"))

    assert "🐋 <b>La Ballena</b>" in enviados[0]


# --- /paella ---


def test_paella(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.02),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/paellas"))

    assert "Vale €2.000,00" in enviados[0]
    assert "<b>33 paellas</b>" in enviados[0]


def test_paella_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/paella"))

    assert "No tienes cartera puesta" in enviados[0]


# --- /croquetas ---


def test_croquetas(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.02),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/croqueta"))

    assert "Vale €2.000,00" in enviados[0]
    assert "<b>200 raciones</b>" in enviados[0]


def test_croquetas_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/croquetas"))

    assert "No tienes cartera puesta" in enviados[0]


# --- /pan ---


def test_pan(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.02),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/barras"))

    assert "Vale €2.000,00" in enviados[0]
    assert "<b>1.666 barras</b>" in enviados[0]


def test_pan_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/pan"))

    assert "No tienes cartera puesta" in enviados[0]


# --- /meta ---


def test_meta(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.02),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/goal 10k"))

    assert "Vale €2.000,00" in enviados[0]
    assert "Te faltan <b>€8.000,00</b>" in enviados[0]
    assert "+400.00%" in enviados[0]


def test_meta_mal_escrita(config, enviados):
    main.atender(config, _mensaje("/meta"))

    assert "/meta 10000" in enviados[0]


def test_meta_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/meta 10000"))

    assert "No tienes cartera puesta" in enviados[0]


# --- /mes ---


def test_mes(con_semana, enviados, sin_fotos_de_verdad, monkeypatch):
    from datetime import datetime

    from crypto_tracker import mes

    monkeypatch.setattr(mes, "horas", lambda ahora: 48)
    # Del mes pasado: no tiene que contar.
    _guardar(con_semana, "bitcoin", 10000.0, 60)
    _guardar(con_semana, "solana", 10.0, 60)
    _semana_guardada(con_semana, 47)

    main.atender(con_semana, _mensaje("/mensual"))

    [(png, pie)] = sin_fotos_de_verdad
    assert png
    assert f"🗓️ <b>Tu {mes.nombre(datetime.now())}</b>" in pie
    assert "+3.57% (+€250,00) en lo que va de mes" in pie
    assert "semana" not in pie
    assert enviados == []


def test_mes_sin_precios(con_semana, enviados):
    main.atender(con_semana, _mensaje("/mes"))

    assert "Aún no tengo precios de este mes" in enviados[0]


def test_mes_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/mes"))

    assert enviados[0] == main.SIN_CARTERA


# --- /anual ---


def test_anual(con_semana, enviados, sin_fotos_de_verdad, monkeypatch):
    from datetime import datetime

    from crypto_tracker import mes

    monkeypatch.setattr(mes, "horas_del_ano", lambda ahora: 48)
    _guardar(con_semana, "bitcoin", 10000.0, 60)
    _guardar(con_semana, "solana", 10.0, 60)
    _semana_guardada(con_semana, 47)

    main.atender(con_semana, _mensaje("/año"))

    [(png, pie)] = sin_fotos_de_verdad
    assert png
    assert f"🗓️ <b>Tu {datetime.now().year}</b>" in pie
    assert "+3.57% (+€250,00) en lo que va de año" in pie
    assert "HISTORY_DAYS" not in pie


def test_anual_avisa_si_borra_los_precios_antes(
    con_semana, sin_fotos_de_verdad, monkeypatch
):
    from dataclasses import replace

    from crypto_tracker import mes

    monkeypatch.setattr(mes, "horas_del_ano", lambda ahora: 200 * 24)
    dibujadas = []
    monkeypatch.setattr(
        main.grafica, "dibujar", lambda *a, **k: dibujadas.append(k) or b"png"
    )
    _semana_guardada(con_semana, 47)

    main.atender(replace(con_semana, history_days=90), _mensaje("/anual"))

    [(_, pie)] = sin_fotos_de_verdad
    assert "Solo tengo precios desde" in pie
    assert "HISTORY_DAYS=366" in pie
    # La gráfica no puede decir "desde el 1 de enero" si empieza más tarde.
    assert dibujadas[0]["subtitulo"].startswith("Desde el ")
    assert "enero" not in dibujadas[0]["subtitulo"]


def test_anual_sin_precios(con_semana, enviados):
    main.atender(con_semana, _mensaje("/ytd"))

    assert "Aún no tengo precios de este año" in enviados[0]


# --- /hodl ---


def test_hodl(config, enviados, monkeypatch):
    _precio(monkeypatch, {"solana": 150.0, "bitcoin": 60000.0, "ethereum": 3000.0})
    main.atender(config, _mensaje("/compra solana 1 100"))
    main.atender(config, _mensaje("/compra bitcoin 0.02 1200"))
    main.atender(config, _mensaje("/venta bitcoin 0.005 350"))
    main.atender(config, _mensaje("/compra ethereum 1 3000"))
    main.atender(config, _mensaje("/venta ethereum todo"))

    main.atender(config, _mensaje("/diamante"))

    texto = enviados[-1]
    assert "<b>Solana</b>  hoy" in texto
    assert "desde la compra del" in texto
    assert "<b>Bitcoin</b>  hoy" in texto
    assert "desde que vendiste un poco el" in texto
    # Ya no la tienes: no sale.
    assert "Ethereum" not in texto


def test_hodl_solo_con_el_env(config, enviados):
    from dataclasses import replace

    config = replace(config, cartera=(Posicion("bitcoin", 0.02),))

    main.atender(config, _mensaje("/hodl"))

    assert "No sé desde cuándo tienes nada" in enviados[0]


def test_hodl_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/hodl"))

    assert enviados[0] == main.SIN_CARTERA


# --- /ppt ---


def test_ppt(config, enviados, monkeypatch):
    from crypto_tracker import ppt

    monkeypatch.setattr(ppt, "sacar", lambda: "piedra")

    main.atender(config, _mensaje("/jugar tijeras"))

    assert "Tú ✌️ tijera · yo ✊ piedra" in enviados[0]
    assert "Gana el bot" in enviados[0]


def test_ppt_sin_decir_nada(config, enviados):
    main.atender(config, _mensaje("/ppt"))

    assert "Saca piedra, papel o tijera" in enviados[0]


# --- /record ---


def test_record(con_semana, enviados):
    _guardar(con_semana, "bitcoin", 60000.0, 50)
    _guardar(con_semana, "solana", 100.0, 50)
    _guardar(con_semana, "bitcoin", 70000.0, 30)
    _guardar(con_semana, "solana", 120.0, 30)
    _guardar(con_semana, "bitcoin", 65000.0, 0)
    _guardar(con_semana, "solana", 110.0, 0)

    main.atender(con_semana, _mensaje("/pico"))

    # 0,1 BTC y 10 SOL: 8.200 en el pico y 7.600 ahora.
    assert "<b>€8.200,00</b>" in enviados[0]
    assert "Ahora vale €7.600,00: 🔻 -7.32%" in enviados[0]
    assert "le faltan <b>€600,00</b>" in enviados[0]


def test_record_sin_precios(con_semana, enviados):
    main.atender(con_semana, _mensaje("/record"))

    assert "Aún no tengo precios guardados" in enviados[0]


def test_record_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/record"))

    assert enviados[0] == main.SIN_CARTERA


# --- /adivina ---


def test_adivina(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    _precio_de(config, "bitcoin", 70000.0, 5)

    main.atender(config, _mensaje("/adivinar 67k"))

    assert "🙂 <b>Caliente</b>" in enviados[0]
    assert "corto por €3.000,00 (4.29%)" in enviados[0]


def test_adivina_otra_la_pide(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: {"ethereum": 2500.0})

    main.atender(config, _mensaje("/adivina eth 2500"))

    assert "🎯 <b>¡Clavado!</b>" in enviados[0]


def test_adivina_mal_escrito(config, enviados):
    main.atender(config, _mensaje("/adivina"))

    assert "/adivina 70000" in enviados[0]


# --- /racha cartera ---


def test_racha_cartera(con_semana, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    # 0,1 BTC y 10 SOL: 7.000, 6.900, 7.100 y 7.200.
    for dias, btc in [(3, 60000.0), (2, 59000.0), (1, 61000.0), (0, 62000.0)]:
        _precio_de(con_semana, "bitcoin", btc, dias * 24 * 60 + 5)
        _precio_de(con_semana, "solana", 100.0, dias * 24 * 60 + 5)

    main.atender(con_semana, _mensaje("/racha Cartera"))

    assert "<b>Tu cartera</b> lleva <b>2 días</b> seguidos subiendo" in enviados[0]
    assert "€6.900,00 → €7.200,00" in enviados[0]
    assert "Con lo que tienes hoy" in enviados[0]


def test_racha_cartera_sin_precios(con_semana, enviados):
    main.atender(con_semana, _mensaje("/racha cartera"))

    assert "No tengo precios guardados de tu cartera" in enviados[0]


def test_racha_cartera_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/racha cartera"))

    assert enviados[0] == main.SIN_CARTERA


# --- /vsbtc ---


def _movimiento_hace(config, coin_id, tipo, cantidad, coste, horas_atras):
    import sqlite3
    from datetime import datetime, timedelta, timezone

    cuando = datetime.now(timezone.utc) - timedelta(hours=horas_atras)
    conn = sqlite3.connect(config.database_path)
    conn.execute(
        "INSERT INTO movimientos (coin_id, tipo, cantidad, coste, created_at) "
        "VALUES (?,?,?,?,?)",
        (coin_id, tipo, cantidad, coste, cuando.isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()


def test_vsbtc(config, enviados, monkeypatch):
    _guardar(config, "bitcoin", 50000.0, 48)
    _movimiento_hace(config, "solana", "compra", 10, 1000, 48)
    monkeypatch.setattr(
        coingecko, "get_prices", lambda ids, cur: {"bitcoin": 60000.0, "solana": 150.0}
    )

    main.atender(config, _mensaje("/vsbtc"))

    # 1.000 € en SOL valen 1.500; en BTC serían 0,02 a 60.000 = 1.200.
    assert "<b>€1.500,00</b>" in enviados[0]
    assert "0,02 BTC: €1.200,00" in enviados[0]
    assert "Le ganas a bitcoin por <b>€300,00</b> (+25,0%)" in enviados[0]


def test_vsbtc_por_su_otro_nombre(config, enviados, monkeypatch):
    _guardar(config, "bitcoin", 50000.0, 48)
    _movimiento_hace(config, "bitcoin", "compra", 0.02, 1000, 48)
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 60000.0})

    main.atender(config, _mensaje("/vsbitcoin"))

    assert "Vas igual que bitcoin" in enviados[0]


def test_vsbtc_sin_movimientos(config, enviados):
    main.atender(config, _mensaje("/vsbtc"))

    assert "No has apuntado ninguna compra" in enviados[0]


def test_vsbtc_sin_bitcoin_guardado(config, enviados, monkeypatch):
    monkeypatch.setattr(
        coingecko, "get_prices", lambda ids, cur: {"bitcoin": 60000.0, "solana": 150.0}
    )
    _movimiento_hace(config, "solana", "compra", 10, 1000, 48)

    main.atender(config, _mensaje("/vsbtc"))

    assert "No tengo el precio de bitcoin" in enviados[0]


def test_vsbtc_sin_conexion(config, enviados, monkeypatch):
    _guardar(config, "bitcoin", 50000.0, 48)
    _movimiento_hace(config, "solana", "compra", 10, 1000, 48)

    def falla(*a, **k):
        raise coingecko.CoinGeckoError("sin red")

    monkeypatch.setattr(coingecko, "get_prices", falla)
    main.atender(config, _mensaje("/vsbtc"))

    assert "No he podido consultar los precios" in enviados[0]


def test_vsbtc_cuenta_lo_que_acabas_de_apuntar(config, enviados, monkeypatch):
    _guardar(config, "bitcoin", 50000.0, 48)
    _movimiento_hace(config, "solana", "compra", 10, 1000, 48)
    # vendida hace nada: el bitcoin de ahora sale de la consulta
    _movimiento_hace(config, "solana", "venta", 5, 750, 0)
    monkeypatch.setattr(
        coingecko, "get_prices", lambda ids, cur: {"bitcoin": 60000.0, "solana": 150.0}
    )

    main.atender(config, _mensaje("/vsbtc"))

    assert "no cuenta" not in enviados[0]
    # 0,02 BTC menos 750/60.000 = 0,0075
    assert "0,0075 BTC" in enviados[0]


def test_vsbtc_sin_precio_de_hoy_de_una(config, enviados, monkeypatch):
    _guardar(config, "bitcoin", 50000.0, 48)
    _movimiento_hace(config, "solana", "compra", 10, 1000, 48)
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 60000.0})

    main.atender(config, _mensaje("/vsbtc"))

    assert "No he podido consultar los precios" in enviados[0]


# --- /rebalanceo ---


PRECIOS_REBALANCEO = {"bitcoin": 60000.0, "ethereum": 3000.0, "solana": 150.0}


@pytest.fixture
def para_rebalanceo(config, monkeypatch):
    from dataclasses import replace

    from crypto_tracker.config import parse_cartera

    monkeypatch.setattr(
        coingecko,
        "get_prices",
        lambda ids, cur: {c: p for c, p in PRECIOS_REBALANCEO.items() if c in ids},
    )
    # 0,1 BTC = 6.000 y 1 ETH = 3.000 y 6,666 SOL = 1.000
    return replace(
        config, cartera=parse_cartera("bitcoin:0.1,ethereum:1,solana:6.6666666667")
    )


def test_rebalanceo(para_rebalanceo, enviados):
    main.atender(para_rebalanceo, _mensaje("/rebalanceo btc 50 eth 30 sol 20"))

    assert "Vende <b>€1.000,00</b> de Bitcoin" in enviados[0]
    assert "Compra <b>€1.000,00</b> de Solana" in enviados[0]
    assert "Ethereum ya está bien: 30%" in enviados[0]


def test_rebalanceo_a_secas(para_rebalanceo, enviados):
    main.atender(para_rebalanceo, _mensaje("/rebalancear"))

    assert "a partes iguales" in enviados[0]
    assert "Vende <b>€2.666,67</b> de Bitcoin" in enviados[0]


def test_rebalanceo_con_una_nueva(para_rebalanceo, enviados):
    main.atender(para_rebalanceo, _mensaje("/rebalanceo btc 100"))

    assert "Vende toda la de Ethereum" in enviados[0]
    assert "Vende toda la de Solana" in enviados[0]
    assert "Compra <b>€4.000,00</b> de Bitcoin" in enviados[0]


def test_rebalanceo_nombre_mal(para_rebalanceo, enviados):
    main.atender(para_rebalanceo, _mensaje("/rebalanceo btc 50 bitcon 50"))

    assert "No encuentro <b>bitcon</b>" in enviados[0]


def test_rebalanceo_no_suma(para_rebalanceo, enviados):
    main.atender(para_rebalanceo, _mensaje("/rebalanceo btc 50 eth 30"))

    assert "suma 80%" in enviados[0]


def test_rebalanceo_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/rebalanceo btc 100"))

    assert enviados[0] == main.SIN_CARTERA


# --- /compras ---


def test_compras(config, enviados, monkeypatch):
    _movimiento_hace(config, "bitcoin", "compra", 0.01, 400, 48)
    _movimiento_hace(config, "ethereum", "compra", 1, 4000, 24)
    precios = {"bitcoin": 60000.0, "ethereum": 3000.0}
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: precios)

    main.atender(config, _mensaje("/compras"))

    assert "🥇 La mejor: 0,01 de Bitcoin" in enviados[0]
    assert "🥴 La peor: 1 de Ethereum" in enviados[0]
    assert "De 2 compras, 1 van ganando y 1 perdiendo" in enviados[0]


def test_compras_de_una(config, enviados, monkeypatch):
    _movimiento_hace(config, "bitcoin", "compra", 0.01, 400, 48)
    _movimiento_hace(config, "ethereum", "compra", 1, 4000, 24)
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 60000.0})

    main.atender(config, _mensaje("/compras btc"))

    assert "Tus compras de Bitcoin" in enviados[0]
    assert "Solo tienes una compra" in enviados[0]


def test_compras_no_confunde_con_compra(config, enviados):
    main.atender(config, _mensaje("/compras"))

    assert "No has apuntado ninguna compra" in enviados[0]


def test_compras_sin_lo_que_costaron(config, enviados, monkeypatch):
    _movimiento_hace(config, "bitcoin", "compra", 0.01, None, 48)
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 60000.0})

    main.atender(config, _mensaje("/compras"))

    assert "no llevan lo que costaron" in enviados[0]


# --- /inflacion ---


def test_inflacion(config, enviados, monkeypatch):
    from datetime import date

    _movimiento_hace(config, "bitcoin", "compra", 0.02, 1000, 400 * 24)
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 60000.0})
    monkeypatch.setattr(
        inflacion, "pedir", lambda: {date(2020, 1, 1): 100.0, date(2026, 9, 1): 110.0}
    )

    main.atender(config, _mensaje("/ipc"))

    assert "🎈 <b>Tu cartera contra la inflación</b>" in enviados[0]
    assert "✅ Le ganas a la inflación" in enviados[0]


def test_inflacion_sin_eurostat(config, enviados, monkeypatch):
    _movimiento_hace(config, "bitcoin", "compra", 0.02, 1000, 400 * 24)

    def pedir():
        raise inflacion.InflacionError("Eurostat no contesta")

    monkeypatch.setattr(inflacion, "pedir", pedir)
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())

    main.atender(config, _mensaje("/inflacion"))

    assert "No he podido mirar el IPC: Eurostat no contesta" in enviados[0]


def test_inflacion_sin_compras(config, enviados, monkeypatch):
    monkeypatch.setattr(inflacion, "pedir", lambda: pytest.fail())

    main.atender(config, _mensaje("/inflacion"))

    assert "No has apuntado ninguna compra" in enviados[0]


def test_inflacion_sin_lo_que_costaron(config, enviados, monkeypatch):
    _movimiento_hace(config, "bitcoin", "compra", 0.01, None, 48)
    monkeypatch.setattr(inflacion, "pedir", lambda: pytest.fail())

    main.atender(config, _mensaje("/inflacion"))

    assert "no llevan lo que costaron" in enviados[0]


# --- /deposito ---


def test_deposito(config, enviados, monkeypatch):
    _movimiento_hace(config, "bitcoin", "compra", 0.02, 1000, 365 * 24)
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 55000.0})

    main.atender(config, _mensaje("/deposito"))

    assert "contra un depósito al 3%" in enviados[0]
    assert "sería €1.030,00 (€30,00 de intereses)" in enviados[0]
    assert "🏆 Le ganas al depósito por <b>€70,00</b>" in enviados[0]
    assert "tendría que dar un <b>10,0%</b> al año" in enviados[0]


def test_deposito_con_interes(config, enviados, monkeypatch):
    _movimiento_hace(config, "bitcoin", "compra", 0.02, 1000, 365 * 24)
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 50000.0})

    main.atender(config, _mensaje("/banco 2,5%"))

    assert "contra un depósito al 2,5%" in enviados[0]
    assert "🐢 El depósito te gana por <b>€25,00</b>" in enviados[0]


def test_deposito_mal_escrito(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())

    main.atender(config, _mensaje("/deposito mucho"))

    assert "no es un interés" in enviados[0]


def test_deposito_sin_compras(config, enviados):
    main.atender(config, _mensaje("/deposito"))

    assert "No has apuntado ninguna compra" in enviados[0]


# --- /rentabilidad ---


def test_rentabilidad(config, enviados, monkeypatch):
    _movimiento_hace(config, "bitcoin", "compra", 0.02, 1000, 365 * 24)
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 55000.0})

    main.atender(config, _mensaje("/rentabilidad"))

    assert "Has metido €1.000,00. Hoy vale €1.100,00" in enviados[0]
    assert "(+10,0%) en 365 días" in enviados[0]
    assert "Al año, un <b>+10,0%</b>" in enviados[0]


def test_rentabilidad_por_tir(config, enviados, monkeypatch):
    _movimiento_hace(config, "bitcoin", "compra", 0.02, 1000, 5 * 24)
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 55000.0})

    main.atender(config, _mensaje("/tir"))

    assert "Con menos de un mes no lo paso a anual" in enviados[0]


def test_rentabilidad_vendido_todo_no_consulta(config, enviados, monkeypatch):
    _movimiento_hace(config, "bitcoin", "compra", 0.02, 1000, 400 * 24)
    _movimiento_hace(config, "bitcoin", "venta", 0.02, 1200, 35 * 24)
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())

    main.atender(config, _mensaje("/rentabilidad"))

    assert "sacado €1.200,00" in enviados[0]
    assert "Ganas <b>+€200,00</b>" in enviados[0]


def test_rentabilidad_sin_compras(config, enviados):
    main.atender(config, _mensaje("/rentabilidad"))

    assert "No has apuntado ninguna compra" in enviados[0]


def test_rentabilidad_sin_lo_que_costaron(config, enviados, monkeypatch):
    _movimiento_hace(config, "bitcoin", "compra", 0.02, None, 48)
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())

    main.atender(config, _mensaje("/rentabilidad"))

    assert "no llevan lo que costaron" in enviados[0]


def test_rentabilidad_sin_conexion(config, enviados, monkeypatch):
    _movimiento_hace(config, "bitcoin", "compra", 0.02, 1000, 48)
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {})

    main.atender(config, _mensaje("/rentabilidad"))

    assert "No he podido consultar los precios" in enviados[0]


# --- /calendario ---


def test_calendario(config, enviados, sin_fotos_de_verdad):
    from datetime import datetime

    from crypto_tracker import mes

    # ayer a 60.000 y hoy a 63.000: hoy sale +5%
    _precio_de(config, "bitcoin", 60000.0, 24 * 60)
    _precio_de(config, "bitcoin", 63000.0, 1)

    main.atender(config, _mensaje("/calendario btc"))

    [(png, pie)] = sin_fotos_de_verdad
    nombre = mes.nombre(datetime.now().astimezone())
    assert png
    assert f"Bitcoin en {nombre}" in pie
    assert "+5,0%" in pie


def test_calendario_a_secas_la_primera(config, enviados, sin_fotos_de_verdad):
    _precio_de(config, "bitcoin", 60000.0, 24 * 60)
    _precio_de(config, "bitcoin", 63000.0, 1)

    main.atender(config, _mensaje("/calendario"))

    assert "Bitcoin en" in sin_fotos_de_verdad[0][1]


def test_calendario_sin_precios(config, enviados, sin_fotos_de_verdad):
    main.atender(config, _mensaje("/calendario solana"))

    assert sin_fotos_de_verdad == []
    assert "No tengo dos días seguidos con precio" in enviados[0]


def test_calendario_mal_escrito(config, enviados):
    main.atender(config, _mensaje("/calendario btc eth octubre"))

    assert "Escríbelo así" in enviados[0]


def test_calendario_sin_imagen_manda_texto(config, enviados, monkeypatch):
    def falla(*a, **k):
        raise grafica.GraficaError("Falta matplotlib")

    monkeypatch.setattr(grafica, "dibujar_calendario", falla)
    _precio_de(config, "bitcoin", 60000.0, 24 * 60)
    _precio_de(config, "bitcoin", 63000.0, 1)

    main.atender(config, _mensaje("/calendario btc"))

    assert "Bitcoin en" in enviados[0]


# --- /riesgo ---


def test_riesgo(con_semana, enviados, monkeypatch):
    # 0,1 BTC y 10 SOL; ayer 6.000 + 1.000 y hoy 6.600 + 1.000
    for coin_id, ayer, hoy in (("bitcoin", 60000.0, 66000.0), ("solana", 100, 100)):
        _guardar(con_semana, coin_id, ayer, 24)
        _guardar(con_semana, coin_id, hoy, 0)
    monkeypatch.setattr(
        coingecko, "get_prices", lambda ids, cur: {"bitcoin": 66000.0, "solana": 100.0}
    )

    main.atender(con_semana, _mensaje("/riesgo"))

    assert "<b>Bitcoin</b> es el 87% de lo que tienes" in enviados[0]
    assert "Con 2 criptos, es como tener 1,3 a partes iguales" in enviados[0]
    # de 7.000 a 7.600: un 8,6% en el día
    assert "Se mueve de media un 8,6% al día" in enviados[0]
    assert "Se mueve menos que bitcoin (10,0%)" in enviados[0]
    assert "🔴 Riesgo alto" in enviados[0]


def test_riesgo_sin_historico(con_semana, enviados, monkeypatch):
    monkeypatch.setattr(
        coingecko, "get_prices", lambda ids, cur: {"bitcoin": 66000.0, "solana": 100.0}
    )

    main.atender(con_semana, _mensaje("/riesgo"))

    assert "es el 87%" in enviados[0]
    assert "Aún no tengo dos días de precios" in enviados[0]


def test_riesgo_sin_precio_de_una(con_semana, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 66000.0})

    main.atender(con_semana, _mensaje("/riesgo"))

    assert "No tengo el precio de <b>solana</b>" in enviados[0]


def test_riesgo_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/riesgo"))

    assert enviados[0] == main.SIN_CARTERA


# con_semana: 0,1 BTC por 5.000 (50.000 de media) y 10 SOL por 1.000
def test_stop(con_semana, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 66000.0})

    main.atender(con_semana, _mensaje("/stop btc -15%"))

    assert "🛑 Te aviso si <b>Bitcoin</b> baja a <b>€42.500,00</b>" in enviados[0]
    assert "un 15% por debajo de lo que te costó (€50.000,00 de media)" in enviados[0]
    assert "Ahora está a €66.000,00: vas +32,0%" in enviados[0]
    [alerta] = database.get_puntuales(con_semana.database_path, "eur")
    assert (alerta.coin_id, alerta.objetivo, alerta.sube) == ("bitcoin", 42500, False)
    assert alerta.nota == "Stop: -15% sobre lo que te costó"
    assert "lo muevo solo a tu nuevo precio medio" in enviados[0]
    assert database.stops(con_semana.database_path) == {alerta.id: -15.0}


def test_el_stop_sigue_al_precio_medio_al_comprar(con_semana, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 45000.0, "solana": 100.0})
    main.atender(con_semana, _mensaje("/stop btc -15%"))
    # Otra 0,1 por 3.000: la media baja de 50.000 a 40.000.
    main.atender(con_semana, _mensaje("/compra btc 0.1 3000"))

    main.ejecutar_ciclo(con_semana, {})

    [a] = database.get_puntuales(con_semana.database_path, "eur")
    assert a.objetivo == pytest.approx(34000)
    assert not any("Era tu /alerta" in t for t in enviados)


def test_un_stop_de_antes_tambien_sigue_al_precio_medio(
    con_semana, enviados, monkeypatch
):
    # Puesto antes de que se guardara el %: solo queda la nota.
    database.crear_puntual(
        con_semana.database_path,
        "bitcoin",
        42500.0,
        False,
        "eur",
        None,
        "Stop: -15% sobre lo que te costó",
    )
    _precio(monkeypatch, {"bitcoin": 45000.0, "solana": 100.0})
    main.atender(con_semana, _mensaje("/compra btc 0.1 3000"))

    main.ejecutar_ciclo(con_semana, {})

    [a] = database.get_puntuales(con_semana.database_path, "eur")
    assert a.objetivo == pytest.approx(34000)


def test_el_stop_sin_cambios_en_la_cartera_no_se_mueve(
    con_semana, enviados, monkeypatch
):
    _precio(monkeypatch, {"bitcoin": 66000.0, "solana": 100.0})
    main.atender(con_semana, _mensaje("/stop btc -15%"))

    main.ejecutar_ciclo(con_semana, {})

    [a] = database.get_puntuales(con_semana.database_path, "eur")
    assert a.objetivo == 42500


def test_el_stop_salta_y_se_borra(con_semana, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 66000.0})
    main.atender(con_semana, _mensaje("/stop btc -15%"))
    enviados.clear()

    _precio(monkeypatch, {"bitcoin": 42000.0, "solana": 100.0})
    main.ejecutar_ciclo(con_semana, {"bitcoin": "%66000.0"})

    aviso = next(t for t in enviados if "Era tu /alerta" in t)
    assert "📝 Stop: -15% sobre lo que te costó" in aviso
    assert database.get_puntuales(con_semana.database_path, "eur") == []


def test_stop_de_ganancia(con_semana, enviados, monkeypatch):
    _precio(monkeypatch, {"solana": 100.0})

    main.atender(con_semana, _mensaje("/stop sol +50%"))

    assert "🎯 Te aviso si <b>Solana</b> sube a <b>€150,00</b>" in enviados[0]
    assert "un 50% por encima" in enviados[0]


def test_stop_de_la_cartera(con_semana, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 66000.0, "solana": 100.0})

    main.atender(con_semana, _mensaje("/stop cartera -20%"))

    # metiste 6.000 y vale 7.600
    assert "<b>tu cartera</b> baja a <b>€4.800,00</b>" in enviados[0]
    assert "de lo que metiste (€6.000,00)" in enviados[0]
    assert "Ahora vale €7.600,00" in enviados[0]
    assert "precio medio cambia" not in enviados[0]


def test_stop_por_el_que_ya_has_pasado(con_semana, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 40000.0})

    main.atender(con_semana, _mensaje("/stop btc -15%"))

    assert "ya vas -20,0% sobre lo que te costó, más allá del -15%" in enviados[0]
    assert database.get_puntuales(con_semana.database_path, "eur") == []


def test_stop_dos_veces(con_semana, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 66000.0})
    main.atender(con_semana, _mensaje("/stop btc -15%"))

    main.atender(con_semana, _mensaje("/stop btc -15%"))

    assert "Ya lo tienes puesto, es la número 1" in enviados[1]


def test_stop_de_una_que_no_tienes(con_semana, enviados, monkeypatch):
    pedidas = _precio(monkeypatch, {"ethereum": 2500.0})

    main.atender(con_semana, _mensaje("/stop eth -15%"))

    assert "No tienes <b>ethereum</b> en la cartera" in enviados[0]
    assert pedidas == []


def test_stop_sin_lo_que_te_costo(config, enviados, monkeypatch):
    from dataclasses import replace

    from crypto_tracker.config import parse_cartera

    sin_coste = replace(config, cartera=parse_cartera("bitcoin:0.1"))
    _precio(monkeypatch, {"bitcoin": 66000.0})

    main.atender(sin_coste, _mensaje("/stop btc -15%"))

    assert "necesito lo que te costó" in enviados[0]


def test_stop_mal_escrito(con_semana, enviados):
    main.atender(con_semana, _mensaje("/stop btc 15%"))

    assert "¿Perder o ganar?" in enviados[0]


def test_stop_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/stop btc -15%"))

    assert enviados[0] == main.SIN_CARTERA


def test_comprar_con_comision(config, enviados, monkeypatch):
    _precio(monkeypatch, {"solana": 140.0})

    main.atender(config, _mensaje("/compra solana 5 700 com 1,5"))

    assert "por €701,50 (con €1,50 de comisión)" in enviados[0]
    assert database.get_cambios_cartera(config.database_path) == {
        "solana": Posicion("solana", 5, 701.5)
    }


def test_comprar_con_comision_en_porcentaje_al_precio_de_ahora(
    config, enviados, monkeypatch
):
    _precio(monkeypatch, {"solana": 150.0})

    main.atender(config, _mensaje("/compra solana 2 fee 0.1%"))

    # 300 al precio de ahora, más un 0,1%
    assert "por €300,30 (con €0,30 de comisión)" in enviados[0]


def test_la_comision_no_hace_parecer_una_errata(config, enviados, monkeypatch):
    # 10 € de comisión en una compra de 20 € la dejaría un 50% por encima
    _precio(monkeypatch, {"solana": 100.0})

    main.atender(config, _mensaje("/compra solana 0.2 20 com 10"))

    assert "⚠️" not in enviados[0]


def test_comprar_con_comision_mal_escrita(config, enviados, monkeypatch):
    _precio(monkeypatch, {"solana": 140.0})

    main.atender(config, _mensaje("/compra solana 5 700 com abc"))

    assert "no es una comisión" in enviados[0]
    assert database.get_cambios_cartera(config.database_path) == {}


def test_vender_con_comision(config, enviados, monkeypatch):
    config = _con_cartera(config, Posicion("bitcoin", 0.02, 1000))
    _precio(monkeypatch, {"bitcoin": 60000.0})

    main.atender(config, _mensaje("/venta bitcoin 0.005 350 com 2"))

    assert "por €348,00 (con €2,00 de comisión)" in enviados[0]
    # costaron 250: la ganancia ya va sin la comisión
    assert "Le sacas +€98,00" in enviados[0]
    [venta] = database.get_ventas(config.database_path)
    assert venta.coste == 348


def test_vender_con_comision_mayor_que_lo_cobrado(config, enviados, monkeypatch):
    config = _con_cartera(config, Posicion("bitcoin", 0.02, 1000))
    _precio(monkeypatch, {"bitcoin": 60000.0})

    main.atender(config, _mensaje("/venta bitcoin 0.005 1 com 2"))

    assert "más que lo que te dieron" in enviados[0]
    assert database.get_ventas(config.database_path) == []


def test_vender_con_comision_sin_conexion_la_apunta_sin_ella(
    config, enviados, monkeypatch
):
    def falla(ids, cur):
        raise coingecko.CoinGeckoError("Sin conexion con CoinGecko")

    monkeypatch.setattr(coingecko, "get_prices", falla)
    config = _con_cartera(config, Posicion("bitcoin", 0.02, 1000))

    main.atender(config, _mensaje("/venta bitcoin 0.005 com 1"))

    assert "comisión" not in enviados[0]
    [venta] = database.get_ventas(config.database_path)
    assert venta.coste is None


def test_comisiones(config, enviados, monkeypatch):
    _precio(monkeypatch, {"solana": 140.0, "bitcoin": 60000.0})
    config = _con_cartera(config, Posicion("bitcoin", 0.02, 1000))
    main.atender(config, _mensaje("/compra solana 5 700 com 1,5"))
    main.atender(config, _mensaje("/venta bitcoin 0.01 600 com 1%"))
    main.atender(config, _mensaje("/compra solana 1 140"))

    main.atender(config, _mensaje("/comisiones"))

    assert "Has pagado <b>€7,50</b> en 2 operaciones" in enviados[-1]
    assert "un 0,58% de lo que moviste" in enviados[-1]
    assert "Bitcoin: €6,00\nSolana: €1,50" in enviados[-1]
    assert "1 compra o venta no lleva comisión apuntada" in enviados[-1]


def test_comisiones_de_un_año_sin_ninguna(config, enviados):
    main.atender(config, _mensaje("/fees 2025"))

    assert "No tienes ninguna comisión apuntada en 2025" in enviados[0]


def test_comisiones_año_raro(config, enviados):
    main.atender(config, _mensaje("/comisiones 1990"))

    assert "Dime un año entre 2009" in enviados[0]


def test_compra_con_comision_y_deshacer(config, enviados, monkeypatch):
    _precio(monkeypatch, {"solana": 140.0})
    main.atender(config, _mensaje("/compra solana 5 700 com 1,5"))

    main.atender(config, _mensaje("/deshacer"))

    assert database.get_cambios_cartera(config.database_path) == {"solana": None}


@pytest.fixture
def con_botones(monkeypatch):
    """Lo que se manda, con sus botones."""
    lista = []
    monkeypatch.setattr(
        telegram,
        "send_message",
        lambda token, chat, texto, **kw: (
            lista.append((texto, kw.get("botones"))) or True
        ),
    )
    return lista


# El 9 de noviembre de 2026 es lunes
LUNES_DCA = datetime(2026, 11, 9, 9, 5).astimezone()


def test_recordar(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 62500.0})

    main.atender(config, _mensaje("/recordar lunes 50 btc"))

    assert (
        "Cada <b>lunes</b> a las 9:00 te recuerdo comprar <b>€50,00</b>"
        in (enviados[0])
    )
    assert "serían 0,0008" in enviados[0]
    [r] = database.get_recordatorios(config.database_path)
    assert (r.coin_id, r.dia, r.importe) == ("bitcoin", 0, 50)


def test_recordar_a_la_hora_del_resumen(con_semana, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 62500.0})

    main.atender(con_semana, _mensaje("/recordar viernes 20 btc"))

    assert "a las 9:00" in enviados[0]


def test_recordar_lista_y_quitar(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 62500.0, "solana": 150.0})
    main.atender(config, _mensaje("/recordar lunes 50 btc"))
    main.atender(config, _mensaje("/recordar jueves 20 sol"))
    enviados.clear()

    main.atender(config, _mensaje("/recordar"))
    main.atender(config, _mensaje("/recordar sol no"))
    main.atender(config, _mensaje("/recordar sol no"))

    assert "<b>Lunes</b>: €50,00 de Bitcoin" in enviados[0]
    assert "<b>Jueves</b>: €20,00 de Solana" in enviados[0]
    assert "ya no te recuerdo la compra de solana" in enviados[1]
    assert "No tenías ningún recordatorio" in enviados[2]
    assert [r.coin_id for r in database.get_recordatorios(config.database_path)] == [
        "bitcoin"
    ]


def test_recordar_sin_ninguno(config, enviados):
    main.atender(config, _mensaje("/recordar"))

    assert "No tienes ningún recordatorio" in enviados[0]


def test_recordar_algo_que_no_existe(config, enviados, monkeypatch):
    _precio(monkeypatch, {})

    main.atender(config, _mensaje("/recordar lunes 50 nada"))

    assert "No encuentro <b>nada</b>" in enviados[0]
    assert database.get_recordatorios(config.database_path) == []


def test_recordar_mal_escrito(config, enviados):
    main.atender(config, _mensaje("/recordar finde 50 btc"))

    assert "no es un día de la semana" in enviados[0]


def test_el_recordatorio_llega_el_dia_una_vez(config, con_botones, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 62500.0})
    main.atender(config, _mensaje("/recordar lunes 50 btc"))
    con_botones.clear()

    main.recordatorios(config, LUNES_DCA - timedelta(days=1))  # domingo
    main.recordatorios(config, LUNES_DCA)
    main.recordatorios(config, LUNES_DCA + timedelta(minutes=5))

    [(texto, botones)] = con_botones
    assert "Toca tu compra de Bitcoin" in texto
    assert "a €62.500,00 son <b>0,0008</b>" in texto
    assert botones == [
        [("✅ Ya la he hecho", "/compra bitcoin 0,0008 50")],
        [("🔕 No recordar más", "/recordar bitcoin no")],
    ]


def test_el_boton_apunta_la_compra(config, con_botones, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 62500.0})
    main.atender(config, _mensaje("/recordar lunes 50 btc"))
    main.recordatorios(config, LUNES_DCA)
    boton = con_botones[-1][1][0][0][1]

    main.atender(config, _mensaje(boton))

    assert database.get_cambios_cartera(config.database_path) == {
        "bitcoin": Posicion("bitcoin", 0.0008, 50)
    }


def test_el_recordatorio_callado_espera(config, con_botones, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 62500.0})
    main.atender(config, _mensaje("/recordar lunes 50 btc"))
    con_botones.clear()
    database.silenciar_hasta(
        config.database_path, datetime.now(timezone.utc) + timedelta(hours=1)
    )

    main.recordatorios(config, LUNES_DCA)

    assert con_botones == []
    [r] = database.get_recordatorios(config.database_path)
    assert r.ultimo is None


def test_el_recordatorio_sin_conexion_se_reintenta(config, con_botones, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 62500.0})
    main.atender(config, _mensaje("/recordar lunes 50 btc"))
    con_botones.clear()

    def falla(ids, cur):
        raise coingecko.CoinGeckoError("Sin conexion con CoinGecko")

    monkeypatch.setattr(coingecko, "get_prices", falla)
    main.recordatorios(config, LUNES_DCA)
    _precio(monkeypatch, {"bitcoin": 62500.0})
    main.recordatorios(config, LUNES_DCA + timedelta(minutes=5))

    assert len(con_botones) == 1


def test_comprar_con_nota(config, enviados, monkeypatch):
    _precio(monkeypatch, {"solana": 140.0})

    main.atender(config, _mensaje("/compra solana 5 700 com 1 por el <b>dip</b>"))

    assert "por €701,00" in enviados[0]
    assert "📝 por el &lt;b&gt;dip&lt;/b&gt;" in enviados[0]
    [m] = database.get_movimientos(config.database_path)
    assert m.nota == "por el <b>dip</b>"


def test_vender_con_nota(config, enviados, monkeypatch):
    config = _con_cartera(config, Posicion("bitcoin", 0.02, 1000))
    _precio(monkeypatch, {"bitcoin": 60000.0})

    main.atender(config, _mensaje("/venta bitcoin todo @70000 para el coche"))

    assert "por €1.400,00" in enviados[0]
    assert "📝 para el coche" in enviados[0]


def test_la_nota_sale_en_movimientos_y_en_compras(config, enviados, monkeypatch):
    _precio(monkeypatch, {"solana": 140.0})
    main.atender(config, _mensaje("/compra solana 5 700 por el halving"))
    main.atender(config, _mensaje("/compra solana 1 100"))
    enviados.clear()

    main.atender(config, _mensaje("/movimientos"))
    main.atender(config, _mensaje("/compras"))

    assert "📝 por el halving" in enviados[0]
    assert enviados[0].count("📝") == 1
    assert "📝 por el halving" in enviados[1]


def test_compra_sin_precio_y_con_nota(config, enviados, monkeypatch):
    _precio(monkeypatch, {"solana": 150.0})

    main.atender(config, _mensaje("/compra solana 2 a ver qué pasa"))

    assert "por €300,00" in enviados[0]
    assert "📝 a ver qué pasa" in enviados[0]


@pytest.fixture
def concentrada(con_semana):
    from dataclasses import replace

    # 0,1 BTC y 10 SOL: con BTC a 66.000 y SOL a 100, BTC es el 87%
    return replace(con_semana, concentracion=70)


def _avisos_concentracion(enviados):
    # Puede ir junto con otros avisos del ciclo, no siempre al principio.
    return [t for t in enviados if "⚖️" in t]


def test_concentracion_avisa_una_vez(concentrada, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 66000.0, "solana": 100.0})

    main.ejecutar_ciclo(concentrada, {})
    main.ejecutar_ciclo(concentrada, {})

    [aviso] = _avisos_concentracion(enviados)
    assert "<b>Bitcoin ya es el 87% de tu cartera</b>" in aviso
    assert "Si cae un 20%, tu cartera cae un 17,4%." in aviso


def test_concentracion_vuelve_a_avisar_si_baja_y_sube(
    concentrada, enviados, monkeypatch
):
    for btc in (66000.0, 15000.0, 66000.0):  # 87%, 60% y otra vez 87%
        _precio(monkeypatch, {"bitcoin": btc, "solana": 100.0})
        main.ejecutar_ciclo(concentrada, {})

    assert len(_avisos_concentracion(enviados)) == 2


def test_concentracion_rondando_el_limite_no_repite(concentrada, enviados, monkeypatch):
    # 87%, 68% (por encima del 65%) y otra vez 87%
    for btc in (66000.0, 21250.0, 66000.0):
        _precio(monkeypatch, {"bitcoin": btc, "solana": 100.0})
        main.ejecutar_ciclo(concentrada, {})

    assert len(_avisos_concentracion(enviados)) == 1


def test_concentracion_sin_el_precio_de_una_no_avisa(
    concentrada, enviados, monkeypatch
):
    _precio(monkeypatch, {"bitcoin": 66000.0})

    main.ejecutar_ciclo(concentrada, {})

    assert _avisos_concentracion(enviados) == []


def test_concentracion_callada_espera(concentrada, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 66000.0, "solana": 100.0})
    database.callar_cripto(
        concentrada.database_path,
        "cartera",
        datetime.now(timezone.utc) + timedelta(hours=1),
    )
    main.ejecutar_ciclo(concentrada, {})
    assert _avisos_concentracion(enviados) == []

    database.callar_cripto(concentrada.database_path, "cartera", None)
    main.ejecutar_ciclo(concentrada, {})

    assert len(_avisos_concentracion(enviados)) == 1


def test_sin_concentracion_no_avisa(con_semana, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 66000.0, "solana": 100.0})

    main.ejecutar_ciclo(con_semana, {})

    assert _avisos_concentracion(enviados) == []


@pytest.fixture
def con_rsi(config):
    from dataclasses import replace

    # 20 días seguidos subiendo, de 100 a 119: RSI 100 si hoy sigue arriba
    for dias in range(1, 21):
        _precio_de(config, "bitcoin", 120.0 - dias, dias * 24 * 60)
    return replace(config, aviso_rsi=True)


def _avisos_rsi(enviados):
    return [t for t in enviados if "RSI de 14 días" in t]


def test_rsi_avisa_una_vez(con_rsi, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 120.0})

    main.ejecutar_ciclo(con_rsi, {})
    main.ejecutar_ciclo(con_rsi, {})

    [aviso] = _avisos_rsi(enviados)
    assert "🔥 <b>Bitcoin está sobrecomprada</b>" in aviso
    assert "RSI de 14 días: <b>100</b>" in aviso
    assert "/rsi bitcoin" in aviso


def test_rsi_de_golpe_a_la_otra_punta_avisa(con_rsi, enviados, monkeypatch):
    for precio in (120.0, 60.0):
        _precio(monkeypatch, {"bitcoin": precio})
        main.ejecutar_ciclo(con_rsi, {})

    arriba, abajo = _avisos_rsi(enviados)
    assert "sobrecomprada" in arriba
    assert "🧊 <b>Bitcoin está sobrevendida</b>" in abajo


def test_rsi_al_alejarse_se_olvida(con_rsi, enviados, monkeypatch):
    database.guardar_zona_rsi(con_rsi.database_path, "bitcoin", "alta")
    _precio(monkeypatch, {"bitcoin": 105.0})  # RSI en medio

    main.ejecutar_ciclo(con_rsi, {})

    assert _avisos_rsi(enviados) == []
    assert database.zona_rsi(con_rsi.database_path, "bitcoin") is None


def test_rsi_sin_dias_suficientes_no_avisa(config, enviados, monkeypatch):
    from dataclasses import replace

    _precio(monkeypatch, {"bitcoin": 120.0})

    main.ejecutar_ciclo(replace(config, aviso_rsi=True), {})

    assert _avisos_rsi(enviados) == []


def test_rsi_si_falla_telegram_lo_reintenta(con_rsi, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 120.0})
    monkeypatch.setattr(telegram, "send_message", lambda *a, **k: False)
    main.ejecutar_ciclo(con_rsi, {})
    assert database.zona_rsi(con_rsi.database_path, "bitcoin") is None

    monkeypatch.setattr(
        telegram,
        "send_message",
        lambda t, c, texto, **k: enviados.append(texto) or True,
    )
    main.ejecutar_ciclo(con_rsi, {})

    assert len(_avisos_rsi(enviados)) == 1


def test_rsi_callada_espera(con_rsi, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 120.0})
    database.callar_cripto(
        con_rsi.database_path,
        "bitcoin",
        datetime.now(timezone.utc) + timedelta(hours=1),
    )
    main.ejecutar_ciclo(con_rsi, {})
    assert _avisos_rsi(enviados) == []

    database.callar_cripto(con_rsi.database_path, "bitcoin", None)
    main.ejecutar_ciclo(con_rsi, {})

    assert len(_avisos_rsi(enviados)) == 1


def test_sin_aviso_rsi_no_avisa(config, enviados, monkeypatch):
    for dias in range(1, 21):
        _precio_de(config, "bitcoin", 120.0 - dias, dias * 24 * 60)
    _precio(monkeypatch, {"bitcoin": 120.0})

    main.ejecutar_ciclo(config, {})

    assert _avisos_rsi(enviados) == []


@pytest.fixture
def con_cruce(config):
    from dataclasses import replace

    # 160 días a 100 y los 50 últimos a 110: la de 50 queda por encima de la de 200.
    for dias in range(1, 211):
        _precio_de(config, "bitcoin", 110.0 if dias <= 50 else 100.0, dias * 24 * 60)
    return replace(config, aviso_cruce=True)


def _avisos_cruce(enviados):
    return [t for t in enviados if "Cruz" in t]


def test_cruce_avisa_una_vez(con_cruce, enviados, monkeypatch):
    database.guardar_lado_cruce(con_cruce.database_path, "bitcoin", "abajo")
    _precio(monkeypatch, {"bitcoin": 110.0})

    main.ejecutar_ciclo(con_cruce, {})
    main.ejecutar_ciclo(con_cruce, {})

    [aviso] = _avisos_cruce(enviados)
    assert "🌟 <b>Cruz dorada en Bitcoin</b>" in aviso
    assert database.lado_cruce(con_cruce.database_path, "bitcoin") == "arriba"


def test_cruce_la_primera_vez_no_avisa(con_cruce, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 110.0})

    main.ejecutar_ciclo(con_cruce, {})

    assert _avisos_cruce(enviados) == []
    assert database.lado_cruce(con_cruce.database_path, "bitcoin") == "arriba"


def test_cruce_si_falla_telegram_lo_reintenta(con_cruce, enviados, monkeypatch):
    database.guardar_lado_cruce(con_cruce.database_path, "bitcoin", "abajo")
    _precio(monkeypatch, {"bitcoin": 110.0})
    monkeypatch.setattr(telegram, "send_message", lambda *a, **k: False)

    main.ejecutar_ciclo(con_cruce, {})

    assert database.lado_cruce(con_cruce.database_path, "bitcoin") == "abajo"


def test_cruce_callada_espera(con_cruce, enviados, monkeypatch):
    database.guardar_lado_cruce(con_cruce.database_path, "bitcoin", "abajo")
    _precio(monkeypatch, {"bitcoin": 110.0})
    database.callar_cripto(
        con_cruce.database_path,
        "bitcoin",
        datetime.now(timezone.utc) + timedelta(hours=1),
    )

    main.ejecutar_ciclo(con_cruce, {})
    assert _avisos_cruce(enviados) == []

    database.callar_cripto(con_cruce.database_path, "bitcoin", None)
    main.ejecutar_ciclo(con_cruce, {})
    assert len(_avisos_cruce(enviados)) == 1


def test_sin_aviso_cruce_no_avisa(con_cruce, enviados, monkeypatch):
    from dataclasses import replace

    database.guardar_lado_cruce(con_cruce.database_path, "bitcoin", "abajo")
    _precio(monkeypatch, {"bitcoin": 110.0})

    main.ejecutar_ciclo(replace(con_cruce, aviso_cruce=False), {})

    assert _avisos_cruce(enviados) == []


@pytest.fixture
def con_volumen(config):
    from dataclasses import replace

    for horas in range(12, 12 * 24, 12):
        hace = datetime.now(timezone.utc) - timedelta(hours=horas)
        _volumen_hace(config, 1e10, hace)
    return replace(config, aviso_volumen=True)


def _volumen_hace(config, volumen, cuando):
    import sqlite3

    conn = sqlite3.connect(config.database_path)
    conn.execute(
        "INSERT INTO prices (coin_id, price, currency, created_at, volume) "
        "VALUES ('bitcoin', 100, 'eur', ?, ?)",
        (cuando.isoformat(timespec="seconds"), volumen),
    )
    conn.commit()
    conn.close()


def _con_volumen_de(monkeypatch, volumen):
    _precio(monkeypatch, {"bitcoin": 110.0})
    monkeypatch.setattr(coingecko, "volumenes", lambda ids: {"bitcoin": volumen})


def _avisos_volumen(enviados):
    return [t for t in enviados if "más de lo normal" in t]


def test_volumen_avisa_una_vez(con_volumen, enviados, monkeypatch):
    _con_volumen_de(monkeypatch, 4e10)

    main.ejecutar_ciclo(con_volumen, {})
    main.ejecutar_ciclo(con_volumen, {})

    [aviso] = _avisos_volumen(enviados)
    assert "📢 <b>Bitcoin mueve mucho más de lo normal</b>" in aviso
    assert "4,0 veces lo normal" in aviso
    assert database.volumen_avisado(con_volumen.database_path, "bitcoin")


def test_volumen_guarda_lo_de_cada_consulta(con_volumen, enviados, monkeypatch):
    _con_volumen_de(monkeypatch, 1.2e10)

    main.ejecutar_ciclo(con_volumen, {})

    serie = database.get_volumenes(con_volumen.database_path, "bitcoin", 1, "eur")
    assert [v for _, v in serie] == [1.2e10]
    assert _avisos_volumen(enviados) == []


def test_volumen_al_calmarse_vuelve_a_avisar(con_volumen, enviados, monkeypatch):
    database.guardar_volumen_avisado(con_volumen.database_path, "bitcoin", True)
    _con_volumen_de(monkeypatch, 2.5e10)
    main.ejecutar_ciclo(con_volumen, {})
    assert database.volumen_avisado(con_volumen.database_path, "bitcoin")

    _con_volumen_de(monkeypatch, 1.5e10)
    main.ejecutar_ciclo(con_volumen, {})
    assert not database.volumen_avisado(con_volumen.database_path, "bitcoin")

    _con_volumen_de(monkeypatch, 3.5e10)
    main.ejecutar_ciclo(con_volumen, {})
    assert len(_avisos_volumen(enviados)) == 1


def test_volumen_con_poca_historia_no_avisa(config, enviados, monkeypatch):
    from dataclasses import replace

    _volumen_hace(config, 1e10, datetime.now(timezone.utc) - timedelta(days=2))
    _con_volumen_de(monkeypatch, 9e10)

    main.ejecutar_ciclo(replace(config, aviso_volumen=True), {})

    assert _avisos_volumen(enviados) == []


def test_volumen_si_falla_telegram_lo_reintenta(con_volumen, enviados, monkeypatch):
    _con_volumen_de(monkeypatch, 4e10)
    monkeypatch.setattr(telegram, "send_message", lambda *a, **k: False)

    main.ejecutar_ciclo(con_volumen, {})

    assert not database.volumen_avisado(con_volumen.database_path, "bitcoin")


def test_volumen_callada_espera(con_volumen, enviados, monkeypatch):
    _con_volumen_de(monkeypatch, 4e10)
    database.callar_cripto(
        con_volumen.database_path,
        "bitcoin",
        datetime.now(timezone.utc) + timedelta(hours=1),
    )

    main.ejecutar_ciclo(con_volumen, {})

    assert _avisos_volumen(enviados) == []


def test_sin_aviso_volumen_no_avisa(con_volumen, enviados, monkeypatch):
    from dataclasses import replace

    _con_volumen_de(monkeypatch, 4e10)

    main.ejecutar_ciclo(replace(con_volumen, aviso_volumen=False), {})

    assert _avisos_volumen(enviados) == []


def _guardar_en(config, coin_id, precio, cuando):
    import sqlite3

    conn = sqlite3.connect(config.database_path)
    conn.execute(
        "INSERT INTO prices (coin_id, price, currency, created_at) VALUES (?,?,?,?)",
        (coin_id, precio, "eur", cuando.astimezone(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()


def _año_guardado(config):
    # 0,1 BTC y 10 SOL: de 6.000 en enero a 8.100 en diciembre
    for mes, dia, btc, sol in ((1, 2, 50000, 100), (12, 31, 66000, 150)):
        cuando = datetime(2025, mes, dia, 12).astimezone()
        _guardar_en(config, "bitcoin", btc, cuando)
        _guardar_en(config, "solana", sol, cuando)


UNO_DE_ENERO = datetime(2026, 1, 1, 9, 5).astimezone()


def test_anual_de_un_año(con_semana, enviados):
    _año_guardado(con_semana)

    main.atender(con_semana, _mensaje("/anual 2025"))

    assert "🎆 <b>Tu 2025 en cripto</b>" in enviados[0]
    assert "de €6.000,00 a <b>€8.100,00</b>" in enviados[0]


def test_anual_de_un_año_mal_escrito(con_semana, enviados):
    main.atender(con_semana, _mensaje("/anual 3000"))

    assert "Dime un año entre 2009 y" in enviados[0]


def test_el_resumen_del_año_llega_el_1_de_enero_una_vez(con_semana, enviados):
    _año_guardado(con_semana)

    main.resumen_anual(con_semana, UNO_DE_ENERO - timedelta(days=1))
    main.resumen_anual(con_semana, UNO_DE_ENERO)
    main.resumen_anual(con_semana, UNO_DE_ENERO + timedelta(minutes=5))

    [texto] = enviados
    assert "Tu 2025 en cripto" in texto
    assert "hasta hoy" not in texto


def test_el_resumen_del_año_sin_nada_no_se_manda(con_semana, enviados):
    main.resumen_anual(con_semana, UNO_DE_ENERO)

    assert enviados == []
    assert (
        database.ultimo_resumen(con_semana.database_path, database.ULTIMO_ANUAL)
        == UNO_DE_ENERO.date()
    )


def test_el_resumen_del_año_sin_resumen_diario(config, enviados):
    main.resumen_anual(config, UNO_DE_ENERO)

    assert enviados == []


def test_caida_de_la_cartera(con_semana, enviados):
    # 0,1 BTC y 10 SOL: 7.000, se hunde a 5.000, vuelve a 7.000 y sube a 7.600
    for horas, btc in ((48, 60000.0), (36, 40000.0), (24, 60000.0), (0, 66000.0)):
        _guardar(con_semana, "bitcoin", btc, horas)
        _guardar(con_semana, "solana", 100.0, horas)

    main.atender(con_semana, _mensaje("/caida cartera"))

    assert enviados[0].startswith("📉 <b>Tu cartera</b>")
    assert "está en su máximo del tramo" in enviados[0]
    assert "Peor caída <b>-28.57%</b>: de €7.000,00" in enviados[0]
    assert "Volvió a ese precio en 1 día" in enviados[0]


def test_caida_de_la_cartera_sin_precios(con_semana, enviados):
    main.atender(con_semana, _mensaje("/caida cartera 7d"))

    assert "Aún no tengo dos precios guardados de tu cartera" in enviados[0]


def test_caida_de_la_cartera_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/caida cartera"))

    assert enviados[0] == main.SIN_CARTERA


# --- /modelo721 ---


def _hoy_es(monkeypatch, dia):
    from datetime import date

    class Fecha(date):
        @classmethod
        def today(cls):
            return dia

    monkeypatch.setattr(main, "date", Fecha)
    # El aviso del ciclo y el comando miran la fecha cada uno en su módulo.
    monkeypatch.setattr(revisiones, "date", Fecha)
    monkeypatch.setattr(respuestas_cartera, "date", Fecha)


def _precio_el_31(config, coin_id, precio, año=2025):
    import sqlite3

    from crypto_tracker.modelo721 import cierre

    conn = sqlite3.connect(config.database_path)
    conn.execute(
        "INSERT INTO prices (coin_id, price, currency, created_at) VALUES (?,?,?,?)",
        (coin_id, precio, "eur", cierre(año).isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()


def test_modelo721_fuera_de_plazo(config, enviados, monkeypatch):
    from datetime import date

    _hoy_es(monkeypatch, date(2026, 11, 16))
    config = _con_cartera(config, Posicion("bitcoin", 0.5, 20000))
    _precio(monkeypatch, {"bitcoin": 80000.0})

    main.atender(config, _mensaje("/modelo721"))

    texto = enviados[0]
    assert "<b>Modelo 721</b>" in texto
    assert "31/12" not in texto
    assert "Hoy vale €40.000,00: le faltan €10.000,00" in texto


def test_modelo721_pasa_hoy(config, enviados, monkeypatch):
    from datetime import date

    _hoy_es(monkeypatch, date(2026, 11, 16))
    config = _con_cartera(config, Posicion("bitcoin", 1, 20000))
    _precio(monkeypatch, {"bitcoin": 80000.0})

    main.atender(config, _mensaje("/721"))

    assert "tendrás que presentarlo en 2027" in enviados[0]


def test_modelo721_en_plazo_te_toca(config, enviados, monkeypatch):
    from datetime import date

    _hoy_es(monkeypatch, date(2026, 3, 1))
    config = _con_cartera(config, Posicion("bitcoin", 1, 20000))
    _precio_el_31(config, "bitcoin", 60000.0)
    _precio(monkeypatch, {"bitcoin": 40000.0})

    main.atender(config, _mensaje("/modelo721"))

    texto = enviados[0]
    assert "El 31/12/2025 tu cartera valía <b>€60.000,00</b>" in texto
    assert "<b>te toca presentarlo</b>" in texto
    assert "quedan 30 días" in texto


def test_modelo721_deshace_lo_comprado_despues(config, enviados, monkeypatch):
    from datetime import date

    _hoy_es(monkeypatch, date(2026, 3, 1))
    config = _con_cartera(config, Posicion("bitcoin", 0.5, 20000))
    _precio_el_31(config, "bitcoin", 60000.0)
    _precio(monkeypatch, {"bitcoin": 60000.0})

    main.atender(config, _mensaje("/compra bitcoin 0.5 30000"))  # ya en 2026
    main.atender(config, _mensaje("/modelo721"))

    assert "El 31/12/2025 tu cartera valía €30.000,00" in enviados[-1]
    assert "no te toca" in enviados[-1]


def test_modelo721_sin_el_precio_del_31(config, enviados, monkeypatch):
    from datetime import date

    _hoy_es(monkeypatch, date(2026, 1, 15))
    config = _con_cartera(config, Posicion("bitcoin", 1, 20000))
    _precio(monkeypatch, {"bitcoin": 40000.0})

    main.atender(config, _mensaje("/modelo721"))

    assert "No tengo guardado lo que valía tu cartera el 31/12/2025" in enviados[0]


def test_modelo721_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/modelo721"))

    assert enviados[0] == main.SIN_CARTERA


def _avisos_721(enviados):
    return [t for t in enviados if t.startswith("🏛️")]


def test_aviso_721_una_vez_al_año(config, enviados, monkeypatch):
    from dataclasses import replace

    config = replace(
        _con_cartera(config, Posicion("bitcoin", 1, 20000)), aviso_721=True
    )
    _precio(monkeypatch, {"bitcoin": 60000.0})

    main.ejecutar_ciclo(config, {})
    main.ejecutar_ciclo(config, {})

    [aviso] = _avisos_721(enviados)
    assert "<b>Tu cartera pasa de €50.000,00</b>" in aviso
    assert "Vale €60.000,00" in aviso


def test_aviso_721_por_debajo_no_avisa(config, enviados, monkeypatch):
    from dataclasses import replace

    config = replace(
        _con_cartera(config, Posicion("bitcoin", 1, 20000)), aviso_721=True
    )
    _precio(monkeypatch, {"bitcoin": 40000.0})

    main.ejecutar_ciclo(config, {})

    assert _avisos_721(enviados) == []


def test_sin_aviso_721_no_avisa(config, enviados, monkeypatch):
    config = _con_cartera(config, Posicion("bitcoin", 1, 20000))
    _precio(monkeypatch, {"bitcoin": 60000.0})

    main.ejecutar_ciclo(config, {})

    assert _avisos_721(enviados) == []


# --- /vsbolsa ---


def _bolsa(monkeypatch, cierre, ahora):
    from datetime import date, timedelta

    pedidos = []

    def pedir(ticker, desde):
        pedidos.append(ticker)
        dias = [date.today() - timedelta(days=d) for d in range(10, 0, -1)]
        return [(d, cierre) for d in dias], ahora

    monkeypatch.setattr(vsbolsa, "pedir", pedir)
    return pedidos


def test_vsbolsa(config, enviados, monkeypatch):
    _movimiento_hace(config, "solana", "compra", 10, 1000, 48)
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"solana": 150.0})
    pedidos = _bolsa(monkeypatch, 500.0, 600.0)

    main.atender(config, _mensaje("/vsbolsa"))

    # 1.000 € en SOL valen 1.500; en el ETF, 2 a 600 = 1.200.
    texto = enviados[0]
    assert "<b>Tu cartera contra el S&P 500</b>" in texto
    assert "<b>€1.500,00</b>" in texto
    assert "tendrías €1.200,00" in texto
    assert "Le ganas al S&P 500 por <b>€300,00</b> (+25,0%)" in texto
    assert "SXR8.DE" in texto
    assert pedidos == ["SXR8.DE"]


def test_vsbolsa_te_gana(config, enviados, monkeypatch):
    _movimiento_hace(config, "solana", "compra", 10, 1000, 48)
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"solana": 50.0})
    pedidos = _bolsa(monkeypatch, 500.0, 550.0)

    main.atender(config, _mensaje("/bolsa world"))

    assert "El MSCI World te gana por <b>€600,00</b>" in enviados[0]
    assert pedidos == ["EUNL.DE"]


def test_vsbolsa_sin_yahoo(config, enviados, monkeypatch):
    _movimiento_hace(config, "solana", "compra", 10, 1000, 48)
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"solana": 50.0})

    def pedir(ticker, desde):
        raise vsbolsa.BolsaError("Yahoo no contesta")

    monkeypatch.setattr(vsbolsa, "pedir", pedir)

    main.atender(config, _mensaje("/vsbolsa"))

    assert "No he podido mirar la bolsa: Yahoo no contesta" in enviados[0]


def test_vsbolsa_otro_indice(config, enviados, monkeypatch):
    monkeypatch.setattr(vsbolsa, "pedir", lambda *a: pytest.fail())

    main.atender(config, _mensaje("/vsbolsa ibex"))

    assert "S&amp;P 500 o el MSCI World" in enviados[0]


def test_vsbolsa_sin_movimientos(config, enviados, monkeypatch):
    monkeypatch.setattr(vsbolsa, "pedir", lambda *a: pytest.fail())

    main.atender(config, _mensaje("/vsbolsa"))

    assert "No has apuntado ninguna compra" in enviados[0]


# --- /escalera ---


# con_semana: 0,1 BTC por 5.000 (50.000 de media)
def test_escalera(con_semana, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 66000.0})

    main.atender(con_semana, _mensaje("/escalera btc 80000 100000"))

    texto = enviados[0]
    assert "🪜 <b>Escalera de venta de Bitcoin</b>" in texto
    assert "Vendes todo lo que tienes (0,1) en 2 escalones" in texto
    assert "1. A <b>€80.000,00</b>: vende 0,05 → €4.000,00" in texto
    assert "(+€1.500,00, a Hacienda €285,00)" in texto
    assert "2. A <b>€100.000,00</b>: vende 0,05 → €5.000,00" in texto
    assert "Le sacarías <b>+€4.000,00</b>" in texto
    assert "son las alertas 1 y 2 de /alertas" in texto
    a, b = database.get_puntuales(con_semana.database_path, "eur")
    assert (a.objetivo, a.sube, a.nota) == (80000, True, "Escalera 1/2: vende 0,05")
    assert (b.objetivo, b.nota) == (100000, "Escalera 2/2: vende 0,05")


def test_escalera_salta_el_primer_escalon(con_semana, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 66000.0, "solana": 100.0})
    main.atender(con_semana, _mensaje("/escalera btc 80k 100k 50%"))
    enviados.clear()

    _precio(monkeypatch, {"bitcoin": 81000.0, "solana": 100.0})
    main.ejecutar_ciclo(con_semana, {"bitcoin": "%66000.0"})

    aviso = next(t for t in enviados if "Era tu /alerta" in t)
    assert "📝 Escalera 1/2: vende 0,025" in aviso
    [queda] = database.get_puntuales(con_semana.database_path, "eur")
    assert queda.objetivo == 100000


def test_escalera_por_debajo_del_precio(con_semana, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 66000.0})

    main.atender(con_semana, _mensaje("/escalera btc 60000 80000"))

    assert "por encima del precio de ahora" in enviados[0]
    assert database.get_puntuales(con_semana.database_path, "eur") == []


def test_escalera_con_una_alerta_igual(con_semana, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 66000.0})
    main.atender(con_semana, _mensaje("/alerta btc 80000"))

    main.atender(con_semana, _mensaje("/escalera btc 80000 90000"))

    assert "Ya tienes una alerta a ese precio, la número 1" in enviados[-1]
    assert len(database.get_puntuales(con_semana.database_path, "eur")) == 1


def test_escalera_de_una_que_no_tienes(con_semana, enviados, monkeypatch):
    pedidas = _precio(monkeypatch, {"ethereum": 2500.0})

    main.atender(con_semana, _mensaje("/escalera eth 3000 4000"))

    assert "No tienes <b>ethereum</b> en la cartera" in enviados[0]
    assert pedidas == []


def test_escalera_mal_escrita(con_semana, enviados):
    main.atender(con_semana, _mensaje("/escalera btc 80000"))

    assert "al menos dos precios" in enviados[0]


def test_escalera_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/escalera btc 80000 90000"))

    assert enviados[0] == main.SIN_CARTERA


# con_semana: 0,1 BTC por 5.000 (50.000 de media)
def test_escalera_compra(con_semana, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 66000.0})

    main.atender(con_semana, _mensaje("/escalera compra btc 40k 60k con 900"))

    texto = enviados[0]
    assert "🪜 <b>Escalera de compra de Bitcoin</b>" in texto
    assert "Metes €900,00 en 2 escalones" in texto
    assert "1. A <b>€60.000,00</b> (-9,1%): mete €450,00 → 0,0075" in texto
    assert "2. A <b>€40.000,00</b> (-39,4%): mete €450,00 → 0,01125" in texto
    assert "tendrías 0,01875 más, a <b>€48.000,00</b> de media" in texto
    assert "Tu precio medio pasaría de €50.000,00 a <b>€49.684,21</b>" in texto
    assert "son las alertas 1 y 2 de /alertas" in texto
    a, b = database.get_puntuales(con_semana.database_path, "eur")
    assert (a.objetivo, a.sube, a.nota) == (
        60000,
        False,
        "Escalera de compra 1/2: mete €450,00",
    )
    assert (b.objetivo, b.sube) == (40000, False)


def test_escalera_compra_salta_al_bajar(con_semana, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 66000.0, "solana": 100.0})
    main.atender(con_semana, _mensaje("/escalera compra btc 60k 40k con 900"))
    enviados.clear()

    _precio(monkeypatch, {"bitcoin": 59000.0, "solana": 100.0})
    main.ejecutar_ciclo(con_semana, {"bitcoin": "%66000.0"})

    aviso = next(t for t in enviados if "Era tu /alerta" in t)
    assert "📝 Escalera de compra 1/2: mete €450,00" in aviso
    [queda] = database.get_puntuales(con_semana.database_path, "eur")
    assert queda.objetivo == 40000


def test_escalera_compra_sin_cartera_ni_dinero(config, enviados, monkeypatch):
    _precio(monkeypatch, {"ethereum": 2500.0})

    main.atender(config, _mensaje("/escalera compra eth 2000 1800"))

    texto = enviados[0]
    assert "Te aviso al bajar, en 2 escalones" in texto
    assert "1. A <b>€2.000,00</b> (-20,0%)\n" in texto
    assert "de media" not in texto
    assert len(database.get_puntuales(config.database_path, "eur")) == 2


def test_escalera_compra_por_encima_del_precio(con_semana, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 66000.0})

    main.atender(con_semana, _mensaje("/escalera compra btc 70000 60000"))

    assert "por debajo del precio de ahora" in enviados[0]
    assert database.get_puntuales(con_semana.database_path, "eur") == []


def test_escalera_compra_con_una_alerta_igual(con_semana, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 66000.0})
    main.atender(con_semana, _mensaje("/alerta btc 60000"))

    main.atender(con_semana, _mensaje("/escalera compra btc 60000 50000"))

    assert "Ya tienes una alerta a ese precio, la número 1" in enviados[-1]
    assert len(database.get_puntuales(con_semana.database_path, "eur")) == 1


# --- /stop movil ---


def test_stop_movil(con_semana, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 80000.0})

    main.atender(con_semana, _mensaje("/stop btc -10% movil"))

    texto = enviados[0]
    assert "<b>Bitcoin</b> baja un 10% desde lo más alto" in texto
    assert "Ahora está a €80.000,00, así que hoy saltaría a <b>€72.000,00</b>" in texto
    [a] = database.get_puntuales(con_semana.database_path, "eur")
    assert a.objetivo == pytest.approx(72000)
    assert not a.sube
    assert a.nota == "Stop móvil: -10% desde lo más alto"
    assert database.moviles(con_semana.database_path) == {a.id: -10.0}


def test_stop_movil_sube_con_el_precio_y_salta(con_semana, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 80000.0, "solana": 100.0})
    main.atender(con_semana, _mensaje("/stop btc -10% movil"))

    for btc in (90000.0, 85000.0):  # máximo nuevo y un poco de bajada
        _precio(monkeypatch, {"bitcoin": btc, "solana": 100.0})
        main.ejecutar_ciclo(con_semana, {})
    [a] = database.get_puntuales(con_semana.database_path, "eur")
    assert a.objetivo == pytest.approx(81000)
    assert len(enviados) == 1

    _precio(monkeypatch, {"bitcoin": 80000.0, "solana": 100.0})
    main.ejecutar_ciclo(con_semana, {})

    assert "Stop móvil: -10% desde lo más alto" in enviados[-1]
    assert database.get_puntuales(con_semana.database_path, "eur") == []
    assert database.moviles(con_semana.database_path) == {}


def test_stop_movil_de_la_cartera(con_semana, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 66000.0, "solana": 100.0})

    main.atender(con_semana, _mensaje("/stop cartera -20% movil"))

    assert (
        "Ahora vale €7.600,00, así que hoy saltaría a <b>€6.080,00</b>" in enviados[0]
    )


def test_stop_movil_al_quitarlo_no_queda_nada(con_semana, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 80000.0})
    main.atender(con_semana, _mensaje("/stop btc -10% movil"))

    main.atender(con_semana, _mensaje("/quitar 1"))

    assert database.moviles(con_semana.database_path) == {}


def test_stop_movil_de_ganancia(con_semana, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())

    main.atender(con_semana, _mensaje("/stop btc +10% movil"))

    assert "El móvil es para cuando baja" in enviados[0]


# --- /backtest ---


def _subidas_y_bajadas(config, *precios):
    # Uno por día, el último de hace una hora.
    for i, precio in enumerate(precios):
        _guardar(config, "bitcoin", precio, (len(precios) - 1 - i) * 24 + 1)


def test_backtest(config, enviados):
    _subidas_y_bajadas(config, 100.0, 120.0, 96.0, 100.0)

    main.atender(config, _mensaje("/backtest btc 20% 7d"))

    texto = enviados[0]
    assert "<b>Bitcoin: vender al +20% y recomprar al -20%</b>" in texto
    assert "Con la regla: <b>€1.250,00</b> (+25,0%), 1 venta y 1 compra" in texto
    assert "Sin tocar nada: €1.000,00 (+0,0%)" in texto
    assert "La regla gana por <b>€250,00</b>" in texto
    assert "venderías si sube a €115,20" in texto
    assert "Solo tengo precios desde" in texto


def test_backtest_gana_no_tocar(config, enviados):
    _subidas_y_bajadas(config, 100.0, 120.0, 200.0)

    main.atender(config, _mensaje("/backtest btc"))

    assert "No tocar nada gana por <b>€800,00</b>" in enviados[0]
    assert "recomprarías si baja a €96,00" in enviados[0]


def test_backtest_a_secas_la_primera_que_vigilo(config, enviados):
    _subidas_y_bajadas(config, 100.0, 105.0)

    main.atender(config, _mensaje("/backtest"))

    assert "Nunca subió un 20%" in enviados[0]


def test_backtest_sin_precios(config, enviados):
    main.atender(config, _mensaje("/backtest solana"))

    assert "No tengo precios guardados de <b>solana</b>" in enviados[0]


def test_backtest_mal_escrito(config, enviados):
    main.atender(config, _mensaje("/backtest btc 150%"))

    assert "menor de 100" in enviados[0]


# --- /tarjeta ---


def test_tarjeta(con_semana, enviados, sin_fotos_de_verdad, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 66000.0, "solana": 100.0})
    _guardar(con_semana, "bitcoin", 60000.0, 24)
    _guardar(con_semana, "solana", 100.0, 24)
    database.save_prices(
        con_semana.database_path, {"bitcoin": 66000.0, "solana": 100.0}, "eur"
    )

    main.atender(con_semana, _mensaje("/tarjeta"))

    [(png, pie)] = sin_fotos_de_verdad
    assert png.startswith(b"\x89PNG")
    # Metiste 6.000 y vale 7.600; hace un día valía 7.000.
    assert "+26,7% sobre lo que has metido" in pie
    assert "+8,6% en los últimos 30 días" in pie
    assert "Bitcoin 87% · Solana 13%" in pie
    assert "€" not in pie


def test_tarjeta_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/tarjeta"))

    assert enviados[0] == main.SIN_CARTERA


def test_tarjeta_sin_nada_que_enseñar(config, enviados, monkeypatch):
    from crypto_tracker.config import parse_cartera

    config = _con_cartera(config, *parse_cartera("bitcoin:0.1"))
    _precio(monkeypatch, {"bitcoin": 66000.0})

    main.atender(config, _mensaje("/compartir"))

    assert "Aún no tengo con qué hacerla" in enviados[0]


def test_tarjeta_sin_imagen_manda_texto(con_semana, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 66000.0, "solana": 100.0})

    def falla(t):
        raise grafica.GraficaError("sin matplotlib")

    monkeypatch.setattr(grafica, "dibujar_tarjeta", falla)

    main.atender(con_semana, _mensaje("/tarjeta"))

    assert "<b>Tu tarjeta</b>" in enviados[0]


def test_tarjeta_mal_escrita(con_semana, enviados):
    main.atender(con_semana, _mensaje("/tarjeta bitcoin"))

    assert "Escríbelo así" in enviados[0]


# --- lo que te has perdido mientras callaba ---


def _callado_hace(config, horas):
    """Como si el /mute se hubiera puesto hace esas horas."""
    import sqlite3
    from datetime import datetime, timedelta, timezone

    cuando = datetime.now(timezone.utc) - timedelta(hours=horas)
    conn = sqlite3.connect(config.database_path)
    conn.execute(
        "UPDATE ajustes SET valor = ? WHERE clave = 'silenciado_desde'",
        (cuando.isoformat(timespec="seconds"),),
    )
    conn.commit()
    conn.close()


def test_unmute_cuenta_lo_que_te_has_perdido(config, enviados):
    main.atender(config, _mensaje("/mute 3h"))
    _callado_hace(config, 2)
    for precio, horas in ((60000.0, 1.5), (66000.0, 1), (63000.0, 0.5)):
        _guardar(config, "bitcoin", precio, horas)

    main.atender(config, _mensaje("/unmute"))

    texto = enviados[-1]
    assert texto.startswith("🔔 Vuelvo a avisar.")
    assert "<b>Mientras callaba</b> (2 h)" in texto
    assert "<b>Bitcoin</b> +5,0%: de €60.000,00 a €63.000,00" in texto
    assert "(entre €60.000,00 y €66.000,00)" in texto
    assert database.inicio_silencio(config.database_path) is None


def test_unmute_sin_precios_guardados(config, enviados):
    main.atender(config, _mensaje("/mute 3h"))

    main.atender(config, _mensaje("/unmute"))

    assert "No guardé precios mientras callaba." in enviados[-1]


def test_alargar_el_mute_no_cambia_el_principio(config, enviados):
    main.atender(config, _mensaje("/mute 1h"))
    _callado_hace(config, 2)
    antes = database.inicio_silencio(config.database_path)

    main.atender(config, _mensaje("/mute 3h"))

    assert database.inicio_silencio(config.database_path) == antes


def test_unmute_de_una_sola_no_cuenta_nada(config, enviados):
    main.atender(config, _mensaje("/mute bitcoin 2h"))

    main.atender(config, _mensaje("/unmute bitcoin"))

    assert "Mientras callaba" not in enviados[-1]


def test_si_el_silencio_se_acaba_solo_lo_cuenta_una_vez(config, enviados):
    from datetime import datetime, timedelta, timezone

    main.atender(config, _mensaje("/mute 3h"))
    _callado_hace(config, 2)
    _guardar(config, "bitcoin", 60000.0, 1)
    _guardar(config, "bitcoin", 57000.0, 0.5)
    # Se acabó hace un minuto.
    database.silenciar_hasta(
        config.database_path, datetime.now(timezone.utc) - timedelta(minutes=1)
    )

    main.fin_del_silencio(config)
    main.fin_del_silencio(config)

    avisos = [t for t in enviados if "Se acabó el silencio" in t]
    assert len(avisos) == 1
    assert "<b>Bitcoin</b> -5,0%" in avisos[0]


def test_mientras_calla_no_cuenta_nada(config, enviados):
    main.atender(config, _mensaje("/mute 3h"))
    enviados.clear()

    main.fin_del_silencio(config)

    assert enviados == []


# --- frases sin barra ---


def test_frase_crea_una_alerta(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 63000.0})

    main.atender(config, _mensaje("Avísame si BTC baja de 60.000€"))

    [a] = database.get_puntuales(config.database_path, "eur")
    assert (a.coin_id, a.objetivo, a.sube) == ("bitcoin", 60000.0, False)
    assert "60.000" in enviados[0]


def test_frase_de_porcentaje(config, enviados, monkeypatch):
    _precio(monkeypatch, {"ethereum": 2000.0})

    main.atender(config, _mensaje("avísame cuando eth suba un 10%"))

    [a] = database.get_puntuales(config.database_path, "eur")
    assert a.objetivo == pytest.approx(2200)
    assert a.sube


def test_frase_de_callar(config, enviados):
    main.atender(config, _mensaje("cállate 2 horas"))

    assert enviados[0].startswith("🔕 Callado hasta las")
    assert database.silenciado_hasta(config.database_path) is not None


def test_frase_que_no_entiende(config, enviados):
    main.atender(config, _mensaje("he comprado 0.01 btc por 600"))

    assert enviados[0] == comandos.NO_ENTIENDO
    assert database.get_movimientos(config.database_path) == []


# --- /estocastico ---


def test_estocastico(config, enviados):
    # Sube un poco cada día durante tres semanas: cierra cerca del techo.
    for dias in range(1, 22):
        _precio_de(config, "bitcoin", 200.0 - dias, dias * 24 * 60)
    _precio_de(config, "bitcoin", 200.0, 5)

    main.atender(config, _mensaje("/estocastico btc"))

    texto = enviados[0]
    assert "🎚️ <b>Bitcoin</b>: estocástico de 14 días" in texto
    assert "🔥 <b>Sobrecompra</b>" in texto
    assert "%K 100" in texto


def test_estocastico_por_su_otro_nombre(config, enviados):
    for dias in range(1, 22):
        _precio_de(config, "bitcoin", 100.0 + dias, dias * 24 * 60)
    _precio_de(config, "bitcoin", 100.0, 5)

    main.atender(config, _mensaje("/stoch"))

    assert "🧊 <b>Sobreventa</b>" in enviados[0]


def test_estocastico_sin_historia(config, enviados):
    main.atender(config, _mensaje("/estocástico"))

    assert "Necesito 17 días seguidos" in enviados[0]


def test_estocastico_de_una_en_una(config, enviados):
    main.atender(config, _mensaje("/estocastico btc eth"))

    assert "De una en una" in enviados[0]


# --- /ruido ---


def test_ruido_cuenta_los_avisos_en_falso(config, enviados):
    # Un vaivén de ±6% cada hora y luego una subida que se queda: con %5,
    # casi todo es ruido; con %7 solo avisa de la subida.
    minutos = 70 * 60
    for i in range(40):
        _precio_de(config, "bitcoin", 106.0 if i % 2 else 100.0, minutos - i * 60)
    _precio_de(config, "bitcoin", 125.0, 28 * 60)
    _precio_de(config, "bitcoin", 125.0, 5)

    main.atender(config, _mensaje("/ruido"))

    texto = enviados[0]
    assert "🔊 <b>Avisos en falso</b>" in texto
    assert "<b>Bitcoin</b>  cada 5 % que se mueva" in texto
    assert "🔴" in texto
    assert "<code>/vigilar bitcoin %7</code>" in texto


def test_ruido_por_su_otro_nombre(config, enviados):
    _precio_de(config, "bitcoin", 100.0, 3 * 24 * 60)
    _precio_de(config, "bitcoin", 101.0, 5)

    main.atender(config, _mensaje("/falsos btc 7d"))

    assert "Ningún aviso en el tramo" in enviados[0]


def test_ruido_de_una_que_no_vigilo(config, enviados):
    main.atender(config, _mensaje("/ruido solana"))

    assert "No vigilo <b>solana</b>" in enviados[0]


def test_ruido_sin_precios(config, enviados):
    main.atender(config, _mensaje("/ruido"))

    assert "Aún no tengo precios guardados" in enviados[0]


def test_ruido_tramo_corto(config, enviados):
    main.atender(config, _mensaje("/ruido 12h"))

    assert "al menos 2 días" in enviados[0]


# --- Contexto en los avisos ---


def test_el_aviso_cuenta_que_paso_las_otras_veces(config, enviados, monkeypatch):
    # Tres veces subió un 10% en un día y a la semana estaba un 5% más arriba.
    for vez in range(3):
        empieza = 60 - vez * 10
        bloque = [100.0, 110.0, *[110.0] * 6, 115.5]
        for i, precio in enumerate(bloque):
            _precio_de(config, "bitcoin", precio, (empieza - i) * 24 * 60)
    _con_fecha(config, 60000.0, 24)
    _precio(monkeypatch, {"bitcoin": 66000.0})

    main.ejecutar_ciclo(config, {"bitcoin": "%62000.0"})

    assert (
        "días subió más de un 8.0% en un día 3 veces: a la semana estaba +5.0% "
        "de media y en 3 de 3 siguió subiendo</i>"
    ) in enviados[0]


def test_sin_casos_parecidos_el_aviso_va_sin_contexto(config, enviados, monkeypatch):
    _con_fecha(config, 60000.0, 24)
    _precio(monkeypatch, {"bitcoin": 66000.0})

    main.ejecutar_ciclo(config, {"bitcoin": "%62000.0"})

    assert "En 24 h" in enviados[0]
    assert "📚" not in enviados[0]


# --- /sesgo ---


def test_sesgo(config, enviados, monkeypatch):
    from crypto_tracker.miedo import Indice

    hoy = datetime.now(timezone.utc).date()
    for horas in (0, 24, 48):
        _movimiento_hace(config, "bitcoin", "compra", 1, 200, horas)
    _movimiento_hace(config, "bitcoin", "venta", 1, 100, 72)
    dias = [hoy - timedelta(days=d) for d in range(5)]
    pedidos = []

    def historico(n):
        pedidos.append(n)
        return [Indice(80, "Extreme Greed", d) for d in dias[:3]] + [
            Indice(15, "Extreme Fear", d) for d in dias[3:]
        ]

    monkeypatch.setattr(miedo, "historico", historico)
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 100.0})

    main.atender(config, _mensaje("/sesgo"))

    texto = enviados[0]
    assert pedidos and pedidos[0] >= 4
    assert "<b>Compras</b> (3) · índice medio 80" in texto
    assert "🤑 Codicia extrema: 3 · hoy 🔻 -50.0%" in texto
    assert "Compras sobre todo con codicia" in texto
    assert "<b>Ventas</b> (1)" in texto
    assert "no me atrevo a decir que es costumbre" in texto


def test_sesgo_sin_movimientos(config, enviados):
    main.atender(config, _mensaje("/humor"))

    assert "No has apuntado ninguna compra ni venta" in enviados[0]


def test_sesgo_sin_indice(config, enviados, monkeypatch):
    _movimiento_hace(config, "bitcoin", "compra", 1, 200, 0)
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 100.0})

    main.atender(config, _mensaje("/sesgo"))

    assert "alternative.me no tiene el índice" in enviados[0]


# --- /alerta con condición ---


def _miedo_de(monkeypatch, valor):
    from crypto_tracker.miedo import Indice

    hoy = datetime.now(timezone.utc).date()
    monkeypatch.setattr(miedo, "pedir", lambda: [Indice(valor, "Fear", hoy)])


def test_crear_alerta_con_condicion(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 65000.0})

    main.atender(config, _mensaje("/alerta btc 60000 si miedo<20"))
    main.atender(config, _mensaje("/alertas"))

    assert "baje a <b>€60.000,00</b>" in enviados[0]
    assert "🔗 Y solo si además está el miedo por debajo de 20" in enviados[0]
    assert "🔗 si el miedo por debajo de 20" in enviados[1]


def test_la_alerta_con_condicion_espera_al_miedo(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 65000.0})
    main.atender(config, _mensaje("/alerta btc 60000 si miedo<20"))
    enviados.clear()
    estado = {"bitcoin": "%59000.0"}  # que el aviso de % no salte
    _precio(monkeypatch, {"bitcoin": 59000.0})

    # Ha llegado al precio, pero el miedo aún no.
    _miedo_de(monkeypatch, 30)
    estado, _ = main.ejecutar_ciclo(config, estado)
    assert enviados == []
    assert len(database.get_puntuales(config.database_path, "eur")) == 1
    main.atender(config, _mensaje("/alertas"))
    assert "falta que se cumpla lo otro" in enviados.pop()

    _miedo_de(monkeypatch, 15)
    main.ejecutar_ciclo(config, estado)

    assert "✅ El miedo en 15, como pedías" in enviados[0]
    assert "Era tu /alerta" in enviados[0]
    assert database.get_puntuales(config.database_path, "eur") == []


def test_la_alerta_con_rsi(config, enviados, monkeypatch):
    # Baja todos los días: el RSI se queda en 0.
    for dias in range(1, 20):
        _precio_de(config, "bitcoin", 60000.0 + dias * 500, dias * 24 * 60)
    database.crear_puntual(
        config.database_path,
        "bitcoin",
        60000,
        False,
        "eur",
        condicion=condicion.Condicion("rsi", True, 30),
    )
    _precio(monkeypatch, {"bitcoin": 59000.0})

    main.ejecutar_ciclo(config, {"bitcoin": "%59000.0"})

    assert "✅ El RSI en 0, como pedías" in enviados[0]


def test_la_alerta_con_miedo_sin_poder_mirarlo_espera(config, enviados, monkeypatch):
    database.crear_puntual(
        config.database_path,
        "bitcoin",
        60000,
        False,
        "eur",
        condicion=condicion.Condicion("miedo", True, 20),
    )
    _precio(monkeypatch, {"bitcoin": 59000.0})

    def falla():
        raise miedo.MiedoError("caído")

    monkeypatch.setattr(miedo, "pedir", falla)
    main.ejecutar_ciclo(config, {"bitcoin": "%59000.0"})

    assert enviados == []
    assert len(database.get_puntuales(config.database_path, "eur")) == 1


def test_alerta_de_la_cartera_con_rsi_no(config, enviados, monkeypatch):
    database.guardar_posicion(
        config.database_path, "bitcoin", Posicion("bitcoin", 1.0, 50000)
    )

    main.atender(config, _mensaje("/alerta cartera 10000 si rsi<30"))

    assert "El RSI es de cada cripto" in enviados[0]


def test_alerta_con_condicion_que_no_entiende(config, enviados):
    main.atender(config, _mensaje("/alerta btc 60000 si volumen>2"))

    assert "Solo sé mirar el miedo y el RSI" in enviados[0]


def test_frase_con_condicion(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 65000.0})

    main.atender(
        config,
        _mensaje("avísame si btc baja de 60000 y el miedo está por debajo de 20"),
    )

    [alerta] = database.get_puntuales(config.database_path, "eur")
    assert alerta.condicion == condicion.Condicion("miedo", True, 20)


# --- /pienso ---


def test_pienso(config, enviados, monkeypatch):
    from crypto_tracker.miedo import Indice

    _precio(monkeypatch, {"bitcoin": 64000.0})
    monkeypatch.setattr(coingecko, "_cambios", {"bitcoin": 11.2})
    hoy = datetime.now(timezone.utc).date()
    monkeypatch.setattr(miedo, "pedir", lambda: [Indice(78, "Extreme Greed", hoy)])

    main.atender(config, _mensaje("/pienso btc 500"))

    texto = enviados[0]
    assert "🧊 <b>Vale, lo pensamos 24 h</b>" in texto
    assert "Quieres meter €500,00 en <b>Bitcoin</b>, que está a €64.000,00" in texto
    assert "🔺 +11.20% en 24 h: comprar justo después de un subidón" in texto
    assert "🤑 Miedo y codicia: 78 (codicia extrema)" in texto
    [p] = database.get_piensos(config.database_path)
    assert (p.coin_id, p.importe, p.precio) == ("bitcoin", 500, 64000)


def test_pienso_a_las_24_h_pregunta_una_vez(config, con_botones, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 64000.0})
    main.atender(config, _mensaje("/pienso btc 500"))
    con_botones.clear()
    ahora = datetime.now(timezone.utc)
    _precio(monkeypatch, {"bitcoin": 60800.0})

    main.pensados(config, ahora + timedelta(hours=23))
    assert con_botones == []
    main.pensados(config, ahora + timedelta(hours=24, minutes=1))
    main.pensados(config, ahora + timedelta(hours=25))

    [(texto, botones)] = con_botones
    assert "¿Sigues queriendo Bitcoin por €500,00?" in texto
    assert "(🔻 -5.00%)" in texto
    assert "te llevas un 5.3% más" in texto
    assert botones == [
        [("✅ La he comprado", "/compra bitcoin 0,00822368 500")],
        [("❌ Al final no", "/pienso bitcoin no")],
    ]
    assert database.get_piensos(config.database_path) == []


def test_pienso_el_boton_apunta_la_compra(config, con_botones, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 62500.0})
    main.atender(config, _mensaje("/pienso btc 50"))
    main.pensados(config, datetime.now(timezone.utc) + timedelta(days=1, minutes=1))
    boton = con_botones[-1][1][0][0][1]

    main.atender(config, _mensaje(boton))

    assert database.get_cambios_cartera(config.database_path) == {
        "bitcoin": Posicion("bitcoin", 0.0008, 50)
    }


def test_pienso_callado_espera(config, con_botones, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 64000.0})
    main.atender(config, _mensaje("/pienso btc 500"))
    con_botones.clear()
    database.silenciar_hasta(
        config.database_path, datetime.now(timezone.utc) + timedelta(days=2)
    )

    main.pensados(config, datetime.now(timezone.utc) + timedelta(days=1, minutes=1))

    assert con_botones == []
    assert len(database.get_piensos(config.database_path)) == 1


def test_pienso_lista_y_olvidar(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 64000.0})
    main.atender(config, _mensaje("/pienso btc 500"))

    main.atender(config, _mensaje("/pienso"))
    main.atender(config, _mensaje("/pienso btc no"))
    main.atender(config, _mensaje("/pienso"))

    assert "<b>Bitcoin</b> €500,00 · te pregunto el" in enviados[1]
    assert "Vale, no apunto nada" in enviados[2]
    assert "No te estás pensando ninguna compra" in enviados[3]


def test_pienso_mal_escrito(config, enviados):
    main.atender(config, _mensaje("/pienso btc mucho"))

    assert "no es un importe" in enviados[0]


def test_pienso_si_sigue_igual(config, con_botones, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 64000.0})
    main.atender(config, _mensaje("/pienso btc 500"))
    _precio(monkeypatch, {"bitcoin": 64100.0})

    main.pensados(config, datetime.now(timezone.utc) + timedelta(days=1, minutes=1))

    assert "Está más o menos igual" in con_botones[-1][0]


# --- /timing ---


def _historico_plano(precio, bache_hace, bache):
    """Un mes a `precio` con un día a `bache` hace `bache_hace` días."""
    hoy = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0)

    def historico(coin_id, dias, cur):
        return [
            (hoy - timedelta(days=d), bache if d == bache_hace else precio)
            for d in range(40, -1, -1)
        ]

    return historico


def test_timing(config, enviados, monkeypatch):
    # Una en el bache y otra cara, cada una con su mes alrededor.
    _movimiento_hace(config, "bitcoin", "compra", 0.01, 500, 20 * 24)
    _movimiento_hace(config, "bitcoin", "compra", 0.01, 650, 18 * 24)
    monkeypatch.setattr(coingecko, "historico", _historico_plano(60000, 20, 50000))

    main.atender(config, _mensaje("/timing"))

    texto = enviados[0]
    assert "⏱️ <b>¿Aciertas el momento?</b>" in texto
    assert "De 2 compras, <b>1</b> fueron más baratas" in texto
    assert "🥇 La mejor: 0,01 de Bitcoin" in texto
    assert "🥴 La peor: 0,01 de Bitcoin" in texto


def test_timing_por_su_otro_nombre_y_de_una(config, enviados, monkeypatch):
    _movimiento_hace(config, "bitcoin", "compra", 0.01, 500, 20 * 24)
    monkeypatch.setattr(coingecko, "historico", _historico_plano(60000, 20, 50000))

    main.atender(config, _mensaje("/momento btc"))

    assert "¿Aciertas el momento de Bitcoin?" in enviados[0]
    assert "Tu compra fue más barata" in enviados[0]
    assert "Tienes buen ojo" in enviados[0]


def test_timing_sin_compras(config, enviados):
    main.atender(config, _mensaje("/timing"))

    assert "No has apuntado ninguna compra" in enviados[0]


def test_timing_sin_precios(config, enviados, monkeypatch):
    _movimiento_hace(config, "bitcoin", "compra", 0.01, 500, 20 * 24)

    def falla(*a):
        raise coingecko.CoinGeckoError("caído")

    monkeypatch.setattr(coingecko, "historico", falla)

    main.atender(config, _mensaje("/timing"))

    assert "No puedo comparar ninguna compra" in enviados[0]


# --- /prediccion ---


def test_prediccion(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 64000.0})

    main.atender(config, _mensaje("/prediccion btc 70k"))

    assert "🔮 Apuntado: <b>Bitcoin</b> a <b>€70.000,00</b> el domingo" in enviados[0]
    assert "dices que sube un 9.4%" in enviados[0]
    [p] = database.get_predicciones(config.database_path, "eur")
    assert (p.entonces, p.predicho, p.real) == (64000, 70000, None)


def test_prediccion_el_domingo_cierra_con_marcador(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 64000.0})
    main.atender(config, _mensaje("/prediccion btc 70000"))
    [p] = database.get_predicciones(config.database_path, "eur")
    # El bot guardó el precio a las 20:00 del domingo.
    minutos = (datetime.now(timezone.utc) - p.cierre).total_seconds() / 60
    _precio_de(config, "bitcoin", 66000.0, minutos)
    enviados.clear()

    main.cerrar_predicciones(config, p.cierre - timedelta(minutes=1))
    assert enviados == []
    main.cerrar_predicciones(config, p.cierre + timedelta(minutes=5))
    main.cerrar_predicciones(config, p.cierre + timedelta(minutes=10))

    [texto] = enviados
    assert "dijiste €70.000,00 y quedó en <b>€66.000,00</b>" in texto
    assert "Te fuiste un 6.1% · ✅ acertaste que subía" in texto
    assert "«se queda igual» se iba un 3.0%: te gana" in texto
    assert "Hacia dónde iba: <b>1 de 1</b>" in texto
    assert "aún es pronto" in texto


def test_prediccion_con_el_bot_apagado_el_domingo(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 64000.0})
    main.atender(config, _mensaje("/prediccion btc 60000"))
    [p] = database.get_predicciones(config.database_path, "eur")
    pedidos = []

    def historico(coin_id, dias, cur):
        pedidos.append(dias)
        return [(p.cierre + timedelta(minutes=30), 61000.0)]

    monkeypatch.setattr(coingecko, "historico", historico)
    enviados.clear()

    # Se enciende el martes: el precio es el del domingo, no el de ahora.
    main.cerrar_predicciones(config, p.cierre + timedelta(days=2))

    assert "quedó en <b>€61.000,00</b>" in enviados[0]
    assert pedidos == [3]


def test_prediccion_se_cambia_pero_no_a_ultima_hora(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 64000.0})
    main.atender(config, _mensaje("/prediccion btc 70000"))
    main.atender(config, _mensaje("/prediccion btc 68000"))
    [p] = database.get_predicciones(config.database_path, "eur")
    assert p.predicho == 68000

    # A menos de un día del domingo, el cierre nuevo ya es el siguiente.
    monkeypatch.setattr(
        "crypto_tracker.prediccion.cierre", lambda ahora: p.cierre + timedelta(days=7)
    )
    main.atender(config, _mensaje("/prediccion btc 66000"))

    assert "ya no se puede cambiar" in enviados[-1]
    assert [
        x.predicho for x in database.get_predicciones(config.database_path, "eur")
    ] == [68000]


def test_prediccion_lista_y_quitar(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 64000.0})
    main.atender(config, _mensaje("/prediccion"))
    main.atender(config, _mensaje("/prediccion btc 70000"))
    main.atender(config, _mensaje("/apuesta"))
    main.atender(config, _mensaje("/prediccion btc no"))

    assert "No has hecho ninguna" in enviados[0]
    assert "🔮 <b>En juego</b>" in enviados[2]
    assert "quitada la de <b>bitcoin</b>" in enviados[3]


def test_prediccion_al_mismo_precio(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 64000.0})

    main.atender(config, _mensaje("/prediccion btc 64000"))

    assert "¿sube o baja?" in enviados[0]


# --- /fantasma ---


def test_fantasma_entero(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 50000.0, "ethereum": 2000.0})
    main.atender(config, _mensaje("/fantasma"))
    main.atender(config, _mensaje("/fantasma compra eth 400"))
    main.atender(config, _mensaje("/fantasma compra btc 100"))

    _precio(monkeypatch, {"bitcoin": 50000.0, "ethereum": 3000.0})
    main.atender(config, _mensaje("/fantasma vende eth 50%"))
    main.atender(config, _mensaje("/fantasma"))

    assert "Aún no tienes cartera fantasma" in enviados[0]
    assert "👻 Comprado: €400,00 de <b>Ethereum</b> a €2.000,00 (0,2)" in enviados[1]
    assert "Te quedan €500,00 sin invertir" in enviados[2]
    assert "👻 Vendido: €300,00 de <b>Ethereum</b>" in enviados[3]
    texto = enviados[4]
    assert "<b>Ethereum</b> 0,1 · €200,00 → €300,00 (🔺 +50.0%)" in texto
    assert "💶 Sin invertir: €800,00" in texto
    # 800 + 300 + 100 = 1.200; en bitcoin seguiría en 1.000.
    assert "Total: <b>€1.200,00</b> de €1.000,00 (🔺 +20.0%)" in texto
    assert "Dejándolo todo en bitcoin el primer día: €1.000,00" in texto
    assert "👉 Le ganas a no hacer nada con bitcoin" in texto
    assert "3 operaciones" in texto


def test_fantasma_no_llega(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 50000.0})

    main.atender(config, _mensaje("/fantasma compra btc 1500"))

    assert "Solo te quedan 1.000,00 sin invertir" in enviados[0]
    assert database.get_fantasma(config.database_path) is None


def test_fantasma_reinicia(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 50000.0})
    main.atender(config, _mensaje("/fantasma compra btc 500"))

    main.atender(config, _mensaje("/simulador reinicia 5000"))

    assert "Cartera fantasma nueva con €5.000,00" in enviados[1]
    f = database.get_fantasma(config.database_path)
    assert (f.caja, f.posiciones, f.btc_inicio) == (5000, {}, 50000)


def test_fantasma_no_toca_la_cartera_de_verdad(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 50000.0})

    main.atender(config, _mensaje("/fantasma compra btc 500"))

    assert database.get_movimientos(config.database_path) == []
    assert database.get_cambios_cartera(config.database_path) == {}


def test_fantasma_empatada_con_bitcoin(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 50000.0, "ethereum": 2000.0})
    main.atender(config, _mensaje("/fantasma compra eth 400"))
    _precio(monkeypatch, {"bitcoin": 50000.0, "ethereum": 1999.99})

    main.atender(config, _mensaje("/fantasma"))

    assert "Vas igual que si no hubieras hecho nada" in enviados[-1]
    assert "-0.0%" not in enviados[-1]


# --- /emocion y /emociones ---


def test_emociones_con_los_botones(config, monkeypatch):
    mandados = _con_botones(monkeypatch)
    _precio(monkeypatch, {"bitcoin": 50000.0})
    for _ in range(2):
        main.atender(config, _mensaje("/compra btc 0.01 400"))  # barata: +25%
        boton = next(d for t, d in mandados[-1][1][1] if "Miedo" in t)
        main.atender(config, _mensaje(boton))
    for _ in range(2):
        main.atender(config, _mensaje("/compra btc 0.01 1000"))  # cara: -50%
        boton = next(d for t, d in mandados[-1][1][2] if "Euforia" in t)
        main.atender(config, _mensaje(boton))
    main.atender(config, _mensaje("/compra btc 0.01 500"))  # sin ánimo
    mandados.clear()

    main.atender(config, _mensaje("/emociones"))

    texto = mandados[0][0]
    assert "😱 Miedo: 2 · hoy 🔺 +25.0%" in texto
    assert "🤩 Euforia: 2 · hoy 🔻 -50.0%" in texto
    assert (
        "👉 Tus mejores compras son con miedo (+25.0%) y las peores con euforia"
        in texto
    )
    assert "1 movimiento sin ánimo apuntado" in texto


def test_emocion_a_mano_y_en_una_venta(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 50000.0})
    main.atender(config, _mensaje("/compra btc 0.02 800"))
    main.atender(config, _mensaje("/venta btc 0.01 400"))
    venta = database.get_movimientos(config.database_path)[0]

    main.atender(config, _mensaje(f"/emocion {venta.id} pánico"))
    main.atender(config, _mensaje("/sentimientos"))

    assert f"😱 Apuntado: la {venta.id} fue con miedo" in enviados[2]
    # Vendiste a 40.000 y hoy está a 50.000: habría valido un 25% más.
    assert "<b>Ventas</b>\n😱 Miedo: 1 · hoy valdría 🔺 +25.0%" in enviados[3]


def test_emocion_de_un_movimiento_que_no_existe(config, enviados):
    main.atender(config, _mensaje("/emocion 99 miedo"))

    assert "No tengo ningún movimiento con el número 99" in enviados[0]


def test_emociones_sin_nada(config, enviados):
    main.atender(config, _mensaje("/emociones"))

    assert "Aún no has dicho con qué ánimo" in enviados[0]


# --- calma ---


def _semanas_movidas_y_una_quieta(config):
    # 50 días subiendo y bajando un 5% y, la última semana, casi quieta.
    precios = [60000.0 * (1.05 if i % 2 else 1.0) for i in range(50)]
    precios += [60000.0, 60100.0, 60050.0, 60080.0, 60020.0, 60060.0, 60040.0]
    for dias_atras, precio in enumerate(reversed(precios)):
        _precio_de(config, "bitcoin", precio, dias_atras * 24 * 60 + 5)


def test_aviso_de_calma_una_vez(config, enviados, monkeypatch):
    from dataclasses import replace

    config = replace(config, aviso_calma=True)
    _semanas_movidas_y_una_quieta(config)
    _precio(monkeypatch, {"bitcoin": 60040.0})

    main.ejecutar_ciclo(config, {"bitcoin": "%60040.0"})
    main.ejecutar_ciclo(config, {"bitcoin": "%60040.0"})

    avisos = [t for t in enviados if "🤫" in t]
    assert len(avisos) == 1
    assert "🤫 <b>Bitcoin</b> lleva 7 días muy quieta" in avisos[0]
    assert "se ha movido un 0.2%" in avisos[0]


def test_sin_aviso_de_calma_no_avisa(config, enviados, monkeypatch):
    _semanas_movidas_y_una_quieta(config)
    _precio(monkeypatch, {"bitcoin": 60040.0})

    main.ejecutar_ciclo(config, {"bitcoin": "%60040.0"})

    assert not any("🤫" in t for t in enviados)


def test_comando_calma(config, enviados):
    _semanas_movidas_y_una_quieta(config)

    main.atender(config, _mensaje("/tormenta"))
    main.atender(config, _mensaje("/squeeze eth"))

    assert "<b>Bitcoin</b>: 0.2% (lo normal, 4.9%) · 🤫 muy quieta" in enviados[0]
    assert "<b>Ethereum</b>: aún no tengo historia bastante" in enviados[1]


# --- /herencia ---


def test_herencia(config, enviados, archivos, monkeypatch):
    database.guardar_posicion(
        config.database_path, "bitcoin", Posicion("bitcoin", 0.02, 1000)
    )
    database.guardar_posicion(
        config.database_path, "ethereum", Posicion("ethereum", 1, 2000)
    )
    _precio(monkeypatch, {"bitcoin": 50000.0, "ethereum": 3000.0})

    main.atender(config, _mensaje("/herencia btc Ledger en el cajón del escritorio"))
    main.atender(config, _mensaje("/herencia nota Habla con mi hermana"))
    main.atender(config, _mensaje("/herencia"))

    assert "📍 Apuntado dónde está <b>bitcoin</b>" in enviados[0]
    assert "📝 Apuntada la nota" in enviados[1]
    contenido, nombre, pie = archivos[0]
    papel = contenido.decode()
    assert nombre.startswith("herencia-cripto-") and nombre.endswith(".txt")
    assert "NO lleva ninguna clave" in papel
    # La que más vale, primero.
    assert papel.index("Ethereum: 1") < papel.index("Bitcoin: 0,02")
    assert "  Dónde: Ledger en el cajón del escritorio" in papel
    assert "  Dónde: sin apuntar" in papel
    assert "En total, unos €4.000,00" in papel
    assert "Nota: Habla con mi hermana" in papel
    assert "impuesto de sucesiones" in papel
    assert "⚠️ 1 cripto sin decir dónde está" in pie


def test_herencia_no_guarda_una_semilla(config, enviados):
    semilla = (
        "abandon ability able about above absent absorb abstract absurd abuse "
        "access accident"
    )

    main.atender(config, _mensaje(f"/herencia btc {semilla}"))
    main.atender(config, _mensaje(f"/legado nota {semilla}"))

    assert "no la guardo" in enviados[0]
    assert "no la guardo" in enviados[1]
    assert database.get_herencia(config.database_path) == ({}, None)


def test_herencia_quitar(config, enviados):
    main.atender(config, _mensaje("/herencia btc Ledger"))
    main.atender(config, _mensaje("/herencia btc no"))

    assert "ya no digo dónde está <b>bitcoin</b>" in enviados[1]
    assert database.get_herencia(config.database_path) == ({}, None)


def test_herencia_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/herencia"))

    assert "No tienes nada en la cartera" in enviados[0]


def _coingecko_caido(monkeypatch):
    def falla(ids, cur):
        raise coingecko.CoinGeckoError("Sin conexion con CoinGecko")

    monkeypatch.setattr(coingecko, "get_prices", falla)


def test_no_avisa_si_binance_no_ve_ese_precio(config, enviados, monkeypatch):
    _precio_hace(config, 63200.0, 5)  # el ciclo anterior, que sí cuadraba
    database.crear_puntual(config.database_path, "bitcoin", 70000, True, "eur")
    _precio(monkeypatch, {"bitcoin": 90000.0})  # un pico que no ha pasado
    monkeypatch.setattr(binance, "precios", lambda ids, cur: {"bitcoin": 63500.0})

    estado, _ = main.ejecutar_ciclo(config, {"bitcoin": "%63000.0"})

    assert enviados == []
    assert estado == {"bitcoin": "%63000.0"}
    # La alerta sigue ahí: si el precio es de verdad, salta en el siguiente.
    assert len(database.get_puntuales(config.database_path, "eur")) == 1


def test_avisa_si_con_binance_no_cuadraba_ni_antes(config, enviados, monkeypatch):
    _precio_hace(config, 69000.0, 5)
    database.crear_puntual(config.database_path, "bitcoin", 70000, True, "eur")
    _precio(monkeypatch, {"bitcoin": 70500.0})
    monkeypatch.setattr(binance, "precios", lambda ids, cur: {"bitcoin": 20000.0})

    main.ejecutar_ciclo(config, {"bitcoin": "%69000.0"})

    assert "Era tu /alerta" in enviados[0]


def test_avisa_si_binance_ve_lo_mismo(config, enviados, monkeypatch):
    database.crear_puntual(config.database_path, "bitcoin", 70000, True, "eur")
    _precio(monkeypatch, {"bitcoin": 70500.0})
    monkeypatch.setattr(binance, "precios", lambda ids, cur: {"bitcoin": 70300.0})

    main.ejecutar_ciclo(config, {"bitcoin": "%69000.0"})

    assert "Era tu /alerta" in enviados[0]


def test_avisa_si_binance_no_contesta(config, enviados, monkeypatch):
    def caido(ids, cur):
        raise binance.BinanceError("Binance tampoco contesta")

    database.crear_puntual(config.database_path, "bitcoin", 70000, True, "eur")
    _precio(monkeypatch, {"bitcoin": 70500.0})
    monkeypatch.setattr(binance, "precios", caido)

    main.ejecutar_ciclo(config, {"bitcoin": "%69000.0"})

    assert "Era tu /alerta" in enviados[0]


def test_sin_coingecko_avisa_con_binance(config, enviados, monkeypatch):
    _coingecko_caido(monkeypatch)
    monkeypatch.setattr(binance, "precios", lambda ids, cur: {"bitcoin": 70000.0})

    estado, error = main.ejecutar_ciclo(config, {"bitcoin": "%60000.0"})

    assert error is None
    assert estado["bitcoin"] != "%60000.0"
    [aviso] = enviados
    assert binance.FUENTE in aviso
    assert "CoinGecko</a>" not in aviso
    # Y se guarda en el histórico como cualquier otro precio.
    assert database.get_price_at(config.database_path, "bitcoin", 0) is not None


def test_con_binance_no_usa_la_variacion_vieja(config, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "_cambios", {"bitcoin": 42.0})
    monkeypatch.setattr(coingecko, "_volumenes", {"bitcoin": 1e9})
    _coingecko_caido(monkeypatch)
    monkeypatch.setattr(binance, "precios", lambda ids, cur: {"bitcoin": 70000.0})

    main.ejecutar_ciclo(config, {"bitcoin": "%60000.0"})

    assert coingecko.cambio_24h("bitcoin") is None
    assert coingecko.volumenes(["bitcoin"]) == {}
    assert "42" not in enviados[0]


def test_con_binance_no_dice_que_coingecko_no_la_conoce(config, enviados, monkeypatch):
    from dataclasses import replace

    con_dos = replace(
        config, watchlist=[Watch("bitcoin", percent=5), Watch("kaspa", step=1)]
    )
    _coingecko_caido(monkeypatch)
    monkeypatch.setattr(binance, "precios", lambda ids, cur: {"bitcoin": 70000.0})

    main.ejecutar_ciclo(con_dos, {"bitcoin": "%60000.0"}, sin_precio=set())

    assert not any("kaspa" in t for t in enviados)


def test_sin_coingecko_ni_binance_sigue_el_error(config, enviados, monkeypatch):
    _coingecko_caido(monkeypatch)

    def tampoco(ids, cur):
        raise binance.BinanceError("Binance tampoco contesta")

    monkeypatch.setattr(binance, "precios", tampoco)

    estado, error = main.ejecutar_ciclo(config, {"bitcoin": "%60000.0"})

    assert estado == {"bitcoin": "%60000.0"}
    assert "CoinGecko" in error
    assert enviados == []


def test_cada_programa_lista_y_quita(config, enviados):
    main.atender(config, _mensaje("/cada viernes 20:00 /status"))
    main.atender(config, _mensaje("/cada dia 9:00 /ayuda"))
    main.atender(config, _mensaje("/cada"))

    assert "cada viernes a las 20:00 te mando /status" in enviados[0]
    assert "cada viernes a las 20:00: /status" in enviados[2]
    assert "cada día a las 09:00: /ayuda" in enviados[2]

    main.atender(config, _mensaje("/cada quitar 1"))
    assert [p.numero for p in database.get_programados(config.database_path)] == [2]


def test_cada_con_un_comando_que_no_existe(config, enviados):
    main.atender(config, _mensaje("/cada dia 9:00 /inventado"))

    assert "No conozco /inventado" in enviados[0]
    assert database.get_programados(config.database_path) == []


def test_cada_manda_el_comando_una_vez(config, enviados):
    main.atender(config, _mensaje("/cada dia 9:00 /ayuda"))
    nueve = datetime(2026, 11, 20, 9, 10).astimezone()

    main.programados(config, nueve)
    main.programados(config, nueve)

    assert len(enviados) == 2  # la confirmación y una sola ayuda
    assert "/status" in enviados[1]


def _precio_de_hace_7_dias(config, coin_id, precio):
    _precio_de(config, coin_id, precio, 7 * 24 * 60)


def test_rezagada_avisa_una_vez(config, enviados, monkeypatch):
    from dataclasses import replace

    config = replace(
        config, watchlist=[Watch("bitcoin", percent=50), Watch("ethereum", percent=50)]
    )
    main.atender(config, _mensaje("/rezagada eth btc 10"))
    _precio_de_hace_7_dias(config, "bitcoin", 60000.0)
    _precio_de_hace_7_dias(config, "ethereum", 4000.0)
    _precio(monkeypatch, {"bitcoin": 66000.0, "ethereum": 3600.0})  # +10% y -10%

    estado, _ = main.ejecutar_ciclo(
        config, {"bitcoin": "%66000.0", "ethereum": "%3600.0"}
    )
    main.ejecutar_ciclo(config, estado)

    assert "te aviso si <b>ethereum</b> va un 10% peor" in enviados[0]
    assert len(enviados) == 2
    assert "<b>Ethereum</b> se queda atrás" in enviados[1]
    assert "<b>-18.2%</b>" in enviados[1]


def test_rezagada_de_una_que_no_vigilas(config, enviados):
    main.atender(config, _mensaje("/rezagada sol btc 10"))

    assert "No guardo el precio de <b>solana</b>" in enviados[0]
    assert database.get_rezagadas(config.database_path) == []


def test_rezagada_lista_y_quita(config, enviados):
    from dataclasses import replace

    config = replace(
        config, watchlist=[Watch("bitcoin", percent=5), Watch("ethereum", percent=5)]
    )
    main.atender(config, _mensaje("/rezagada eth btc 10"))
    main.atender(config, _mensaje("/rezagada"))
    main.atender(config, _mensaje("/rezagada eth btc no"))

    assert "Ethereum</b> contra Bitcoin" in enviados[1]
    assert "ya no comparo" in enviados[2]
    assert database.get_rezagadas(config.database_path) == []


def test_equivale_da_lo_mismo_que_el_suelto(config, enviados, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    config = replace(config, cartera=(Posicion("bitcoin", 0.01),))
    _precio_de(config, "bitcoin", 100000.0, 5)

    main.atender(config, _mensaje("/equivale kebabs"))
    main.atender(config, _mensaje("/kebab"))

    assert "Te da para <b>166 kebabs</b>" in enviados[0]
    assert enviados[0] == enviados[1]


def test_equivale_a_secas_dice_las_que_hay(config, enviados):
    main.atender(config, _mensaje("/equivale"))

    assert "¿En qué quieres ver tu cartera?" in enviados[0]
    assert "kebab" in enviados[0]
    assert "No tengo" not in enviados[0]


def test_equivale_de_algo_que_no_tengo(config, enviados):
    main.atender(config, _mensaje("/equivale <b>yate"))

    assert enviados[0].startswith("No tengo «&lt;b&gt;yate» 🤷")


def test_equivale_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/equivale cafe"))

    assert "PORTFOLIO" in enviados[0]


# --- /importar ---

CSV_BINANCE = (
    '"Date(UTC)","Pair","Side","Price","Executed","Amount","Fee"\n'
    '"2024-05-02 08:00:00","BTCEUR","SELL","60000","0.001BTC","60EUR","0.06EUR"\n'
    '"2024-03-01 10:15:22","BTCEUR","BUY","50000","0.002BTC","100EUR","0.1EUR"\n'
    '"2024-03-02 09:00:00","ETHBTC","BUY","0.05","1ETH","0.05BTC","0"\n'
)


@pytest.fixture
def con_csv(monkeypatch):
    """Lo que bajaría de Telegram al mandar el archivo."""
    monkeypatch.setattr(main, "_importacion", None)
    monkeypatch.setattr(
        telegram, "descargar", lambda token, file_id: CSV_BINANCE.encode()
    )


def _archivo(nombre="binance.csv"):
    mensaje = _mensaje("")
    mensaje["document"] = {"file_id": "abc", "file_name": nombre, "file_size": 300}
    return mensaje


def test_importar_enseña_antes_de_apuntar(config, enviados, con_csv):
    main.atender(config, _archivo())

    texto = enviados[0]
    assert "🟢 1 compras · 🔴 1 ventas" in texto
    assert "Del 01/03/2024 al 02/05/2024" in texto
    assert "1 saltadas: en BTC, no en EUR" in texto
    assert "contarían dos veces" in texto
    assert database.get_movimientos(config.database_path) == []


def test_importar_si_las_apunta_con_su_fecha(config, enviados, con_csv):
    main.atender(config, _archivo())
    main.atender(config, _mensaje("/importar si"))

    assert enviados[1].startswith("✅ Apuntadas 2 operaciones de Binance")
    venta, compra = database.get_movimientos(config.database_path)
    assert compra.cuando == datetime(2024, 3, 1, 10, 15, 22, tzinfo=timezone.utc)
    assert (compra.tipo, compra.cantidad, compra.coste) == ("compra", 0.002, 100.1)
    assert compra.nota == "Binance"
    assert (venta.tipo, venta.coste) == ("venta", 59.94)
    (queda,) = main._con_cambios(config).cartera
    assert queda.cantidad == pytest.approx(0.001)


def test_importar_dos_veces_no_repite(config, enviados, con_csv):
    main.atender(config, _archivo())
    main.atender(config, _mensaje("/importar si"))
    main.atender(config, _archivo())

    assert "No hay nada nuevo que apuntar." in enviados[2]
    assert "2 ya estaban apuntadas" in enviados[2]
    assert len(database.get_movimientos(config.database_path)) == 2


def test_importar_no_las_mete_antes_de_lo_apuntado(config, enviados, con_csv):
    main.atender(config, _mensaje("/compra bitcoin 0.01 500"))
    main.atender(config, _archivo())

    assert "No hay nada nuevo que apuntar." in enviados[1]
    assert "2 son de antes de tu último movimiento" in enviados[1]


def test_importar_cancelar(config, enviados, con_csv):
    main.atender(config, _archivo())
    main.atender(config, _mensaje("/importar no"))
    main.atender(config, _mensaje("/importar si"))

    assert enviados[1] == "Vale, no apunto nada."
    assert enviados[2].startswith("No tengo nada pendiente")
    assert database.get_movimientos(config.database_path) == []


def test_importar_venta_sin_cripto(config, enviados, monkeypatch, con_csv):
    solo_venta = "\n".join(CSV_BINANCE.splitlines()[:2])
    monkeypatch.setattr(telegram, "descargar", lambda t, f: solo_venta.encode())

    main.atender(config, _archivo())
    main.atender(config, _mensaje("/importar si"))

    assert "1 venta sin apuntar" in enviados[1]
    assert database.get_movimientos(config.database_path) == []


def test_importar_archivo_que_no_es_csv(config, enviados, con_csv):
    main.atender(config, _archivo("foto.jpg"))

    assert enviados[0] == "Solo sé leer el CSV de Binance o de Kraken. Mira /importar"


def test_importar_csv_que_no_es_de_binance(config, enviados, monkeypatch, con_csv):
    monkeypatch.setattr(telegram, "descargar", lambda t, f: b"a,b\n1,2\n")

    main.atender(config, _archivo())

    assert enviados[0].startswith("No parece el historial de operaciones")


def test_importar_si_no_se_puede_bajar(config, enviados, monkeypatch, con_csv):
    monkeypatch.setattr(telegram, "descargar", lambda t, f: None)

    main.atender(config, _archivo())

    assert enviados[0] == "No he podido bajar el archivo. Prueba otra vez."


def test_importar_a_secas_explica_como(config, enviados):
    main.atender(config, _mensaje("/importar"))

    assert "Historial de operaciones" in enviados[0]


# --- avisos sueltos juntos ---


def _baja_y_vuelve(concentrada, monkeypatch):
    # Al volver a 66.000 saltan dos: la concentración y que vuelve a lo que costó.
    for btc in (66000.0, 15000.0, 66000.0):
        _precio(monkeypatch, {"bitcoin": btc, "solana": 100.0})
        main.ejecutar_ciclo(concentrada, {})


def test_avisos_sueltos_del_ciclo_van_en_un_mensaje(concentrada, enviados, monkeypatch):
    _baja_y_vuelve(concentrada, monkeypatch)

    ultimo = enviados[-1]
    assert ultimo.startswith("<b>2 avisos</b>")
    assert "⚖️ <b>Bitcoin ya es el 87%" in ultimo
    assert "vuelve a lo que te costó" in ultimo


def test_si_no_llega_el_mensaje_junto_salta_otra_vez(concentrada, monkeypatch):
    enviados = []
    funciona = [True]
    monkeypatch.setattr(
        telegram,
        "send_message",
        lambda t, c, texto, **kw: funciona[0] and (enviados.append(texto) or True),
    )

    for btc in (66000.0, 15000.0):
        _precio(monkeypatch, {"bitcoin": btc, "solana": 100.0})
        main.ejecutar_ciclo(concentrada, {})
    funciona[0] = False
    _precio(monkeypatch, {"bitcoin": 66000.0, "solana": 100.0})
    main.ejecutar_ciclo(concentrada, {})
    antes = len(enviados)

    funciona[0] = True
    main.ejecutar_ciclo(concentrada, {})

    assert len(enviados) == antes + 1
    assert enviados[-1].startswith("<b>2 avisos</b>")


def test_avisos_sueltos_van_con_el_de_precio(concentrada, enviados, monkeypatch):
    for btc in (66000.0, 15000.0):
        _precio(monkeypatch, {"bitcoin": btc, "solana": 100.0})
        main.ejecutar_ciclo(concentrada, {})
    enviados.clear()

    _precio(monkeypatch, {"bitcoin": 66000.0, "solana": 100.0})
    # Con BTC vigilado al 5%, de 15.000 a 66.000 también cruza el de precio.
    main.ejecutar_ciclo(concentrada, {"bitcoin": "%15000.0"})

    [mensaje] = enviados
    assert "⚖️" in mensaje
    assert "vuelve a lo que te costó" in mensaje
    # Antes de la línea de la fuente, que va siempre al final.
    assert mensaje.index("⚖️") < mensaje.index("Price data by")


# --- panel web ---


def test_panel_con_lo_guardado(config, monkeypatch):
    from dataclasses import replace

    from crypto_tracker.config import parse_cartera

    def sin_red(*a, **k):
        raise AssertionError("el panel no debe consultar CoinGecko")

    monkeypatch.setattr(coingecko, "get_prices", sin_red)
    con_cartera = replace(config, cartera=parse_cartera("bitcoin:0.1:5000"))
    database.save_prices(config.database_path, {"bitcoin": 60000.0}, "eur")
    database.crear_puntual(config.database_path, "bitcoin", 70000.0, True, "eur")

    datos = main.datos_panel(con_cartera)

    assert datos.total == 6000.0
    assert datos.ganancia == 1000.0
    assert [v.coin_id for v in datos.vigiladas] == ["bitcoin"]
    assert datos.alertas[0].precio == 60000.0
    assert datos.actualizado is not None


def test_panel_recien_instalado(config):
    html = main.pagina_panel(config)

    assert "Sin cartera" in html
    assert "todavía sin precios" in html


def test_panel_se_sirve_por_http(config, monkeypatch):
    import threading
    import urllib.error
    import urllib.request
    from http.server import HTTPServer

    hecho = threading.Event()
    servidor = {}

    # En un puerto libre cualquiera, para no chocar con nada.
    class EnPuertoLibre(HTTPServer):
        def __init__(self, direccion, atender):
            super().__init__(("127.0.0.1", 0), atender)
            servidor["este"] = self
            hecho.set()

    monkeypatch.setattr(main, "HTTPServer", EnPuertoLibre)
    hilo = threading.Thread(target=main.servir_panel, args=(config, 0))
    hilo.start()
    hecho.wait(5)
    base = f"http://127.0.0.1:{servidor['este'].server_address[1]}"
    try:
        with urllib.request.urlopen(base + "/") as r:
            assert r.status == 200
            assert "CryptoPriceTracker" in r.read().decode()
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(base + "/otra")
        assert e.value.code == 404
    finally:
        servidor["este"].shutdown()
        hilo.join()


# --- /impuestos csv ---


def test_impuestos_csv_para_la_renta(config, enviados, archivos, monkeypatch):
    from datetime import date

    config = _con_cartera(config, Posicion("bitcoin", 0.02, 1000))
    _precio(monkeypatch, {})
    # Lo del .env (0,02 a 1000) es lo más viejo: FIFO vende eso primero.
    main.atender(config, _mensaje("/compra bitcoin 0.01 800"))
    main.atender(config, _mensaje("/venta bitcoin 0.01 900 com 1"))
    enviados.clear()
    año = date.today().year

    main.atender(config, _mensaje(f"/impuestos {año} csv"))

    contenido, nombre, pie = archivos[0]
    filas = [f.split(";") for f in contenido.decode("utf-8-sig").splitlines()]
    assert filas[1][1:6] == ["bitcoin", "0,01", "899", "500", "399"]
    assert filas[2][:6] == ["total", "", "", "899", "500", "399"]
    assert nombre == f"renta-{año}.csv"
    assert f"1 venta de {año}" in pie
    assert enviados == []


def test_impuestos_csv_sin_ventas(config, enviados, archivos):
    main.atender(config, _mensaje("/impuestos csv"))

    assert archivos == []
    assert "no has vendido nada" in enviados[0]


def test_impuestos_normal_dice_lo_del_csv(config, enviados, monkeypatch):
    from datetime import date

    config = _con_cartera(config, Posicion("bitcoin", 0.02, 1000))
    _precio(monkeypatch, {})
    main.atender(config, _mensaje("/venta bitcoin 0.01 900"))
    enviados.clear()

    main.atender(config, _mensaje("/impuestos"))

    assert f"/impuestos {date.today().year} csv" in enviados[0]


CSV_KRAKEN = (
    '"txid","ordertxid","pair","time","type","ordertype","price","cost","fee",'
    '"vol","margin","misc","ledgers"\n'
    '"T2","O2","XXBTZEUR","2024-05-02 08:00:00.1234","sell","limit","60000.0",'
    '"60.00","0.16","0.00100000","0.00000","","L3,L4"\n'
    '"T1","O1","XXBTZEUR","2024-03-01 10:15:22.5000","buy","market","50000.0",'
    '"100.00","0.26","0.00200000","0.00000","","L1,L2"\n'
)


def test_importar_de_kraken(config, enviados, monkeypatch, con_csv):
    monkeypatch.setattr(telegram, "descargar", lambda t, f: CSV_KRAKEN.encode())

    main.atender(config, _archivo("trades.csv"))
    assert "Lo que he leído del CSV de Kraken" in enviados[0]
    main.atender(config, _mensaje("/importar si"))

    assert enviados[1].startswith("✅ Apuntadas 2 operaciones de Kraken")
    venta, compra = database.get_movimientos(config.database_path)
    assert compra.cuando == datetime(2024, 3, 1, 10, 15, 22, tzinfo=timezone.utc)
    assert (compra.cantidad, compra.coste, compra.nota) == (0.002, 100.26, "Kraken")
    assert (venta.cantidad, venta.coste, venta.nota) == (0.001, 59.84, "Kraken")


# --- /binance ---


def test_binance_sin_clave_explica_como_crearla(config, enviados, monkeypatch):
    monkeypatch.delenv("BINANCE_API_KEY", raising=False)
    monkeypatch.delenv("BINANCE_API_SECRET", raising=False)

    main.atender(config, _mensaje("/binance"))

    assert "Habilitar lectura" in enviados[0]
    assert "BINANCE_API_SECRET" in enviados[0]


def test_binance_compara_y_no_enseña_el_secreto(config, enviados, monkeypatch, caplog):
    import logging

    import requests

    monkeypatch.setenv("BINANCE_API_KEY", "CLAVE-DE-PRUEBA")
    monkeypatch.setenv("BINANCE_API_SECRET", "SECRETO-QUE-NO-SALE")
    config = _con_cartera(config, Posicion("bitcoin", 0.2, 5000))

    class Respuesta:
        status_code = 200

        def json(self):
            return {
                "balances": [
                    {"asset": "BTC", "free": "0.15", "locked": "0"},
                    {"asset": "ETH", "free": "1", "locked": "0"},
                ]
            }

    monkeypatch.setattr(requests, "get", lambda url, **k: Respuesta())

    with caplog.at_level(logging.DEBUG):
        main.atender(config, _mensaje("/binance"))

    texto = enviados[0]
    assert (
        "<b>Bitcoin</b>: 0,15 en Binance, 0,2 apuntado (0,05 menos en Binance)" in texto
    )
    assert "➕ <b>Ethereum</b>: 1 en Binance, sin apuntar" in texto
    assert "SECRETO-QUE-NO-SALE" not in texto
    assert "SECRETO-QUE-NO-SALE" not in caplog.text


def _inline(monkeypatch):
    """Lo que el bot contestaría a una consulta inline, sin ir a Telegram."""
    contestadas = []
    monkeypatch.setattr(
        telegram,
        "answer_inline",
        lambda token, qid, tarjetas, cache: contestadas.append((qid, tarjetas)),
    )
    # Si tirara de CoinGecko con cada letra, este test se enteraría.
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    return contestadas


def test_inline_con_lo_guardado(config, monkeypatch):
    contestadas = _inline(monkeypatch)
    ayer = datetime.now(timezone.utc) - timedelta(hours=24, minutes=5)
    database.guardar_serie(config.database_path, "bitcoin", [(ayer, 60000)], "eur")
    database.save_prices(
        config.database_path, {"bitcoin": 63000.0, "ethereum": 2500.0}, "eur"
    )

    main.atender_inline(config, {"id": "q9", "from": {"id": 123}, "query": "btc eth"})

    qid, tarjetas = contestadas[0]
    assert qid == "q9"
    assert [t.coin_id for t in tarjetas] == ["bitcoin", "ethereum"]
    assert tarjetas[0].texto == "💰 <b>Bitcoin</b>  €63.000,00\n🔺 +5.00% en 24 h"
    assert tarjetas[1].descripcion.startswith("Sin datos de las últimas 24 h")


def test_inline_vacia_son_las_vigiladas_y_salta_las_que_no_tengo(config, monkeypatch):
    contestadas = _inline(monkeypatch)
    database.save_prices(config.database_path, {"bitcoin": 63000.0}, "eur")

    main.atender_inline(config, {"id": "q1", "from": {"id": 123}, "query": ""})
    main.atender_inline(config, {"id": "q2", "from": {"id": 123}, "query": "sol"})

    assert [t.coin_id for t in contestadas[0][1]] == ["bitcoin"]
    assert contestadas[1][1] == []


def test_inline_de_otro_no_contesta(config, monkeypatch):
    contestadas = _inline(monkeypatch)
    database.save_prices(config.database_path, {"bitcoin": 63000.0}, "eur")

    main.atender_inline(config, {"id": "q1", "from": {"id": 999}, "query": "btc"})

    assert contestadas == []


# --- /mute ... salvo 10% ---


def test_mute_con_salvo(config, monkeypatch):
    mandados = _con_botones(monkeypatch)

    main.atender(config, _mensaje("/mute 7d salvo 10%"))

    assert database.silencio_salvo(config.database_path) == 10
    assert "(7 d)" in mandados[0][0]
    assert mandados[0][0].endswith("se mueve más de un 10% en 24 h.")

    main.atender(config, _mensaje("/mute"))
    assert ", salvo si alguna se mueve más de un 10%." in mandados[1][0]


def test_mute_con_salvo_con_decimales(config, monkeypatch):
    mandados = _con_botones(monkeypatch)

    main.atender(config, _mensaje("/mute 2h salvo 7,5%"))

    assert mandados[0][0].endswith("más de un 7,5% en 24 h.")


def test_mute_con_salvo_de_una_sola_no(config, enviados):
    main.atender(config, _mensaje("/mute btc 2h salvo 5%"))

    assert "va con el /mute de todas" in enviados[0]
    assert database.criptos_calladas(config.database_path) == {}


def test_callado_con_salvo_avisa_de_lo_gordo_una_vez(config, enviados, monkeypatch):
    _precio_de(config, "bitcoin", 100.0, 24 * 60)
    _precio(monkeypatch, {"bitcoin": 85.0})
    main.atender(config, _mensaje("/mute 7d salvo 10%"))
    enviados.clear()

    main.ejecutar_ciclo(config, {})
    main.ejecutar_ciclo(config, {})

    assert len(enviados) == 1
    assert enviados[0].startswith("🚨 <b>Bitcoin</b> 🔻 -15,0% en 24 h")


def test_callado_con_salvo_no_avisa_de_lo_pequeño(config, enviados, monkeypatch):
    _precio_de(config, "bitcoin", 100.0, 24 * 60)
    _precio(monkeypatch, {"bitcoin": 95.0})
    main.atender(config, _mensaje("/mute 7d salvo 10%"))
    enviados.clear()

    main.ejecutar_ciclo(config, {})

    assert enviados == []


def test_callado_sin_salvo_no_avisa_de_nada(config, enviados, monkeypatch):
    _precio_de(config, "bitcoin", 100.0, 24 * 60)
    _precio(monkeypatch, {"bitcoin": 50.0})
    main.atender(config, _mensaje("/mute 7d salvo 10%"))
    main.atender(config, _mensaje("/mute 7d"))  # el nuevo quita el salvo
    enviados.clear()

    main.ejecutar_ciclo(config, {})

    assert enviados == []


def test_salvo_sin_silencio_no_hace_nada(config, enviados, monkeypatch):
    _precio_de(config, "bitcoin", 100.0, 24 * 60)
    _precio(monkeypatch, {"bitcoin": 85.0})
    main.atender(config, _mensaje("/mute 7d salvo 10%"))
    main.atender(config, _mensaje("/unmute"))
    enviados.clear()

    main.ejecutar_ciclo(config, {})

    assert not any(t.startswith("🚨") for t in enviados)
    assert database.silencio_salvo(config.database_path) is None


# --- /spread ---


def test_spread(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 60000.0, "ethereum": 2000.0, "tether": 0.92})
    monkeypatch.setattr(
        binance, "precios", lambda ids, cur: {"bitcoin": 60060.0, "ethereum": 1900.0}
    )

    main.atender(config, _mensaje("/spread btc eth usdt"))

    texto = enviados[0]
    assert texto.index("Ethereum") < texto.index("Bitcoin")  # la más separada antes
    assert "⚠️ <b>Ethereum</b>" in texto
    assert "(+0,10%)" in texto
    assert "➖ <b>Tether</b>: es una estable" in texto


def test_spread_a_secas_las_que_vigilas(config, enviados, monkeypatch):
    pedidas = _precio(monkeypatch, {"bitcoin": 60000.0})
    monkeypatch.setattr(binance, "precios", lambda ids, cur: {"bitcoin": 60000.0})

    main.atender(config, _mensaje("/spread"))

    assert pedidas == [["bitcoin"]]
    assert "(igual)" in enviados[0]


def test_spread_boton_con_lo_que_escribiste(config, monkeypatch):
    mandados = _con_botones(monkeypatch)
    _precio(monkeypatch, {"bitcoin": 60000.0, "avalanche-2": 30.0})
    monkeypatch.setattr(
        binance, "precios", lambda ids, cur: {"bitcoin": 60000.0, "avalanche-2": 30.0}
    )

    main.atender(config, _mensaje("/spread btc avax"))

    assert mandados[0][1] == [[("🔄 Actualizar", "/spread btc avax")]]


def test_spread_con_muchas_va_sin_boton(config, enviados, monkeypatch):
    nombres = "bitcoin ethereum solana cardano dogecoin litecoin chainlink polkadot"
    precios = {c: 1.0 for c in nombres.split()}
    _precio(monkeypatch, precios)
    monkeypatch.setattr(binance, "precios", lambda ids, cur: precios)

    main.atender(config, _mensaje(f"/spread {nombres}"))

    assert "CoinGecko contra Binance" in enviados[0]


def test_spread_si_binance_no_contesta(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 60000.0})

    def caido(ids, cur):
        raise binance.BinanceError("sin red")

    monkeypatch.setattr(binance, "precios", caido)

    main.atender(config, _mensaje("/spread btc"))

    assert "Binance no contesta ahora mismo" in enviados[0]


def test_spread_en_libras_no(config, enviados):
    from dataclasses import replace

    main.atender(replace(config, vs_currency="gbp"), _mensaje("/spread btc"))

    assert "euros o en dólares" in enviados[0]


# --- invitados ---


@pytest.fixture
def a_quien(monkeypatch):
    """[(chat, texto)] de todo lo que se manda, para ver a quién llega cada cosa."""
    lista = []
    monkeypatch.setattr(
        telegram,
        "send_message",
        lambda token, chat, texto, **kw: lista.append((str(chat), texto)) or True,
    )
    return lista


def _de(chat, texto, tipo="private", nombre="Ana"):
    m = _mensaje(texto, chat=chat)
    m["chat"]["type"] = tipo
    m["from"] = {"id": chat, "first_name": nombre}
    return m


def _invitar(config, a_quien):
    main.atender(config, _mensaje("/invitar"))
    return a_quien[-1][1].split("<code>/start ")[1].split("</code>")[0]


def test_invitar_y_entrar(config, a_quien):
    codigo = _invitar(config, a_quien)

    main.atender(config, _de(555, f"/start {codigo.lower()}"))

    assert a_quien[-2][0] == "555" and "¡Dentro!" in a_quien[-2][1]
    assert a_quien[-1][0] == "123" and "<b>Ana</b> ha entrado" in a_quien[-1][1]
    assert database.es_invitado(config.database_path, "555")
    import os

    assert os.path.exists(os.path.join(os.path.dirname(config.database_path),
                                       "usuarios", "555.db"))  # fmt: skip


def test_el_codigo_se_gasta(config, a_quien):
    codigo = _invitar(config, a_quien)
    main.atender(config, _de(555, f"/start {codigo}"))

    main.atender(config, _de(777, f"/start {codigo}"))

    assert a_quien[-1][0] == "777"
    assert "no vale" in a_quien[-1][1]
    assert not database.es_invitado(config.database_path, "777")


def test_sin_codigo_ni_contesto(config, a_quien):
    main.atender(config, _de(777, "/start"))
    main.atender(config, _de(777, "hola"))
    main.atender(config, _de(777, "/precio btc"))

    assert a_quien == []


def test_desde_un_grupo_no(config, a_quien):
    codigo = _invitar(config, a_quien)

    main.atender(config, _de(-100999, f"/start {codigo}", tipo="supergroup"))

    assert "por privado" in a_quien[-1][1]
    assert database.get_invitados(config.database_path) == []


def test_cada_uno_con_sus_cosas(config, a_quien, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 60000.0, "solana": 150.0})
    codigo = _invitar(config, a_quien)
    main.atender(config, _de(555, f"/start {codigo}"))

    main.atender(config, _de(555, "/vigilar solana %5"))
    main.atender(config, _de(555, "/vigilar"))
    main.atender(config, _mensaje("/vigilar"))

    suyo, tuyo = a_quien[-2], a_quien[-1]
    assert suyo[0] == "555" and "Solana" in suyo[1] and "Bitcoin" not in suyo[1]
    assert tuyo[0] == "123" and "Bitcoin" in tuyo[1] and "Solana" not in tuyo[1]


def test_el_invitado_no_usa_lo_tuyo(config, a_quien):
    codigo = _invitar(config, a_quien)
    main.atender(config, _de(555, f"/start {codigo}"))

    for orden in ("/binance", "/consultas", "/invitar", "/usuarios", "/expulsar 123"):
        main.atender(config, _de(555, orden))
        assert a_quien[-1] == ("555", "Eso solo lo puede usar quien lleva el bot.")


def test_usuarios_y_expulsar(config, a_quien, monkeypatch):
    mandados = []
    codigo = _invitar(config, a_quien)
    main.atender(config, _de(555, f"/start {codigo}"))

    monkeypatch.setattr(
        telegram,
        "send_message",
        lambda token, chat, texto, **kw: mandados.append((chat, texto, kw)) or True,
    )
    main.atender(config, _mensaje("/usuarios"))
    assert "Ana" in mandados[0][1]
    assert mandados[0][2]["botones"] == [[("✖ Ana", "/expulsar 555")]]

    main.atender_boton(config, _boton("/expulsar 555"))
    assert mandados[1][0] == "555" and "Ya no puedes" in mandados[1][1]
    assert "Fuera" in mandados[2][1]

    mandados.clear()
    main.atender(config, _de(555, "/precio btc"))
    assert mandados == []


def test_lleno_no_gasta_el_codigo(config, a_quien, monkeypatch):
    from crypto_tracker import usuarios

    codigo = _invitar(config, a_quien)
    monkeypatch.setattr(usuarios, "MAX_INVITADOS", 0)

    main.atender(config, _de(555, f"/start {codigo}"))
    assert "lo máximo" in a_quien[-1][1]

    monkeypatch.setattr(usuarios, "MAX_INVITADOS", 10)
    main.atender(config, _de(555, f"/start {codigo}"))
    assert "¡Dentro!" in a_quien[-2][1]


def test_invitar_lleno(config, a_quien, monkeypatch):
    from crypto_tracker import usuarios

    monkeypatch.setattr(usuarios, "MAX_INVITADOS", 0)
    main.atender(config, _mensaje("/invitar"))

    assert "lo máximo" in a_quien[-1][1]


# --- el ciclo con invitados ---


def _una_vuelta(config, monkeypatch):
    """ejecutar_bucle hasta la primera espera, que es donde se corta."""
    monkeypatch.setattr(telegram, "set_commands", lambda *a: True)
    monkeypatch.setattr(main, "apuntar_consultas", lambda c: None)
    monkeypatch.setattr(main, "avisar_encendido", lambda c: None)

    def corta(*a):
        raise KeyboardInterrupt

    monkeypatch.setattr(main, "esperar_escuchando", corta)
    with pytest.raises(KeyboardInterrupt):
        main.ejecutar_bucle(config, {})


def _con_invitado(config, a_quien, chat=555):
    codigo = _invitar(config, a_quien)
    main.atender(config, _de(chat, f"/start {codigo}"))


def test_el_ciclo_avisa_a_cada_uno_con_una_consulta(config, a_quien, monkeypatch):
    pedidas = _precio(monkeypatch, {"bitcoin": 60000.0, "solana": 150.0})
    _con_invitado(config, a_quien)
    main.atender(config, _de(555, "/alerta solana 140"))
    main.atender(config, _mensaje("/alerta bitcoin 55000"))
    pedidas.clear()
    a_quien.clear()

    pedidas = _precio(monkeypatch, {"bitcoin": 50000.0, "solana": 130.0})
    _una_vuelta(config, monkeypatch)

    assert pedidas == [["bitcoin", "solana"]]  # una sola, con las de los dos
    suyos = [t for c, t in a_quien if c == "555"]
    tuyos = [t for c, t in a_quien if c == "123"]
    assert any("Solana" in t for t in suyos)
    assert not any("Bitcoin" in t for t in suyos)
    assert any("Bitcoin" in t for t in tuyos)
    assert not any("Solana" in t for t in tuyos)


def test_el_invitado_sin_nada_no_pasa_ciclo(config, a_quien, monkeypatch):
    pedidas = _precio(monkeypatch, {"bitcoin": 60000.0})
    _con_invitado(config, a_quien)
    pasados = []
    original = main.ejecutar_ciclo
    monkeypatch.setattr(
        main,
        "ejecutar_ciclo",
        lambda c, *a: pasados.append(c.telegram_chat_id) or original(c, *a),
    )

    _una_vuelta(config, monkeypatch)

    assert pasados == ["123"]
    assert pedidas == [["bitcoin"]]


def test_si_falla_lo_de_un_invitado_sigues_tu(config, a_quien, monkeypatch, caplog):
    _precio(monkeypatch, {"bitcoin": 60000.0, "solana": 150.0})
    _con_invitado(config, a_quien)
    main.atender(config, _de(555, "/vigilar solana %5"))
    original = main.ejecutar_ciclo

    def rompe(c, *a):
        if c.invitado:
            raise RuntimeError("roto")
        return original(c, *a)

    monkeypatch.setattr(main, "ejecutar_ciclo", rompe)
    _una_vuelta(config, monkeypatch)

    assert "Error en el ciclo del invitado 555" in caplog.text
    assert main._pulso.ultimo_bien is not None  # el tuyo fue bien


def test_un_id_que_no_existe_no_se_pide_aparte(config, monkeypatch):
    pedidas = _precio(monkeypatch, {"bitcoin": 60000.0})
    pedidos = main.pedir_precios(["bitcoin", "no-existe"], "eur")
    pedidas.clear()

    from dataclasses import replace

    con_rara = replace(config, watchlist=[Watch("bitcoin"), Watch("no-existe")])
    main.ejecutar_ciclo(con_rara, {}, set(), pedidos)

    assert pedidas == []


def test_inline_del_invitado_con_lo_suyo(config, a_quien, monkeypatch):
    from crypto_tracker import usuarios

    _precio(monkeypatch, {"solana": 150.0})
    _con_invitado(config, a_quien)
    main.atender(config, _de(555, "/vigilar solana %5"))
    database.save_prices(config.database_path, {"bitcoin": 63000.0}, "eur")
    database.save_prices(usuarios.archivo(config, "555"), {"solana": 150.0}, "eur")
    contestadas = _inline(monkeypatch)

    main.atender_inline(config, {"id": "q1", "from": {"id": 555}, "query": ""})
    main.atender_inline(config, {"id": "q2", "from": {"id": 555}, "query": "btc"})

    assert [t.coin_id for t in contestadas[0][1]] == ["solana"]
    assert contestadas[1][1] == []  # tu bitcoin no lo ve


def test_la_ayuda_del_invitado_sin_lo_tuyo(config, a_quien):
    _con_invitado(config, a_quien)

    main.atender(config, _de(555, "/ayuda todo"))
    suya = a_quien[-1][1]
    main.atender(config, _mensaje("/ayuda todo"))
    tuya = a_quien[-1][1]

    for orden in ("/invitar", "/usuarios", "/expulsar", "/binance", "/consultas"):
        assert f"\n{orden} — " not in suya
        assert f"\n{orden} — " in tuya
    assert "\n/precio — " in suya

    main.atender(config, _de(555, "/ayuda invitar"))
    assert a_quien[-1][1] == "Eso solo lo puede usar quien lleva el bot."

    main.atender(config, _de(555, "/ayuda sistema"))
    assert "\n/ajustes — " in a_quien[-1][1]
    assert "\n/invitar — " not in a_quien[-1][1]


def test_dominancia_del_invitado_con_tu_historico(config, a_quien, monkeypatch):
    from crypto_tracker import usuarios
    from crypto_tracker.dominancia import Foto

    _con_invitado(config, a_quien)
    hace_semana = datetime.now(timezone.utc) - timedelta(days=7)
    database.guardar_dominancia(config.database_path, Foto(hace_semana, 56.0, 13, 6))
    _mercado_global(monkeypatch, 58.0)

    main.atender(config, _de(555, "/dominancia"))

    assert a_quien[-1][0] == "555"
    assert "🔺 +2,0 puntos en 7 días" in a_quien[-1][1]
    # La foto de hoy también va a la tuya, no a la suya.
    assert len(database.get_dominancia(config.database_path, 1)) == 1
    suyo = usuarios.archivo(config, "555")
    assert database.get_dominancia(suyo, 24 * 30) == []


@pytest.fixture
def fijo(monkeypatch):
    """El Telegram de /envivo: apunta lo que se le pide y lo da por bueno."""

    class Fijo:
        hechos: list = []
        error_al_editar = None
        deja_borrar = True

    f = Fijo()
    f.hechos = []
    numeros = iter(range(500, 600))

    def enviar(token, chat, texto):
        numero = next(numeros)
        f.hechos.append(("enviar", numero, texto))
        return numero

    def editar(token, chat, numero, texto):
        f.hechos.append(("editar", numero, texto))
        return f.error_al_editar

    def borrar(token, chat, numero):
        f.hechos.append(("borrar", numero))
        return f.deja_borrar

    monkeypatch.setattr(telegram, "enviar_con_id", enviar)
    monkeypatch.setattr(telegram, "editar_mensaje", editar)
    monkeypatch.setattr(telegram, "borrar_mensaje", borrar)
    monkeypatch.setattr(
        telegram, "fijar", lambda t, c, n: f.hechos.append(("fijar", n)) or True
    )
    monkeypatch.setattr(
        telegram, "desfijar", lambda t, c, n: f.hechos.append(("desfijar", n)) or True
    )
    return f


def test_envivo_sin_precios_no_pone_nada(config, enviados, fijo):
    main.atender(config, _mensaje("/envivo"))

    assert "no tengo precios" in enviados[0]
    assert fijo.hechos == []
    assert database.envivo(config.database_path) is None


def test_envivo_lo_manda_y_lo_fija(config, enviados, fijo):
    database.save_prices(config.database_path, {"bitcoin": 63000.0}, "eur")

    main.atender(config, _mensaje("/envivo"))

    (_, numero, texto), fijado = fijo.hechos
    assert "En vivo" in texto
    assert "63.000" in texto
    assert fijado == ("fijar", numero)
    assert database.envivo(config.database_path) == numero
    assert "Fijado arriba" in enviados[0]
    assert "cada 5 min" in enviados[0]


def test_envivo_se_edita_en_cada_ciclo_sin_pedir_precios(
    config, enviados, fijo, monkeypatch
):
    def no_pedir(*a, **k):
        raise AssertionError("no tiene que gastar consultas")

    monkeypatch.setattr(coingecko, "get_prices", no_pedir)
    database.save_prices(config.database_path, {"bitcoin": 63000.0}, "eur")
    main.atender(config, _mensaje("/envivo"))
    database.save_prices(config.database_path, {"bitcoin": 64500.0}, "eur")

    main.en_vivo(config, datetime(2026, 11, 22, 9, 5).astimezone())

    accion, numero, texto = fijo.hechos[-1]
    assert (accion, numero) == ("editar", database.envivo(config.database_path))
    assert "64.500" in texto
    assert "a las 09:05" in texto
    assert len(enviados) == 1  # solo el "Fijado arriba": editar no manda nada


def test_envivo_lleva_la_cartera(config, enviados, fijo):
    from dataclasses import replace

    con_cartera = replace(config, cartera=(Posicion("ethereum", 2.0, 4000.0),))
    database.save_prices(
        config.database_path, {"bitcoin": 63000.0, "ethereum": 2500.0}, "eur"
    )

    main.atender(con_cartera, _mensaje("/envivo"))

    texto = fijo.hechos[0][2]
    assert "Tu cartera" in texto
    assert "5.000" in texto


def test_envivo_sin_ponerlo_el_ciclo_no_hace_nada(config, fijo):
    database.save_prices(config.database_path, {"bitcoin": 63000.0}, "eur")

    main.en_vivo(config)

    assert fijo.hechos == []


def test_envivo_si_lo_borras_deja_de_editarlo(config, enviados, fijo):
    database.save_prices(config.database_path, {"bitcoin": 63000.0}, "eur")
    main.atender(config, _mensaje("/envivo"))
    fijo.error_al_editar = "HTTP 400: Bad Request: message to edit not found"

    main.en_vivo(config)
    main.en_vivo(config)

    assert database.envivo(config.database_path) is None
    assert [h[0] for h in fijo.hechos].count("editar") == 1


def test_envivo_un_fallo_de_red_no_lo_quita(config, enviados, fijo):
    database.save_prices(config.database_path, {"bitcoin": 63000.0}, "eur")
    main.atender(config, _mensaje("/envivo"))
    fijo.error_al_editar = ""

    main.en_vivo(config)

    assert database.envivo(config.database_path) is not None


def test_envivo_no_lo_quita(config, enviados, fijo):
    database.save_prices(config.database_path, {"bitcoin": 63000.0}, "eur")
    main.atender(config, _mensaje("/envivo"))
    numero = database.envivo(config.database_path)

    main.atender(config, _mensaje("/envivo no"))

    assert fijo.hechos[-1] == ("borrar", numero)
    assert database.envivo(config.database_path) is None
    assert "quitado" in enviados[1]


def test_envivo_no_con_uno_viejo_lo_desfija(config, enviados, fijo):
    database.save_prices(config.database_path, {"bitcoin": 63000.0}, "eur")
    main.atender(config, _mensaje("/envivo"))
    numero = database.envivo(config.database_path)
    fijo.deja_borrar = False

    main.atender(config, _mensaje("/envivo no"))

    assert fijo.hechos[-1] == ("desfijar", numero)


def test_envivo_no_sin_tenerlo(config, enviados, fijo):
    main.atender(config, _mensaje("/envivo no"))

    assert "No lo tenías puesto" in enviados[0]
    assert fijo.hechos == []


def test_envivo_otra_vez_lo_baja_y_quita_el_de_antes(config, enviados, fijo):
    database.save_prices(config.database_path, {"bitcoin": 63000.0}, "eur")
    main.atender(config, _mensaje("/envivo"))
    primero = database.envivo(config.database_path)

    main.atender(config, _mensaje("/envivo"))

    segundo = database.envivo(config.database_path)
    assert segundo != primero
    assert ("borrar", primero) in fijo.hechos
    assert fijo.hechos[-1] == ("fijar", segundo)


def test_envivo_si_no_deja_fijar_te_lo_dice(config, enviados, fijo, monkeypatch):
    database.save_prices(config.database_path, {"bitcoin": 63000.0}, "eur")
    monkeypatch.setattr(telegram, "fijar", lambda t, c, n: False)

    main.atender(config, _mensaje("/envivo"))

    assert "No he podido fijarlo" in enviados[0]
    assert database.envivo(config.database_path) is not None


def _latidos(monkeypatch):
    from crypto_tracker import latido

    dados = []
    monkeypatch.setattr(latido, "mandar", lambda url: dados.append(url) or True)
    return dados


def test_el_bucle_da_el_latido_si_el_ciclo_va_bien(config, enviados, monkeypatch):
    from dataclasses import replace

    dados = _latidos(monkeypatch)
    monkeypatch.setattr(main, "ejecutar_ciclo", lambda c, e, s, p=None: (e, None))
    monkeypatch.setattr(main, "pedir_precios", lambda *a: main.Pedidos({}))

    _una_vuelta(replace(config, latido_url="https://hc-ping.com/abc"), monkeypatch)

    assert dados == ["https://hc-ping.com/abc"]


def test_sin_precios_no_hay_latido(config, enviados, monkeypatch):
    from dataclasses import replace

    dados = _latidos(monkeypatch)
    monkeypatch.setattr(
        main, "ejecutar_ciclo", lambda c, e, s, p=None: (e, "CoinGecko no contesta")
    )
    monkeypatch.setattr(main, "pedir_precios", lambda *a: main.Pedidos({}))

    _una_vuelta(replace(config, latido_url="https://hc-ping.com/abc"), monkeypatch)

    assert dados == []


def test_si_el_ciclo_revienta_no_hay_latido(config, enviados, monkeypatch):
    from dataclasses import replace

    def revienta(*a, **k):
        raise RuntimeError("algo raro")

    dados = _latidos(monkeypatch)
    monkeypatch.setattr(main, "ejecutar_ciclo", revienta)
    monkeypatch.setattr(main, "pedir_precios", lambda *a: main.Pedidos({}))

    _una_vuelta(replace(config, latido_url="https://hc-ping.com/abc"), monkeypatch)

    assert dados == []


def test_sin_latido_puesto_no_llama_a_nadie(config, enviados, monkeypatch):
    dados = _latidos(monkeypatch)
    monkeypatch.setattr(main, "ejecutar_ciclo", lambda c, e, s, p=None: (e, None))
    monkeypatch.setattr(main, "pedir_precios", lambda *a: main.Pedidos({}))

    _una_vuelta(config, monkeypatch)

    assert dados == []


# --- /semaforo ---


def _sin_funding(monkeypatch):
    def sin_futuros(par):
        raise funding.FundingError("sin futuros")

    monkeypatch.setattr(funding, "pedir", sin_futuros)


def test_semaforo_subiendo_sin_parar_queda_en_ambar(config, enviados, monkeypatch):
    from crypto_tracker.miedo import Indice

    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    monkeypatch.setattr(
        miedo, "pedir", lambda: [Indice(80, "Extreme Greed", datetime.now().date())]
    )
    _sin_funding(monkeypatch)
    # Subiendo sin parar la tendencia vota a favor y lo pasada que va, en contra
    for dias in range(40):
        _precio_de(config, "bitcoin", 100.0 * 1.03 ** (40 - dias), dias * 24 * 60)

    main.atender(config, _mensaje("/semaforo btc"))

    assert enviados[0].startswith("🟡 <b>Bitcoin</b>: luz ámbar")
    assert "2 a favor · 2 en contra · 1 en medio" in enviados[0]
    assert "❌ <b>RSI 100</b>" in enviados[0]
    assert "❌ <b>Miedo 80</b>" in enviados[0]
    assert "✅ <b>Medias</b>: por encima de todas" in enviados[0]
    assert "Sin datos de el funding" in enviados[0]


def test_semaforo_rojo_cayendo_con_euforia(config, enviados, monkeypatch):
    from crypto_tracker.miedo import Indice

    monkeypatch.setattr(
        miedo, "pedir", lambda: [Indice(80, "Extreme Greed", datetime.now().date())]
    )
    monkeypatch.setattr(
        funding, "pedir", lambda par: ({"lastFundingRate": "0.0009"}, [])
    )
    # Plana un mes y luego cuesta abajo cada día más deprisa, sin llegar a hundirse
    precios = [100.0] * 30 + [100.0 - 0.05 * n * n for n in range(1, 11)]
    for hace, precio in enumerate(reversed(precios)):
        _precio_de(config, "bitcoin", precio, hace * 24 * 60)

    main.atender(config, _mensaje("/semaforo btc"))

    assert enviados[0].startswith("🔴 <b>Bitcoin</b>: luz roja"), enviados[0]
    assert "❌ <b>Funding</b>: muy apalancado al alza" in enviados[0]


def test_semaforo_cuenta_el_funding_si_lo_hay(config, enviados, monkeypatch):
    monkeypatch.setattr(
        funding, "pedir", lambda par: ({"lastFundingRate": "-0.0005"}, [])
    )
    for dias in range(40):
        _precio_de(config, "bitcoin", 100.0 + dias % 3, dias * 24 * 60)

    main.atender(config, _mensaje("/semaforo"))

    assert "✅ <b>Funding</b>: muchos apostando a que baja" in enviados[0]
    assert "Sin datos de el miedo" in enviados[0]


def test_semaforo_con_pocos_dias(config, enviados, monkeypatch):
    _sin_funding(monkeypatch)
    _precio_de(config, "bitcoin", 100.0, 60)

    main.atender(config, _mensaje("/semaforo btc"))

    assert "Me faltan días de <b>bitcoin</b>" in enviados[0]
    assert "/rellenar bitcoin" in enviados[0]


def test_semaforo_sin_precios(config, enviados):
    main.atender(config, _mensaje("/semaforo sol"))

    assert "No tengo precios guardados de <b>solana</b>" in enviados[0]


def test_semaforo_de_varias(config, enviados):
    main.atender(config, _mensaje("/semaforo btc eth"))

    assert "De una en una" in enviados[0]


# --- /ideal ---


def _avisos_ideal(enviados):
    return [t for t in enviados if "alejado de tu reparto" in t]


# con_semana tiene 0,1 BTC y 10 SOL: con BTC a 60.000 y SOL a 400 van 60/40


def test_ideal_lo_guarda_y_dice_como_vas(con_semana, enviados, monkeypatch):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    database.save_prices(
        con_semana.database_path, {"bitcoin": 66000.0, "solana": 100.0}, "eur"
    )

    main.atender(con_semana, _mensaje("/ideal btc 60 sol 40"))

    assert enviados[0].startswith("👌 Apuntado.")
    assert "⚠️ <b>Bitcoin</b> 87% · querías 60% · le sobran 27 puntos" in enviados[0]
    assert "se aleje 5 puntos" in enviados[0]


def test_ideal_a_secas_sin_tenerlo(con_semana, enviados):
    main.atender(con_semana, _mensaje("/ideal"))

    assert "No tienes un reparto ideal puesto" in enviados[0]


def test_ideal_a_secas_ensena_el_guardado(con_semana, enviados):
    main.atender(con_semana, _mensaje("/ideal btc 60 sol 40 margen 10"))
    main.atender(con_semana, _mensaje("/ideal"))

    assert not enviados[1].startswith("👌")
    assert "<b>Bitcoin</b> 60%" in enviados[1]
    assert "se aleje 10 puntos" in enviados[1]


def test_ideal_mal_escrito_no_guarda_nada(con_semana, enviados):
    main.atender(con_semana, _mensaje("/ideal btc 60 sol 30"))

    assert "suma 90%" in enviados[0]
    assert database.reparto_ideal(con_semana.database_path) is None


def test_ideal_sin_cartera(config, enviados):
    main.atender(config, _mensaje("/ideal btc 60 eth 40"))

    assert enviados[0] == main.SIN_CARTERA


def test_ideal_no_lo_quita(con_semana, enviados, monkeypatch):
    main.atender(con_semana, _mensaje("/ideal btc 60 sol 40"))
    main.atender(con_semana, _mensaje("/ideal no"))
    _precio(monkeypatch, {"bitcoin": 66000.0, "solana": 100.0})
    main.ejecutar_ciclo(con_semana, {})

    assert "ya no vigilo tu reparto" in enviados[1]
    assert _avisos_ideal(enviados) == []


def test_ideal_avisa_una_vez_al_alejarse(con_semana, enviados, monkeypatch):
    main.atender(con_semana, _mensaje("/ideal btc 60 sol 40"))
    _precio(monkeypatch, {"bitcoin": 60000.0, "solana": 400.0})
    main.ejecutar_ciclo(con_semana, {})
    assert _avisos_ideal(enviados) == []

    # SOL a la mitad: 75/25
    _precio(monkeypatch, {"bitcoin": 60000.0, "solana": 200.0})
    main.ejecutar_ciclo(con_semana, {})
    main.ejecutar_ciclo(con_semana, {})

    [aviso] = _avisos_ideal(enviados)
    assert "<b>Bitcoin</b> 75% · querías 60% · le sobran 15 puntos" in aviso
    assert "<code>/rebalanceo bitcoin 60 solana 40</code>" in aviso


def test_ideal_vuelve_a_avisar_si_se_arregla_y_se_aleja(
    con_semana, enviados, monkeypatch
):
    main.atender(con_semana, _mensaje("/ideal btc 60 sol 40"))
    for sol in (200.0, 400.0, 200.0):  # 75/25, 60/40 y otra vez 75/25
        _precio(monkeypatch, {"bitcoin": 60000.0, "solana": sol})
        main.ejecutar_ciclo(con_semana, {})

    assert len(_avisos_ideal(enviados)) == 2


def test_ideal_rondando_el_margen_no_repite(con_semana, enviados, monkeypatch):
    main.atender(con_semana, _mensaje("/ideal btc 60 sol 40"))
    # 75/25, 64/36 (a 4 puntos, sin arreglar del todo) y otra vez 75/25
    for sol in (200.0, 337.5, 200.0):
        _precio(monkeypatch, {"bitcoin": 60000.0, "solana": sol})
        main.ejecutar_ciclo(con_semana, {})

    assert len(_avisos_ideal(enviados)) == 1


def test_ideal_sin_el_precio_de_una_no_avisa(con_semana, enviados, monkeypatch):
    main.atender(con_semana, _mensaje("/ideal btc 60 sol 40"))
    _precio(monkeypatch, {"bitcoin": 60000.0})

    main.ejecutar_ciclo(con_semana, {})

    assert _avisos_ideal(enviados) == []


def test_ideal_callado_espera(con_semana, enviados, monkeypatch):
    main.atender(con_semana, _mensaje("/ideal btc 60 sol 40"))
    _precio(monkeypatch, {"bitcoin": 60000.0, "solana": 200.0})
    database.callar_cripto(
        con_semana.database_path,
        "cartera",
        datetime.now(timezone.utc) + timedelta(hours=1),
    )
    main.ejecutar_ciclo(con_semana, {})
    assert _avisos_ideal(enviados) == []

    database.callar_cripto(con_semana.database_path, "cartera", None)
    main.ejecutar_ciclo(con_semana, {})

    assert len(_avisos_ideal(enviados)) == 1


# --- /informe ---


def test_informe_manda_el_pdf_del_año(config, enviados, archivos, monkeypatch):
    from datetime import date

    config = _con_cartera(config, Posicion("bitcoin", 0.02, 1000))
    _precio(monkeypatch, {})
    main.atender(config, _mensaje("/venta bitcoin 0.01 900 com 1"))
    enviados.clear()
    año = date.today().year

    main.atender(config, _mensaje("/informe"))

    contenido, nombre, pie = archivos[0]
    assert contenido.startswith(b"%PDF")
    assert nombre == f"informe-{año}.pdf"
    assert f"Tu informe de {año}: 1 venta" in pie
    assert f"/impuestos {año} csv" in pie
    assert enviados == []


def test_informe_sin_ventas_no_manda_nada(config, enviados, archivos):
    main.atender(config, _mensaje("/informe"))

    assert archivos == []
    assert "no hay informe que hacer" in enviados[0]


def test_informe_año_que_no_vale(config, enviados, archivos):
    main.atender(config, _mensaje("/informe mañana"))

    assert archivos == []
    assert "como /informe 2025" in enviados[0]


def test_informe_sin_matplotlib_lo_dice(config, enviados, archivos, monkeypatch):
    from crypto_tracker import informe_pdf

    def sin_matplotlib(*a):
        raise grafica.GraficaError("Falta matplotlib.")

    config = _con_cartera(config, Posicion("bitcoin", 0.02, 1000))
    _precio(monkeypatch, {})
    main.atender(config, _mensaje("/venta bitcoin 0.01 900"))
    enviados.clear()
    monkeypatch.setattr(informe_pdf, "dibujar", sin_matplotlib)

    main.atender(config, _mensaje("/informe"))

    assert archivos == []
    assert "Falta matplotlib" in enviados[0]


# --- el aviso de /comisionred 5 ---


def _red(monkeypatch, media_hora):
    """mempool.space con la de media hora a eso; se puede ir cambiando."""
    ahora = {"halfHourFee": media_hora}
    monkeypatch.setattr(comisionred, "pedir", lambda: (dict(ahora), []))
    monkeypatch.setattr(comisionred, "pedir_ahora", lambda: dict(ahora))
    return ahora


def _avisos_red(enviados):
    return [t for t in enviados if "Mover bitcoin ya está barato" in t]


def test_comisionred_pone_el_aviso(config, enviados, monkeypatch):
    _red(monkeypatch, 30)

    main.atender(config, _mensaje("/comisionred 5"))

    assert "Ahora está a 30 sat/vB" in enviados[0]
    assert "baje a <b>5</b> o menos" in enviados[0]
    assert database.aviso_comisionred(config.database_path) == 5


def test_comisionred_si_ya_esta_barata_no_pone_nada(config, enviados, monkeypatch):
    _red(monkeypatch, 4)

    main.atender(config, _mensaje("/comisionred 5"))

    assert "Ya está a <b>4 sat/vB</b>" in enviados[0]
    assert database.aviso_comisionred(config.database_path) is None


def test_comisionred_mal_escrito(config, enviados, monkeypatch):
    _red(monkeypatch, 30)

    main.atender(config, _mensaje("/comisionred barato"))

    assert "de 1 a 1000" in enviados[0]
    assert database.aviso_comisionred(config.database_path) is None


def test_comisionred_avisa_una_vez_al_bajar(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 80000.0})
    red = _red(monkeypatch, 30)
    main.atender(config, _mensaje("/comisionred 5"))
    main.ejecutar_ciclo(config, {})
    assert _avisos_red(enviados) == []

    red["halfHourFee"] = 4
    main.ejecutar_ciclo(config, {})
    main.ejecutar_ciclo(config, {})

    [aviso] = _avisos_red(enviados)
    assert "<b>€0,45</b> · 4 sat/vB" in aviso
    assert "Pedías 5 o menos" in aviso
    assert database.aviso_comisionred(config.database_path) is None


def test_comisionred_sin_aviso_el_ciclo_no_pregunta(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 80000.0})
    monkeypatch.setattr(comisionred, "pedir_ahora", lambda: pytest.fail())

    main.ejecutar_ciclo(config, {})


def test_comisionred_si_mempool_falla_sigue_puesto(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 80000.0})
    _red(monkeypatch, 30)
    main.atender(config, _mensaje("/comisionred 5"))

    def falla():
        raise comisionred.ComisionRedError("mempool.space no contesta")

    monkeypatch.setattr(comisionred, "pedir_ahora", falla)
    main.ejecutar_ciclo(config, {})

    assert _avisos_red(enviados) == []
    assert database.aviso_comisionred(config.database_path) == 5


def test_comisionred_callado_espera_a_que_vuelvas(config, enviados, monkeypatch):
    _precio(monkeypatch, {"bitcoin": 80000.0})
    red = _red(monkeypatch, 30)
    main.atender(config, _mensaje("/comisionred 5"))
    red["halfHourFee"] = 4
    database.silenciar_hasta(
        config.database_path, datetime.now(timezone.utc) + timedelta(hours=1)
    )
    main.ejecutar_ciclo(config, {})
    assert _avisos_red(enviados) == []

    database.silenciar_hasta(config.database_path, None)
    main.ejecutar_ciclo(config, {})

    assert len(_avisos_red(enviados)) == 1


def test_comisionred_no_quita_el_aviso(config, enviados, monkeypatch):
    _red(monkeypatch, 30)
    main.atender(config, _mensaje("/comisionred 5"))

    main.atender(config, _mensaje("/comisionred no"))
    main.atender(config, _mensaje("/comisionred no"))

    assert "ya no te aviso" in enviados[1]
    assert "No tenías ningún aviso" in enviados[2]
    assert database.aviso_comisionred(config.database_path) is None


def test_comisionred_a_secas_recuerda_el_aviso(config, monkeypatch):
    mandados = _con_botones(monkeypatch)
    _red(monkeypatch, 30)
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: {"bitcoin": 80000.0})
    main.atender(config, _mensaje("/comisionred 5"))

    main.atender(config, _mensaje("/comisionred"))

    assert "🔔 Te aviso cuando la de media hora baje a 5 sat/vB" in mandados[-1][0]


# --- /liga ---


def _cerrada(ruta, predicho, real, hace_dias=0):
    """Una predicción ya cerrada, con bitcoin a 100 cuando se hizo."""
    from crypto_tracker.prediccion import Prediccion

    cierre = datetime(2026, 11, 22, 19, 0, tzinfo=timezone.utc) - timedelta(
        days=hace_dias
    )
    p = database.guardar_prediccion(
        ruta,
        Prediccion(
            None, "bitcoin", cierre - timedelta(days=3), cierre, 100.0, predicho
        ),
        "eur",
    )
    database.cerrar_prediccion(ruta, p.id, real)


def _archivo_de(config, chat):
    from crypto_tracker import usuarios

    return usuarios.archivo(config, str(chat))


def test_liga_sin_nada_cerrado(config, enviados):
    main.atender(config, _mensaje("/liga"))

    assert "Todavía no se ha cerrado ninguna predicción" in enviados[0]


def test_liga_entre_el_dueño_y_un_invitado(config, a_quien):
    _con_invitado(config, a_quien)
    _cerrada(config.database_path, 150, 110)  # acierta el lado, lejísimos: 1
    _cerrada(_archivo_de(config, 555), 109, 110)  # clavada: 2

    main.atender(config, _mensaje("/liga"))
    tuya = a_quien[-1]
    main.atender(config, _de(555, "/liga"))
    suya = a_quien[-1]

    assert tuya[0] == "123"
    assert "🥇 <b>Ana</b> · 2 puntos" in tuya[1]
    assert "🥈 <b>El anfitrión</b> 👈 · 1 punto" in tuya[1]
    # El invitado ve la misma tabla, con la marca en su fila.
    assert suya[0] == "555"
    assert "🥇 <b>Ana</b> 👈 · 2 puntos" in suya[1]
    assert "🥈 <b>El anfitrión</b> · 1 punto" in suya[1]


def test_liga_semana_solo_cuenta_el_ultimo_domingo(config, a_quien):
    _con_invitado(config, a_quien)
    _cerrada(config.database_path, 109, 110, hace_dias=7)
    _cerrada(config.database_path, 109, 110, hace_dias=14)
    _cerrada(_archivo_de(config, 555), 150, 110)

    main.atender(config, _mensaje("/liga semana"))

    texto = a_quien[-1][1]
    assert "La jornada del 22/11" in texto
    assert "Ana" in texto
    assert "El anfitrión" not in texto


def test_liga_no_cuenta_a_quien_has_expulsado(config, a_quien):
    _con_invitado(config, a_quien)
    _cerrada(_archivo_de(config, 555), 109, 110)
    main.atender(config, _mensaje("/expulsar 555"))

    main.atender(config, _mensaje("/liga"))

    assert "Todavía no se ha cerrado ninguna predicción" in a_quien[-1][1]


def test_liga_mal_escrita(config, enviados):
    main.atender(config, _mensaje("/liga bitcoin"))

    assert "/liga semana" in enviados[0]


# --- los 👍 y 👎 de los avisos ---


def test_el_aviso_lleva_los_botones_de_votar(config, monkeypatch):
    mandados = _con_botones(monkeypatch)
    _precio(monkeypatch, {"bitcoin": 60000.0})
    _, _ = main.ejecutar_ciclo(config, {})
    estado = database.load_state(config.database_path)
    _precio(monkeypatch, {"bitcoin": 64000.0})  # +6,7% con la regla de %5

    main.ejecutar_ciclo(config, estado)

    _, teclado = mandados[-1]
    votar = [b for fila in teclado for b in fila if b[1].startswith("/voto bitcoin")]
    assert [b[0] for b in votar] == ["👍 Me sirve", "👎 Sobraba"]


def test_pulsar_el_voto_lo_apunta(config, enviados):
    aviso = int(datetime.now(timezone.utc).timestamp())

    main.atender(config, _mensaje(f"/voto bitcoin no {aviso}"))

    assert "👎 Apuntado: el aviso de <b>Bitcoin</b> sobraba." in enviados[0]
    assert "llevas 👍 0 · 👎 1" in enviados[0]
    [v] = database.get_votos(config.database_path)
    assert (v.coin_id, v.util) == ("bitcoin", False)


def test_cambiar_de_opinion_no_cuenta_dos_veces(config, enviados):
    aviso = int(datetime.now(timezone.utc).timestamp())

    main.atender(config, _mensaje(f"/voto bitcoin no {aviso}"))
    main.atender(config, _mensaje(f"/voto bitcoin si {aviso}"))

    assert "llevas 👍 1 · 👎 0" in enviados[1]


def test_voto_escrito_a_mano(config, enviados):
    main.atender(config, _mensaje("/voto bitcoin si"))

    assert "va con los botones 👍 y 👎" in enviados[0]
    assert database.get_votos(config.database_path) == []


def test_ruido_ensena_tus_votos_y_propone_por_ellos(config, enviados):
    # Sube limpio un 6% al día: para el precio no hay ruido.
    for dias, precio in enumerate([142, 142, 142, 134, 126, 119, 112, 106, 100]):
        _precio_de(config, "bitcoin", float(precio), dias * 24 * 60 + 5)
    ahora = int(datetime.now(timezone.utc).timestamp())
    for n in range(4):
        main.atender(config, _mensaje(f"/voto bitcoin no {ahora - n * 86400}"))
    enviados.clear()

    main.atender(config, _mensaje("/ruido bitcoin"))

    assert "Tus votos: 👍 0 · 👎 4" in enviados[0]
    assert "Te sobran la mayoría" in enviados[0]
    assert "<code>/vigilar bitcoin %" in enviados[0]


# --- /juntas ---

# Veinte días yendo a la vez y los diez últimos, por si se quieren separar.
_A_LA_VEZ = [2, -1, 3, -2, 1, -3, 2, 1, -1, 2, -2, 3, -1, 1, 2, -3, 1, -1, 2, -2]
_ULTIMOS = [2, -2, 3, -1, 2, -3, 1, 2, -2, 1]


def _historia(config, coin_id, cambios, precio=100.0):
    """Un precio por día acabando hoy, a partir de los % de cada día."""
    precios = [precio]
    for c in cambios:
        precios.append(precios[-1] * (1 + c / 100))
    for hace, p in enumerate(reversed(precios)):
        _precio_de(config, coin_id, p, hace * 24 * 60 + 1)
    return precios[-1]


@pytest.fixture
def dos(config):
    from dataclasses import replace

    return replace(
        config, watchlist=[Watch("bitcoin", percent=50), Watch("ethereum", percent=50)]
    )


def _avisos_juntas(enviados):
    return [t for t in enviados if "han dejado de ir juntas" in t]


def test_juntas_avisa_una_vez_cuando_se_separan(dos, enviados, monkeypatch):
    btc = _historia(dos, "bitcoin", _A_LA_VEZ)
    eth = _historia(dos, "ethereum", _A_LA_VEZ)
    main.atender(dos, _mensaje("/juntas eth btc"))
    assert "te aviso si <b>bitcoin</b> y <b>ethereum</b> dejan de ir" in enviados[0]
    _precio(monkeypatch, {"bitcoin": btc, "ethereum": eth})
    estado, _ = main.ejecutar_ciclo(dos, {})
    assert _avisos_juntas(enviados) == []

    # Diez días más: bitcoin sigue igual y ethereum hace justo lo contrario.
    btc = _historia(dos, "bitcoin", _ULTIMOS, btc)
    eth = _historia(dos, "ethereum", [-c for c in _ULTIMOS], eth)
    _precio(monkeypatch, {"bitcoin": btc, "ethereum": eth})
    estado, _ = main.ejecutar_ciclo(dos, estado)
    main.ejecutar_ciclo(dos, estado)

    [aviso] = _avisos_juntas(enviados)
    assert "💔 <b>Bitcoin y Ethereum han dejado de ir juntas</b>" in aviso
    assert "/comparar bitcoin ethereum 10d" in aviso
    [pareja] = database.get_juntas(dos.database_path)
    assert pareja.avisada


def test_juntas_de_dos_que_no_van_juntas_no_la_pone(dos, enviados):
    _historia(dos, "bitcoin", _A_LA_VEZ)
    _historia(dos, "ethereum", [-c for c in _A_LA_VEZ])

    main.atender(dos, _mensaje("/juntas btc eth"))

    assert "no van juntas" in enviados[0]
    assert "/correlacion bitcoin ethereum" in enviados[0]
    assert database.get_juntas(dos.database_path) == []


def test_juntas_sin_dias_la_pone_y_lo_dice(dos, enviados):
    main.atender(dos, _mensaje("/juntas btc eth"))

    assert "Aún no tengo días para compararlas" in enviados[0]
    assert len(database.get_juntas(dos.database_path)) == 1


def test_juntas_de_una_que_no_vigilas(config, enviados):
    main.atender(config, _mensaje("/juntas btc sol"))

    assert "No guardo el precio de <b>solana</b>" in enviados[0]
    assert database.get_juntas(config.database_path) == []


def test_juntas_lista_y_quita(dos, enviados):
    main.atender(dos, _mensaje("/juntas btc eth"))
    main.atender(dos, _mensaje("/juntas"))
    main.atender(dos, _mensaje("/juntas eth btc no"))
    main.atender(dos, _mensaje("/juntas"))

    assert "<b>Bitcoin</b> y <b>Ethereum</b>" in enviados[1]
    assert "ya no miro" in enviados[2]
    assert "No vigilas ninguna pareja" in enviados[3]


def test_juntas_mal_escrito(dos, enviados):
    main.atender(dos, _mensaje("/juntas btc"))

    assert "De dos en dos" in enviados[0]


# --- /funding btc avisa ---


def _futuros(monkeypatch, tasa):
    """Binance con la media de la semana a ese %; se puede ir cambiando."""
    estado = {"tasa": tasa, "pedidas": 0}

    def pedir(par):
        estado["pedidas"] += 1
        texto = repr(estado["tasa"] / 100)
        return {"lastFundingRate": texto}, [{"fundingRate": texto}]

    monkeypatch.setattr(funding, "pedir", pedir)
    return estado


def _avisos_funding(enviados):
    return [t for t in enviados if "<b>Funding de BTC:" in t and "No repito" in t]


def _dentro_de(horas):
    return datetime.now(timezone.utc) + timedelta(hours=horas)


def test_funding_avisa_pone_el_aviso(config, enviados, monkeypatch):
    _futuros(monkeypatch, 0.01)

    main.atender(config, _mensaje("/funding btc avisa"))

    assert "te aviso cuando el funding de <b>bitcoin</b>" in enviados[0]
    assert "Ahora: 😐 tranquilo" in enviados[0]
    [v] = database.get_funding(config.database_path)
    assert (v.par, v.coin_id, v.extremo) == ("BTCUSDT", "bitcoin", "")


def test_funding_avisa_una_vez_al_irse_al_extremo(config, enviados, monkeypatch):
    futuros = _futuros(monkeypatch, 0.01)
    main.atender(config, _mensaje("/funding btc avisa"))
    enviados.clear()

    futuros["tasa"] = 0.07
    main.revisar_funding(config, set(), None, _dentro_de(2))
    main.revisar_funding(config, set(), None, _dentro_de(4))

    [aviso] = _avisos_funding(enviados)
    assert "🔥 <b>Funding de BTC: muy apalancado al alza</b>" in aviso
    assert "<b>+0,0700%</b>" in aviso


def test_funding_vuelve_a_avisar_si_se_calma_y_repite(config, enviados, monkeypatch):
    futuros = _futuros(monkeypatch, 0.01)
    main.atender(config, _mensaje("/funding btc avisa"))
    enviados.clear()

    for horas, tasa in ((2, 0.07), (4, 0.01), (6, -0.02)):
        futuros["tasa"] = tasa
        main.revisar_funding(config, set(), None, _dentro_de(horas))

    assert len(_avisos_funding(enviados)) == 2
    assert "😱" in enviados[-1]


def test_funding_no_pregunta_a_binance_en_cada_ciclo(config, enviados, monkeypatch):
    futuros = _futuros(monkeypatch, 0.01)
    _precio(monkeypatch, {"bitcoin": 60000.0})
    main.atender(config, _mensaje("/funding btc avisa"))
    antes = futuros["pedidas"]

    main.ejecutar_ciclo(config, {})
    main.ejecutar_ciclo(config, {})

    # Se miró al ponerlo: hasta dentro de una hora no toca.
    assert futuros["pedidas"] == antes


def test_funding_si_ya_estaba_en_el_extremo_no_avisa_de_eso(
    config, enviados, monkeypatch
):
    _futuros(monkeypatch, 0.07)
    main.atender(config, _mensaje("/funding btc avisa"))
    enviados.clear()

    main.revisar_funding(config, set(), None, _dentro_de(2))

    assert enviados == []


def test_funding_si_binance_falla_sigue_puesto(config, enviados, monkeypatch):
    _futuros(monkeypatch, 0.01)
    main.atender(config, _mensaje("/funding btc avisa"))
    enviados.clear()

    def falla(par):
        raise funding.FundingError("Binance no contesta")

    monkeypatch.setattr(funding, "pedir", falla)
    main.revisar_funding(config, set(), None, _dentro_de(2))

    assert enviados == []
    assert len(database.get_funding(config.database_path)) == 1


def test_funding_callada_no_avisa(config, enviados, monkeypatch):
    futuros = _futuros(monkeypatch, 0.01)
    main.atender(config, _mensaje("/funding btc avisa"))
    enviados.clear()
    futuros["tasa"] = 0.07

    main.revisar_funding(config, {"bitcoin"}, None, _dentro_de(2))
    assert enviados == []

    main.revisar_funding(config, set(), None, _dentro_de(2))
    assert len(_avisos_funding(enviados)) == 1


def test_funding_no_quita_el_aviso(config, enviados, monkeypatch):
    _futuros(monkeypatch, 0.01)
    main.atender(config, _mensaje("/funding btc avisa"))

    main.atender(config, _mensaje("/funding btc no"))
    main.atender(config, _mensaje("/funding btc no"))

    assert "ya no te aviso del funding de bitcoin" in enviados[1]
    assert "No tenías ese aviso" in enviados[2]
    assert database.get_funding(config.database_path) == []


def test_funding_normal_recuerda_el_aviso(config, monkeypatch):
    mandados = _con_botones(monkeypatch)
    _futuros(monkeypatch, 0.01)
    main.atender(config, _mensaje("/funding btc avisa"))

    main.atender(config, _mensaje("/funding btc"))

    assert "🔔 Te aviso si se va a un extremo" in mandados[-1][0]


# --- /encuesta ---


@pytest.fixture
def encuestas(monkeypatch):
    """Las encuestas que se mandarían: (chat, pregunta, opciones, cierre)."""
    lista = []

    def enviar(token, chat, pregunta, opciones, cierre, sin_sonido=False):
        lista.append((str(chat), pregunta, opciones, cierre))
        return f"poll-{len(lista)}"

    monkeypatch.setattr(telegram, "enviar_encuesta", enviar)
    return lista


def _voto(poll_id, opciones, usuario=123):
    return {"poll_id": poll_id, "user": {"id": usuario}, "option_ids": opciones}


def _guardada(config):
    from crypto_tracker import encuesta

    return encuesta.de_texto(database.encuesta(config.database_path))


def test_encuesta_manda_la_primera_sin_gastar_consultas(
    config, enviados, encuestas, monkeypatch
):
    monkeypatch.setattr(coingecko, "get_prices", lambda *a, **k: pytest.fail())
    database.save_prices(config.database_path, {"bitcoin": 80000.0}, "eur")

    main.atender(config, _mensaje("/encuesta"))

    [(chat, pregunta, opciones, cierre)] = encuestas
    assert chat == "123"
    assert "¿Dónde estará Bitcoin el domingo" in pregunta
    assert opciones[2] == "↗️ Entre €80.000,00 y €84.000,00"
    guardada = _guardada(config)
    assert (guardada.poll_id, guardada.entonces) == ("poll-1", 80000.0)
    # Se cierra sola un día antes del domingo.
    assert cierre == int((guardada.cierre - timedelta(hours=24)).timestamp())
    assert "Cada lunes te mando la de esa semana" in enviados[0]


def test_encuesta_sin_precios_no_la_pone(config, enviados, encuestas):
    main.atender(config, _mensaje("/encuesta"))

    assert encuestas == []
    assert "no tengo precios" in enviados[0]
    assert database.encuesta(config.database_path) is None


def test_encuesta_si_telegram_no_la_manda_no_queda_puesta(
    config, enviados, monkeypatch
):
    database.save_prices(config.database_path, {"bitcoin": 80000.0}, "eur")
    monkeypatch.setattr(telegram, "enviar_encuesta", lambda *a, **k: None)

    main.atender(config, _mensaje("/encuesta"))

    assert "No he podido mandarte la encuesta" in enviados[0]
    assert database.encuesta(config.database_path) is None


def test_encuesta_dos_veces_no_manda_otra(config, enviados, encuestas):
    database.save_prices(config.database_path, {"bitcoin": 80000.0}, "eur")

    main.atender(config, _mensaje("/encuesta"))
    main.atender(config, _mensaje("/encuesta"))

    assert len(encuestas) == 1
    assert "Ya la tienes puesta" in enviados[1]


def test_votar_lo_apunta_como_prediccion(config, enviados, encuestas):
    database.save_prices(config.database_path, {"bitcoin": 80000.0}, "eur")
    main.atender(config, _mensaje("/encuesta"))
    enviados.clear()

    main.atender_voto(config, _voto("poll-1", [3]))

    [p] = database.get_predicciones(config.database_path, "eur")
    assert (p.coin_id, p.entonces, p.predicho) == ("bitcoin", 80000.0, 86000.0)
    assert p.cierre == _guardada(config).cierre
    assert "<b>Bitcoin</b> por encima de €84.000,00" in enviados[0]
    assert "Lo cuento como <b>€86.000,00</b>" in enviados[0]


def test_cambiar_el_voto_cambia_la_prediccion(config, enviados, encuestas):
    database.save_prices(config.database_path, {"bitcoin": 80000.0}, "eur")
    main.atender(config, _mensaje("/encuesta"))

    main.atender_voto(config, _voto("poll-1", [3]))
    main.atender_voto(config, _voto("poll-1", [1]))

    [p] = database.get_predicciones(config.database_path, "eur")
    assert p.predicho == pytest.approx(78000.0)


def test_retirar_el_voto_quita_la_prediccion(config, enviados, encuestas):
    database.save_prices(config.database_path, {"bitcoin": 80000.0}, "eur")
    main.atender(config, _mensaje("/encuesta"))
    main.atender_voto(config, _voto("poll-1", [2]))

    main.atender_voto(config, _voto("poll-1", []))

    assert database.get_predicciones(config.database_path, "eur") == []
    assert "quitada tu predicción" in enviados[-1]


def test_un_voto_en_una_encuesta_vieja_no_cuenta(config, enviados, encuestas):
    database.save_prices(config.database_path, {"bitcoin": 80000.0}, "eur")
    main.atender(config, _mensaje("/encuesta"))
    enviados.clear()

    main.atender_voto(config, _voto("otra", [2]))

    assert enviados == []
    assert database.get_predicciones(config.database_path, "eur") == []


def test_un_voto_de_un_desconocido_no_cuenta(config, enviados, encuestas):
    database.save_prices(config.database_path, {"bitcoin": 80000.0}, "eur")
    main.atender(config, _mensaje("/encuesta"))
    enviados.clear()

    main.atender_voto(config, _voto("poll-1", [2], usuario=999))

    assert enviados == []
    assert database.get_predicciones(config.database_path, "eur") == []


def test_un_voto_fuera_de_plazo_no_cuenta(config, enviados, encuestas):
    from crypto_tracker.respuestas import recordatorios

    database.save_prices(config.database_path, {"bitcoin": 80000.0}, "eur")
    main.atender(config, _mensaje("/encuesta"))
    enviados.clear()
    tarde = _guardada(config).cierre - timedelta(hours=1)

    recordatorios.voto_encuesta(config, "poll-1", [2], tarde)

    assert enviados == []
    assert database.get_predicciones(config.database_path, "eur") == []


def test_el_voto_del_invitado_va_a_su_archivo(config, a_quien, encuestas):
    _con_invitado(config, a_quien)
    main.atender(config, _de(555, "/vigilar solana %5"))
    database.save_prices(_archivo_de(config, 555), {"solana": 200.0}, "eur")
    main.atender(config, _de(555, "/encuesta"))

    main.atender_voto(config, _voto("poll-1", [2], usuario=555))

    assert encuestas[0][0] == "555"
    assert database.get_predicciones(config.database_path, "eur") == []
    [p] = database.get_predicciones(_archivo_de(config, 555), "eur")
    assert (p.coin_id, p.predicho) == ("solana", pytest.approx(205.0))
    assert a_quien[-1][0] == "555"


def test_la_encuesta_de_cada_semana_sale_el_lunes(config, enviados, encuestas):
    database.save_prices(config.database_path, {"bitcoin": 80000.0}, "eur")
    main.atender(config, _mensaje("/encuesta"))
    primera = _guardada(config).cierre
    # El lunes de después de ese domingo, a las diez.
    lunes = (primera + timedelta(days=1)).astimezone().replace(hour=10, minute=0)

    main.encuesta_semanal(config, lunes - timedelta(days=3))  # el viernes, nada
    assert len(encuestas) == 1
    main.encuesta_semanal(config, lunes)
    main.encuesta_semanal(config, lunes + timedelta(hours=1))

    assert len(encuestas) == 2
    assert _guardada(config).cierre == primera + timedelta(days=7)
    assert _guardada(config).poll_id == "poll-2"


def test_sin_encuesta_puesta_el_lunes_no_manda_nada(config, encuestas):
    database.save_prices(config.database_path, {"bitcoin": 80000.0}, "eur")
    lunes = datetime(2026, 11, 23, 10, 0).astimezone()

    main.encuesta_semanal(config, lunes)

    assert encuestas == []


def test_encuesta_no_la_quita(config, enviados, encuestas):
    database.save_prices(config.database_path, {"bitcoin": 80000.0}, "eur")
    main.atender(config, _mensaje("/encuesta"))
    primera = _guardada(config).cierre
    lunes = (primera + timedelta(days=1)).astimezone().replace(hour=10, minute=0)

    main.atender(config, _mensaje("/encuesta no"))
    main.atender(config, _mensaje("/encuesta no"))
    main.encuesta_semanal(config, lunes)

    assert "ya no te mando la encuesta" in enviados[1]
    assert "No la tenías puesta" in enviados[2]
    assert len(encuestas) == 1


def test_el_bucle_reparte_los_votos(config, monkeypatch):
    votos = []
    monkeypatch.setattr(main, "atender_voto", lambda c, v: votos.append(v))
    tandas = [[{"update_id": 7, "poll_answer": _voto("poll-1", [0])}]]
    monkeypatch.setattr(
        telegram, "get_updates", lambda t, o, e: tandas.pop() if tandas else []
    )
    # El reloj da un salto tras la primera tanda, para que la espera se acabe.
    reloj = iter([0.0, 0.0, 99.0])
    monkeypatch.setattr(main.time, "monotonic", lambda: next(reloj, 99.0))

    offset = main.esperar_escuchando(config, 10, None)

    assert offset == 8
    assert votos == [_voto("poll-1", [0])]
