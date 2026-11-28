"""Tests de /correlacion."""

from datetime import date, timedelta

import pytest

from crypto_tracker.avisos.alerts import formatear_correlacion
from crypto_tracker.correlacion import (
    MAX_TODAS,
    Correlacion,
    calcular,
    interpretar,
    juntar,
    matriz,
)
from crypto_tracker.nucleo.periodo import PeriodoError

HOY = date(2026, 10, 13)


def _dias(*precios, hasta=HOY):
    return [
        (hasta - timedelta(days=len(precios) - 1 - i), p) for i, p in enumerate(precios)
    ]


SUBE_BAJA = (100, 110, 99, 105, 120, 108, 112, 101, 115)


@pytest.mark.parametrize(
    "argumento,esperado",
    [
        ("btc eth", (["bitcoin", "ethereum"], 720)),
        ("btc sol 7d", (["bitcoin", "solana"], 168)),
        ("90d", ([], 2160)),
        ("", ([], 720)),
    ],
)
def test_interpretar(argumento, esperado):
    assert interpretar(argumento) == esperado


@pytest.mark.parametrize("argumento", ["btc", "btc eth sol", "btc 7d"])
def test_interpretar_de_dos_en_dos(argumento):
    with pytest.raises(PeriodoError, match="/correlacion btc eth 30d"):
        interpretar(argumento)


def test_interpretar_la_misma():
    with pytest.raises(PeriodoError, match="la misma"):
        interpretar("btc bitcoin")


def test_iguales_dan_uno():
    # El doble de precio, pero los mismos %: se mueven igual
    c = calcular(_dias(*SUBE_BAJA), _dias(*(p * 2 for p in SUBE_BAJA)))

    assert c.valor == pytest.approx(1)
    assert c.dias == 8


def test_al_reves_da_menos_uno():
    una = _dias(*SUBE_BAJA)
    # Cada día, el mismo % pero al contrario
    precios = [100.0]
    for (_, antes), (_, despues) in zip(una, una[1:], strict=False):
        precios.append(precios[-1] * (2 - despues / antes))

    assert calcular(una, _dias(*precios)).valor == pytest.approx(-1)


def test_solo_cuenta_los_dias_en_comun():
    largo = SUBE_BAJA + SUBE_BAJA
    # La otra empieza 6 días más tarde: 17 cambios contra 11
    c = calcular(_dias(*largo), _dias(*largo[6:]))

    assert c.dias == 11


def test_pocos_dias_o_sin_moverse():
    assert calcular(_dias(*SUBE_BAJA[:7]), _dias(*SUBE_BAJA[:7])) is None
    assert calcular(_dias(*SUBE_BAJA), _dias(*[100] * 9)) is None


def test_un_hueco_no_cuenta_como_un_dia():
    largo = SUBE_BAJA + SUBE_BAJA
    una = _dias(*largo)
    del una[8]  # sin ese día se pierden dos cambios: el suyo y el siguiente

    assert calcular(una, _dias(*largo)).dias == 15


@pytest.mark.parametrize(
    "valor,esperado",
    [
        (0.85, "van muy juntas"),
        (0.5, "suelen ir juntas"),
        (0.1, "cada una va a lo suyo"),
        (-0.6, "suelen ir al revés"),
    ],
)
def test_formatear(valor, esperado):
    texto = formatear_correlacion("bitcoin", "ethereum", Correlacion(valor, 29), 720)

    assert "🔗 <b>Bitcoin</b> y <b>Ethereum</b>, últimos 30 días" in texto
    assert f"<b>{valor:+.2f}</b>".replace(".", ",") in texto
    assert esperado in texto
    assert "Con 29 días" in texto


# --- todas contra todas ---


@pytest.mark.parametrize(
    "texto, sale",
    [
        ("todas", (["todas"], 30 * 24)),
        ("TODAS 90d", (["todas"], 90 * 24)),
    ],
)
def test_interpretar_todas(texto, sale):
    assert interpretar(texto) == sale


def test_juntar():
    assert juntar(["bitcoin", "ethereum"], ["ethereum", "solana"]) == [
        "bitcoin",
        "ethereum",
        "solana",
    ]
    assert len(juntar([f"c{i}" for i in range(20)])) == MAX_TODAS


def test_matriz():
    al_reves = tuple(200 - p for p in SUBE_BAJA)
    m = matriz(
        {
            "bitcoin": _dias(*SUBE_BAJA),
            "ethereum": _dias(*(p * 2 for p in SUBE_BAJA)),
            "tether": _dias(*al_reves),
            "nueva": _dias(10, 11),  # sin días suficientes
        }
    )

    assert m.ids == ["bitcoin", "ethereum", "tether", "nueva"]
    assert len(m.parejas) == 6
    assert m.de("bitcoin", "bitcoin") == 1.0
    assert m.de("bitcoin", "ethereum") == pytest.approx(1)
    # Da igual el orden en que se pregunte.
    assert m.de("tether", "bitcoin") == m.de("bitcoin", "tether")
    assert m.de("bitcoin", "tether") < -0.9
    assert m.de("bitcoin", "nueva") is None

    a, b, valor = m.con_valor[0]
    assert {a, b} == {"bitcoin", "ethereum"}
    assert len(m.con_valor) == 3
    assert m.con_valor[-1][2] < -0.9


def test_matriz_media():
    m = matriz(
        {
            "bitcoin": _dias(*SUBE_BAJA),
            "ethereum": _dias(*(p * 2 for p in SUBE_BAJA)),
        }
    )

    assert m.media == pytest.approx(1)
    assert matriz({"bitcoin": _dias(*SUBE_BAJA), "nueva": _dias(1, 2)}).media is None
