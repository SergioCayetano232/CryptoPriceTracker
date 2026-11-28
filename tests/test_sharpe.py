"""Tests de /sharpe."""

import math
from datetime import date, timedelta

import pytest

from crypto_tracker.avisos.alerts import formatear_sharpe
from crypto_tracker.sharpe import (
    DIAS,
    MIN_CAMBIOS,
    Sharpe,
    SharpeError,
    calcular,
    interpretar,
    nota,
)

INICIO = date(2026, 6, 1)


def _dias(valores, desde=INICIO):
    return [(desde + timedelta(days=i), v) for i, v in enumerate(valores)]


def _serie(n, sube, baja):
    """Un día sube, al otro baja: así se mueve pero sabemos cuánto."""
    valores = [1000.0]
    for i in range(n):
        valores.append(valores[-1] * (1 + (sube if i % 2 == 0 else baja)))
    return valores


@pytest.mark.parametrize(
    "texto, esperado",
    [("", DIAS), ("180d", 180), ("30", 30), ("365 días", 365), ("60 dias", 60)],
)
def test_interpretar(texto, esperado):
    assert interpretar(texto) == esperado


@pytest.mark.parametrize("texto", ["7d", "400", "siempre", "3m"])
def test_interpretar_mal(texto):
    with pytest.raises(SharpeError):
        interpretar(texto)


def test_cuentas():
    s = calcular(_dias(_serie(40, 0.03, -0.01)))

    cambios = [math.log(1.03), math.log(0.99)] * 20
    media = sum(cambios) / 40
    desviacion = math.sqrt(sum((c - media) ** 2 for c in cambios) / 39)
    assert s.contados == 40
    assert s.gana == pytest.approx((1.03**20 * 0.99**20 - 1) * 100)
    assert s.se_mueve == pytest.approx(desviacion * math.sqrt(365) * 100)
    assert s.ratio == pytest.approx(media / desviacion * math.sqrt(365))
    assert s.nota == "muy bueno"


def test_el_signo_cuadra_con_lo_ganado():
    # +10% y -10% cada día: la media simple da cero, pero se pierde dinero.
    s = calcular(_dias(_serie(40, 0.10, -0.10)))
    assert s.gana < 0
    assert s.ratio < 0


def test_perdiendo_sale_negativo():
    s = calcular(_dias(_serie(40, 0.01, -0.03)))
    assert s.ratio < 0
    assert s.nota.startswith("pierdes")


def test_mismo_ratio_con_mas_dinero():
    poco = calcular(_dias(_serie(40, 0.03, -0.01)))
    mucho = calcular(_dias([v * 50 for v in _serie(40, 0.03, -0.01)]))
    assert mucho.ratio == pytest.approx(poco.ratio)


def test_el_salto_de_un_hueco_no_cuenta():
    # Bot parado un mes y al volver la cartera vale el doble: no es un día.
    antes = _dias(_serie(20, 0.02, -0.02))
    despues = _dias(
        [v * 2 for v in _serie(20, 0.02, -0.02)], desde=INICIO + timedelta(days=60)
    )
    s = calcular(antes + despues)

    assert s.contados == 40
    assert abs(s.gana) < 2


def test_pocos_dias():
    assert calcular(_dias(_serie(MIN_CAMBIOS - 1, 0.03, -0.01))) is None


def test_quieta():
    assert calcular(_dias([1000.0] * 50)) is None


@pytest.mark.parametrize(
    "ratio, empieza",
    [
        (-0.3, "pierdes"),
        (0.2, "flojo"),
        (0.5, "aceptable"),
        (1.5, "bueno"),
        (2.0, "muy"),
    ],
)
def test_nota(ratio, empieza):
    assert nota(ratio).startswith(empieza)


def _hecho(ratio, nota_):
    return Sharpe(ratio, 45.2, 32.1, 89, nota_)


def test_formatear():
    texto = formatear_sharpe(_hecho(1.4, "bueno"), _hecho(0.85, "aceptable"), 90)

    assert "📐 <b>Tu Sharpe de los últimos 90 días: 1,40</b>" in texto
    assert "Nota: bueno" in texto
    assert "🔺 En estos días: 45,2%" in texto
    assert "Se mueve al año: 32,1%" in texto
    assert "₿ Bitcoin: 0,85 (aceptable)" in texto
    assert "Mejor que bitcoin" in texto
    assert "89 días" in texto


def test_formatear_peor_que_bitcoin():
    texto = formatear_sharpe(_hecho(0.3, "flojo"), _hecho(1.2, "bueno"), 90)
    assert "Peor que bitcoin" in texto


def test_formatear_casi_igual():
    texto = formatear_sharpe(_hecho(1.0, "bueno"), _hecho(1.05, "bueno"), 90)
    assert "Casi igual que bitcoin" in texto


def test_formatear_sin_bitcoin():
    assert "Bitcoin" not in formatear_sharpe(_hecho(1.4, "bueno"), None, 90)
