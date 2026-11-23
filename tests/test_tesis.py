"""Tests de /tesis."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from crypto_tracker.tesis import (
    MAX_TEXTO,
    Nueva,
    Quitar,
    Tesis,
    TesisError,
    Veredicto,
    a_texto,
    de_texto,
    interpretar,
    marcador,
    pendientes,
    siguiente,
    tocan,
)

CUANDO = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)


def _tesis(numero=1, **cambios):
    t = Tesis(numero, "bitcoin", "sale el ETF", 60000.0, CUANDO)
    return replace(t, **cambios)


@pytest.mark.parametrize(
    "texto, sale",
    [
        ("btc sale el ETF", Nueva("bitcoin", 30, "sale el ETF")),
        ("sol 90d la red va a más", Nueva("solana", 90, "la red va a más")),
        ("eth 7D poco", Nueva("ethereum", 7, "poco")),
        # Un número que no es plazo es parte del porqué.
        ("btc 2 halvings más", Nueva("bitcoin", 30, "2 halvings más")),
        ("si 3", Veredicto(3, True)),
        ("Sí #3", Veredicto(3, True)),
        ("acerté 3", Veredicto(3, True)),
        ("no 4", Veredicto(4, False)),
        ("fallé 4", Veredicto(4, False)),
        ("quitar 5", Quitar(5)),
    ],
)
def test_interpretar(texto, sale):
    assert interpretar(texto) == sale


@pytest.mark.parametrize(
    "texto, error",
    [
        ("", "la cripto y por qué"),
        ("btc", "¿Y por qué?"),
        ("btc 90d", "¿Y por qué?"),
        ("btc 3d muy rápido", "entre 7 y 365"),
        ("btc 400d muy lento", "entre 7 y 365"),
        ("btc " + "a" * (MAX_TEXTO + 1), "Muy largo"),
        ("si", "Falta el número"),
        ("no tres", "Falta el número"),
        ("quitar", "Falta el número"),
    ],
)
def test_interpretar_mal(texto, error):
    with pytest.raises(TesisError, match=error):
        interpretar(texto)


def test_vence_y_tocan():
    t = _tesis(dias=30)

    assert t.vence == CUANDO + timedelta(days=30)
    assert tocan([t], CUANDO + timedelta(days=29, hours=23)) == []
    assert tocan([t], CUANDO + timedelta(days=30)) == [t]
    # Ya preguntada, no se vuelve a preguntar.
    assert tocan([replace(t, final=70000)], CUANDO + timedelta(days=40)) == []


def test_cambio():
    assert _tesis().cambio(66000) == pytest.approx(10)


def test_siguiente():
    assert siguiente([]) == 1
    assert siguiente([_tesis(1), _tesis(4)]) == 5


def test_pendientes():
    a, b = _tesis(1), _tesis(2, final=70000.0)

    assert pendientes([a, b]) == [a]


def test_marcador():
    lista = [
        _tesis(1, final=70000.0, acerto=True),
        _tesis(2, final=50000.0, acerto=False),
        _tesis(3, final=65000.0, acerto=True),
        _tesis(4, final=65000.0),  # preguntada, sin contestar
        _tesis(5),
    ]

    assert marcador(lista) == (2, 3)
    assert marcador([]) == (0, 0)


@pytest.mark.parametrize(
    "t",
    [
        _tesis(),
        _tesis(dias=90, final=71000.5, acerto=True),
        _tesis(final=50000.0, acerto=False),
        _tesis(final=50000.0),
        # Con barras en el texto, que es lo que separa los campos.
        _tesis(texto="sube | o baja | quién sabe"),
    ],
)
def test_ida_y_vuelta(t):
    assert de_texto(t.numero, a_texto(t)) == t


def test_de_texto_roto():
    assert de_texto(1, "esto no es una tesis") is None
