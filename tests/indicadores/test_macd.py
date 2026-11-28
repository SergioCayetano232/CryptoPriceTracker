"""Tests de /macd."""

from datetime import date, timedelta

import pytest

from crypto_tracker.avisos.alerts import formatear_macd
from crypto_tracker.indicadores.macd import MINIMO, Macd, calcular

INICIO = date(2026, 6, 1)


# Cae cada vez más deprisa: el MACD va claramente por debajo de su señal.
CAYENDO = [300.0 - 0.1 * i**2 for i in range(40)]


def _rebote(n):
    return [CAYENDO[-1] + 0.5 * j**2 for j in range(1, n + 1)]


def _dias(valores, desde=INICIO):
    return [(desde + timedelta(days=i), v) for i, v in enumerate(valores)]


def test_en_linea_recta():
    # Subiendo 1 al día, la de 12 va 5,5 días por detrás y la de 26, 12,5.
    m = calcular(_dias([100.0 + i for i in range(200)]))

    assert m.macd == pytest.approx(7, abs=0.01)
    assert m.señal == pytest.approx(7, abs=0.01)
    assert m.ahora == 299
    assert m.dias == 200


def test_quieta():
    m = calcular(_dias([100.0] * 60))
    assert m.macd == 0 and m.señal == 0 and m.histograma == 0
    assert m.cruce_hace is None


def test_cayendo():
    m = calcular(_dias(CAYENDO))
    assert not m.arriba
    assert m.macd < 0
    assert m.cruce_hace is None


def test_cruce_hacia_arriba():
    m = calcular(_dias(CAYENDO + _rebote(10)))

    assert m.arriba
    assert m.cruce_hace is not None and m.cruce_hace < 10
    assert m.cogiendo_fuerza

    # El día de antes del cruce aún iba por debajo.
    antes = calcular(_dias((CAYENDO + _rebote(10))[: -m.cruce_hace - 1]))
    assert not antes.arriba


def test_cruce_de_hoy():
    for n in range(1, 20):
        m = calcular(_dias(CAYENDO + _rebote(n)))
        if m.arriba:
            break
    assert m.cruce_hace == 0


def test_solo_el_ultimo_tramo_seguido():
    viejos = _dias([100.0] * 50)
    nuevos = _dias([100.0] * MINIMO, desde=INICIO + timedelta(days=80))
    assert calcular(viejos + nuevos) is None
    assert calcular(_dias([100.0] * (MINIMO + 1))).dias == MINIMO + 1


def test_pocos_dias():
    assert calcular(_dias([100.0] * MINIMO)) is None
    assert calcular([]) is None


def test_formatear_arriba():
    m = Macd(1500.0, 1200.0, 80000.0, 200.0, 3, 90)
    texto = formatear_macd("bitcoin", m, "eur")

    assert "📶 <b>Bitcoin</b>: MACD de 12 y 26 días" in texto
    assert "🐂 <b>Empuje al alza</b>" in texto
    assert "Desde hace 3 días" in texto
    assert "💪 Y cogiendo fuerza" in texto
    assert "De fondo sube" in texto
    assert "MACD €1.500,00 · Señal €1.200,00 · Diferencia +€300,00" in texto


def test_formatear_abajo():
    m = Macd(-1500.0, -1200.0, 80000.0, -400.0, 0, 90)
    texto = formatear_macd("bitcoin", m, "eur")

    assert "🐻 <b>Empuje a la baja</b>" in texto
    assert "✂️ La ha cruzado hoy" in texto
    assert "perdiendo fuerza" in texto
    assert "De fondo baja" in texto
    assert "Diferencia -€300,00" in texto


@pytest.mark.parametrize(
    "hace, frase", [(1, "La cruzó ayer"), (None, "en todos los 90 días")]
)
def test_formatear_cruce(hace, frase):
    m = Macd(10.0, 5.0, 100.0, 1.0, hace, 90)
    assert frase in formatear_macd("bitcoin", m, "eur")
