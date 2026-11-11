"""Tests de /limite."""

from datetime import date, datetime

import pytest

from crypto_tracker.alerts import formatear_limite, linea_limite
from crypto_tracker.limite import (
    PONER,
    QUITAR,
    VER,
    Limite,
    LimiteError,
    gastado,
    interpretar,
)
from crypto_tracker.movimientos import Movimiento

HOY = date(2026, 11, 11)


def _mov(dia, coste=100.0, tipo="compra"):
    cuando = datetime(dia.year, dia.month, dia.day, 12).astimezone()
    return Movimiento(1, "bitcoin", tipo, 0.01, coste, None, cuando)


def test_gastado_solo_este_mes_y_solo_compras():
    movs = [
        _mov(date(2026, 11, 1), 100),
        _mov(date(2026, 11, 10), 50),
        _mov(date(2026, 10, 31), 500),  # el mes pasado
        _mov(date(2025, 11, 5), 500),  # noviembre, pero de otro año
        _mov(date(2026, 11, 5), 300, "venta"),
        _mov(date(2026, 11, 5), 20, "recompensa"),
        _mov(date(2026, 11, 5), None),
    ]

    assert gastado(movs, HOY) == 150


def test_limite():
    assert Limite(300, 150).falta == 150
    assert not Limite(300, 150).cerca
    assert Limite(300, 250).cerca
    assert not Limite(300, 300).pasado
    assert Limite(300, 301).pasado
    assert not Limite(300, 301).cerca


@pytest.mark.parametrize(
    "texto,esperado",
    [
        ("", (VER, None)),
        ("no", (QUITAR, None)),
        ("quitar", (QUITAR, None)),
        ("300", (PONER, 300)),
        ("1k", (PONER, 1000)),
        ("300 €", (PONER, 300)),
    ],
)
def test_interpretar(texto, esperado):
    assert interpretar(texto) == esperado


@pytest.mark.parametrize("texto", ["mucho", "0", "-5", "300 400"])
def test_interpretar_mal(texto):
    with pytest.raises(LimiteError):
        interpretar(texto)


def test_linea_al_pasarte():
    linea = linea_limite(Limite(300, 350), "eur")

    assert linea == (
        "⚠️ Con esta, este mes llevas <b>€350,00</b> en compras: €50,00 por "
        "encima de tu límite de €300,00"
    )


def test_linea_cerca():
    linea = linea_limite(Limite(300, 250), "eur")

    assert linea == "🧮 Llevas €250,00 de tus €300,00 de este mes: te quedan €50,00"


def test_linea_lejos_no_dice_nada():
    assert linea_limite(Limite(300, 100), "eur") is None


def test_formatear():
    texto = formatear_limite(Limite(300, 150), "eur", HOY)

    assert texto.startswith("🧮 <b>Tu límite: €300,00 al mes</b>\n")
    assert "En noviembre llevas €150,00 en compras" in texto
    assert "<code>▓▓▓▓▓░░░░░</code> 50%" in texto
    assert "Te quedan €150,00 hasta fin de mes" in texto


def test_formatear_pasado_y_recien_puesto():
    texto = formatear_limite(Limite(300, 450), "eur", HOY, puesto=True)

    assert texto.startswith("✅ Hecho, te aviso al comprar si te pasas\n\n")
    assert "<code>▓▓▓▓▓▓▓▓▓▓</code> 100%" in texto
    assert "⚠️ Te has pasado €150,00" in texto
