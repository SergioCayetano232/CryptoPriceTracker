"""Tests de /ideal y de su aviso."""

import pytest

from crypto_tracker import ideal
from crypto_tracker.avisos.alerts import formatear_aviso_ideal, formatear_ideal
from crypto_tracker.cartera import Valor
from crypto_tracker.ideal import Ideal, IdealError, Parte


def _valores(**cuanto):
    return [Valor(c, v) for c, v in cuanto.items()]


def test_interpretar_un_reparto():
    assert ideal.interpretar("btc 60 eth 40") == Ideal(
        {"bitcoin": 60, "ethereum": 40}, 5
    )


def test_interpretar_con_margen():
    assert ideal.interpretar("btc 60 eth 40 margen 10").margen == 10
    assert ideal.interpretar("btc 60 eth 40 margen 7,5%").margen == 7.5


def test_a_secas_es_verlo_y_con_no_quitarlo():
    assert ideal.interpretar("") is None
    assert ideal.interpretar("no") == ideal.QUITAR


@pytest.mark.parametrize(
    "texto, falla",
    [
        ("btc 60 eth 30", "suma 90%"),
        ("btc 60 eth", "/ideal btc 60 eth 40"),
        ("btc 60 eth 40 margen 0", "El margen va de 1 a 50"),
        ("btc 60 eth 40 margen mucho", "El margen va de 1 a 50"),
        ("margen 10", "Falta el reparto"),
    ],
)
def test_interpretar_mal(texto, falla):
    with pytest.raises(IdealError, match=falla):
        ideal.interpretar(texto)


def test_el_error_no_manda_a_rebalanceo():
    with pytest.raises(IdealError) as e:
        ideal.interpretar("btc sesenta eth 40")
    assert "/rebalanceo" not in str(e.value)


def test_se_guarda_y_se_lee_igual():
    uno = Ideal({"bitcoin": 60.0, "ethereum": 40.0}, 7.5)

    assert ideal.de_texto(ideal.a_texto(uno)) == uno


@pytest.mark.parametrize("texto", [None, "", "esto no es json", "{}", '{"reparto": 3}'])
def test_lo_guardado_roto_es_como_no_tener(texto):
    assert ideal.de_texto(texto) is None


def test_partes_la_mas_alejada_primero():
    lista = ideal.partes(
        _valores(bitcoin=680, ethereum=300, solana=20),
        {"bitcoin": 60, "ethereum": 40},
    )

    assert [(p.coin_id, round(p.peso), p.objetivo) for p in lista] == [
        ("ethereum", 30, 40),
        ("bitcoin", 68, 60),
        ("solana", 2, 0),  # la tienes y no la querías
    ]
    assert lista[0].puntos == pytest.approx(-10)


def test_la_que_quieres_y_no_tienes_pesa_cero():
    [_, nueva] = sorted(
        ideal.partes(_valores(bitcoin=100), {"bitcoin": 80, "solana": 20}),
        key=lambda p: p.coin_id,
    )

    assert (nueva.coin_id, nueva.peso, nueva.puntos) == ("solana", 0, -20)


def test_sin_valor_no_hay_partes():
    assert ideal.partes(_valores(bitcoin=0), {"bitcoin": 100}) == []


def _lista(*puntos):
    return [Parte(f"c{i}", 50 + p, 50) for i, p in enumerate(puntos)]


def test_avisa_al_pasar_el_margen_y_solo_una_vez():
    assert not ideal.toca(_lista(4, -4), 5, avisado=False)
    assert ideal.toca(_lista(5, -5), 5, avisado=False)
    assert not ideal.toca(_lista(8, -8), 5, avisado=True)


def test_no_se_rearma_hasta_arreglarlo_a_medias():
    # Con margen 5 hay que bajar de 2,5 puntos
    assert ideal.sigue_avisado(_lista(4, -4), 5, avisado=True)
    assert ideal.sigue_avisado(_lista(2.5, -2.5), 5, avisado=True)
    assert not ideal.sigue_avisado(_lista(2, -2), 5, avisado=True)
    assert not ideal.sigue_avisado(_lista(9, -9), 5, avisado=False)


def test_el_comando_para_volver():
    assert ideal.comando({"bitcoin": 60.0, "ethereum": 37.5, "solana": 2.5}) == (
        "/rebalanceo bitcoin 60 ethereum 37.5 solana 2.5"
    )


def test_el_comando_para_volver_se_entiende():
    from crypto_tracker import rebalanceo

    reparto = {"bitcoin": 60.0, "ethereum": 37.5, "solana": 2.5}
    escrito = ideal.comando(reparto).removeprefix("/rebalanceo ")

    assert rebalanceo.interpretar(escrito) == reparto


def test_mensaje_del_aviso():
    uno = Ideal({"bitcoin": 60, "ethereum": 40}, 5)
    lista = ideal.partes(_valores(bitcoin=680, ethereum=320), uno.reparto)

    texto = formatear_aviso_ideal(lista, uno)

    assert "⚖️ <b>Tu cartera se ha alejado de tu reparto</b>" in texto
    assert "<b>Bitcoin</b> 68% · querías 60% · le sobran 8 puntos" in texto
    assert "<b>Ethereum</b> 32% · querías 40% · le faltan 8 puntos" in texto
    assert "<code>/rebalanceo bitcoin 60 ethereum 40</code>" in texto


def test_el_aviso_solo_nombra_las_que_se_han_salido():
    uno = Ideal({"bitcoin": 50, "ethereum": 30, "solana": 20}, 5)
    lista = ideal.partes(_valores(bitcoin=570, ethereum=240, solana=190), uno.reparto)

    texto = formatear_aviso_ideal(lista, uno)

    assert "Bitcoin" in texto and "Ethereum" in texto
    assert "Solana" not in texto


def test_mensaje_de_ideal_con_cartera():
    uno = Ideal({"bitcoin": 60, "ethereum": 40}, 5)
    lista = ideal.partes(_valores(bitcoin=680, ethereum=320), uno.reparto)

    texto = formatear_ideal(uno, lista)

    assert "⚖️ <b>Tu reparto ideal</b>" in texto
    assert "⚠️ <b>Bitcoin</b> 68% · querías 60%" in texto
    assert "Aviso cuando alguna se aleje 5 puntos" in texto
    assert "/ideal no" in texto


def test_mensaje_de_ideal_sin_precios():
    uno = Ideal({"bitcoin": 60, "ethereum": 40}, 10)

    texto = formatear_ideal(uno, [])

    assert "<b>Bitcoin</b> 60%" in texto
    assert "se aleje 10 puntos" in texto
