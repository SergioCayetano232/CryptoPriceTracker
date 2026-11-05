"""Tests de /adivina."""

import pytest

from crypto_tracker.adivina import AdivinaError, Intento, interpretar
from crypto_tracker.alerts import formatear_adivina


@pytest.mark.parametrize(
    "argumento,esperado",
    [
        ("70000", ("bitcoin", 70000)),
        ("70k", ("bitcoin", 70000)),
        ("70.000 €", ("bitcoin", 70000)),
        ("eth 2500", ("ethereum", 2500)),
        ("SOL 150,5", ("solana", 150.5)),
    ],
)
def test_interpretar(argumento, esperado):
    assert interpretar(argumento) == esperado


@pytest.mark.parametrize("argumento", ["", "mucho", "btc 0", "btc eth 3"])
def test_interpretar_mal(argumento):
    with pytest.raises(AdivinaError, match="/adivina 70000"):
        interpretar(argumento)


@pytest.mark.parametrize(
    "dicho,nota",
    [
        (70000, "¡Clavado!"),
        (70350, "¡Clavado!"),  # 0,5% justo
        (71000, "Casi, casi"),
        (67000, "Caliente"),
        (60000, "Templado"),
        (45000, "Frío, frío"),
        (200000, "Ni de lejos"),
    ],
)
def test_nota(dicho, nota):
    assert Intento("bitcoin", dicho, 70000).nota[1] == nota


def test_corto_o_pasado():
    assert Intento("bitcoin", 60000, 70000).corto
    assert not Intento("bitcoin", 80000, 70000).corto


def test_formatear():
    texto = formatear_adivina(Intento("bitcoin", 67000, 70000), "eur")

    assert texto.startswith("🙂 <b>Caliente</b>")
    assert "Dijiste €67.000,00 y <b>Bitcoin</b> está a <b>€70.000,00</b>" in texto
    assert "Te has quedado corto por €3.000,00 (4.29%)" in texto


def test_formatear_pasado():
    texto = formatear_adivina(Intento("ethereum", 2600, 2500), "eur")

    assert "Te has quedado pasado por €100,00 (4.00%)" in texto


def test_formatear_exacto():
    texto = formatear_adivina(Intento("bitcoin", 70000, 70000), "eur")

    assert "🎯 <b>¡Clavado!</b>" in texto
    assert "Te has quedado" not in texto
