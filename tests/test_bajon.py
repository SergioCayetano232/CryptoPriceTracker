"""Tests del aviso de caída de la cartera desde su récord."""

from datetime import datetime, timedelta, timezone

from crypto_tracker.alerts import formatear_bajon
from crypto_tracker.bajon import escalon, toca
from crypto_tracker.record import Record

RECORD = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
DESDE = datetime(2026, 8, 1, tzinfo=timezone.utc)


def _r(ahora, maximo=1000.0, cuando=RECORD):
    return Record(maximo, cuando, ahora, DESDE)


def test_escalon():
    assert escalon(_r(1000), 20) == 0
    assert escalon(_r(850), 20) == 0
    assert escalon(_r(800), 20) == 1
    assert escalon(_r(550), 20) == 2
    # justo el 40%, que con decimales sale 1,9999...
    assert escalon(_r(600), 20) == 2


def test_escalon_en_record():
    assert escalon(_r(1200), 20) == 0


def test_toca_la_primera_vez():
    assert toca(_r(790), 20, None) == 1


def test_no_repite_el_mismo_escalon():
    assert toca(_r(750), 20, (RECORD, 1)) is None


def test_avisa_si_cae_otro_escalon():
    assert toca(_r(590), 20, (RECORD, 1)) == 2


def test_si_se_recupera_no_avisa():
    assert toca(_r(900), 20, (RECORD, 1)) is None


def test_record_nuevo_empieza_de_cero():
    nuevo = RECORD + timedelta(days=10)
    assert toca(_r(1100, maximo=1400, cuando=nuevo), 20, (RECORD, 2)) == 1


def test_sin_caida_suficiente():
    assert toca(_r(810), 20, None) is None


def test_formatear():
    texto = formatear_bajon(_r(750), 1, 20, "eur")

    assert "📉 <b>Tu cartera ha caído un 25,0% desde su récord</b>" in texto
    assert "€1.000,00" in texto
    assert "<b>€750,00</b>" in texto
    assert "€250,00" in texto
    assert "Ya pasa del 20%. El siguiente aviso, al 40%" in texto


def test_formatear_segundo_escalon():
    texto = formatear_bajon(_r(590), 2, 20, "eur")

    assert "Ya pasa del 40%. El siguiente aviso, al 60%" in texto
