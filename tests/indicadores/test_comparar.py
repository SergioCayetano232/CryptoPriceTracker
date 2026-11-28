"""Tests de /comparar."""

from datetime import datetime, timedelta, timezone

import pytest

from crypto_tracker.indicadores.comparar import (
    Resultado,
    comparar,
    en_base_100,
    interpretar,
    media,
)
from crypto_tracker.nucleo.periodo import PeriodoError

AHORA = datetime(2026, 10, 8, 12, 0, tzinfo=timezone.utc)


def _serie(*precios, dias=7):
    """Precios repartidos desde hace tantos dias hasta ahora."""
    paso = timedelta(days=dias) / max(1, len(precios) - 1)
    inicio = AHORA - timedelta(days=dias)
    return [(inicio + paso * i, p) for i, p in enumerate(precios)]


@pytest.mark.parametrize(
    "argumento,esperado",
    [
        ("btc eth sol", (["bitcoin", "ethereum", "solana"], 168)),
        ("btc, eth 30d", (["bitcoin", "ethereum"], 720)),
        ("BTC btc 12h", (["bitcoin"], 12)),
        ("30d", ([], 720)),
        ("", ([], 168)),
    ],
)
def test_interpretar(argumento, esperado):
    assert interpretar(argumento) == esperado


def test_interpretar_demasiadas():
    with pytest.raises(PeriodoError, match="Como mucho 10"):
        interpretar(" ".join(f"moneda-{i}" for i in range(11)))


def test_interpretar_tramo_malo():
    with pytest.raises(PeriodoError):
        interpretar("btc 500d")


def test_comparar_de_mejor_a_peor():
    series = {
        "bitcoin": _serie(100, 90, 110),
        "solana": _serie(100, 130),
        "ethereum": _serie(100, 80),
    }

    resultados, sin_datos = comparar(series, 168, AHORA)

    assert [r.coin_id for r in resultados] == ["solana", "bitcoin", "ethereum"]
    assert resultados[0] == Resultado("solana", pytest.approx(30), None)
    assert resultados[2].porcentaje == pytest.approx(-20)
    assert sin_datos == []


def test_comparar_sin_precios_suficientes():
    series = {"bitcoin": _serie(100, 110), "solana": _serie(100), "pepe": []}

    resultados, sin_datos = comparar(series, 168, AHORA)

    assert [r.coin_id for r in resultados] == ["bitcoin"]
    assert sin_datos == ["solana", "pepe"]


def test_comparar_sin_todo_el_tramo():
    serie = _serie(100, 110, dias=2)

    resultados, _ = comparar({"bitcoin": serie}, 168, AHORA)

    assert resultados[0].desde == serie[0][0]


def test_comparar_con_el_ultimo_precio_viejo():
    serie = _serie(100, 110, dias=7)
    viejo = [(cuando - timedelta(days=1), p) for cuando, p in _serie(100, 110, dias=5)]

    resultados, _ = comparar({"bitcoin": serie, "solana": viejo}, 168, AHORA)

    assert resultados[0].hasta is None
    assert resultados[1].hasta == viejo[-1][0]


def test_media():
    resultados = [Resultado(c, p, None) for c, p in [("a", 50), ("b", 10), ("c", -20)]]

    assert media(resultados) == pytest.approx(13.333, 0.001)
    assert media(resultados[:1]) is None
    assert media([]) is None


def test_en_base_100_todas_empiezan_igual():
    series = {"bitcoin": _serie(60000, 66000), "dogecoin": _serie(0.2, 0.15)}
    resultados, _ = comparar(series, 168, AHORA)

    lineas = en_base_100(series, resultados)

    assert [c for c, _ in lineas] == ["bitcoin", "dogecoin"]  # de mejor a peor
    (_, btc), (_, doge) = lineas
    assert [round(v, 6) for _, v in btc] == [100, 110]
    assert [round(v, 6) for _, v in doge] == [100, 75]
    assert btc[0][0] == series["bitcoin"][0][0]  # las fechas no se tocan


def test_en_base_100_salta_las_que_no_tienen_datos():
    series = {"bitcoin": _serie(100, 120), "pepe": []}
    resultados, sin_datos = comparar(series, 168, AHORA)

    assert [c for c, _ in en_base_100(series, resultados)] == ["bitcoin"]
    assert sin_datos == ["pepe"]
