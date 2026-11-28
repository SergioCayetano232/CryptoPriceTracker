"""Tests de /juntas."""

from datetime import date, timedelta

import pytest

from crypto_tracker.avisos import juntas
from crypto_tracker.avisos.alerts import formatear_aviso_juntas, formatear_juntas
from crypto_tracker.avisos.juntas import JuntasError, Medida, Pareja
from crypto_tracker.correlacion import Correlacion

HOY = date(2026, 11, 22)


def _dias(cambios, hoy=HOY):
    """Un precio por día, acabando hoy, a partir de los % de cada día."""
    precio, precios = 100.0, [100.0]
    for c in cambios:
        precio *= 1 + c / 100
        precios.append(precio)
    return [
        (hoy - timedelta(days=len(precios) - 1 - i), p) for i, p in enumerate(precios)
    ]


# Un mes yendo a la vez...
A_LA_VEZ = [2, -1, 3, -2, 1, -3, 2, 1, -1, 2, -2, 3, -1, 1, 2, -3, 1, -1, 2, -2]
# ...y los últimos diez días una sigue igual y la otra hace lo contrario.
ULTIMOS = [2, -2, 3, -1, 2, -3, 1, 2, -2, 1]


def _medida(corta, larga=0.9):
    return Medida(
        None if corta is None else Correlacion(corta, 9),
        None if larga is None else Correlacion(larga, 29),
        4.2,
        -7.9,
    )


def test_interpretar_siempre_en_el_mismo_orden():
    assert juntas.interpretar("eth btc") == ("bitcoin", "ethereum", False)
    assert juntas.interpretar("btc eth") == ("bitcoin", "ethereum", False)
    assert juntas.interpretar("eth btc no") == ("bitcoin", "ethereum", True)


@pytest.mark.parametrize(
    "texto, falla",
    [("btc", "De dos en dos"), ("btc eth sol", "De dos en dos"), ("btc btc", "misma")],
)
def test_interpretar_mal(texto, falla):
    with pytest.raises(JuntasError, match=falla):
        juntas.interpretar(texto)


def test_medir_dos_que_siguen_juntas():
    una = _dias(A_LA_VEZ + ULTIMOS)
    otra = _dias([c * 1.5 for c in A_LA_VEZ + ULTIMOS])

    m = juntas.medir(una, otra, HOY)

    assert m.corta.valor == pytest.approx(1, abs=0.01)
    assert m.larga.valor == pytest.approx(1, abs=0.01)
    assert juntas.van_juntas(m) is True


def test_medir_dos_que_se_separan_al_final():
    una = _dias(A_LA_VEZ + ULTIMOS)
    otra = _dias(A_LA_VEZ + [-c for c in ULTIMOS])

    m = juntas.medir(una, otra, HOY)

    assert m.corta.valor == pytest.approx(-1, abs=0.01)
    assert m.corta.dias == juntas.CORTA
    # En el mes todavía se nota que iban juntas, aunque menos.
    assert m.larga.valor > m.corta.valor
    assert m.cambio_una == pytest.approx((una[-1][1] / una[-11][1] - 1) * 100)
    assert m.cambio_otra < 0 < m.cambio_una


def test_medir_con_pocos_dias():
    m = juntas.medir(_dias([1, 2, -1]), _dias([1, 2, -1]), HOY)

    assert m.corta is None and m.larga is None
    assert juntas.van_juntas(m) is None


def test_avisa_al_separarse_y_solo_una_vez():
    assert juntas.toca(Pareja("a", "b"), _medida(0.5)) == (False, False)
    assert juntas.toca(Pareja("a", "b"), _medida(0.3)) == (True, True)
    assert juntas.toca(Pareja("a", "b", True), _medida(-0.2)) == (False, True)


def test_no_se_rearma_hasta_que_vuelven_a_ir_juntas():
    assert juntas.toca(Pareja("a", "b", True), _medida(0.5)) == (False, True)
    assert juntas.toca(Pareja("a", "b", True), _medida(0.6)) == (False, False)


def test_sin_dias_se_queda_como_estaba():
    assert juntas.toca(Pareja("a", "b"), _medida(None)) == (False, False)
    assert juntas.toca(Pareja("a", "b", True), _medida(None)) == (False, True)


def test_mensaje_del_aviso():
    texto = formatear_aviso_juntas(Pareja("bitcoin", "ethereum"), _medida(0.12, 0.85))

    assert "💔 <b>Bitcoin y Ethereum han dejado de ir juntas</b>" in texto
    assert "Estos 10 días: <b>+0,12</b>" in texto
    assert "En el mes: +0,85" in texto
    assert "Bitcoin +4,2% · Ethereum -7,9%" in texto
    assert "/comparar bitcoin ethereum 10d" in texto


def test_lista():
    texto = formatear_juntas([Pareja("bitcoin", "ethereum"), Pareja("a", "b", True)])

    assert "<b>Bitcoin</b> y <b>Ethereum</b>" in texto
    assert "<b>A</b> y <b>B</b> · separadas ahora" in texto
    assert "/juntas bitcoin ethereum no" in texto


def test_lista_vacia():
    assert "/juntas btc eth" in formatear_juntas([])
