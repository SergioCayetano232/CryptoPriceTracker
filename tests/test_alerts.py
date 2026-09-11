"""Tests de la logica de alertas."""

import pytest

from crypto_tracker.alerts import (
    ALTO,
    BAJO,
    NORMAL,
    clasificar,
    formatear,
    formatear_resumen,
    revisar,
)
from crypto_tracker.config import Watch

# --- clasificar ---


@pytest.mark.parametrize(
    "precio,esperado",
    [
        (40000, BAJO),
        (50000, NORMAL),  # justo en el minimo, todavia no es bajo
        (60000, NORMAL),
        (70000, NORMAL),  # justo en el maximo, todavia no es alto
        (80000, ALTO),
    ],
)
def test_clasificar_zonas(precio, esperado):
    watch = Watch("bitcoin", min_price=50000, max_price=70000)
    assert clasificar(precio, watch) == esperado


def test_clasificar_solo_maximo():
    watch = Watch("bitcoin", max_price=70000)
    assert clasificar(10, watch) == NORMAL
    assert clasificar(80000, watch) == ALTO


# --- umbrales fijos ---


def test_umbral_avisa_al_cruzar():
    watch = Watch("bitcoin", min_price=50000, max_price=70000)
    avisos, estado = revisar({"bitcoin": 75000}, [watch], {"bitcoin": NORMAL})

    assert len(avisos) == 1
    assert avisos[0].estado == ALTO
    assert avisos[0].threshold == 70000
    assert estado["bitcoin"] == ALTO


def test_umbral_no_repite_aviso():
    watch = Watch("bitcoin", min_price=50000, max_price=70000)
    avisos, _ = revisar({"bitcoin": 76000}, [watch], {"bitcoin": ALTO})

    assert avisos == []


def test_umbral_avisa_otra_vez_tras_volver_a_normal():
    watch = Watch("bitcoin", min_price=50000, max_price=70000)

    _, estado = revisar({"bitcoin": 75000}, [watch], {})
    _, estado = revisar({"bitcoin": 60000}, [watch], estado)
    avisos, _ = revisar({"bitcoin": 75000}, [watch], estado)

    assert len(avisos) == 1


def test_umbral_avisa_en_el_primer_ciclo_si_ya_esta_fuera():
    watch = Watch("bitcoin", min_price=50000, max_price=70000)
    avisos, _ = revisar({"bitcoin": 45000}, [watch], {})

    assert len(avisos) == 1
    assert avisos[0].estado == BAJO


# --- paso / variacion ---


def test_paso_primer_ciclo_no_avisa():
    watch = Watch("bitcoin", step=1000)
    avisos, estado = revisar({"bitcoin": 63500}, [watch], {})

    assert avisos == []
    assert float(estado["bitcoin"]) == 63000


def test_paso_avisa_al_subir_de_nivel():
    watch = Watch("bitcoin", step=1000)
    avisos, estado = revisar({"bitcoin": 64200}, [watch], {"bitcoin": "63000.0"})

    assert len(avisos) == 1
    assert avisos[0].estado == ALTO
    assert avisos[0].threshold == 64000
    assert float(estado["bitcoin"]) == 64000


def test_paso_avisa_al_bajar_de_nivel():
    watch = Watch("bitcoin", step=1000)
    avisos, _ = revisar({"bitcoin": 62800}, [watch], {"bitcoin": "63000.0"})

    assert len(avisos) == 1
    assert avisos[0].estado == BAJO
    # bajando de 63000 a 62800 lo que cruza es el 63000
    assert avisos[0].threshold == 63000


def test_paso_no_avisa_dentro_del_mismo_nivel():
    watch = Watch("bitcoin", step=1000)
    avisos, _ = revisar({"bitcoin": 63900}, [watch], {"bitcoin": "63000.0"})

    assert avisos == []


def test_paso_salto_grande_avisa_una_vez():
    watch = Watch("bitcoin", step=1000)
    avisos, estado = revisar({"bitcoin": 67500}, [watch], {"bitcoin": "63000.0"})

    assert len(avisos) == 1
    assert float(estado["bitcoin"]) == 67000


def test_paso_estado_viejo_no_numerico_se_ignora():
    # versiones antiguas guardaban "alto"/"bajo" en vez del nivel
    watch = Watch("bitcoin", step=1000)
    avisos, estado = revisar({"bitcoin": 63500}, [watch], {"bitcoin": "alto"})

    assert avisos == []
    assert float(estado["bitcoin"]) == 63000


# --- varias criptos ---


def test_sin_precio_mantiene_el_estado():
    watch = Watch("bitcoin", min_price=50000, max_price=70000)
    avisos, estado = revisar({}, [watch], {"bitcoin": ALTO})

    assert avisos == []
    assert estado["bitcoin"] == ALTO


def test_varias_criptos_a_la_vez():
    watchlist = [
        Watch("bitcoin", max_price=70000),
        Watch("ethereum", step=100),
    ]
    precios = {"bitcoin": 75000, "ethereum": 3250}
    avisos, _ = revisar(precios, watchlist, {"ethereum": "3100.0"})

    assert {a.coin_id for a in avisos} == {"bitcoin", "ethereum"}


# --- formateo ---


def test_formatear_incluye_precio_y_umbral():
    watch = Watch("bitcoin", max_price=70000)
    avisos, _ = revisar({"bitcoin": 75000}, [watch], {"bitcoin": NORMAL})
    texto = formatear(avisos[0], "eur")

    assert "Bitcoin" in texto
    assert "70.000,00" in texto
    assert "75.000,00" in texto
    assert "🚀" in texto


def test_formatear_baratas_con_mas_decimales():
    watch = Watch("dogecoin", min_price=0.5)
    avisos, _ = revisar({"dogecoin": 0.3421}, [watch], {"dogecoin": NORMAL})
    texto = formatear(avisos[0], "usd")

    assert "0,3421" in texto
    assert "🔻" in texto


def test_formatear_escapa_html():
    from crypto_tracker.alerts import Alert

    alerta = Alert("<b>hack</b>", 100, 90, ALTO)
    texto = formatear(alerta, "eur")

    assert "<b>hack</b>" not in texto
    assert "&lt;" in texto


# --- resumen ---


def test_resumen_con_variacion():
    texto = formatear_resumen([("bitcoin", 63000.0, 5.0)], "eur")

    assert "Bitcoin" in texto
    assert "63.000,00" in texto
    assert "+5.00%" in texto
    assert "🔺" in texto


def test_resumen_con_bajada():
    texto = formatear_resumen([("bitcoin", 57000.0, -4.25)], "eur")

    assert "-4.25%" in texto
    assert "🔻" in texto


def test_resumen_sin_historico():
    texto = formatear_resumen([("bitcoin", 63000.0, None)], "eur")

    assert "sin histórico" in texto
    assert "%" not in texto


def test_resumen_varias_criptos():
    texto = formatear_resumen(
        [("bitcoin", 63000.0, 5.0), ("ethereum", 3200.0, -2.0)], "eur"
    )

    assert len(texto.splitlines()) == 4  # titulo, blanco y dos criptos
    assert "Ethereum" in texto


def test_resumen_escapa_html():
    texto = formatear_resumen([("<b>hack</b>", 100.0, 1.0)], "eur")

    assert "<b>hack</b>" not in texto
    assert "&lt;" in texto


# --- porcentaje ---


def test_porcentaje_primera_vez_no_avisa():
    watch = Watch("bitcoin", percent=5)

    avisos, estado = revisar({"bitcoin": 60000}, [watch], {})

    assert avisos == []
    assert estado["bitcoin"] == "%60000"


def test_porcentaje_avisa_al_subir():
    watch = Watch("bitcoin", percent=5)

    avisos, estado = revisar({"bitcoin": 63000}, [watch], {"bitcoin": "%60000"})

    assert len(avisos) == 1
    assert avisos[0].estado == ALTO
    assert avisos[0].percent == pytest.approx(5.0)
    assert avisos[0].threshold == 60000
    assert estado["bitcoin"] == "%63000"


def test_porcentaje_avisa_al_bajar():
    watch = Watch("bitcoin", percent=5)

    avisos, _ = revisar({"bitcoin": 56000}, [watch], {"bitcoin": "%60000"})

    assert avisos[0].estado == BAJO
    assert avisos[0].percent == pytest.approx(-6.6667, abs=0.001)


def test_porcentaje_no_avisa_si_se_queda_corto():
    watch = Watch("bitcoin", percent=5)

    avisos, estado = revisar({"bitcoin": 62000}, [watch], {"bitcoin": "%60000"})

    assert avisos == []
    # la referencia no se mueve: si no, nunca acumularia hasta el 5%
    assert estado["bitcoin"] == "%60000"


def test_porcentaje_acumula_hasta_saltar():
    watch = Watch("bitcoin", percent=5)
    estado = {"bitcoin": "%60000"}

    for precio in (61000, 62000, 62500):
        avisos, estado = revisar({"bitcoin": precio}, [watch], estado)
        assert avisos == []

    avisos, estado = revisar({"bitcoin": 63500}, [watch], estado)

    assert len(avisos) == 1
    assert estado["bitcoin"] == "%63500"


def test_porcentaje_la_referencia_se_mueve_con_cada_aviso():
    # una subida larga avisa por tramos, no una sola vez
    watch = Watch("bitcoin", percent=5)
    estado = {"bitcoin": "%60000"}

    avisos, estado = revisar({"bitcoin": 63000}, [watch], estado)
    assert len(avisos) == 1

    avisos, estado = revisar({"bitcoin": 66200}, [watch], estado)
    assert len(avisos) == 1
    assert avisos[0].threshold == 63000


def test_porcentaje_ignora_un_estado_de_otro_formato():
    # si antes era bitcoin:1000 el estado guardado es "63000", sin el %
    watch = Watch("bitcoin", percent=5)

    avisos, estado = revisar({"bitcoin": 63000}, [watch], {"bitcoin": "63000"})

    assert avisos == []
    assert estado["bitcoin"] == "%63000"


def test_formatear_porcentaje():
    from crypto_tracker.alerts import Alert

    alerta = Alert("bitcoin", 63000.0, 60000.0, ALTO, percent=5.0)
    texto = formatear(alerta, "eur")

    assert "5.00%" in texto
    assert "63.000,00" in texto
    assert "60.000,00" in texto
