"""Tests del envio a Telegram, sin llamar a la API de verdad."""

import json

import pytest
import requests

from crypto_tracker import telegram


class RespuestaFalsa:
    def __init__(self, status=200, data=None):
        self.status_code = status
        self._data = data if data is not None else {"ok": True}

    def json(self):
        return self._data


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


def test_corte_no_deja_etiquetas_abiertas(monkeypatch):
    from crypto_tracker.alerts import Alert, con_fuente, formatear_varios

    enviado = {}

    def capturar(url, json=None, timeout=None):
        enviado.update(json)
        return RespuestaFalsa()

    monkeypatch.setattr(requests, "post", capturar)
    # un mensaje de avisos de verdad, pero enorme
    muchos = [Alert(f"cripto-{i}", 1234.56, 1200.0, "alto") for i in range(200)]
    texto = con_fuente(formatear_varios(muchos, "eur"))
    assert len(texto) > telegram.MAX_LENGTH

    telegram.send_message("token", "123", texto)

    assert len(enviado["text"]) <= telegram.MAX_LENGTH
    assert enviado["text"].endswith("[...cortado]")
    assert _etiquetas_cerradas(enviado["text"])


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
