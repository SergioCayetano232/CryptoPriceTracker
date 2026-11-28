"""Tests del buzón que junta los avisos sueltos de un ciclo."""

import contextlib

from crypto_tracker.avisos.buzon import Buzon


def test_vacio_no_manda_nada():
    mandados = []
    assert Buzon().entregar(lambda t: mandados.append(t) or True)
    assert mandados == []


def test_uno_solo_va_tal_cual():
    b = Buzon()
    b.echar("RSI de bitcoin")
    assert b.juntar() == "RSI de bitcoin"


def test_varios_en_un_mensaje_con_cuantos_son():
    b = Buzon()
    b.echar("uno")
    b.echar("dos")
    b.echar("tres")

    mandados = []
    b.entregar(lambda t: mandados.append(t) or True)

    assert len(mandados) == 1
    assert mandados[0] == "<b>3 avisos</b>\n\nuno\n\ndos\n\ntres"


def test_apunta_solo_si_llega():
    apuntados = []
    b = Buzon()
    b.echar("uno", lambda: apuntados.append("uno"))
    b.echar("dos", lambda: apuntados.append("dos"))

    assert not b.entregar(lambda t: False)
    assert apuntados == []

    assert b.entregar(lambda t: True)
    assert apuntados == ["uno", "dos"]


def test_sin_al_llegar_tambien_vale():
    b = Buzon()
    b.echar("solo texto")
    assert b.entregar(lambda t: True)


def test_despues_de_llegar_se_vacia():
    apuntados = []
    b = Buzon()
    b.echar("uno", lambda: apuntados.append("uno"))
    b.entregar(lambda t: True)

    assert b.vacio()
    b.entregar(lambda t: True)
    assert apuntados == ["uno"]


def test_si_un_apunte_revienta_no_se_repiten_los_demas():
    apuntados = []

    def revienta():
        raise RuntimeError("disco lleno")

    b = Buzon()
    b.echar("uno", lambda: apuntados.append("uno"))
    b.echar("dos", revienta)
    with contextlib.suppress(RuntimeError):
        b.llegaron()
    b.llegaron()

    assert apuntados == ["uno"]
