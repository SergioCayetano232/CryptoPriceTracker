"""Tests del CSV de /impuestos para la Renta."""

from datetime import datetime, timezone

import pytest

from crypto_tracker.hacienda import renta
from crypto_tracker.inversion.movimientos import Movimiento
from crypto_tracker.nucleo.config import Posicion


def _cuando(año, mes=6):
    return datetime(año, mes, 1, 12, tzinfo=timezone.utc)


def _pos(cantidad, invertido, coin="bitcoin"):
    return Posicion(coin, cantidad, invertido)


def _mov(id_, tipo, cantidad, coste, antes, cuando, coin="bitcoin"):
    return Movimiento(id_, coin, tipo, cantidad, coste, antes, cuando)


# Compras en 2024 a 100 y a 300; en 2025 se vende 1,5 a 600.
HISTORIA = [
    _mov(1, "compra", 1, 100, None, _cuando(2024, 1)),
    _mov(2, "compra", 1, 300, _pos(1, 100), _cuando(2024, 3)),
    _mov(3, "venta", 1.5, 600, _pos(2, 400), _cuando(2025, 5)),
]


def _filas(contenido: bytes) -> list[list[str]]:
    texto = contenido.decode("utf-8-sig")
    return [linea.split(";") for linea in texto.strip().split("\r\n")]


@pytest.mark.parametrize(
    "argumento, esperado",
    [
        ("2025 csv", ("2025", True)),
        ("csv", ("", True)),
        ("2025 CSV", ("2025", True)),
        ("2025", ("2025", False)),
        ("", ("", False)),
    ],
)
def test_pide_csv(argumento, esperado):
    assert renta.pide_csv(argumento) == esperado


def test_venta_con_fifo_y_compras_de_otro_año():
    [v] = renta.ventas(HISTORIA, 2025)

    assert v.transmision == 600
    # 1 del primer lote (100) y 0,5 del segundo (150).
    assert v.adquisicion == pytest.approx(250)
    assert v.ganancia == pytest.approx(350)


def test_solo_las_ventas_de_ese_año():
    assert renta.ventas(HISTORIA, 2024) == []


def test_venta_sin_coste_no_inventa_ganancia():
    sin_coste = [
        _mov(1, "compra", 1, None, None, _cuando(2024)),
        _mov(2, "venta", 1, 500, _pos(1, None), _cuando(2025)),
    ]

    [v] = renta.ventas(sin_coste, 2025)

    assert v.adquisicion is None
    assert v.ganancia is None


def test_csv_con_su_total():
    filas = _filas(renta.a_csv(renta.ventas(HISTORIA, 2025), "eur"))

    assert filas[0] == [
        "fecha_venta",
        "cripto",
        "cantidad",
        "valor_transmision_eur",
        "valor_adquisicion_eur",
        "ganancia_eur",
        "numero",
    ]
    assert filas[1] == ["2025-05-01", "bitcoin", "1,5", "600", "250", "350", "3"]
    assert filas[2] == ["total", "", "", "600", "250", "350", ""]


def test_el_total_deja_fuera_las_que_no_se_pueden_contar():
    lista = [
        renta.Venta(1, _cuando(2025), "bitcoin", 1, 500.0, 200.0),
        renta.Venta(2, _cuando(2025), "solana", 3, 90.0, None),
    ]

    filas = _filas(renta.a_csv(lista, "eur"))

    assert filas[2] == ["2025-06-01", "solana", "3", "90", "", "", "2"]
    assert filas[3] == ["total", "", "", "500", "200", "300", ""]


def test_perdidas_en_negativo():
    lista = [renta.Venta(1, _cuando(2025), "bitcoin", 1, 80.0, 100.0)]

    assert _filas(renta.a_csv(lista, "eur"))[1][5] == "-20"


def test_sin_ninguna_contable_no_hay_total():
    lista = [renta.Venta(1, _cuando(2025), "bitcoin", 1, None, None)]

    assert len(_filas(renta.a_csv(lista, "eur"))) == 2


def test_nombre():
    assert renta.nombre(2025) == "renta-2025.csv"
