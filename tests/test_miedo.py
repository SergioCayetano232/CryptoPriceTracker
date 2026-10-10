"""Tests de /miedo."""

from datetime import date

import pytest
import requests

from crypto_tracker import miedo
from crypto_tracker.miedo import Indice, MiedoError, hace, leer, nombre

# 10/10/2026 a las 00:00 UTC
HOY = 1791590400
DIA = 86400


def _fila(valor="64", clase="Greed", ts=HOY):
    return {"value": valor, "value_classification": clase, "timestamp": str(ts)}


def test_leer():
    assert leer({"data": [_fila()]}) == [Indice(64, "Greed", date(2026, 10, 10))]


def test_leer_ignora_lo_raro():
    datos = {
        "data": [
            None,
            _fila(valor="x"),
            _fila(valor="150"),
            {"value": "50"},
            _fila(valor="20", clase="Extreme Fear", ts=HOY - DIA),
        ]
    }

    assert leer(datos) == [Indice(20, "Extreme Fear", date(2026, 10, 9))]
    assert leer({"metadata": {"error": "algo"}}) == []
    assert leer(None) == []


@pytest.mark.parametrize(
    "clase, esperado",
    [
        ("Extreme Fear", ("😱", "Miedo extremo")),
        ("greed", ("😏", "Codicia")),
        ("Euforia total", ("📊", "Euforia total")),
    ],
)
def test_nombre(clase, esperado):
    assert nombre(Indice(50, clase, date(2026, 10, 10))) == esperado


def test_hace_busca_por_dia_aunque_falte_alguno():
    lista = leer({"data": [_fila(ts=HOY), _fila(valor="40", ts=HOY - 7 * DIA)]})

    assert hace(lista, 7).valor == 40
    assert hace(lista, 1) is None  # el de ayer no vino
    assert hace([], 1) is None


class _Respuesta:
    def __init__(self, datos, status=200):
        self.datos, self.status_code = datos, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)

    def json(self):
        return self.datos


def test_pedir(monkeypatch):
    pedido = {}

    def get(url, params=None, timeout=None):
        pedido.update(url=url, params=params, timeout=timeout)
        return _Respuesta({"data": [_fila()]})

    monkeypatch.setattr(requests, "get", get)

    assert miedo.pedir()[0].valor == 64
    assert pedido["params"] == {"limit": miedo.DIAS}
    assert pedido["timeout"]


def test_pedir_falla(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: _Respuesta({}, 503))

    with pytest.raises(MiedoError, match="no contesta"):
        miedo.pedir()
