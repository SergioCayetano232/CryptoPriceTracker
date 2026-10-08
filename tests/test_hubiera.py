"""Tests de /si."""

from datetime import datetime, timezone

import pytest

from crypto_tracker.alerts import formatear_hubiera
from crypto_tracker.hubiera import Pregunta, interpretar
from crypto_tracker.periodo import PeriodoError


@pytest.mark.parametrize(
    "argumento,esperado",
    [
        ("1000 bitcoin 30d", Pregunta(1000, "bitcoin", 720)),
        ("1000 btc", Pregunta(1000, "bitcoin", 720)),  # sin tramo, 30 dias
        ("500€ Solana 7d", Pregunta(500, "solana", 168)),
        ("500 € solana 12h", Pregunta(500, "solana", 12)),
        ("1.000 eur ethereum", Pregunta(1000, "ethereum", 720)),
        ("1k bitcoin", Pregunta(1000, "bitcoin", 720)),
    ],
)
def test_interpretar(argumento, esperado):
    assert interpretar(argumento, "eur") == esperado


@pytest.mark.parametrize("argumento", ["", "1000", "1000 bitcoin 30d de mas"])
def test_interpretar_formato_malo(argumento):
    with pytest.raises(PeriodoError, match="/si 1000 bitcoin 30d"):
        interpretar(argumento, "eur")


@pytest.mark.parametrize("cantidad", ["mucho", "0", "-5"])
def test_interpretar_cantidad_mala(cantidad):
    with pytest.raises(PeriodoError, match="no es una cantidad"):
        interpretar(f"{cantidad} bitcoin", "eur")


def test_interpretar_tramo_malo():
    with pytest.raises(PeriodoError):
        interpretar("1000 bitcoin mucho", "eur")


def test_formatear_ganando():
    texto = formatear_hubiera(1000, "bitcoin", 50000, 60000, 720, None, "eur")

    assert "€1.000,00 en <b>Bitcoin</b> hace 30 días" in texto
    assert "hoy tendrías <b>€1.200,00</b>" in texto
    assert "🔺 +20.00% (+€200,00)" in texto
    assert "Entonces €50.000,00 · ahora €60.000,00" in texto
    assert "Solo tengo" not in texto


def test_formatear_perdiendo():
    texto = formatear_hubiera(1000, "bitcoin", 60000, 45000, 12, None, "eur")

    assert "hace 12 h" in texto
    assert "<b>€750,00</b>" in texto
    assert "🔻 -25.00% (-€250,00)" in texto


def test_formatear_sin_todo_el_tramo():
    desde = datetime(2026, 10, 3, 10, 0, tzinfo=timezone.utc)

    texto = formatear_hubiera(1000, "bitcoin", 50000, 60000, 720, desde, "eur")

    assert f"Bitcoin</b> el {desde.astimezone():%d/%m}," in texto
    assert "Solo tengo precios desde entonces, no de hace 30 días" in texto
