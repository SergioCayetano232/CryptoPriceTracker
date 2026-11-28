"""Tests de /prediccion."""

from datetime import datetime, timedelta, timezone

import pytest

from crypto_tracker.curiosidades.prediccion import (
    Marcador,
    Prediccion,
    PrediccionError,
    cierre,
    interpretar,
    marcador,
    tocan,
)

AHORA = datetime(2026, 11, 17, 10, 0, tzinfo=timezone.utc)  # martes


def _p(entonces, predicho, real=None, cierre_=AHORA):
    return Prediccion(None, "bitcoin", AHORA, cierre_, entonces, predicho, real)


@pytest.mark.parametrize(
    "argumento,esperado",
    [
        ("btc 70000", ("bitcoin", 70000)),
        ("eth 3.500", ("ethereum", 3500)),
        ("btc 70k", ("bitcoin", 70000)),
        ("btc no", ("bitcoin", None)),
    ],
)
def test_interpretar(argumento, esperado):
    assert interpretar(argumento) == esperado


@pytest.mark.parametrize("argumento", ["", "btc", "btc mucho", "btc -5", "btc 1 2"])
def test_interpretar_malo(argumento):
    with pytest.raises(PrediccionError):
        interpretar(argumento)


def test_cierre_es_el_domingo_a_las_20():
    c = cierre(AHORA).astimezone()

    assert c.weekday() == 6
    assert (c.hour, c.minute) == (20, 0)
    assert timedelta(days=4) < c - AHORA < timedelta(days=6)


def test_cierre_con_poco_margen_pasa_al_siguiente():
    domingo = cierre(AHORA)
    casi = domingo - timedelta(hours=5)

    assert cierre(casi) == domingo + timedelta(days=7)


def test_cierre_justo_con_margen_se_queda():
    domingo = cierre(AHORA)

    assert cierre(domingo - timedelta(hours=25)) == domingo


def test_cuentas_de_una():
    # Estaba a 100, dijiste 110 y quedó en 105.
    p = _p(100, 110, 105)

    assert p.error == pytest.approx(4.76, abs=0.01)
    assert p.error_quieto == pytest.approx(4.76, abs=0.01)
    assert p.acierta_lado
    assert not p.gana_al_quieto  # empate: no gana


def test_falla_el_lado():
    p = _p(100, 110, 95)

    assert not p.acierta_lado
    assert not p.gana_al_quieto


def test_tocan():
    pendiente = _p(100, 110, cierre_=AHORA)
    futura = _p(100, 110, cierre_=AHORA + timedelta(days=1))
    hecha = _p(100, 110, 105, cierre_=AHORA)

    assert tocan([pendiente, futura, hecha], AHORA) == [pendiente]


def test_marcador():
    lista = [_p(100, 110, 108), _p(100, 90, 105), _p(100, 102, 101), _p(100, 120)]

    m = marcador(lista)

    assert m == Marcador(
        total=3,
        lado=2,
        error_medio=pytest.approx((1.85 + 14.29 + 0.99) / 3, abs=0.01),
        al_quieto=1,  # la de 102 empata con "se queda igual": no cuenta
    )
    assert m.mejor_que_moneda is None  # con 3 no se puede decir


def test_mejor_que_moneda():
    assert Marcador(4, 3, 1, 1).mejor_que_moneda
    assert not Marcador(4, 2, 1, 1).mejor_que_moneda


def test_marcador_vacio():
    assert marcador([_p(100, 110)]) is None
