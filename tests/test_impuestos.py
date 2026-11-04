"""Tests de /impuestos."""

from datetime import datetime, timezone

import pytest

from crypto_tracker.alerts import formatear_impuestos
from crypto_tracker.config import Posicion
from crypto_tracker.impuestos import (
    Impuestos,
    ImpuestosError,
    calcular,
    interpretar,
    por_tramos,
)
from crypto_tracker.movimientos import Movimiento


def _venta(cobrado, antes, año=2026):
    cuando = datetime(año, 6, 1, tzinfo=timezone.utc)
    return Movimiento(1, "bitcoin", "venta", antes.cantidad, cobrado, antes, cuando)


def test_por_debajo_del_primer_tramo():
    assert por_tramos(1000) == [(19, pytest.approx(1000), pytest.approx(190))]


def test_varios_tramos():
    tramos = por_tramos(60_000)

    assert [t for t, _, _ in tramos] == [19, 21, 23]
    assert [b for _, b, _ in tramos] == pytest.approx([6000, 44000, 10000])
    # 1.140 + 9.240 + 2.300
    assert sum(c for _, _, c in tramos) == pytest.approx(12680)


def test_el_ultimo_tramo_no_tiene_techo():
    tramos = por_tramos(400_000)

    assert tramos[-1][:2] == (30, pytest.approx(100_000))


def test_perdiendo_no_hay_tramos():
    assert por_tramos(-500) == []
    assert por_tramos(0) == []


def test_solo_cuenta_las_ventas_del_año():
    ventas = [
        _venta(3000, Posicion("bitcoin", 0.02, 1000), año=2025),
        _venta(1500, Posicion("bitcoin", 0.01, 1000), año=2026),
    ]

    i = calcular(ventas, 2026)

    assert i.ventas == 1
    assert i.ganancia == pytest.approx(500)
    assert i.total == pytest.approx(95)
    assert i.tipo_medio == pytest.approx(19)


def test_venta_sin_coste_no_cuenta():
    ventas = [_venta(1500, Posicion("bitcoin", 0.01, None))]

    i = calcular(ventas, 2026)

    assert i.sin_datos == 1
    assert i.ganancia == 0


@pytest.mark.parametrize("texto, año", [("", 2026), ("2025", 2025), (" 2024 ", 2024)])
def test_interpretar(texto, año):
    assert interpretar(texto, 2026) == año


@pytest.mark.parametrize("texto", ["2027", "1999", "ayer", "-2025"])
def test_interpretar_mal(texto):
    with pytest.raises(ImpuestosError):
        interpretar(texto, 2026)


def test_formatear():
    i = Impuestos(2026, 10_000, por_tramos(10_000), 1, 3)

    texto = formatear_impuestos(i, "eur")

    assert texto.startswith("🏛️ <b>Impuestos de 2026</b>\n\n")
    assert "Has ganado vendiendo <b>+€10.000,00</b>" in texto
    assert "Al 19%: €6.000,00 → €1.140,00" in texto
    assert "Al 21%: €4.000,00 → €840,00" in texto
    assert "A Hacienda, unos <b>€1.980,00</b>  <i>(19.80% de media)</i>" in texto
    assert "No cuento 1 venta" in texto
    assert "FIFO" in texto
    assert "Ojo" not in texto


def test_formatear_perdiendo():
    texto = formatear_impuestos(Impuestos(2026, -300, [], 0, 1), "eur")

    assert "has perdido <b>-€300,00</b>" in texto
    assert "No pagas nada" in texto
    assert "Hacienda, unos" not in texto


def test_formatear_sin_ventas():
    texto = formatear_impuestos(Impuestos(2025, 0, [], 0, 0), "eur")

    assert texto == "En 2025 no has vendido nada, así que no hay nada que declarar."


def test_formatear_en_dolares_avisa():
    texto = formatear_impuestos(Impuestos(2026, 100, por_tramos(100), 0, 1), "usd")

    assert "Hacienda lo quiere en euros" in texto
