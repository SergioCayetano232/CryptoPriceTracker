"""Tests de /promediar."""

import pytest

from crypto_tracker.alerts import formatear_promediar
from crypto_tracker.cartera import Valor
from crypto_tracker.promediar import PromediarError, Promedio, calcular, interpretar


def test_cuanto_comprar():
    # 0,016 a 62.500 de media, bitcoin a 40.000 y quieres que te salga a 50.000.
    p = calcular(Valor("bitcoin", 640.0, 1000.0, 0.016), 50000)

    assert p.comprar == pytest.approx(0.02)
    assert p.dinero == pytest.approx(800)
    # Comprobado al revés: lo metido entre lo que tienes da el medio pedido.
    assert (1000 + p.dinero) / (0.016 + p.comprar) == pytest.approx(50000)


def test_ya_te_sale_mas_barato():
    p = calcular(Valor("bitcoin", 640.0, 1000.0, 0.016), 70000)

    assert p.ya_esta
    assert p.comprar is None


@pytest.mark.parametrize("objetivo", [40000, 30000])
def test_por_debajo_del_precio_no_se_puede(objetivo):
    p = calcular(Valor("bitcoin", 640.0, 1000.0, 0.016), objetivo)

    assert p.imposible
    assert p.comprar is None


def test_sin_coste():
    assert calcular(Valor("bitcoin", 640.0, None, 0.016), 50000) is None


@pytest.mark.parametrize(
    "texto,esperado",
    [
        ("bitcoin 50000", ("bitcoin", 50000)),
        ("btc 50k", ("bitcoin", 50000)),
        ("eth 1.500 €", ("ethereum", 1500)),
    ],
)
def test_interpretar(texto, esperado):
    assert interpretar(texto) == esperado


@pytest.mark.parametrize("texto", ["", "bitcoin", "bitcoin cero", "btc -5", "a b c"])
def test_interpretar_mal(texto):
    with pytest.raises(PromediarError):
        interpretar(texto)


def test_formatear():
    texto = formatear_promediar(
        Promedio("bitcoin", 0.016, 62500.0, 40000.0, 50000.0), "eur"
    )

    assert texto.startswith("⚖️ <b>Para que Bitcoin te salga a €50.000,00</b>\n\n")
    assert "Compra <b>0,02 Bitcoin</b> por <b>€800,00</b>" in texto
    assert "al precio de ahora (€40.000,00)" in texto
    assert "Tienes 0,016 a €62.500,00 de media" in texto
    assert "tendrías 0,036 a €50.000,00" in texto


def test_formatear_ya_esta():
    texto = formatear_promediar(
        Promedio("bitcoin", 0.016, 62500.0, 40000.0, 70000.0), "eur"
    )

    assert texto.startswith("🟢 <b>Bitcoin</b> ya te sale a €62.500,00")


def test_formatear_imposible():
    texto = formatear_promediar(
        Promedio("bitcoin", 0.016, 62500.0, 40000.0, 30000.0), "eur"
    )

    assert texto.startswith("🔴 <b>Bitcoin</b> está a €40.000,00")
    assert "entre €40.000,00 y €62.500,00" in texto
