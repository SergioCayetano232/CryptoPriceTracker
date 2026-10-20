"""Tests de /dca."""

from datetime import datetime, timedelta, timezone

import pytest

from crypto_tracker.alerts import formatear_dca
from crypto_tracker.dca import Plan, calcular, interpretar
from crypto_tracker.periodo import PeriodoError


@pytest.mark.parametrize(
    "argumento,esperado",
    [
        ("50 bitcoin semanal 90d", Plan(50, "bitcoin", "semanal", 2160)),
        ("50 btc", Plan(50, "bitcoin", "semanal", 2160)),  # semanal y 90 dias
        ("50€ btc 30d mensual", Plan(50, "bitcoin", "mensual", 720)),
        ("10 eur solana diario", Plan(10, "solana", "diario", 2160)),
        ("1k Ethereum 8sem", Plan(1000, "ethereum", "semanal", 1344)),
    ],
)
def test_interpretar(argumento, esperado):
    assert interpretar(argumento, "eur") == esperado


@pytest.mark.parametrize("argumento", ["", "50", "50 btc semanal 90d de mas"])
def test_interpretar_formato_malo(argumento):
    with pytest.raises(PeriodoError, match="/dca 50 bitcoin semanal 90d"):
        interpretar(argumento, "eur")


def test_interpretar_frecuencia_mala():
    with pytest.raises(PeriodoError, match="No entiendo 'anual'"):
        interpretar("50 btc anual", "eur")


def test_interpretar_cantidad_mala():
    with pytest.raises(PeriodoError, match="no es una cantidad"):
        interpretar("mucho btc", "eur")


def test_tramo_mas_corto_que_la_frecuencia():
    with pytest.raises(PeriodoError, match="/si"):
        interpretar("50 btc mensual 7d", "eur")


INICIO = datetime(2026, 9, 1, tzinfo=timezone.utc)


def _serie(precios, cada_horas=24):
    return [
        (INICIO + timedelta(hours=i * cada_horas), p) for i, p in enumerate(precios)
    ]


def test_calcular_una_compra_por_semana():
    # 15 dias de precios, uno al dia: compra el dia 0, el 7 y el 14
    precios = [100.0] * 7 + [50.0] * 7 + [200.0]
    r = calcular(_serie(precios), 100, 7 * 24)

    assert r.compras == 3
    assert r.cripto == pytest.approx(1 + 2 + 0.5)
    assert r.valor == pytest.approx(3.5 * 200)
    # Los 300 de golpe a 100 son 3, que ahora valen 600
    assert r.de_golpe == pytest.approx(600)


def test_calcular_con_el_bot_parado_no_junta_compras():
    # Del dia 0 salta al 20: las compras de en medio se pierden, no se hacen de golpe
    serie = [(INICIO, 100.0), (INICIO + timedelta(days=20), 100.0)]

    assert calcular(serie, 100, 7 * 24).compras == 2


def test_formatear_dca():
    texto = formatear_dca(100, "bitcoin", "cada semana", 3, 3.5, 700, 360, None, "eur")

    assert "Metiendo €100,00 en <b>Bitcoin</b> cada semana hace 15 días" in texto
    assert "hoy tendrías <b>€700,00</b>" in texto
    assert "+133.33% (+€400,00)" in texto
    assert "3 compras, €300,00 en total · precio medio €85,71" in texto


def test_formatear_dca_comparado_con_de_golpe():
    texto = formatear_dca(
        100, "bitcoin", "cada semana", 3, 3.5, 700, 360, None, "eur", de_golpe=600
    )

    assert "📦 Todo de golpe en la primera: €600,00 (+100.00%)" in texto
    assert "Mejor poco a poco, por €100,00" in texto


def test_formatear_dca_mejor_de_golpe():
    texto = formatear_dca(
        100, "bitcoin", "cada semana", 2, 1.5, 300, 360, None, "eur", de_golpe=400
    )

    assert "Mejor de golpe, por €100,00" in texto


def test_formatear_dca_con_una_compra_no_compara():
    texto = formatear_dca(
        50, "bitcoin", "cada día", 1, 1, 40, 2160, None, "eur", de_golpe=40
    )

    assert "de golpe" not in texto


def test_formatear_dca_sin_todo_el_tramo():
    desde = datetime(2026, 9, 20, 12, tzinfo=timezone.utc)
    texto = formatear_dca(50, "bitcoin", "cada día", 1, 1, 40, 2160, desde, "eur")

    assert "1 compra," in texto
    assert "Solo tengo precios desde entonces, no de hace 90 días" in texto
