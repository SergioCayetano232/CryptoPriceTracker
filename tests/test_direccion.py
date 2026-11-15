"""Tests de /direccion."""

import pytest
import requests

from crypto_tracker import database, direccion
from crypto_tracker.alerts import (
    formatear_direccion_nueva,
    formatear_direcciones,
    formatear_movimiento_direccion,
)
from crypto_tracker.direccion import (
    DireccionError,
    Saldo,
    Vigilada,
    buscar,
    cargar,
    interpretar,
    leer,
    movida,
)

BC1 = "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
LEGACY = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"


def _datos(funded=150_000_000, spent=50_000_000, txs=3, pend_f=0, pend_s=0, pend_t=0):
    return {
        "address": BC1,
        "chain_stats": {
            "funded_txo_sum": funded,
            "spent_txo_sum": spent,
            "tx_count": txs,
        },
        "mempool_stats": {
            "funded_txo_sum": pend_f,
            "spent_txo_sum": pend_s,
            "tx_count": pend_t,
        },
    }


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("", ("ver", "", "")),
        (f"{BC1} frío", ("añadir", BC1, "frío")),
        (f"{BC1.upper()} el de casa", ("añadir", BC1, "el de casa")),
        (LEGACY, ("añadir", LEGACY, "1A1zP1eP…")),
        ("quitar frío", ("quitar", "frío", "")),
        ("borrar el de casa", ("quitar", "el de casa", "")),
    ],
)
def test_interpretar(texto, esperado):
    assert interpretar(texto) == esperado


@pytest.mark.parametrize(
    "texto", ["hola", "bc1", "quitar", "0x1234567890abcdef1234567890"]
)
def test_interpretar_mal(texto):
    with pytest.raises(DireccionError):
        interpretar(texto)


def test_nombre_largo_se_corta():
    assert len(interpretar(f"{BC1} {'x' * 50}")[2]) == 30


def test_leer_con_lo_pendiente():
    assert leer(_datos()) == Saldo(100_000_000, 3)
    # Sale medio bitcoin aún sin confirmar: ya cuenta.
    assert leer(_datos(pend_s=50_000_000, pend_t=1)) == Saldo(50_000_000, 4)


@pytest.mark.parametrize(
    "datos",
    [None, [], {}, {"chain_stats": {}, "mempool_stats": {}}, {"chain_stats": None}],
)
def test_leer_raro(datos):
    assert leer(datos) is None


def test_movida():
    antes = Vigilada(BC1, "frío", 100, 3)
    assert movida(antes, Saldo(100, 3)) is None
    assert movida(antes, Saldo(150, 4)) == 50
    assert movida(antes, Saldo(40, 4)) == -60
    # Entra y sale lo mismo: se avisa igual, ha habido movimiento.
    assert movida(antes, Saldo(100, 5)) == 0


def test_cargar_y_guardar():
    v = Vigilada(BC1, "frío", 123, 4)
    assert cargar(BC1, v.guardar()) == v
    assert cargar(BC1, "roto") is None
    assert cargar(BC1, '{"nombre": "x"}') is None


def test_buscar():
    lista = [Vigilada(BC1, "Frío", 1, 1), Vigilada(LEGACY, "satoshi", 1, 1)]
    assert buscar(lista, "frío").direccion == BC1
    assert buscar(lista, LEGACY.lower()).nombre == "satoshi"
    assert buscar(lista, "otra") is None


class _Respuesta:
    def __init__(self, datos, status=200):
        self.datos, self.status_code = datos, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")

    def json(self):
        if isinstance(self.datos, Exception):
            raise self.datos
        return self.datos


def test_pedir(monkeypatch):
    def get(url, **k):
        assert url == f"https://mempool.space/api/address/{BC1}"
        return _Respuesta(_datos())

    monkeypatch.setattr(requests, "get", get)

    assert direccion.pedir(BC1) == Saldo(100_000_000, 3)


@pytest.mark.parametrize(
    "respuesta, mensaje",
    [
        (_Respuesta("Invalid Bitcoin address", 400), "no existe"),
        (_Respuesta({}, 500), "no contesta"),
        (_Respuesta(ValueError("x")), "no es JSON"),
        (_Respuesta({"chain_stats": {}}), "no entiendo"),
    ],
)
def test_pedir_falla(monkeypatch, respuesta, mensaje):
    monkeypatch.setattr(requests, "get", lambda url, **k: respuesta)

    with pytest.raises(DireccionError, match=mensaje):
        direccion.pedir(BC1)


def test_pedir_sin_red(monkeypatch):
    def get(url, **k):
        raise requests.ConnectionError("caída")

    monkeypatch.setattr(requests, "get", get)

    with pytest.raises(DireccionError, match="no contesta"):
        direccion.pedir(BC1)


def test_base_de_datos(tmp_path):
    ruta = str(tmp_path / "t.db")
    database.init_db(ruta)

    database.guardar_direccion(ruta, BC1, "uno")
    database.guardar_direccion(ruta, LEGACY, "dos")
    # Al cambiarla no se va al final.
    database.guardar_direccion(ruta, BC1, "tres")
    assert database.direcciones(ruta) == {BC1: "tres", LEGACY: "dos"}
    assert list(database.direcciones(ruta)) == [BC1, LEGACY]

    database.guardar_direccion(ruta, BC1, None)
    assert database.direcciones(ruta) == {LEGACY: "dos"}


def test_formatear_lista():
    lista = [
        Vigilada(BC1, "frío", 50_000_000, 3),
        Vigilada(LEGACY, "satoshi", 5_000, 1),
    ]
    texto = formatear_direcciones(lista, 80000.0, "eur")

    assert "👀 <b>Las direcciones que vigilo</b>" in texto
    assert "• <b>frío</b>: 0,5 BTC (€40.000,00)" in texto
    assert "bc1qxy…0wlh" in texto
    assert f"https://mempool.space/address/{BC1}" in texto
    assert "• <b>satoshi</b>: 0,00005 BTC (€4,00)" in texto
    assert "Entre todas: <b>0,50005 BTC (€40.004,00)</b>" in texto


def test_formatear_lista_vacia():
    assert "No vigilo ninguna" in formatear_direcciones([], None, "eur")


def test_formatear_nueva_sin_precio():
    texto = formatear_direccion_nueva(Vigilada(BC1, "<frío>", 0, 0), None, "eur")
    assert texto.startswith("👀 Vigilo <b>&lt;frío&gt;</b>: ahora tiene 0 BTC.")


@pytest.mark.parametrize(
    "cambio, linea",
    [
        (10_000_000, "📥 Han entrado <b>0,1 BTC (€8.000,00)</b>"),
        (-10_000_000, "📤 Han salido <b>0,1 BTC (€8.000,00)</b>"),
        (0, "el saldo sigue igual"),
    ],
)
def test_formatear_movimiento(cambio, linea):
    texto = formatear_movimiento_direccion(
        Vigilada(BC1, "frío", 50_000_000, 3),
        cambio,
        Saldo(60_000_000, 4),
        80000.0,
        "eur",
    )

    assert "🔔 <b>Se ha movido frío</b>" in texto
    assert linea in texto
    assert "Ahora tiene 0,6 BTC (€48.000,00)" in texto
