"""Tests de apuntar compras y ventas de la cartera desde Telegram."""

from datetime import datetime, timezone

import pytest

from crypto_tracker.alerts import formatear_compra, formatear_movimientos
from crypto_tracker.config import Posicion
from crypto_tracker.movimientos import (
    Movimiento,
    MovimientoError,
    buscar,
    cobrado,
    combinar,
    comprar,
    descuadre,
    interpretar_compra,
    interpretar_deshacer,
    interpretar_venta,
    precio_medio,
    texto_cantidad,
    totales,
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
        # con @, el precio de cada una en vez del total
        ("bitcoin 0.01 @60000", ("bitcoin", 0.01, 600)),
        ("bitcoin 0.01 @60k", ("bitcoin", 0.01, 600)),
        ("bitcoin 0,5 @ 60.000€", ("bitcoin", 0.5, 30000)),
        ("sol 4 @150,5", ("solana", 4, 602)),
    ],
)
def test_interpretar_compra(argumento, esperado):
    assert interpretar_compra(argumento) == esperado


@pytest.mark.parametrize("argumento", ["", "bitcoin", "bitcoin 1 2 3", "btc 1 @"])
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
        ("bitcoin 1 @gratis", "no es un número"),
        ("bitcoin 1 @-5", "negativo"),
    ],
)
def test_interpretar_compra_numeros_malos(argumento, mensaje):
    with pytest.raises(MovimientoError, match=mensaje):
        interpretar_compra(argumento)


@pytest.mark.parametrize(
    "argumento, esperado",
    [
        ("bitcoin 0.005", ("bitcoin", 0.005, None)),
        ("Bitcoin todo", ("bitcoin", None, None)),
        ("bitcoin TODO", ("bitcoin", None, None)),
        ("bitcoin 0.005 400", ("bitcoin", 0.005, "400")),
        ("bitcoin todo @ 70000", ("bitcoin", None, "@70000")),
    ],
)
def test_interpretar_venta(argumento, esperado):
    assert interpretar_venta(argumento) == esperado


@pytest.mark.parametrize(
    "precio, esperado",
    [("400", 400), ("400,50", 400.5), ("@70000", 350), ("@70k", 350)],
)
def test_cobrado(precio, esperado):
    assert cobrado(precio, 0.005) == pytest.approx(esperado)


@pytest.mark.parametrize("precio", ["mucho", "-5"])
def test_cobrado_malo(precio):
    with pytest.raises(MovimientoError):
        cobrado(precio, 0.005)


@pytest.mark.parametrize(
    "argumento", ["", "bitcoin", "bitcoin 0.005 400 más", "bitcoin 0.005 @"]
)
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


# --- /deshacer ---


def test_deshacer_a_secas_es_la_ultima():
    assert interpretar_deshacer("") is None


def test_deshacer_con_el_numero_del_boton():
    assert interpretar_deshacer("12") == 12


@pytest.mark.parametrize("argumento", ["bitcoin", "-1", "1.5"])
def test_deshacer_mal_escrito(argumento):
    with pytest.raises(MovimientoError):
        interpretar_deshacer(argumento)


# --- el precio medio al comprar ---


def test_precio_medio():
    assert precio_medio(Posicion("bitcoin", 0.02, 1200.0)) == 60000.0


def test_precio_medio_sin_lo_que_costo():
    assert precio_medio(Posicion("bitcoin", 0.02)) is None
    assert precio_medio(None) is None


def test_compra_que_baja_el_precio_medio():
    antes = Posicion("bitcoin", 0.01, 700.0)
    ahora = comprar(antes, "bitcoin", 0.01, 500.0)

    texto = formatear_compra(0.01, 500.0, ahora, "eur", antes)

    assert "🔻 Te sale a €60.000,00 cada una, antes a €70.000,00." in texto


def test_compra_que_sube_el_precio_medio():
    antes = Posicion("bitcoin", 0.01, 500.0)
    ahora = comprar(antes, "bitcoin", 0.01, 700.0)

    texto = formatear_compra(0.01, 700.0, ahora, "eur", antes)

    assert "🔺 Te sale a €60.000,00 cada una, antes a €50.000,00." in texto


def test_primera_compra_sin_precio_medio():
    ahora = comprar(None, "bitcoin", 0.01, 600.0)

    texto = formatear_compra(0.01, 600.0, ahora, "eur")

    assert "Te sale a" not in texto
    assert texto.endswith("que te costaron €600,00. Mira /cartera")


# --- el total de /movimientos ---

CUANDO = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)


def _mov(tipo: str, coste: float | None, coin_id: str = "bitcoin") -> Movimiento:
    return Movimiento(1, coin_id, tipo, 0.01, coste, None, CUANDO)


def test_totales():
    lista = [_mov("compra", 600), _mov("compra", 400), _mov("venta", 350)]

    assert totales(lista) == (1000, 350)


def test_totales_sin_lo_que_costo_no_suma():
    assert totales([_mov("compra", None), _mov("venta", 200)]) == (0, 200)


def test_movimientos_con_el_total():
    lista = [_mov("venta", 350), _mov("compra", 600, "ethereum")]

    texto = formatear_movimientos(lista, "eur")

    assert texto.endswith("\n\nEn total: €600,00 comprado · €350,00 vendido")


def test_movimientos_total_de_todos_aunque_salgan_menos():
    todos = [_mov("compra", 100)] * 12

    texto = formatear_movimientos(todos[:10], "eur", todos=todos)

    assert "En total de los 12: €1.200,00 comprado" in texto


def test_movimientos_sin_precios_sin_total():
    texto = formatear_movimientos([_mov("compra", None)], "eur")

    assert "En total" not in texto


# --- compras que no cuadran con el precio ---


def test_compra_normal_no_descuadra():
    assert descuadre(0.01, 620, 60000) is None


def test_compra_con_un_cero_de_mas():
    assert descuadre(0.01, 6000, 60000) == pytest.approx(900)


def test_compra_con_un_cero_de_menos():
    assert descuadre(0.1, 600, 60000) == pytest.approx(-90)


def test_descuadre_sin_precio_o_sin_cantidad():
    assert descuadre(0.01, 6000, None) is None
    assert descuadre(0, 6000, 60000) is None
