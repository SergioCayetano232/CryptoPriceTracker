"""Tests de /liga."""

from datetime import datetime, timedelta, timezone

import pytest

from crypto_tracker.avisos.alerts import formatear_liga
from crypto_tracker.curiosidades import liga
from crypto_tracker.curiosidades.liga import Jugador, LigaError, Puesto
from crypto_tracker.curiosidades.prediccion import Prediccion

DOMINGO = datetime(2026, 11, 22, 19, 0, tzinfo=timezone.utc)
ANTERIOR = DOMINGO - timedelta(days=7)


def _p(predicho, real, cierre=DOMINGO, entonces=100.0):
    hecha = cierre - timedelta(days=3)
    return Prediccion(1, "bitcoin", hecha, cierre, entonces, predicho, real)


# Estaba a 100 y acabó en 110.
CLAVADA = _p(109, 110)  # acierta el lado y se acerca: 2 puntos
TIMIDA = _p(101, 110)  # acierta el lado, pero casi como no decir nada: 2 por poco
PASADA = _p(150, 110)  # acierta el lado y se va lejísimos: 1 punto
AL_REVES = _p(90, 110)  # ni una cosa ni otra: 0
EN_JUEGO = _p(120, None)


def test_puntos():
    assert liga.puntos(CLAVADA) == 2
    assert liga.puntos(PASADA) == 1
    assert liga.puntos(AL_REVES) == 0


def test_interpretar():
    assert liga.interpretar("") is False
    assert liga.interpretar(" Semana ") is True
    with pytest.raises(LigaError, match="/liga semana"):
        liga.interpretar("bitcoin")


def test_clasifica_de_mas_a_menos_puntos():
    tabla = liga.clasificar(
        [
            Jugador("Luis", False, [AL_REVES, PASADA]),
            Jugador("Ana", True, [CLAVADA, CLAVADA]),
        ]
    )

    assert [(p.nombre, p.puntos, p.total, p.lado) for p in tabla] == [
        ("Ana", 4, 2, 2),
        ("Luis", 1, 2, 1),
    ]
    assert tabla[0].yo and not tabla[1].yo


def test_a_igualdad_de_puntos_gana_quien_menos_se_va():
    tabla = liga.clasificar(
        [Jugador("Timo", False, [TIMIDA]), Jugador("Ana", False, [CLAVADA])]
    )

    assert [p.nombre for p in tabla] == ["Ana", "Timo"]
    assert tabla[0].error_medio == pytest.approx(100 / 110)


def test_quien_no_tiene_ninguna_cerrada_no_sale():
    tabla = liga.clasificar(
        [Jugador("Ana", False, [CLAVADA]), Jugador("Luis", False, [EN_JUEGO])]
    )

    assert [p.nombre for p in tabla] == ["Ana"]
    assert liga.clasificar([Jugador("Luis", False, [])]) == []


def test_la_ultima_jornada_es_el_ultimo_domingo_cerrado():
    jugadores = [
        Jugador("Ana", False, [_p(109, 110, ANTERIOR), EN_JUEGO]),
        Jugador("Luis", False, [CLAVADA]),
    ]

    assert liga.ultima_jornada(jugadores) == DOMINGO
    assert liga.ultima_jornada([Jugador("Ana", False, [EN_JUEGO])]) is None


def test_de_una_jornada_solo_cuenta_lo_de_ese_domingo():
    jugadores = [
        Jugador("Ana", False, [_p(109, 110, ANTERIOR), _p(109, 110, ANTERIOR)]),
        Jugador("Luis", False, [PASADA, _p(109, 110, ANTERIOR)]),
    ]

    tabla = liga.clasificar(jugadores, DOMINGO)

    assert [(p.nombre, p.puntos, p.total) for p in tabla] == [("Luis", 1, 1)]


def _puesto(nombre, puntos, yo=False):
    return Puesto(nombre, yo, puntos, 3, 2, 4.25)


def test_los_empatados_comparten_puesto():
    tabla = [_puesto("a", 5), _puesto("b", 5), _puesto("c", 3), _puesto("d", 1)]

    assert liga.posiciones(tabla) == [1, 1, 3, 4]


def test_mensaje():
    tabla = [
        _puesto("Ana (@ana)", 5),
        _puesto("Tú", 4, yo=True),
        _puesto("Luis <b>", 2),
        _puesto("Eva", 1),
    ]

    texto = formatear_liga(tabla, None)

    assert texto.startswith("🏆 <b>La liga de predicciones</b>")
    assert "🥇 <b>Ana (@ana)</b> · 5 puntos" in texto
    assert "🥈 <b>Tú</b> 👈 · 4 puntos" in texto
    assert "🥉 <b>Luis &lt;b&gt;</b> · 2 puntos" in texto
    assert "4. <b>Eva</b> · 1 punto\n" in texto
    assert "3 predicciones · acierta el lado en 2 · se va un 4,2%" in texto
    assert "/liga semana" in texto


def test_mensaje_de_una_jornada():
    texto = formatear_liga([_puesto("Ana", 2)], DOMINGO)

    assert "La jornada del 22/11" in texto
    assert "/liga semana" not in texto


def test_mensaje_sin_nadie():
    texto = formatear_liga([], None)

    assert "Todavía no se ha cerrado ninguna predicción" in texto
    assert "/prediccion btc 70000" in texto
