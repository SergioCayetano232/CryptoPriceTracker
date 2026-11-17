"""Tests de /escalera."""

from datetime import datetime, timezone

import pytest

from crypto_tracker.config import Posicion
from crypto_tracker.escalera import EscaleraError, calcular, interpretar, nota
from crypto_tracker.movimientos import Movimiento

CUANDO = datetime(2026, 6, 1, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "texto, sale",
    [
        ("btc 80000 90000 100000", ("bitcoin", [80000, 90000, 100000], 100.0)),
        ("btc 80k 90k 50%", ("bitcoin", [80000, 90000], 50.0)),
        # Desordenados o repetidos da igual: se suben de abajo arriba.
        ("eth 5000 4000 4000", ("ethereum", [4000, 5000], 100.0)),
    ],
)
def test_interpretar(texto, sale):
    assert interpretar(texto) == sale


@pytest.mark.parametrize(
    "texto, error",
    [
        ("", "al menos dos precios"),
        ("btc 80000", "al menos dos precios"),
        ("btc 80000 80000", "dos precios distintos"),
        ("btc 80000 hola", "'hola' no es un precio"),
        ("btc 80000 90000 0%", "entre 1% y 100%"),
        ("btc 80000 90000 150%", "entre 1% y 100%"),
        ("btc " + " ".join(str(p) for p in range(1, 12)), "Como mucho 10"),
    ],
)
def test_interpretar_mal(texto, error):
    with pytest.raises(EscaleraError, match=error):
        interpretar(texto)


def test_calcular_reparte_a_partes_iguales():
    # 0,3 BTC a 50.000 de media: 0,1 en cada escalón.
    e = calcular(Posicion("bitcoin", 0.3, 15000), [80000, 90000, 100000], 100, 66000, 0)

    assert [x.cantidad for x in e.escalones] == pytest.approx([0.1, 0.1, 0.1])
    assert [x.cobrado for x in e.escalones] == pytest.approx([8000, 9000, 10000])
    assert [x.ganancia for x in e.escalones] == pytest.approx([3000, 4000, 5000])
    assert e.cobrado == pytest.approx(27000)
    assert e.ganancia == pytest.approx(12000)
    assert e.queda == pytest.approx(0)


def test_calcular_con_porcentaje_deja_el_resto():
    e = calcular(Posicion("bitcoin", 0.4, 20000), [80000, 90000], 50, 66000, 0)

    assert [x.cantidad for x in e.escalones] == pytest.approx([0.1, 0.1])
    assert e.queda == pytest.approx(0.2)


def test_calcular_hacienda_sube_de_tramo():
    # 12.000 de ganancia: los primeros 6.000 al 19% y el resto al 21%.
    e = calcular(Posicion("bitcoin", 0.3, 15000), [80000, 90000, 100000], 100, 66000, 0)

    assert e.escalones[0].hacienda == pytest.approx(3000 * 0.19)
    assert e.escalones[1].hacienda == pytest.approx(3000 * 0.19 + 1000 * 0.21)
    assert e.hacienda == pytest.approx(6000 * 0.19 + 6000 * 0.21)


def test_calcular_cuenta_lo_ya_ganado_este_año():
    e = calcular(Posicion("bitcoin", 0.2, 10000), [80000, 90000], 100, 66000, 6000)

    assert e.escalones[0].hacienda == pytest.approx(3000 * 0.21)


def test_calcular_con_fifo_vende_primero_lo_mas_viejo():
    # 0,1 a 3.000 y luego 0,1 a 7.000: el primer escalón se lleva el lote barato.
    historia = [
        Movimiento(1, "bitcoin", "compra", 0.1, 3000, None, CUANDO),
        Movimiento(
            2, "bitcoin", "compra", 0.1, 7000, Posicion("bitcoin", 0.1, 3000), CUANDO
        ),
    ]
    e = calcular(
        Posicion("bitcoin", 0.2, 10000), [80000, 90000], 100, 66000, 0, historia
    )

    assert [x.coste for x in e.escalones] == pytest.approx([3000, 7000])


def test_calcular_sin_saber_lo_que_costo():
    e = calcular(Posicion("bitcoin", 0.2), [80000, 90000], 100, 66000, 0)

    assert e.escalones[0].ganancia is None
    assert e.ganancia is None
    assert e.hacienda is None
    assert e.cobrado == pytest.approx(17000)


def test_calcular_con_el_primero_ya_pasado():
    with pytest.raises(EscaleraError, match="por encima del precio de ahora"):
        calcular(Posicion("bitcoin", 0.2, 10000), [60000, 90000], 100, 66000, 0)


def test_nota():
    assert nota(2, 3, "0,1") == "Escalera 2/3: vende 0,1"
