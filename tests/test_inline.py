"""Tests del modo inline (@tubot btc)."""

from datetime import datetime, timedelta, timezone

from crypto_tracker.inline import criptos, hace, tarjeta
from crypto_tracker.simbolos import MAX_VARIAS

AHORA = datetime(2026, 11, 21, 12, 0, tzinfo=timezone.utc)


def test_traduce_los_simbolos():
    assert criptos("btc, eth", []) == ["bitcoin", "ethereum"]


def test_vacia_son_las_vigiladas():
    assert criptos("  ", ["solana", "bitcoin"]) == ["solana", "bitcoin"]


def test_no_pasa_del_maximo():
    muchas = " ".join(f"moneda{i}" for i in range(MAX_VARIAS + 5))
    assert len(criptos(muchas, [])) == MAX_VARIAS


def test_tarjeta_con_variacion():
    t = tarjeta("bitcoin", 62340.5, 2.1, "eur")

    assert t.titulo == "Bitcoin  €62.340,50"
    assert t.descripcion == "🔺 +2.10% en 24 h"
    assert t.texto == "💰 <b>Bitcoin</b>  €62.340,50\n🔺 +2.10% en 24 h"


def test_tarjeta_sin_24h_no_lo_pone_en_el_mensaje():
    t = tarjeta("avalanche-2", 30, None, "usd")

    assert t.titulo == "Avalanche 2  $30,00"
    assert t.descripcion == "Sin datos de las últimas 24 h"
    assert "24 h" not in t.texto


def test_moneda_sin_simbolo():
    assert tarjeta("bitcoin", 1, 0, "chf").titulo == "Bitcoin  CHF 1,00"


def test_dice_de_cuando_es_el_precio():
    t = tarjeta("bitcoin", 100, -1.5, "eur", AHORA - timedelta(minutes=7), AHORA)
    assert t.descripcion == "🔻 -1.50% en 24 h · hace 7 min"


def test_hace():
    assert hace(AHORA, AHORA) == "ahora mismo"
    assert hace(AHORA - timedelta(minutes=59), AHORA) == "hace 59 min"
    assert hace(AHORA - timedelta(hours=3, minutes=20), AHORA) == "hace 3 h"
    assert hace(AHORA - timedelta(hours=47), AHORA) == "hace 47 h"
    assert hace(AHORA - timedelta(days=36, hours=12), AHORA) == "hace 36 días"


def test_un_precio_reciente_no_lleva_aviso():
    t = tarjeta("bitcoin", 100, 1, "eur", AHORA - timedelta(minutes=59), AHORA)
    assert "Precio de" not in t.texto


def test_un_precio_viejo_lo_dice_en_el_mensaje():
    t = tarjeta("bitcoin", 100, None, "eur", AHORA - timedelta(days=3), AHORA)
    assert t.texto.endswith("\n<i>Precio de hace 3 días</i>")
