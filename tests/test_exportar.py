"""Tests de /exportar."""

from datetime import date, datetime, timezone

import pytest

from crypto_tracker.config import Posicion
from crypto_tracker.exportar import (
    a_csv,
    interpretar,
    movimientos_a_csv,
    nombre_archivo,
    nombre_movimientos,
    pide_movimientos,
)
from crypto_tracker.movimientos import Movimiento
from crypto_tracker.periodo import PeriodoError

_CUANDO = datetime(2026, 10, 3, 10, 0, tzinfo=timezone.utc)


def test_interpretar():
    assert interpretar("Bitcoin 7d") == ("bitcoin", 168)
    assert interpretar("bitcoin 12h") == ("bitcoin", 12)
    assert interpretar("bitcoin") == ("bitcoin", 720)  # sin tramo, 30 dias


@pytest.mark.parametrize("argumento", ["", "bitcoin 7d de mas"])
def test_interpretar_formato_malo(argumento):
    with pytest.raises(PeriodoError, match="/exportar bitcoin 30d"):
        interpretar(argumento)


def test_interpretar_tramo_malo():
    with pytest.raises(PeriodoError):
        interpretar("bitcoin mucho")


def test_csv():
    serie = [
        (datetime(2026, 10, 3, 10, 0, tzinfo=timezone.utc), 62000.0),
        (datetime(2026, 10, 3, 10, 5, tzinfo=timezone.utc), 62010.55),
        (datetime(2026, 10, 3, 10, 10, tzinfo=timezone.utc), 0.0000123),
    ]

    texto = a_csv(serie, "eur").decode("utf-8-sig")
    lineas = texto.split("\r\n")

    assert lineas[0] == "fecha;precio_eur"
    assert lineas[1].endswith(";62000")
    assert lineas[2].endswith(";62010,55")
    assert lineas[3].endswith(";0,0000123")
    assert len(lineas) == 5  # cabecera, tres precios y el salto del final


def test_csv_lleva_bom_para_excel():
    assert a_csv([], "eur").startswith(b"\xef\xbb\xbf")


def test_csv_en_hora_local():
    cuando = datetime(2026, 10, 3, 10, 0, tzinfo=timezone.utc)
    local = cuando.astimezone().strftime("%Y-%m-%d %H:%M")

    assert local in a_csv([(cuando, 1.0)], "eur").decode("utf-8-sig")


def test_nombre_archivo():
    hoy = date(2026, 10, 3)

    assert nombre_archivo("bitcoin", 720, hoy) == "bitcoin-30d-2026-10-03.csv"
    assert nombre_archivo("bitcoin", 12, hoy) == "bitcoin-12h-2026-10-03.csv"
    assert nombre_archivo("bitcoin", 36, hoy) == "bitcoin-36h-2026-10-03.csv"


@pytest.mark.parametrize(
    "argumento, sale",
    [
        ("movimientos", True),
        (" Movimientos ", True),
        ("bitcoin 7d", False),
        ("", False),
    ],
)
def test_pide_movimientos(argumento, sale):
    assert pide_movimientos(argumento) is sale


def test_pide_movimientos_de_mas():
    with pytest.raises(PeriodoError, match="/exportar movimientos"):
        pide_movimientos("movimientos 2025")


def _mov(id, tipo, cantidad, coste, antes=None, nota=None, coin_id="bitcoin"):
    return Movimiento(id, coin_id, tipo, cantidad, coste, antes, _CUANDO, nota)


def _filas(lista, currency="eur"):
    import csv
    from io import StringIO

    texto = movimientos_a_csv(lista, currency).decode("utf-8-sig")
    return list(csv.reader(StringIO(texto, newline=""), delimiter=";"))


def test_csv_movimientos():
    antes = Posicion("bitcoin", 0.02, 1000)
    # Vienen del más nuevo al más antiguo, como los da la base de datos
    filas = _filas([_mov(2, "venta", 0.01, 700, antes), _mov(1, "compra", 0.02, 1000)])

    assert filas[0] == [
        "fecha",
        "tipo",
        "cripto",
        "cantidad",
        "importe_eur",
        "precio_unidad_eur",
        "ganancia_eur",
        "nota",
    ]
    fecha = _CUANDO.astimezone().strftime("%Y-%m-%d %H:%M")
    assert filas[1] == [fecha, "compra", "bitcoin", "0,02", "1000", "50000", "", ""]
    assert filas[2] == [fecha, "venta", "bitcoin", "0,01", "700", "70000", "200", ""]


def test_csv_movimientos_en_otra_moneda():
    assert "importe_usd" in _filas([], "USD")[0]


def test_csv_movimientos_sin_precio_deja_huecos():
    [_, fila] = _filas([_mov(1, "venta", 0.01, None, Posicion("bitcoin", 0.02, 1000))])

    assert fila[4:7] == ["", "", ""]


def test_csv_movimientos_sin_saber_lo_que_costo():
    [_, fila] = _filas([_mov(1, "venta", 0.01, 700, Posicion("bitcoin", 0.02, None))])

    assert fila[4] == "700"
    assert fila[6] == ""


def test_csv_movimientos_nota_con_separadores():
    nota = 'por; el "halving"\ny ya'

    [_, fila] = _filas([_mov(1, "compra", 1, 10, nota=nota)])

    assert fila[7] == nota


@pytest.mark.parametrize("nota", ["=1+1", "+10%", "-10% y vendo", "@alguien"])
def test_csv_movimientos_nota_que_parece_formula(nota):
    [_, fila] = _filas([_mov(1, "compra", 1, 10, nota=nota)])

    assert fila[7] == f"'{nota}"


def test_csv_movimientos_cantidad_pequeña_sin_notacion_cientifica():
    [_, fila] = _filas([_mov(1, "compra", 0.00000123, 10)])

    assert fila[3] == "0,00000123"


def test_csv_movimientos_lleva_bom():
    assert movimientos_a_csv([], "eur").startswith(b"\xef\xbb\xbf")


def test_nombre_movimientos():
    assert nombre_movimientos(date(2026, 10, 3)) == "movimientos-2026-10-03.csv"
