"""Tests de /direccion."""

import pytest
import requests

from crypto_tracker.avisos import direccion
from crypto_tracker.avisos.alerts import (
    formatear_direccion_nueva,
    formatear_direcciones,
    formatear_movimiento_direccion,
)
from crypto_tracker.avisos.direccion import (
    DireccionError,
    Saldo,
    Vigilada,
    buscar,
    cargar,
    interpretar,
    leer,
    movida,
)
from crypto_tracker.nucleo import database

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
    texto = formatear_direcciones(lista, {"bitcoin": 80000.0}, "eur")

    assert "👀 <b>Las direcciones que vigilo</b>" in texto
    assert "• <b>frío</b>: 0,5 BTC (€40.000,00)" in texto
    assert "bc1qxy…0wlh" in texto
    assert f"https://mempool.space/address/{BC1}" in texto
    assert "• <b>satoshi</b>: 0,00005 BTC (€4,00)" in texto
    assert "Entre todas: <b>0,50005 BTC (€40.004,00)</b>" in texto


def test_formatear_lista_vacia():
    assert "No vigilo ninguna" in formatear_direcciones([], {}, "eur")


def test_formatear_nueva_sin_precio():
    texto = formatear_direccion_nueva(Vigilada(BC1, "<frío>", 0, 0), {}, "eur")
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
        {"bitcoin": 80000.0},
        "eur",
    )

    assert "🔔 <b>Se ha movido frío</b>" in texto
    assert linea in texto
    assert "Ahora tiene 0,6 BTC (€48.000,00)" in texto


# --- ethereum ---

ETH = "0xde0b295669a9fd93d5f28d9ec85e40f4cb697bae"
ETH_MIXTA = "0xde0B295669a9FD93d5F28D9Ec85E40f4cb697BAe"


def test_interpretar_eth_en_minusculas():
    assert interpretar(f"{ETH_MIXTA} fundación") == ("añadir", ETH, "fundación")


def test_eth_corta_no_vale():
    with pytest.raises(DireccionError, match="ni de ethereum"):
        interpretar("0xde0b295669a9fd93d5f28d9ec85e40f4cb697ba")


def test_de_que_red_es():
    assert direccion.coin_id(ETH) == "ethereum"
    assert direccion.coin_id(BC1) == "bitcoin"
    assert direccion.ver(ETH) == (f"https://etherscan.io/address/{ETH}", "etherscan.io")
    assert direccion.ver(BC1)[1] == "mempool.space"


def test_a_moneda():
    assert direccion.a_moneda(ETH, 2 * 10**18) == 2.0
    assert direccion.a_moneda(BC1, 50_000_000) == 0.5


@pytest.mark.parametrize(
    "datos, wei",
    [
        ({"jsonrpc": "2.0", "id": 1, "result": "0x1bc16d674ec80000"}, 2 * 10**18),
        ({"result": "0x0"}, 0),
        ({"error": {"code": -32602, "message": "invalid argument"}}, None),
        ({"result": "nada"}, None),
        ([], None),
    ],
)
def test_leer_eth(datos, wei):
    assert direccion.leer_eth(datos) == wei


def test_pedir_eth(monkeypatch):
    def post(url, json, **k):
        assert url == "https://ethereum-rpc.publicnode.com"
        assert json["method"] == "eth_getBalance"
        assert json["params"] == [ETH, "latest"]
        return _Respuesta({"result": "0xde0b6b3a7640000"})

    monkeypatch.setattr(requests, "post", post)

    assert direccion.pedir(ETH) == Saldo(10**18, 0)


def test_pedir_eth_falla(monkeypatch):
    monkeypatch.setattr(
        requests, "post", lambda url, **k: _Respuesta({"error": {"code": 1}})
    )

    with pytest.raises(DireccionError, match="no entiendo"):
        direccion.pedir(ETH)


def test_pedir_eth_sin_red(monkeypatch):
    def post(url, **k):
        raise requests.ConnectionError("caída")

    monkeypatch.setattr(requests, "post", post)

    with pytest.raises(DireccionError, match="no contesta"):
        direccion.pedir(ETH)


def test_movida_eth_por_el_saldo():
    antes = Vigilada(ETH, "f", 10**18, 0)

    assert movida(antes, Saldo(10**18, 0)) is None
    assert movida(antes, Saldo(3 * 10**18, 0)) == 2 * 10**18
    assert movida(antes, Saldo(0, 0)) == -(10**18)


def test_guardar_y_cargar_eth_sin_perder_wei():
    v = Vigilada(ETH, "f", 14156924268674340757215, 0)

    assert cargar(ETH, v.guardar()) == v


def test_formatear_movimiento_eth():
    texto = formatear_movimiento_direccion(
        Vigilada(ETH, "fundación", 10**18, 0),
        -(5 * 10**17),
        Saldo(5 * 10**17, 0),
        {"ethereum": 3000.0},
        "eur",
    )

    assert "📤 Han salido <b>0,5 ETH (€1.500,00)</b>" in texto
    assert "Ahora tiene 0,5 ETH (€1.500,00)" in texto
    assert (
        f'<a href="https://etherscan.io/address/{ETH}">Verlo en etherscan.io</a>'
        in texto
    )


def test_lista_con_las_dos_redes_no_las_suma():
    lista = [
        Vigilada(BC1, "frío", 50_000_000, 3),
        Vigilada(LEGACY, "viejo", 50_000_000, 1),
        Vigilada(ETH, "fundación", 2 * 10**18, 0),
    ]

    texto = formatear_direcciones(lista, {"bitcoin": 80000.0}, "eur")

    assert "fundación</b>: 2 ETH ·" in texto  # sin precio de ethereum, sin euros
    assert "Entre todas: <b>1 BTC (€80.000,00)</b>" in texto
    assert texto.count("Entre todas") == 1


def test_lo_de_sin_confirmar_solo_si_hay_de_bitcoin():
    solo_eth = formatear_direcciones([Vigilada(ETH, "f", 0, 0)], {}, "eur")
    con_btc = formatear_direcciones(
        [Vigilada(ETH, "f", 0, 0), Vigilada(BC1, "frío", 0, 0)], {}, "eur"
    )

    assert "sin esperar a que se confirme" not in solo_eth
    assert "En bitcoin, sin esperar a que se confirme." in con_btc
