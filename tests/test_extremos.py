"""Tests de los avisos de maximo y minimo de los ultimos dias."""

from datetime import datetime, timedelta, timezone

from crypto_tracker.alerts import ALTO, BAJO, Alert, formatear
from crypto_tracker.extremos import revisar, toca

AHORA = datetime(2026, 10, 3, 12, tzinfo=timezone.utc)
HACE_30_DIAS = AHORA - timedelta(days=30)


def test_maximo():
    aviso = revisar("bitcoin", 70500.0, (HACE_30_DIAS, 70000.0, 55000.0), AHORA, 30)

    assert aviso == Alert("bitcoin", 70500.0, 70000.0, ALTO, extremo_dias=30)


def test_minimo():
    aviso = revisar("bitcoin", 54000.0, (HACE_30_DIAS, 70000.0, 55000.0), AHORA, 30)

    assert aviso.estado == BAJO
    assert aviso.threshold == 55000.0


def test_dentro_del_rango_no_avisa():
    assert (
        revisar("bitcoin", 60000.0, (HACE_30_DIAS, 70000.0, 55000.0), AHORA, 30) is None
    )


def test_igualar_el_maximo_no_es_superarlo():
    assert (
        revisar("bitcoin", 70000.0, (HACE_30_DIAS, 70000.0, 55000.0), AHORA, 30) is None
    )


def test_sin_historico_suficiente_no_avisa():
    hace_3_dias = AHORA - timedelta(days=3)

    assert (
        revisar("bitcoin", 99999.0, (hace_3_dias, 70000.0, 55000.0), AHORA, 30) is None
    )


def test_sin_nada_guardado():
    assert revisar("bitcoin", 70500.0, None, AHORA, 30) is None


def test_un_ciclo_de_retraso_vale():
    casi = HACE_30_DIAS + timedelta(minutes=5)

    assert revisar("bitcoin", 70500.0, (casi, 70000.0, 55000.0), AHORA, 30) is not None


def test_toca():
    assert toca(None, AHORA)
    assert not toca(AHORA - timedelta(hours=5), AHORA)
    assert toca(AHORA - timedelta(hours=24), AHORA)


def test_mensaje_de_maximo():
    aviso = Alert("bitcoin", 70500.0, 70000.0, ALTO, extremo_dias=30)

    texto = formatear(aviso, "eur")

    assert texto.startswith("🏔 <b>Bitcoin</b> marca su máximo de 30 días\n")
    assert "Ahora a <b>€70.500,00</b>, el anterior era €70.000,00" in texto


def test_mensaje_de_minimo():
    aviso = Alert("bitcoin", 54000.0, 55000.0, BAJO, extremo_dias=7)

    assert "🕳 <b>Bitcoin</b> marca su mínimo de 7 días" in formatear(aviso, "eur")
