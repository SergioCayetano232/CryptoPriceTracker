"""Tests del envio a Telegram, sin llamar a la API de verdad."""

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
