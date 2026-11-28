"""Tests de /cada, los comandos que te manda solo."""

from datetime import date, datetime, time

import pytest

from crypto_tracker.avisos.alerts import formatear_programados
from crypto_tracker.avisos.cada import (
    CadaError,
    Programado,
    a_texto,
    de_texto,
    interpretar,
    para_quitar,
    toca,
)

# Un viernes cualquiera a las 20:05
VIERNES = datetime(2026, 11, 20, 20, 5).astimezone()


@pytest.mark.parametrize(
    "argumento, sale",
    [
        ("viernes 20:00 /cartera", (4, time(20, 0), "/cartera")),
        ("Sábado 9 /precio btc eth", (5, time(9, 0), "/precio btc eth")),
        ("dia 8:30 /status", (None, time(8, 30), "/status")),
        ("día 8:30 /status", (None, time(8, 30), "/status")),
    ],
)
def test_interpretar(argumento, sale):
    assert interpretar(argumento) == sale


@pytest.mark.parametrize(
    "argumento, error",
    [
        ("viernes /cartera", "Escríbelo así"),
        ("viernes 20:00 cartera", "Escríbelo así"),
        ("finde 20:00 /cartera", "no es un día"),
        ("viernes 25:00 /cartera", "no es una hora"),
        ("viernes tarde /cartera", "no es una hora"),
        ("dia 9:00 /cada dia 9:00 /status", "dentro de otro"),
        ("dia 9:00 /alerta btc | 3", "no puede llevar |"),
    ],
)
def test_interpretar_mal(argumento, error):
    with pytest.raises(CadaError, match=error):
        interpretar(argumento)


def test_para_quitar():
    assert para_quitar("quitar 2") == 2
    assert para_quitar("no #3") == 3
    assert para_quitar("viernes 20:00 /cartera") is None
    with pytest.raises(CadaError):
        para_quitar("quitar todos")


def test_toca():
    viernes = Programado(1, 4, time(20, 0), "/cartera")
    diario = Programado(2, None, time(20, 0), "/status")

    assert toca(viernes, VIERNES)
    assert toca(diario, VIERNES)
    assert not toca(Programado(3, 0, time(20, 0), "/cartera"), VIERNES)  # lunes
    assert not toca(Programado(4, 4, time(21, 0), "/cartera"), VIERNES)  # aún no
    # Ya mandado hoy
    assert not toca(Programado(1, 4, time(20, 0), "/cartera", VIERNES.date()), VIERNES)


def test_guardar_y_leer():
    p = Programado(3, None, time(9, 0), "/precio btc", date(2026, 11, 18))
    assert de_texto(3, a_texto(p)) == p
    assert de_texto(1, "roto") is None


def test_formatear_programados():
    texto = formatear_programados([Programado(1, 4, time(20, 0), "/cartera")])
    assert "<code>1</code>  cada viernes a las 20:00: /cartera" in texto
    assert "/cada quitar 1" in texto
    assert "No tienes nada programado" in formatear_programados([])
