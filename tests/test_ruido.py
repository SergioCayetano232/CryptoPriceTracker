"""Tests de /ruido."""

from datetime import datetime, timedelta, timezone

import pytest

from crypto_tracker.config import Watch
from crypto_tracker.periodo import PeriodoError
from crypto_tracker.ruido import (
    Cuenta,
    analizar,
    candidatas,
    contar,
    interpretar,
    simular,
)

INICIO = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)


def _cada_hora(*precios):
    return [(INICIO + timedelta(hours=i), p) for i, p in enumerate(precios)]


def _cada_dia(*precios):
    return [(INICIO + timedelta(days=i), p) for i, p in enumerate(precios)]


@pytest.mark.parametrize(
    "argumento,esperado",
    [
        ("bitcoin 7d", ("bitcoin", 168)),
        ("btc", ("bitcoin", 720)),
        ("7d", ("", 168)),
        ("", ("", 720)),
    ],
)
def test_interpretar(argumento, esperado):
    assert interpretar(argumento) == esperado


@pytest.mark.parametrize("argumento", ["bitcoin 1d", "btc eth"])
def test_interpretar_malo(argumento):
    with pytest.raises(PeriodoError):
        interpretar(argumento)


def test_simular_porcentaje_como_el_bot():
    avisos = simular(_cada_hora(100, 106, 107, 100), Watch("bitcoin", percent=5))

    assert [(a.precio, a.sube) for a in avisos] == [(106, True), (100, False)]
    # La vuelta es la mitad del movimiento: de 100 a 106, en 103.
    assert avisos[0].vuelta == 103


def test_simular_umbral_no_avisa_de_lo_que_ya_estaba_cruzado():
    # Empieza ya por encima de 120: eso no es un aviso del tramo.
    avisos = simular(_cada_hora(130, 125, 110, 125), Watch("bitcoin", max_price=120))

    assert [a.precio for a in avisos] == [125]
    assert avisos[0].vuelta == 120


def test_contar_falso_cerrado_y_pendiente():
    # Sube un 6% y a la hora lo ha deshecho: en falso. La bajada se queda
    # un día entero y la subida a 107 dos: buenos. El de 113, en la última
    # hora: aún no se sabe.
    serie = _cada_hora(100, 106, 100, *[100] * 30, 107, *[107] * 48, 113)
    watch = Watch("bitcoin", percent=5)

    cuenta = contar(serie, simular(serie, watch))

    assert cuenta == Cuenta(avisos=4, falsos=1, pendientes=1)
    assert cuenta.cerrados == 3


def test_contar_bajada_que_rebota():
    serie = _cada_hora(100, 94, 99, *[99] * 30)

    cuenta = contar(serie, simular(serie, Watch("bitcoin", percent=5)))

    assert cuenta.falsos == 1


def test_contar_mira_solo_las_24_h_siguientes():
    # Vuelve, pero a los dos días: eso ya no es ruido.
    serie = _cada_dia(100, 106, 106, 100, 100)

    cuenta = contar(serie, simular(serie, Watch("bitcoin", percent=5)))

    assert cuenta.avisos == 2
    assert cuenta.falsos == 0


def test_contar_sin_precios():
    assert contar([], []) == Cuenta(0, 0, 0)


def test_candidatas():
    assert [w.percent for w in candidatas(Watch("btc", percent=5))] == [
        7,
        10,
        15,
        20,
        25,
        30,
    ]
    pasos = candidatas(Watch("btc", step=1000))
    assert [w.step for w in pasos][:2] == [2000, 3000]
    # Detrás de los pasos, los %, por si ningún paso sirve.
    assert pasos[5] == Watch("btc", percent=1)
    assert candidatas(Watch("btc", min_price=50, max_price=80)) == []


def test_analizar_propone_la_primera_que_calla_el_ruido():
    # Un vaivén de ±6% cada hora durante días: con %5 todo es ruido.
    # Encima, una subida limpia de un 25% que se queda.
    vaiven = [100, 106] * 30
    serie = _cada_hora(*vaiven, 125, *[125] * 30)

    r = analizar(serie, Watch("bitcoin", percent=5))

    assert r.cuenta.mucho
    otra, suya = r.propuesta
    assert otra.percent == 7
    assert suya.falsos == 0
    assert suya.avisos == 1


def test_analizar_sin_ruido_no_propone():
    serie = _cada_dia(100, 106, 112, 118, 125, 125)

    r = analizar(serie, Watch("bitcoin", percent=5))

    assert not r.cuenta.mucho
    assert r.propuesta is None


def test_pocos_avisos_no_son_mucho_ruido():
    # Uno de uno en falso es el 100%, pero con uno no se puede decir nada.
    serie = _cada_hora(100, 106, 100, *[100] * 30)

    r = analizar(serie, Watch("bitcoin", percent=5))

    assert r.cuenta.falsos >= 1
    assert not r.cuenta.mucho
    assert r.propuesta is None
