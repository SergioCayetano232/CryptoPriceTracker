"""Tests de la grafica. No miran el dibujo, eso se mira a ojo."""

from datetime import datetime, timedelta, timezone

import pytest

from crypto_tracker.grafica import (
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
