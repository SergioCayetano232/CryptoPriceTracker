"""Tests de apuntar compras y ventas de la cartera desde Telegram."""

import pytest

from crypto_tracker.config import Posicion
from crypto_tracker.movimientos import (
    MovimientoError,
    buscar,
    combinar,
    comprar,
    interpretar_compra,
    interpretar_venta,
    texto_cantidad,
    vender,
)

# --- leer lo que escribes ---


@pytest.mark.parametrize(
    "argumento, esperado",
    [
        ("bitcoin 0.01 600", ("bitcoin", 0.01, 600)),
        ("Bitcoin 0,01 600€", ("bitcoin", 0.01, 600)),
        ("ethereum 2 3.000", ("ethereum", 2, 3000)),
        ("solana 5", ("solana", 5, None)),
        ("solana 5 0", ("solana", 5, 0)),
    ],
)
def test_interpretar_compra(argumento, esperado):
    assert interpretar_compra(argumento) == esperado


@pytest.mark.parametrize("argumento", ["", "bitcoin", "bitcoin 1 2 3"])
def test_interpretar_compra_formato_malo(argumento):
    with pytest.raises(MovimientoError, match="/compra bitcoin 0.01 600"):
        interpretar_compra(argumento)


@pytest.mark.parametrize(
    "argumento, mensaje",
    [
        ("bitcoin mucho", "no es un número"),
        ("bitcoin 0 600", "mayor que 0"),
        ("bitcoin -1 600", "mayor que 0"),
        ("bitcoin 1 -600", "negativo"),
        ("bitcoin 1 gratis", "no es un número"),
    ],
)
def test_interpretar_compra_numeros_malos(argumento, mensaje):
    with pytest.raises(MovimientoError, match=mensaje):
        interpretar_compra(argumento)


@pytest.mark.parametrize(
    "argumento, esperado",
    [
        ("bitcoin 0.005", ("bitcoin", 0.005)),
        ("Bitcoin todo", ("bitcoin", None)),
        ("bitcoin TODO", ("bitcoin", None)),
    ],
)
def test_interpretar_venta(argumento, esperado):
    assert interpretar_venta(argumento) == esperado


@pytest.mark.parametrize("argumento", ["", "bitcoin", "bitcoin 0.005 400"])
def test_interpretar_venta_formato_malo(argumento):
    with pytest.raises(MovimientoError, match="/venta bitcoin todo"):
        interpretar_venta(argumento)


def test_interpretar_venta_cantidad_mala():
    with pytest.raises(MovimientoError, match="mayor que 0"):
        interpretar_venta("bitcoin 0")


# --- comprar ---


def test_comprar_algo_nuevo():
    assert comprar(None, "solana", 5, 700) == Posicion("solana", 5, 700)


def test_comprar_suma_cantidad_y_coste():
    despues = comprar(Posicion("bitcoin", 0.016, 1000), "bitcoin", 0.01, 600)
    assert despues.cantidad == pytest.approx(0.026)
    assert despues.invertido == 1600


def test_comprar_sin_saber_lo_de_antes_no_inventa_el_coste():
    despues = comprar(Posicion("bitcoin", 0.016), "bitcoin", 0.01, 600)
    assert despues.invertido is None


# --- vender ---


def test_vender_una_parte_baja_lo_invertido_en_proporcion():
    antes = Posicion("bitcoin", 0.02, 1000)
    despues = vender(antes, "bitcoin", 0.005)
    assert despues.cantidad == pytest.approx(0.015)
    assert despues.invertido == pytest.approx(750)


def test_vender_sin_coste_sigue_sin_coste():
    assert vender(Posicion("bitcoin", 1), "bitcoin", 0.5) == Posicion("bitcoin", 0.5)


def test_vender_todo():
    assert vender(Posicion("bitcoin", 0.02, 1000), "bitcoin", None) is None


def test_vender_justo_lo_que_tienes_es_venderlo_todo():
    # 0.1 + 0.2 no da 0.3 exacto; que no quede un resto de 0,00000000000004
    antes = Posicion("bitcoin", 0.1 + 0.2, 1000)
    assert vender(antes, "bitcoin", 0.3) is None


def test_vender_mas_de_lo_que_tienes():
    with pytest.raises(MovimientoError, match="Solo tienes 0,02 de bitcoin"):
        vender(Posicion("bitcoin", 0.02, 1000), "bitcoin", 0.5)


def test_vender_lo_que_no_tienes():
    with pytest.raises(MovimientoError, match="No tienes solana"):
        vender(None, "solana", 1)


# --- juntar con el .env ---

ENV = (Posicion("bitcoin", 0.016, 1000), Posicion("ethereum", 0.4))


def test_combinar_sin_cambios():
    assert combinar(ENV, {}) == ENV


def test_combinar_cambia_quita_y_anade():
    cambios = {
        "bitcoin": Posicion("bitcoin", 0.026, 1600),
        "ethereum": None,
        "solana": Posicion("solana", 5, 700),
    }
    assert combinar(ENV, cambios) == (
        Posicion("bitcoin", 0.026, 1600),
        Posicion("solana", 5, 700),
    )


def test_combinar_vendida_que_no_estaba_en_el_env():
    assert combinar(ENV, {"solana": None}) == ENV


def test_buscar():
    assert buscar(ENV, "ethereum") == Posicion("ethereum", 0.4)
    assert buscar(ENV, "solana") is None


@pytest.mark.parametrize(
    "valor, texto",
    [(0.016, "0,016"), (1500, "1.500"), (2.5, "2,5"), (0.00000001, "0,00000001")],
)
def test_texto_cantidad(valor, texto):
    assert texto_cantidad(valor) == texto
