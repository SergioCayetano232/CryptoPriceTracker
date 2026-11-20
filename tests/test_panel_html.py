"""Tests de la página del panel."""

from datetime import datetime, timedelta, timezone

from crypto_tracker import panel
from crypto_tracker.config import Posicion, Watch
from crypto_tracker.panel_html import pagina
from crypto_tracker.puntuales import Puntual

AHORA = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)


def _panel(**cambios):
    filas, _ = panel.filas_cartera(
        [Posicion("bitcoin", 0.1, 5000.0)], {"bitcoin": 60000.0}, {}, {}
    )
    datos = {
        "moneda": "eur",
        "filas": filas,
        "vigiladas": [],
        "alertas": [],
        "serie": [],
        "actualizado": AHORA - timedelta(minutes=2),
    }
    datos.update(cambios)
    return panel.Panel(**datos)


def test_sale_el_total_y_lo_ganado():
    html = pagina(_panel(), AHORA, parado=False)

    assert "€6.000,00" in html
    assert "€1.000,00 · +20,00 %" in html
    assert "Actualizado hace 2 min" in html


def test_sin_cartera_explica_como_ponerla():
    html = pagina(_panel(filas=[]), AHORA, parado=False)

    assert "Sin cartera" in html
    assert "/compra" in html
    assert "Lo que tienes" not in html


def test_avisa_si_el_bot_esta_parado():
    html = pagina(_panel(actualizado=AHORA - timedelta(hours=3)), AHORA, parado=True)

    assert "estado--parado" in html
    assert "no guarda precios desde hace 3 h" in html


def test_la_nota_de_una_alerta_no_se_cuela_como_html():
    [alerta] = panel.alertas(
        [Puntual(1, "bitcoin", 70000.0, True, nota="<script>x</script>")],
        {"bitcoin": 60000.0},
        None,
    )

    html = pagina(_panel(alertas=[alerta]), AHORA, parado=False)

    assert "<script>x</script>" not in html
    assert "&lt;script&gt;x&lt;/script&gt;" in html
    assert "16,7 %" in html
    assert "le falta subir" in html


def test_alerta_que_ya_ha_llegado():
    [alerta] = panel.alertas(
        [Puntual(1, "bitcoin", 50000.0, True)], {"bitcoin": 60000.0}, None
    )

    html = pagina(_panel(alertas=[alerta]), AHORA, parado=False)

    assert "Ya está" in html


def test_grafica_con_pocos_datos():
    html = pagina(_panel(), AHORA, parado=False)

    assert "Aún no hay precios suficientes" in html


def test_grafica_con_datos():
    serie = [(AHORA - timedelta(hours=h), 6000.0 + h) for h in range(10, 0, -1)]

    html = pagina(_panel(serie=serie), AHORA, parado=False)

    assert 'class="grafica__linea"' in html
    assert "€6.010,00" in html  # el máximo


def test_vigiladas_con_su_regla():
    v = panel.Vigilada("bitcoin", Watch("bitcoin", percent=5), 60000.0, 2.5)

    html = pagina(_panel(vigiladas=[v]), AHORA, parado=False)

    assert "cada 5 % que se mueva" in html
    assert "+2,50 %" in html


def test_siempre_lleva_lo_de_coingecko():
    # El plan gratis pide citarles junto a los datos.
    assert "Price data by CoinGecko" in pagina(_panel(), AHORA, parado=False)
