"""Tests de /encuesta."""

from datetime import datetime, timedelta, timezone

import pytest

from crypto_tracker.avisos.alerts import (
    formatear_voto_encuesta,
    opciones_encuesta,
    pregunta_encuesta,
)
from crypto_tracker.curiosidades import encuesta, prediccion
from crypto_tracker.curiosidades.encuesta import Encuesta, EncuestaError
from crypto_tracker.curiosidades.prediccion import Prediccion

# Un lunes a media mañana, en la hora de aquí.
LUNES = datetime(2026, 11, 23, 10, 0).astimezone()
DOMINGO = prediccion.cierre(LUNES)
UNA = Encuesta("p1", "bitcoin", 80000.0, DOMINGO)


def test_interpretar():
    assert encuesta.interpretar("") is True
    assert encuesta.interpretar(" NO ") is False
    with pytest.raises(EncuestaError, match="/encuesta no"):
        encuesta.interpretar("bitcoin")


def test_los_limites_son_un_5_por_ciento_a_cada_lado():
    assert encuesta.limites(80000.0) == (76000.0, 84000.0)


@pytest.mark.parametrize(
    "opcion, precio", [(0, 74000.0), (1, 78000.0), (2, 82000.0), (3, 86000.0)]
)
def test_cada_opcion_apunta_el_centro_de_su_tramo(opcion, precio):
    assert encuesta.predicho(80000.0, opcion) == pytest.approx(precio)


def test_una_opcion_que_no_existe():
    assert encuesta.predicho(80000.0, 4) is None
    assert encuesta.predicho(80000.0, -1) is None


def test_se_cierra_un_dia_antes_del_domingo():
    assert encuesta.se_cierra(DOMINGO) == DOMINGO - timedelta(hours=24)
    assert encuesta.a_tiempo(UNA, DOMINGO - timedelta(hours=25))
    assert not encuesta.a_tiempo(UNA, DOMINGO - timedelta(hours=24))


def test_toca_el_lunes_si_la_ultima_era_de_otra_semana():
    vieja = Encuesta("p0", "bitcoin", 80000.0, DOMINGO - timedelta(days=7))

    assert encuesta.toca(LUNES, vieja)
    assert not encuesta.toca(LUNES, UNA)  # la de esta semana ya salió


def test_no_toca_antes_de_las_nueve_ni_a_final_de_semana():
    vieja = Encuesta("p0", "bitcoin", 80000.0, DOMINGO - timedelta(days=7))

    assert not encuesta.toca(LUNES.replace(hour=8, minute=59), vieja)
    assert encuesta.toca(LUNES + timedelta(days=2), vieja)  # el miércoles aún vale
    assert not encuesta.toca(LUNES + timedelta(days=3), vieja)  # el jueves ya no


def test_se_guarda_y_se_lee_igual():
    assert encuesta.de_texto(encuesta.a_texto(UNA)) == UNA


@pytest.mark.parametrize("texto", [None, "", "no es json", "{}", '{"poll_id": 1}'])
def test_lo_guardado_roto_es_como_no_tenerla(texto):
    assert encuesta.de_texto(texto) is None


def test_la_pregunta_dice_el_dia_y_el_precio():
    texto = pregunta_encuesta(UNA, "eur")

    assert f"¿Dónde estará Bitcoin el domingo {DOMINGO.astimezone():%d/%m}" in texto
    assert "Ahora está a €80.000,00" in texto
    assert "<" not in texto  # Telegram la enseña tal cual, sin HTML
    assert len(texto) <= 300


def test_las_opciones_van_de_la_que_mas_baja_a_la_que_mas_sube():
    opciones = opciones_encuesta(UNA, "eur")

    assert opciones == [
        "📉 Por debajo de €76.000,00 (-5% o más)",
        "↘️ Entre €76.000,00 y €80.000,00",
        "↗️ Entre €80.000,00 y €84.000,00",
        "🚀 Por encima de €84.000,00 (+5% o más)",
    ]
    assert len(opciones) == len(encuesta.CENTROS)
    assert all(len(o) <= 100 for o in opciones)


def test_las_opciones_caben_con_una_cripto_de_centimos():
    barata = Encuesta("p1", "shiba-inu", 0.00001234, DOMINGO)

    assert all(len(o) <= 100 for o in opciones_encuesta(barata, "eur"))


def test_mensaje_al_votar():
    p = Prediccion(1, "bitcoin", LUNES, DOMINGO, 80000.0, 82000.0)
    elegida = opciones_encuesta(UNA, "eur")[2]

    texto = formatear_voto_encuesta(p, elegida, "eur")

    assert "<b>Bitcoin</b> entre €80.000,00 y €84.000,00 el domingo" in texto
    assert "Lo cuento como <b>€82.000,00</b>" in texto
    assert "/prediccion bitcoin" in texto


def test_mensaje_al_votar_una_de_las_puntas():
    p = Prediccion(1, "bitcoin", LUNES, DOMINGO, 80000.0, 86000.0)

    texto = formatear_voto_encuesta(p, opciones_encuesta(UNA, "eur")[3], "eur")

    assert "<b>Bitcoin</b> por encima de €84.000,00 el domingo" in texto
    assert "(+5%" not in texto


def test_el_cierre_cabe_en_lo_que_deja_telegram():
    # Desde cualquier día de la semana, el cierre queda a menos de un mes.
    for dias in range(7):
        ahora = LUNES + timedelta(days=dias)
        falta = encuesta.se_cierra(prediccion.cierre(ahora)) - ahora

        assert encuesta.MINIMO_TELEGRAM < falta < encuesta.MAXIMO_TELEGRAM


def test_el_cierre_es_un_instante_y_no_depende_de_la_zona():
    assert DOMINGO.astimezone(timezone.utc) == DOMINGO
