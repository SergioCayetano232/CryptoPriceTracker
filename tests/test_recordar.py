"""Tests de /recordar."""

from datetime import date, datetime, time, timedelta, timezone

import pytest

from crypto_tracker.puntuales import numero
from crypto_tracker.recordar import (
    RecordarError,
    Recordatorio,
    a_texto,
    comando_compra,
    de_texto,
    interpretar,
    para_quitar,
    toca,
)

MADRID = timezone(timedelta(hours=1))
# El 9 de noviembre de 2026 es lunes
LUNES = datetime(2026, 11, 9, 9, 5, tzinfo=MADRID)


@pytest.mark.parametrize(
    "texto, sale",
    [
        ("lunes 50 btc", Recordatorio("bitcoin", 0, 50)),
        ("Miércoles 25,5 eth", Recordatorio("ethereum", 2, 25.5)),
        ("sabado 100€ sol", Recordatorio("solana", 5, 100)),
    ],
)
def test_interpretar(texto, sale):
    assert interpretar(texto) == sale


@pytest.mark.parametrize(
    "texto, error",
    [
        ("lunes 50", "Escríbelo así"),
        ("finde 50 btc", "no es un día"),
        ("lunes cincuenta btc", "no es una cantidad"),
        ("lunes 0 btc", "no es una cantidad"),
    ],
)
def test_interpretar_mal(texto, error):
    with pytest.raises(RecordarError, match=error):
        interpretar(texto)


@pytest.mark.parametrize(
    "texto, sale",
    [("btc no", "bitcoin"), ("quitar eth", "ethereum"), ("lunes 50 btc", None)],
)
def test_para_quitar(texto, sale):
    assert para_quitar(texto) == sale


def test_toca_el_dia_y_a_la_hora():
    r = Recordatorio("bitcoin", 0, 50)

    assert toca(r, LUNES, time(9, 0))
    assert not toca(r, LUNES, time(10, 0))  # aún no es la hora
    assert not toca(r, LUNES + timedelta(days=1), time(9, 0))  # martes


def test_sin_horario_a_las_nueve():
    assert toca(Recordatorio("bitcoin", 0, 50), LUNES, None)


def test_no_toca_dos_veces_el_mismo_dia():
    r = Recordatorio("bitcoin", 0, 50, ultimo=LUNES.date())

    assert not toca(r, LUNES, time(9, 0))


def test_comando_compra():
    r = Recordatorio("bitcoin", 0, 50)

    assert comando_compra(r, 68000) == "/compra bitcoin 0,00073529 50"


def test_el_comando_se_lee_bien_con_cantidades_grandes():
    # 1.234 se leería como mil doscientos: por eso va con coma
    comando = comando_compra(Recordatorio("pepe", 0, 12.5), 0.01)

    assert comando == "/compra pepe 1250 12,5"
    assert numero(comando.split()[2]) == 1250


def test_ida_y_vuelta_del_texto():
    r = Recordatorio("bitcoin", 4, 25.5, date(2026, 11, 6))

    assert de_texto("bitcoin", a_texto(r)) == r
    assert de_texto("bitcoin", a_texto(Recordatorio("bitcoin", 0, 50))).ultimo is None


def test_texto_roto():
    assert de_texto("bitcoin", "lo que sea") is None
