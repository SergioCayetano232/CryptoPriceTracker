"""Tests del envio a Telegram, sin llamar a la API de verdad."""

import json

import pytest
import requests

from crypto_tracker.nucleo import telegram


class RespuestaFalsa:
    def __init__(self, status=200, data=None):
        self.status_code = status
        self._data = data if data is not None else {"ok": True}

    def json(self):
        return self._data


@pytest.fixture(autouse=True)
def sin_esperas(monkeypatch):
    esperas = []
    monkeypatch.setattr(telegram.time, "sleep", esperas.append)
    return esperas


def _en_orden(*respuestas):
    """requests.post falso que va dando estas respuestas (o lanzándolas)."""
    pendientes = list(respuestas)
    llamadas = []

    def post(*a, **k):
        llamadas.append(1)
        r = pendientes.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    post.llamadas = llamadas
    return post


def test_envio_correcto(monkeypatch):
    monkeypatch.setattr(requests, "post", lambda *a, **k: RespuestaFalsa())

    assert telegram.send_message("token", "123", "hola") is True


def test_mensaje_vacio_no_se_envia(monkeypatch):
    def no_llamar(*a, **k):
        raise AssertionError("no deberia llamar a la API")

    monkeypatch.setattr(requests, "post", no_llamar)

    assert telegram.send_message("token", "123", "   ") is False


def test_telegram_rechaza(monkeypatch):
    respuesta = RespuestaFalsa(400, {"ok": False, "description": "chat not found"})
    monkeypatch.setattr(requests, "post", lambda *a, **k: respuesta)

    assert telegram.send_message("token", "123", "hola") is False


def test_sin_conexion(monkeypatch):
    def falla(*a, **k):
        raise requests.ConnectionError()

    monkeypatch.setattr(requests, "post", falla)

    assert telegram.send_message("token", "123", "hola") is False


def test_timeout(monkeypatch):
    def falla(*a, **k):
        raise requests.Timeout()

    monkeypatch.setattr(requests, "post", falla)

    assert telegram.send_message("token", "123", "hola") is False


def test_mensaje_largo_se_corta(monkeypatch):
    enviado = {}

    def capturar(url, json=None, timeout=None):
        enviado.update(json)
        return RespuestaFalsa()

    monkeypatch.setattr(requests, "post", capturar)
    telegram.send_message("token", "123", "x" * 5000)

    assert len(enviado["text"]) <= telegram.MAX_LENGTH


def test_escape():
    assert telegram.escape("<b>hola</b>") == "&lt;b&gt;hola&lt;/b&gt;"


# --- leer mensajes ---


def test_leer_mensajes(monkeypatch):
    mensajes = [{"update_id": 7, "message": {"text": "/status"}}]
    pedido = {}

    def get(url, params=None, timeout=None):
        pedido.update(params)
        return RespuestaFalsa(data={"ok": True, "result": mensajes})

    monkeypatch.setattr(requests, "get", get)

    assert telegram.get_updates("token", 5, 30) == mensajes
    assert pedido["offset"] == 5
    assert pedido["timeout"] == 30


def test_leer_mensajes_la_primera_vez_sin_offset(monkeypatch):
    pedido = {}

    def get(url, params=None, timeout=None):
        pedido.update(params)
        return RespuestaFalsa(data={"ok": True, "result": []})

    monkeypatch.setattr(requests, "get", get)
    telegram.get_updates("token", None, 30)

    assert "offset" not in pedido


def test_leer_mensajes_sin_conexion(monkeypatch):
    def falla(*a, **k):
        raise requests.ConnectionError()

    monkeypatch.setattr(requests, "get", falla)

    with pytest.raises(telegram.TelegramError):
        telegram.get_updates("token", None, 30)


def test_otro_programa_leyendo_lo_dice_claro(monkeypatch):
    respuesta = RespuestaFalsa(409, {"ok": False, "description": "Conflict"})
    monkeypatch.setattr(requests, "get", lambda *a, **k: respuesta)

    with pytest.raises(telegram.TelegramError, match="otro programa"):
        telegram.get_updates("token", None, 30)


def test_menu_de_comandos(monkeypatch):
    enviado = {}

    def capturar(url, json=None, timeout=None):
        enviado.update(json)
        return RespuestaFalsa()

    monkeypatch.setattr(requests, "post", capturar)

    assert telegram.set_commands("token", {"status": "Como van"}) is True
    assert enviado["commands"] == [{"command": "status", "description": "Como van"}]


def test_sin_sonido(monkeypatch):
    enviado = {}

    def capturar(url, json=None, timeout=None):
        enviado.update(json)
        return RespuestaFalsa()

    monkeypatch.setattr(requests, "post", capturar)

    telegram.send_message("token", "123", "hola")
    assert enviado["disable_notification"] is False

    telegram.send_message("token", "123", "hola", sin_sonido=True)
    assert enviado["disable_notification"] is True


# --- imagenes ---


def test_mandar_imagen(monkeypatch):
    enviado = {}

    def capturar(url, data=None, files=None, timeout=None):
        enviado.update(url=url, data=data, files=files)
        return RespuestaFalsa()

    monkeypatch.setattr(requests, "post", capturar)

    assert telegram.send_photo("token", "123", b"\x89PNG...", "pie") is True
    assert enviado["url"].endswith("/sendPhoto")
    assert enviado["data"]["caption"] == "pie"
    assert enviado["files"]["photo"][1] == b"\x89PNG..."


def test_imagen_rechazada(monkeypatch):
    respuesta = RespuestaFalsa(400, {"ok": False, "description": "bad photo"})
    monkeypatch.setattr(requests, "post", lambda *a, **k: respuesta)

    assert telegram.send_photo("token", "123", b"x") is False


def test_pie_largo_se_corta(monkeypatch):
    enviado = {}

    def capturar(url, data=None, files=None, timeout=None):
        enviado.update(data)
        return RespuestaFalsa()

    monkeypatch.setattr(requests, "post", capturar)
    telegram.send_photo("token", "123", b"x", "y" * 3000)

    assert len(enviado["caption"]) <= telegram.MAX_CAPTION


# --- archivos ---


def test_mandar_archivo(monkeypatch):
    enviado = {}

    def capturar(url, data=None, files=None, timeout=None):
        enviado.update(url=url, data=data, files=files)
        return RespuestaFalsa()

    monkeypatch.setattr(requests, "post", capturar)

    assert telegram.send_document("token", "123", b"a;b", "x.csv", "pie") is True
    assert enviado["url"].endswith("/sendDocument")
    assert enviado["files"]["document"] == ("x.csv", b"a;b", "text/csv")
    assert enviado["data"]["caption"] == "pie"


@pytest.mark.parametrize(
    "nombre, tipo",
    [("informe-2025.pdf", "application/pdf"), ("copia.zip", "application/zip")],
)
def test_el_tipo_del_archivo_sale_del_nombre(monkeypatch, nombre, tipo):
    enviado = {}

    def capturar(url, data=None, files=None, timeout=None):
        enviado.update(files=files)
        return RespuestaFalsa()

    monkeypatch.setattr(requests, "post", capturar)

    assert telegram.send_document("token", "123", b"x", nombre)
    assert enviado["files"]["document"][2] == tipo


def test_archivo_rechazado(monkeypatch):
    respuesta = RespuestaFalsa(400, {"ok": False, "description": "too big"})
    monkeypatch.setattr(requests, "post", lambda *a, **k: respuesta)

    assert telegram.send_document("token", "123", b"x", "x.csv") is False


# --- cortar sin romper el html ---


def _etiquetas_cerradas(texto):
    return all(
        texto.count(f"<{t}>") + texto.count(f"<{t} ") == texto.count(f"</{t}>")
        for t in ("b", "i", "code", "a")
    )


def test_lo_largo_llega_entero_en_varios(monkeypatch):
    from crypto_tracker.alerts import Alert, con_fuente, formatear_varios

    enviados = []

    def capturar(url, json=None, timeout=None):
        enviados.append(json["text"])
        return RespuestaFalsa()

    monkeypatch.setattr(requests, "post", capturar)
    # un mensaje de avisos de verdad, pero enorme
    muchos = [Alert(f"cripto-{i}", 1234.56, 1200.0, "alto") for i in range(200)]
    texto = con_fuente(formatear_varios(muchos, "eur"))
    assert len(texto) > telegram.MAX_LENGTH

    assert telegram.send_message("token", "123", texto) is True

    assert len(enviados) > 1
    for trozo in enviados:
        assert len(trozo) <= telegram.MAX_LENGTH
        assert _etiquetas_cerradas(trozo)
    junto = "\n".join(enviados)
    assert "[...cortado]" not in junto
    assert all(f"Cripto {i}" in junto for i in (0, 100, 199))


def test_mas_de_cinco_trozos_se_corta(monkeypatch):
    enviados = []

    def capturar(url, json=None, timeout=None):
        enviados.append(json["text"])
        return RespuestaFalsa()

    monkeypatch.setattr(requests, "post", capturar)
    enorme = "\n".join(f"<b>Linea {i}</b> con algo de texto" for i in range(5000))

    telegram.send_message("token", "123", enorme)

    assert len(enviados) == telegram.MAX_TROZOS
    assert enviados[-1].endswith("[...cortado]")


def test_los_botones_van_en_el_ultimo(monkeypatch):
    enviados = []

    def capturar(url, json=None, timeout=None):
        enviados.append(json)
        return RespuestaFalsa()

    monkeypatch.setattr(requests, "post", capturar)
    largo = "\n".join("una linea cualquiera" for _ in range(400))

    telegram.send_message("token", "123", largo, botones=[[("Vale", "/ok")]])

    assert len(enviados) > 1
    assert all("reply_markup" not in e for e in enviados[:-1])
    assert "reply_markup" in enviados[-1]


def test_si_falla_un_trozo_para(monkeypatch):
    enviados = []

    def capturar(url, json=None, timeout=None):
        enviados.append(json)
        return RespuestaFalsa(400, {"ok": False, "description": "Bad Request"})

    monkeypatch.setattr(requests, "post", capturar)
    largo = "\n".join("una linea cualquiera" for _ in range(400))

    assert telegram.send_message("token", "123", largo) is False
    assert len(enviados) == 1


def test_partir_corta_por_saltos_de_linea():
    assert telegram._partir("aaa\nbbb\nccc", 8, 5) == ["aaa\nbbb", "ccc"]
    assert telegram._partir("corto", 100, 5) == ["corto"]


def test_corte_del_pie_de_foto(monkeypatch):
    enviado = {}

    def capturar(url, data=None, files=None, timeout=None):
        enviado.update(data)
        return RespuestaFalsa()

    monkeypatch.setattr(requests, "post", capturar)
    pie = "\n".join(f"<b>Linea {i}</b> con algo de texto" for i in range(100))

    telegram.send_photo("token", "123", b"x", pie)

    assert len(enviado["caption"]) <= telegram.MAX_CAPTION
    assert _etiquetas_cerradas(enviado["caption"])


def test_lo_corto_no_se_toca():
    assert telegram._recortar("<b>hola</b>\nadios", 100) == "<b>hola</b>\nadios"


# --- botones ---


def test_mensaje_con_botones(monkeypatch):
    enviado = {}

    def capturar(url, json=None, timeout=None):
        enviado.update(json)
        return RespuestaFalsa()

    monkeypatch.setattr(requests, "post", capturar)
    botones = [[("📈 Gráfica", "/historico bitcoin")], [("🔕 Callar", "/mute 1h")]]
    telegram.send_message("token", "123", "hola", botones=botones)

    assert enviado["reply_markup"] == {
        "inline_keyboard": [
            [{"text": "📈 Gráfica", "callback_data": "/historico bitcoin"}],
            [{"text": "🔕 Callar", "callback_data": "/mute 1h"}],
        ]
    }


def test_boton_con_https_abre_la_web_en_telegram(monkeypatch):
    enviado = {}

    def capturar(url, json=None, timeout=None):
        enviado.update(json)
        return RespuestaFalsa()

    monkeypatch.setattr(requests, "post", capturar)
    botones = [[("Abrir el panel", "https://mi-panel.example/app")]]
    telegram.send_message("token", "123", "hola", botones=botones)

    assert enviado["reply_markup"]["inline_keyboard"] == [
        [{"text": "Abrir el panel", "web_app": {"url": "https://mi-panel.example/app"}}]
    ]


def test_mensaje_sin_botones_como_antes(monkeypatch):
    enviado = {}

    def capturar(url, json=None, timeout=None):
        enviado.update(json)
        return RespuestaFalsa()

    monkeypatch.setattr(requests, "post", capturar)
    telegram.send_message("token", "123", "hola")

    assert "reply_markup" not in enviado


def test_pide_tambien_los_botones_pulsados(monkeypatch):
    pedido = {}

    def get(url, params=None, timeout=None):
        pedido.update(params)
        return RespuestaFalsa(data={"ok": True, "result": []})

    monkeypatch.setattr(requests, "get", get)
    telegram.get_updates("token", None, 30)

    assert "callback_query" in pedido["allowed_updates"]
    assert "inline_query" in pedido["allowed_updates"]
    assert "poll_answer" in pedido["allowed_updates"]


def test_contestar_un_boton(monkeypatch):
    enviado = {}

    def capturar(url, json=None, timeout=None):
        enviado.update(json)
        return RespuestaFalsa()

    monkeypatch.setattr(requests, "post", capturar)

    assert telegram.answer_callback("token", "abc") is True
    assert enviado == {"callback_query_id": "abc"}


def test_contestar_un_boton_sin_conexion(monkeypatch):
    def falla(*a, **k):
        raise requests.ConnectionError()

    monkeypatch.setattr(requests, "post", falla)

    assert telegram.answer_callback("token", "abc") is False


def test_imagen_con_botones(monkeypatch):
    enviado = {}

    def capturar(url, data=None, files=None, timeout=None):
        enviado.update(data)
        return RespuestaFalsa()

    monkeypatch.setattr(requests, "post", capturar)
    telegram.send_photo("token", "123", b"x", botones=[[("🔄 Actualizar", "/status")]])

    # Va en un formulario, asi que el teclado viaja como texto JSON.
    assert json.loads(enviado["reply_markup"]) == {
        "inline_keyboard": [[{"text": "🔄 Actualizar", "callback_data": "/status"}]]
    }


def test_imagen_sin_botones_como_antes(monkeypatch):
    enviado = {}

    def capturar(url, data=None, files=None, timeout=None):
        enviado.update(data)
        return RespuestaFalsa()

    monkeypatch.setattr(requests, "post", capturar)
    telegram.send_photo("token", "123", b"x")

    assert "reply_markup" not in enviado


def test_corte_de_red_se_reintenta(monkeypatch, sin_esperas):
    post = _en_orden(requests.ConnectionError(), RespuestaFalsa())
    monkeypatch.setattr(requests, "post", post)

    assert telegram.send_message("token", "123", "hola") is True
    assert len(post.llamadas) == 2
    assert sin_esperas == [2]


def test_se_rinde_tras_tres_intentos(monkeypatch, sin_esperas):
    post = _en_orden(*[requests.Timeout() for _ in range(3)])
    monkeypatch.setattr(requests, "post", post)

    assert telegram.send_message("token", "123", "hola") is False
    assert len(post.llamadas) == 3
    assert sin_esperas == [2, 4]


def test_error_suyo_se_reintenta(monkeypatch):
    caido = RespuestaFalsa(502, {"ok": False, "description": "Bad Gateway"})
    post = _en_orden(caido, RespuestaFalsa())
    monkeypatch.setattr(requests, "post", post)

    assert telegram.send_message("token", "123", "hola") is True


def test_chat_mal_puesto_no_insiste(monkeypatch, sin_esperas):
    malo = RespuestaFalsa(400, {"ok": False, "description": "chat not found"})
    post = _en_orden(malo)
    monkeypatch.setattr(requests, "post", post)

    assert telegram.send_message("token", "123", "hola") is False
    assert len(post.llamadas) == 1
    assert sin_esperas == []


def test_429_espera_lo_que_pide(monkeypatch, sin_esperas):
    frenado = RespuestaFalsa(
        429,
        {
            "ok": False,
            "description": "Too Many Requests",
            "parameters": {"retry_after": 7},
        },
    )
    monkeypatch.setattr(requests, "post", _en_orden(frenado, RespuestaFalsa()))

    assert telegram.send_message("token", "123", "hola") is True
    assert sin_esperas == [7]


def test_429_con_espera_larga_lo_deja(monkeypatch, sin_esperas):
    frenado = RespuestaFalsa(
        429,
        {
            "ok": False,
            "description": "Too Many Requests",
            "parameters": {"retry_after": 300},
        },
    )
    post = _en_orden(frenado)
    monkeypatch.setattr(requests, "post", post)

    assert telegram.send_message("token", "123", "hola") is False
    assert len(post.llamadas) == 1
    assert sin_esperas == []


# --- bajar archivos ---


class ArchivoFalso:
    def __init__(self, status=200, contenido=b""):
        self.status_code = status
        self.content = contenido


def test_descargar_un_archivo(monkeypatch):
    pedidos = []

    def capturar(url, params=None, timeout=None):
        pedidos.append(url)
        if "getFile" in url:
            return RespuestaFalsa(data={"ok": True, "result": {"file_path": "d/a.csv"}})
        return ArchivoFalso(contenido=b"hola")

    monkeypatch.setattr(requests, "get", capturar)

    assert telegram.descargar("token", "abc") == b"hola"
    assert pedidos[1] == "https://api.telegram.org/file/bottoken/d/a.csv"


@pytest.mark.parametrize(
    "respuesta",
    [
        RespuestaFalsa(data={"ok": False, "description": "file is too big"}),
        RespuestaFalsa(data={"ok": True, "result": {}}),
    ],
)
def test_descargar_si_telegram_no_lo_da(monkeypatch, respuesta):
    monkeypatch.setattr(requests, "get", lambda *a, **k: respuesta)

    assert telegram.descargar("token", "abc") is None


def test_descargar_sin_red(monkeypatch):
    def sin_red(*a, **k):
        raise requests.ConnectionError()

    monkeypatch.setattr(requests, "get", sin_red)

    assert telegram.descargar("token", "abc") is None


def test_contesta_la_consulta_inline(monkeypatch):
    from crypto_tracker.nucleo.inline import tarjeta

    pedidos = []
    monkeypatch.setattr(
        requests,
        "post",
        lambda url, json, **k: pedidos.append((url, json)) or RespuestaFalsa(),
    )

    ok = telegram.answer_inline("T", "q1", [tarjeta("bitcoin", 63000, 1, "eur")], 30)

    url, payload = pedidos[0]
    assert ok
    assert url.endswith("/answerInlineQuery")
    assert payload["inline_query_id"] == "q1"
    assert payload["cache_time"] == 30
    assert payload["is_personal"] is True
    resultado = payload["results"][0]
    assert resultado["type"] == "article"
    assert resultado["id"] == "bitcoin"
    assert resultado["input_message_content"]["parse_mode"] == "HTML"


def _apuntando(monkeypatch, respuesta=None):
    pedidos = []
    monkeypatch.setattr(
        requests,
        "post",
        lambda url, json, **k: (
            pedidos.append((url, json)) or (respuesta or RespuestaFalsa())
        ),
    )
    return pedidos


def test_enviar_con_id_devuelve_el_del_mensaje(monkeypatch):
    dada = RespuestaFalsa(data={"ok": True, "result": {"message_id": 77}})
    pedidos = _apuntando(monkeypatch, dada)

    assert telegram.enviar_con_id("T", "123", "hola") == 77
    url, payload = pedidos[0]
    assert url.endswith("/sendMessage")
    assert payload["disable_notification"] is True


def test_enviar_con_id_sin_red(monkeypatch):
    def sin_red(*a, **k):
        raise requests.ConnectionError()

    monkeypatch.setattr(requests, "post", sin_red)

    assert telegram.enviar_con_id("T", "123", "hola") is None


def test_editar_mensaje(monkeypatch):
    pedidos = _apuntando(monkeypatch)

    assert telegram.editar_mensaje("T", "123", 77, "nuevo") is None
    url, payload = pedidos[0]
    assert url.endswith("/editMessageText")
    assert payload["message_id"] == 77
    assert payload["text"] == "nuevo"


def test_editar_sin_cambios_no_es_un_fallo(monkeypatch):
    igual = {
        "ok": False,
        "description": "Bad Request: message is not modified: specified new "
        "message content and reply markup are exactly the same",
    }
    _apuntando(monkeypatch, RespuestaFalsa(400, igual))

    assert telegram.editar_mensaje("T", "123", 77, "igual") is None


def test_editar_uno_borrado_dice_el_error(monkeypatch):
    borrado = {"ok": False, "description": "Bad Request: message to edit not found"}
    _apuntando(monkeypatch, RespuestaFalsa(400, borrado))

    assert "message to edit not found" in telegram.editar_mensaje("T", "1", 77, "x")


def test_editar_sin_red_da_error_vacio(monkeypatch):
    def sin_red(*a, **k):
        raise requests.Timeout()

    monkeypatch.setattr(requests, "post", sin_red)

    assert telegram.editar_mensaje("T", "123", 77, "x") == ""


def test_fijar_no_avisa(monkeypatch):
    pedidos = _apuntando(monkeypatch)

    assert telegram.fijar("T", "123", 77)
    url, payload = pedidos[0]
    assert url.endswith("/pinChatMessage")
    assert payload["disable_notification"] is True


def test_borrar_y_desfijar(monkeypatch):
    pedidos = _apuntando(monkeypatch)

    assert telegram.borrar_mensaje("T", "123", 77)
    assert telegram.desfijar("T", "123", 77)
    assert [url.rsplit("/", 1)[1] for url, _ in pedidos] == [
        "deleteMessage",
        "unpinChatMessage",
    ]


def test_no_deja_borrar_uno_viejo(monkeypatch):
    viejo = {"ok": False, "description": "Bad Request: message can't be deleted"}
    _apuntando(monkeypatch, RespuestaFalsa(400, viejo))

    assert not telegram.borrar_mensaje("T", "123", 77)


def test_enviar_encuesta_devuelve_su_id(monkeypatch):
    dada = RespuestaFalsa(data={"ok": True, "result": {"poll": {"id": "777"}}})
    pedidos = _apuntando(monkeypatch, dada)

    numero = telegram.enviar_encuesta("T", "123", "¿Sube?", ["Sí", "No"], 1795000000)

    url, payload = pedidos[0]
    assert numero == "777"
    assert url.endswith("/sendPoll")
    assert payload["options"] == [{"text": "Sí"}, {"text": "No"}]
    # Anónima no llegarían los votos.
    assert payload["is_anonymous"] is False
    assert payload["close_date"] == 1795000000


def test_enviar_encuesta_rechazada(monkeypatch):
    mal = {"ok": False, "description": "Bad Request: POLL_OPTION_INVALID"}
    _apuntando(monkeypatch, RespuestaFalsa(400, mal))

    assert telegram.enviar_encuesta("T", "123", "¿Sube?", ["Sí", "No"], 1) is None


def test_enviar_encuesta_sin_el_id_en_la_respuesta(monkeypatch):
    _apuntando(monkeypatch, RespuestaFalsa(data={"ok": True, "result": {}}))

    assert telegram.enviar_encuesta("T", "123", "¿Sube?", ["Sí", "No"], 1) is None
