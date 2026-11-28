"""Tests de /emocion y /emociones."""

from datetime import datetime, timezone

import pytest

from crypto_tracker.inversion.emocion import (
    EmocionError,
    Grupo,
    calcular,
    interpretar,
    leer,
)
from crypto_tracker.inversion.movimientos import Movimiento

CUANDO = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)


def _mov(emocion, coste=100.0, tipo="compra", cantidad=1.0, coin_id="bitcoin"):
    return Movimiento(1, coin_id, tipo, cantidad, coste, None, CUANDO, emocion=emocion)


@pytest.mark.parametrize(
    "texto,esperado",
    [
        ("miedo", "miedo"),
        ("FOMO", "fomo"),
        ("Eufórico", "euforia"),
        ("pánico", "miedo"),
        ("calma", "tranquilo"),
        ("ilusión", None),
    ],
)
def test_leer(texto, esperado):
    assert leer(texto) == esperado


def test_interpretar():
    assert interpretar("12 miedo") == (12, "miedo")
    assert interpretar("#3 euforia") == (3, "euforia")


@pytest.mark.parametrize(
    "argumento,error",
    [("miedo", "Escríbelo así"), ("12", "Escríbelo así"), ("12 ilusión", "No conozco")],
)
def test_interpretar_malo(argumento, error):
    with pytest.raises(EmocionError, match=error):
        interpretar(argumento)


def test_calcular():
    movs = [
        _mov("euforia", coste=200),  # hoy vale 100: -50%
        _mov("euforia", coste=200),
        _mov("miedo", coste=50),  # +100%
        _mov("miedo", coste=50),
        _mov("miedo", tipo="venta", coste=50),  # lo vendido hoy valdría el doble
        _mov(None),
    ]

    e = calcular(movs, {"bitcoin": 100.0})

    assert e.compras == [
        Grupo("miedo", 2, pytest.approx(100)),
        Grupo("euforia", 2, pytest.approx(-50)),
    ]
    assert e.ventas == [Grupo("miedo", 1, pytest.approx(100))]
    assert e.sin == 1
    mejor, peor = e.mejor_y_peor()
    assert (mejor.emocion, peor.emocion) == ("miedo", "euforia")


def test_con_una_de_cada_no_saca_conclusiones():
    e = calcular([_mov("euforia"), _mov("miedo")], {"bitcoin": 100.0})

    assert e.mejor_y_peor() is None


def test_sin_coste_o_sin_precio():
    e = calcular(
        [_mov("miedo", coste=None), _mov("miedo", coin_id="pepe")],
        {"bitcoin": 100.0},
    )

    assert e.compras == [Grupo("miedo", 2, None)]


def test_en_frase():
    from crypto_tracker.inversion.emocion import en_frase

    assert en_frase("euforia") == "euforia"
    assert en_frase("fomo") == "FOMO"
