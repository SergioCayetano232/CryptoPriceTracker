"""Tests de /horas."""

from datetime import datetime, timedelta

import pytest

from crypto_tracker.alerts import formatear_horas
from crypto_tracker.horas import Horas, calcular, interpretar
from crypto_tracker.periodo import PeriodoError

INICIO = datetime(2026, 10, 5).astimezone()  # medianoche de aquí


def _dia(dia, precios):
    """Un precio por hora, desde las 00:00 de ese día."""
    base = INICIO + timedelta(days=dia)
    return [(base + timedelta(hours=h), p) for h, p in enumerate(precios)]


def test_barata_y_cara():
    # Todas a 100 salvo las 4, a 98, y las 17, a 102.
    precios = [100.0] * 24
    precios[4], precios[17] = 98.0, 102.0

    h = calcular(_dia(0, precios) + _dia(1, precios))

    assert h.dias == 2
    assert h.barata == 4
    assert h.cara == 17
    assert h.medias[4] == pytest.approx(-2)
    assert len(h.medias) == 24


def test_compara_con_la_media_de_cada_dia():
    # El segundo día está todo un 10% más arriba, pero la forma es la misma.
    lunes = [100.0] * 24
    lunes[3] = 99.0
    martes = [p * 1.1 for p in lunes]

    h = calcular(_dia(0, lunes) + _dia(1, martes))

    assert h.barata == 3
    assert h.medias[23] == pytest.approx(h.medias[0])


def test_salta_los_dias_con_pocas_horas():
    completo = [100.0] * 24
    completo[6] = 90.0
    corto = [50.0] * 10

    h = calcular(_dia(0, completo) + _dia(1, corto))

    assert h.dias == 1
    assert h.barata == 6


def test_sin_dias_completos():
    assert calcular([]) is None
    assert calcular(_dia(0, [100.0] * 19)) is None


def test_interpretar():
    assert interpretar("btc 7d") == ("bitcoin", 7 * 24)
    assert interpretar("solana") == ("solana", 30 * 24)
    assert interpretar("") == ("", 30 * 24)
    with pytest.raises(PeriodoError):
        interpretar("btc eth")


def test_ahorro():
    h = Horas({4: -1.0, 17: 1.0}, 3)

    # 99 en vez de 101
    assert h.ahorro == pytest.approx(1.98, abs=0.01)


def test_formatear_sin_diferencia_no_dice_ahorro():
    texto = formatear_horas("eth", Horas({1: 0.0, 2: 0.0}, 1), 7 * 24)

    assert "Comprando" not in texto


def test_formatear():
    medias = {h: 0.0 for h in range(24)}
    medias[4], medias[17] = -0.8, 0.6

    texto = formatear_horas("bitcoin", Horas(medias, 12), 30 * 24)

    assert texto.startswith("🕐 <b>Bitcoin</b> por horas, últimos 30 días")
    assert "🟢 Más barata sobre las <b>04:00</b> (-0.80%)" in texto
    assert "🔴 Más cara sobre las <b>17:00</b> (+0.60%)" in texto
    assert "Comprando a las 04:00 y no a las 17:00, un <b>1.39%</b> más barato" in texto
    assert "<code>00h ▅▅▅▅▁" in texto
    assert "en 12 días completos" in texto
    assert "no lo tomes como una regla" not in texto


def test_formatear_sin_todas_las_horas_y_poca_diferencia():
    texto = formatear_horas("eth", Horas({1: -0.1, 2: 0.1}, 1), 7 * 24)

    assert "<code>" not in texto
    assert "en 1 día completo" in texto
    assert "no lo tomes como una regla" in texto


def test_formatear_dice_como_suele_estar_ahora():
    medias = {h: 0.0 for h in range(24)}
    medias[4], medias[17] = -0.8, 0.6

    barata = formatear_horas("btc", Horas(medias, 5), 30 * 24, INICIO.replace(hour=4))
    cara = formatear_horas("btc", Horas(medias, 5), 30 * 24, INICIO.replace(hour=17))
    igual = formatear_horas("btc", Horas(medias, 5), 30 * 24, INICIO.replace(hour=9))

    assert "Ahora son las 04:00: a esta hora suele estar -0.80%, más barata" in barata
    assert "Ahora son las 17:00: a esta hora suele estar +0.60%, más cara" in cara
    assert "+0.00%, justo en la media del día" in igual


def test_formatear_sin_datos_de_la_hora_de_ahora():
    texto = formatear_horas("eth", Horas({1: -0.1, 2: 0.1}, 1), 7 * 24, INICIO)

    assert "Ahora son" not in texto
