"""Tests de /ultimo."""

from datetime import datetime, timezone

import pytest

from crypto_tracker import database
from crypto_tracker.alerts import formatear_ultimo
from crypto_tracker.avisados import Aviso, Ultimo, juntar

AHORA = datetime(2026, 10, 25, 12, tzinfo=timezone.utc)


def _aviso(dia, hora=12, precio=100.0, sube=True):
    return Aviso(datetime(2026, 10, dia, hora, tzinfo=timezone.utc), precio, sube)


def test_juntar_el_mas_reciente_primero_y_sin_avisos_al_final():
    lista = juntar(
        ["solana", "bitcoin", "ethereum", "cardano"],
        {"bitcoin": _aviso(20), "ethereum": _aviso(24), "ripple": _aviso(25)},
        {"bitcoin": 110.0},
    )

    assert [u.coin_id for u in lista] == ["ethereum", "bitcoin", "solana", "cardano"]
    assert lista[1].ahora == 110.0


def test_desde_entonces():
    assert Ultimo("bitcoin", _aviso(20), 110.0).desde_entonces == pytest.approx(10)
    assert Ultimo("bitcoin", _aviso(20), None).desde_entonces is None
    assert Ultimo("bitcoin", None, 110.0).desde_entonces is None


def test_guardar_y_leer(tmp_path):
    db = str(tmp_path / "p.db")
    database.init_db(db)
    cuando = datetime(2026, 10, 24, 9, 30, tzinfo=timezone.utc)

    database.guardar_avisos(db, [("bitcoin", 0.1 + 0.2, True)], cuando)
    database.guardar_avisos(db, [("solana", 105.5, False)], cuando)
    # El siguiente de la misma pisa al anterior.
    database.guardar_avisos(db, [("bitcoin", 82000.0, False)], AHORA)

    assert database.ultimos_avisos(db) == {
        "bitcoin": Aviso(AHORA, 82000.0, False),
        "solana": Aviso(cuando, 105.5, False),
    }


def test_formatear():
    texto = formatear_ultimo(
        [
            Ultimo("bitcoin", _aviso(22, precio=80000.0, sube=True), 84000.0),
            Ultimo("solana", _aviso(25, hora=9, precio=110.0, sube=False), None),
            Ultimo("cardano", None),
        ],
        "usd",
        AHORA,
    )

    assert "<b>Bitcoin</b>  hace 3 días, el 22/10" in texto
    assert "🔺 Subió a $80.000,00  ·  desde entonces +5.00%" in texto
    assert "<b>Solana</b>  hoy a las" in texto
    assert "🔻 Bajó a $110,00\n" in texto
    assert "<b>Cardano</b>  <i>aún no ha avisado</i>" in texto
