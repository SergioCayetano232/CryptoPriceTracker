"""Tests de la grafica. No miran el dibujo, eso se mira a ojo."""

from datetime import datetime, timedelta, timezone

import pytest

from crypto_tracker.informes.grafica import (
    GraficaError,
    _eje,
    _formato_eje,
    _margen_eje,
    dibujar,
)

AHORA = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)


def _serie(precios):
    return [
        (AHORA - timedelta(minutes=5 * i), p) for i, p in enumerate(reversed(precios))
    ][::-1]


@pytest.mark.parametrize(
    "precios",
    [
        [60000.0, 61000.0, 59000.0, 62000.0],  # normal
        [100.0, 100.0, 100.0],  # plano: sin rango no puede petar
        [0.34, 0.33],  # de centimos
        [1.0, 2.0],  # lo minimo
    ],
)
def test_sale_un_png(precios):
    png = dibujar("bitcoin", _serie(precios), "eur", 24)

    assert png.startswith(b"\x89PNG")


def test_con_un_solo_precio_no_dibuja():
    with pytest.raises(GraficaError):
        dibujar("bitcoin", _serie([60000.0]), "eur", 24)


def test_sin_matplotlib_avisa_claro(monkeypatch):
    import builtins

    importar = builtins.__import__

    def sin_matplotlib(nombre, *a, **k):
        if nombre.startswith("matplotlib"):
            raise ImportError(nombre)
        return importar(nombre, *a, **k)

    monkeypatch.setattr(builtins, "__import__", sin_matplotlib)

    with pytest.raises(GraficaError, match="pip install"):
        dibujar("bitcoin", _serie([1.0, 2.0]), "eur", 24)


def test_numeros_del_eje():
    assert _eje(63000) == "63.000"
    assert _eje(0.3421) == "0,3421"
    assert _eje(0.00001234) == "0,00001234"


def test_el_eje_deja_sitio_a_los_numeros_largos():
    assert _margen_eje(80000) == 0.08  # lo de siempre no se mueve
    assert _margen_eje(0.0000055) > 0.08


def test_sale_un_png_de_una_cripto_de_centimos():
    serie = [(AHORA - timedelta(hours=h), 0.0000052 + h * 1e-9) for h in (2, 1, 0)]

    assert dibujar("shiba-inu", serie, "eur", 24).startswith(b"\x89PNG")


def test_sale_un_png_de_una_semana():
    serie = [(AHORA - timedelta(hours=h), 60000.0 + h) for h in range(168, -1, -1)]

    assert dibujar("bitcoin", serie, "eur", 168).startswith(b"\x89PNG")


@pytest.mark.parametrize(
    "horas, formato", [(24, "%H:%M"), (12, "%H:%M"), (48, "%d/%m %Hh"), (168, "%d/%m")]
)
def test_el_eje_pone_fechas_en_tramos_largos(horas, formato):
    assert _formato_eje(horas) == formato


def test_sale_un_png_de_la_cartera_con_lo_invertido():
    serie = _serie([1800.0, 2100.0, 1950.0])

    png = dibujar("cartera", serie, "eur", 168, titulo="Tu cartera", invertido=2000)

    assert png.startswith(b"\x89PNG")


def test_lo_invertido_lejos_de_la_serie_no_peta():
    assert dibujar("cartera", _serie([1.0, 2.0]), "eur", 24, invertido=1000).startswith(
        b"\x89PNG"
    )


# --- /tarjeta ---


def _tarjeta(total=66.7, tramo=12.5, linea=(0, 6, 12.5)):
    from datetime import date

    from crypto_tracker.informes.tarjeta import Tarjeta
    from crypto_tracker.reparto import Trozo

    reparto = [Trozo("bitcoin", 0, 75, 0), Trozo("otras", 0, 25, None)]
    return Tarjeta(total, tramo, 720, list(linea), reparto, date(2026, 11, 16))


def test_tarjeta_sale_un_png():
    from crypto_tracker.informes.grafica import dibujar_tarjeta

    assert dibujar_tarjeta(_tarjeta()).startswith(b"\x89PNG")


def test_tarjeta_sin_lo_invertido_ni_linea():
    from crypto_tracker.informes.grafica import dibujar_tarjeta

    assert dibujar_tarjeta(_tarjeta(total=None, linea=())).startswith(b"\x89PNG")


def test_tarjeta_sin_ningun_porcentaje():
    from crypto_tracker.informes.grafica import GraficaError, dibujar_tarjeta

    with pytest.raises(GraficaError):
        dibujar_tarjeta(_tarjeta(total=None, tramo=None, linea=()))


@pytest.mark.parametrize(
    "horas, sale",
    [
        (720, "en los últimos 30 días"),
        (24, "en las últimas 24 h"),
        (1, "en la última hora"),
    ],
)
def test_en_el_tramo(horas, sale):
    from crypto_tracker.informes.grafica import _en_el_tramo

    assert _en_el_tramo(horas) == sale


def test_comparar_nombres_cortos_y_el_cero_sin_signo():
    from crypto_tracker.informes.grafica import _corto, _pct_eje

    assert _corto("avalanche-2") == "AVAX"
    assert _corto("pepe") == "Pepe"
    assert _corto("una-cripto-larguisima") == "Una Cripto …"
    assert _pct_eje(0.0, 0) == "0%"
    assert _pct_eje(-0.3, 0) == "0%"
    assert _pct_eje(-0.3, 1) == "-0,3%"
    assert _pct_eje(10, 0) == "+10%"


def test_comparar_dibuja_y_rechaza_demasiadas():
    from datetime import datetime, timedelta, timezone

    from crypto_tracker.informes.grafica import GraficaError, dibujar_comparar

    ahora = datetime.now(timezone.utc)
    serie = [(ahora - timedelta(hours=1), 100.0), (ahora, 105.0)]

    assert dibujar_comparar([("bitcoin", serie)], 24).startswith(b"\x89PNG")
    with pytest.raises(GraficaError):
        dibujar_comparar([(f"c{i}", serie) for i in range(7)], 24)
    with pytest.raises(GraficaError):
        dibujar_comparar([], 24)


@pytest.mark.parametrize(
    "donde, sale",
    [(0.0, "left"), (0.11, "left"), (0.5, "center"), (0.89, "right"), (1.0, "right")],
)
def test_alineacion_de_las_etiquetas_en_los_bordes(donde, sale):
    from crypto_tracker.informes.grafica import _alineacion

    assert _alineacion(donde) == sale


def test_las_etiquetas_de_los_bordes_van_hacia_dentro(monkeypatch):
    # El mínimo al principio y el máximo al final, como en una subida.
    from matplotlib.axes import Axes

    from crypto_tracker.informes.grafica import dibujar

    puestas = []
    original = Axes.annotate

    def annotate(self, texto, *a, **k):
        puestas.append((texto, k.get("ha")))
        return original(self, texto, *a, **k)

    monkeypatch.setattr(Axes, "annotate", annotate)
    ahora = datetime(2026, 11, 23, tzinfo=timezone.utc)
    serie = [(ahora - timedelta(hours=100 - i), 1000.0 + i) for i in range(100)]

    dibujar("bitcoin", serie, "eur", 100)

    assert ("€1.099,00", "right") in puestas
    assert ("€1.000,00", "left") in puestas


def test_mapa_sale_un_png_con_una_o_con_treinta():
    from crypto_tracker.informes.grafica import dibujar_mapa
    from crypto_tracker.mapa import Casilla, Mapa

    una = Mapa([Casilla("bitcoin", "BTC", 1.0, 0.0)])
    treinta = Mapa(
        [Casilla(f"c{i}", f"C{i}", 1e12 / (i + 1) ** 2, i - 15.0) for i in range(30)]
    )

    assert dibujar_mapa(una, set()).startswith(b"\x89PNG")
    assert dibujar_mapa(treinta, {"c0", "c29"}).startswith(b"\x89PNG")


@pytest.mark.parametrize(
    "variacion, sale",
    [(0, "#334155"), (8, "#15803d"), (-20, "#b91c1c")],
)
def test_color_del_mapa(variacion, sale):
    from crypto_tracker.informes.grafica import _color_mapa

    assert _color_mapa(variacion) == sale


def test_en_el_mapa_lo_que_se_mueve_poco_sale_flojo():
    from crypto_tracker.informes.grafica import _color_mapa

    assert _color_mapa(0.5) not in {"#334155", "#15803d"}
    assert _color_mapa(0.5) != _color_mapa(4)
