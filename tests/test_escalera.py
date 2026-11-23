"""Tests de /escalera."""

from datetime import datetime, timezone

import pytest

from crypto_tracker.config import Posicion
from crypto_tracker.escalera import (
    EscaleraError,
    calcular,
    calcular_compra,
    es_compra,
    interpretar,
    interpretar_compra,
    nota,
    nota_compra,
)
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


# --- de compra ---


def test_es_compra():
    assert es_compra("compra btc 60k 50k")
    assert not es_compra("btc 80k 90k")
    assert not es_compra("")


@pytest.mark.parametrize(
    "texto, sale",
    [
        ("compra btc 60000 50000", ("bitcoin", [60000, 50000], None)),
        ("compra btc 50k 60k 55k con 900", ("bitcoin", [60000, 55000, 50000], 900)),
        ("compra eth 2000 1800 con 300€", ("ethereum", [2000, 1800], 300)),
    ],
)
def test_interpretar_compra(texto, sale):
    assert interpretar_compra(texto) == sale


@pytest.mark.parametrize(
    "texto, error",
    [
        ("compra", "al menos dos precios"),
        ("compra btc 60000 con 900", "al menos dos precios"),
        ("compra btc 60k 50k con", "va al final"),
        ("compra btc 60k con 900 50k", "va al final"),
        ("compra btc 60k 50k con mucho", "'mucho' no es una cantidad"),
        ("compra btc 60k 50k con 0", "'0' no es una cantidad"),
    ],
)
def test_interpretar_compra_mal(texto, error):
    with pytest.raises(EscaleraError, match=error):
        interpretar_compra(texto)


def test_calcular_compra_reparte_el_dinero():
    e = calcular_compra("bitcoin", [60000, 50000], 1000, 66000, None)

    assert [x.gasto for x in e.escalones] == [500, 500]
    assert [x.cantidad for x in e.escalones] == pytest.approx([1 / 120, 0.01])
    # Media armónica: 1000 entre lo que compras, no la media de los precios.
    assert e.media == pytest.approx(1000 / (1 / 120 + 0.01))
    assert e.media_despues == e.media


def test_calcular_compra_baja_tu_precio_medio():
    # 0,1 BTC a 70.000 de media y 1.000 más a 60k y 40k.
    e = calcular_compra(
        "bitcoin", [60000, 40000], 1000, 66000, Posicion("bitcoin", 0.1, 7000)
    )

    assert e.media_antes == pytest.approx(70000)
    comprado = 500 / 60000 + 500 / 40000
    assert e.media_despues == pytest.approx(8000 / (0.1 + comprado))


def test_calcular_compra_sin_dinero():
    e = calcular_compra(
        "bitcoin", [60000, 50000], None, 66000, Posicion("bitcoin", 0.1, 7000)
    )

    assert e.escalones[0].cantidad is None
    assert e.comprado is None
    assert e.media_despues is None


def test_calcular_compra_sin_saber_lo_que_costo_lo_de_antes():
    e = calcular_compra("bitcoin", [60000, 50000], 1000, 66000, Posicion("bitcoin", 1))

    assert e.media is not None
    assert e.media_antes is None
    assert e.media_despues is None


def test_calcular_compra_con_el_primero_por_encima():
    with pytest.raises(EscaleraError, match="por debajo del precio de ahora"):
        calcular_compra("bitcoin", [70000, 50000], 1000, 66000, None)


def test_la_de_venta_por_debajo_sugiere_la_de_compra():
    with pytest.raises(EscaleraError, match="/escalera compra"):
        calcular(Posicion("bitcoin", 0.2, 10000), [50000, 60000], 100, 66000, 0)


def test_nota_compra():
    assert nota_compra(1, 2, "€500,00") == "Escalera de compra 1/2: mete €500,00"
    assert nota_compra(2, 2, None) == "Escalera de compra 2/2"
