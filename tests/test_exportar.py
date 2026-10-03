"""Tests de /exportar."""

from datetime import date, datetime, timezone

import pytest

from crypto_tracker.exportar import a_csv, interpretar, nombre_archivo
from crypto_tracker.periodo import PeriodoError


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
