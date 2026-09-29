"""Tests del envio a Telegram, sin llamar a la API de verdad."""

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
