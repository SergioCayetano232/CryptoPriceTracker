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
            caida_cartera=20,
            concentracion=70,
            aviso_rsi=True,
            aviso_cruce=True,
            aviso_volumen=True,
            aviso_calma=True,
            copia_semanal=True,
            horas_tranquilas=(time(23, 0), time(8, 0)),
            latido_url="https://hc-ping.com/abc",
        )
    )

    assert texto == [
        "💱 Precios en EUR",
        "⏱️ Consulto cada 5 min 30 s",
        "💾 Guardo 90 días de precios",
        "📰 Resumen cada día a las 09:00",
        "⚡ Aviso si se mueve un 8% en 1 h",
        "📈 Aviso de máximos y mínimos de 30 días",
        "📉 Aviso si la cartera cae un 20% desde su récord",
        "⚖️ Aviso si una cripto pasa del 70% de la cartera",
        "🔥 Aviso al entrar en sobrecompra o sobreventa",
        "🌟 Aviso de cruz dorada y de la muerte",
        "📢 Aviso si el volumen pasa del triple de lo normal",
        "🤫 Aviso si una se queda mucho más quieta de lo normal",
        "📦 Copia de seguridad cada semana",
        "🌙 Sin sonar de 23:00 a 08:00",
        "💓 Latido a hc-ping.com en cada consulta",
    ]


def test_nada_puesto():
    texto = lineas(_config(history_days=0))

    assert "💾 Guardo todos los precios, no borro nada" in texto
    assert "📰 Sin resumen diario" in texto
    assert "⚡ Sin aviso de movimientos bruscos" in texto
    assert "📈 Sin aviso de máximos y mínimos" in texto
    assert "🔥 Sin aviso de RSI" in texto
    assert "🌟 Sin aviso de cruce de medias" in texto
    assert "🤫 Sin aviso de calma" in texto
    assert "🌙 Los avisos suenan siempre" in texto


def test_brusco_con_decimales_y_minutos():
    texto = lineas(_config(brusco_porcentaje=2.5, brusco_minutos=90))

    assert "⚡ Aviso si se mueve un 2,5% en 1 h 30 min" in texto


def test_mensaje():
    texto = mensaje(_config())

    assert texto.startswith("⚙️ <b>Tus ajustes</b>")
    assert "/horario" in texto


def test_latido_enseña_el_servicio_pero_no_la_clave():
    texto = lineas(_config(latido_url="https://hc-ping.com/mi-clave"))

    assert "💓 Latido a hc-ping.com en cada consulta" in texto
    assert "mi-clave" not in "".join(texto)


def test_sin_latido():
    assert "💓 Sin latido a un servicio de fuera" in lineas(_config())


def test_a_un_invitado_no_le_sale_el_latido():
    texto = lineas(_config(latido_url="https://hc-ping.com/x", invitado=True))

    assert not any("atido" in linea for linea in texto)
