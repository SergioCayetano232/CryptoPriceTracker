"""Tests de los 👍 y 👎 de los avisos."""

from datetime import datetime, timedelta, timezone

import pytest

from crypto_tracker.avisos import voto
from crypto_tracker.avisos.alerts import formatear_voto
from crypto_tracker.avisos.voto import Voto, VotoError, Votos
from crypto_tracker.nucleo import comandos

AVISO = datetime(2026, 11, 22, 10, 30, tzinfo=timezone.utc)


def test_lo_del_boton_se_vuelve_a_leer_igual():
    for util in (True, False):
        nombre, argumento = comandos.interpretar(voto.datos("bitcoin", util, AVISO))

        assert nombre == "voto"
        assert voto.interpretar(argumento) == Voto("bitcoin", AVISO, util)


def test_el_boton_cabe_en_telegram_con_un_id_largo():
    largo = voto.datos("wrapped-liquid-staked-ether-20", False, AVISO)

    assert len(largo.encode()) <= 64


@pytest.mark.parametrize(
    "texto", ["", "bitcoin", "bitcoin si", "bitcoin quizas 1795000000", "btc si ayer"]
)
def test_escrito_a_mano_no_vale(texto):
    with pytest.raises(VotoError):
        voto.interpretar(texto)


def test_una_hora_imposible_no_revienta():
    with pytest.raises(VotoError):
        voto.interpretar("bitcoin si " + "9" * 30)


def test_contar_los_de_una_cripto():
    votos = [
        Voto("bitcoin", AVISO, True),
        Voto("bitcoin", AVISO + timedelta(hours=1), False),
        Voto("bitcoin", AVISO + timedelta(hours=2), False),
        Voto("solana", AVISO, False),
    ]

    assert voto.contar(votos, "bitcoin") == Votos(1, 2)
    assert voto.contar(votos, "ethereum") == Votos(0, 0)


def test_contar_solo_los_del_tramo():
    votos = [
        Voto("bitcoin", AVISO - timedelta(days=40), False),
        Voto("bitcoin", AVISO, True),
    ]

    assert voto.contar(votos, "bitcoin", AVISO - timedelta(days=30)) == Votos(1, 0)


@pytest.mark.parametrize(
    "utiles, sobran, muchos",
    [(0, 2, False), (0, 3, True), (1, 2, True), (2, 2, False), (3, 1, False)],
)
def test_muchos_sobran_con_mas_de_la_mitad_y_al_menos_tres(utiles, sobran, muchos):
    assert Votos(utiles, sobran).muchos_sobran is muchos


def test_mensaje_del_voto():
    texto = formatear_voto("bitcoin", True, Votos(2, 1))

    assert "👍 Apuntado: el aviso de <b>Bitcoin</b> te sirvió." in texto
    assert "llevas 👍 2 · 👎 1" in texto
    assert "/ruido" not in texto


def test_mensaje_cuando_te_sobran_casi_todos():
    texto = formatear_voto("bitcoin", False, Votos(1, 3))

    assert "👎 Apuntado: el aviso de <b>Bitcoin</b> sobraba." in texto
    assert "/ruido bitcoin" in texto
