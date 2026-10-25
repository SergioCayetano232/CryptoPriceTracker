"""Tests de /ajustes."""

from datetime import time

from crypto_tracker.ajustes import lineas, mensaje
from crypto_tracker.config import Config


def _config(**cambios):
    datos = dict(
        telegram_token="t",
        telegram_chat_id="1",
        watchlist=[],
        vs_currency="eur",
        check_interval=330,
        database_path=":memory:",
        history_days=90,
    )
    return Config(**{**datos, **cambios})


def test_todo_puesto():
    texto = lineas(
        _config(
            resumen_diario=time(9, 0),
            brusco_porcentaje=8,
            brusco_minutos=60,
            extremos_dias=30,
            horas_tranquilas=(time(23, 0), time(8, 0)),
        )
    )

    assert texto == [
        "💱 Precios en EUR",
        "⏱️ Consulto cada 5 min 30 s",
        "💾 Guardo 90 días de precios",
        "📰 Resumen cada día a las 09:00",
        "⚡ Aviso si se mueve un 8% en 1 h",
        "📈 Aviso de máximos y mínimos de 30 días",
        "🌙 Sin sonar de 23:00 a 08:00",
    ]


def test_nada_puesto():
    texto = lineas(_config(history_days=0))

    assert "💾 Guardo todos los precios, no borro nada" in texto
    assert "📰 Sin resumen diario" in texto
    assert "⚡ Sin aviso de movimientos bruscos" in texto
    assert "📈 Sin aviso de máximos y mínimos" in texto
    assert "🌙 Los avisos suenan siempre" in texto


def test_brusco_con_decimales_y_minutos():
    texto = lineas(_config(brusco_porcentaje=2.5, brusco_minutos=90))

    assert "⚡ Aviso si se mueve un 2,5% en 1 h 30 min" in texto


def test_mensaje():
    texto = mensaje(_config())

    assert texto.startswith("⚙️ <b>Tus ajustes</b>")
    assert "/horario" in texto
