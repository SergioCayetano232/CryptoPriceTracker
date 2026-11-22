"""Tests del latido a un servicio de fuera."""

import requests

from crypto_tracker import latido


class Respuesta:
    def __init__(self, status=200):
        self.status_code = status


def test_da_el_toque_a_la_url(monkeypatch):
    pedidas = []
    monkeypatch.setattr(
        requests, "get", lambda url, **k: pedidas.append((url, k)) or Respuesta()
    )

    assert latido.mandar("https://hc-ping.com/abc")
    assert pedidas == [("https://hc-ping.com/abc", {"timeout": latido.TIMEOUT})]


def test_sin_red_no_revienta(monkeypatch):
    def sin_red(*a, **k):
        raise requests.ConnectionError("https://hc-ping.com/abc")

    monkeypatch.setattr(requests, "get", sin_red)

    assert not latido.mandar("https://hc-ping.com/abc")


def test_la_clave_no_sale_en_el_log(monkeypatch, caplog):
    def sin_red(*a, **k):
        raise requests.ConnectionError("fallo con https://hc-ping.com/secreto")

    monkeypatch.setattr(requests, "get", sin_red)

    with caplog.at_level("WARNING", logger="crypto_tracker"):
        latido.mandar("https://hc-ping.com/secreto")

    assert "secreto" not in caplog.text


def test_un_404_no_cuenta(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda url, **k: Respuesta(404))

    assert not latido.mandar("https://hc-ping.com/abc")


def test_servicio_es_solo_el_dominio():
    assert latido.servicio("https://hc-ping.com/1234-abcd") == "hc-ping.com"
