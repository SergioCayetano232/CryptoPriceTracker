"""Tests de las alertas de una sola vez."""

import pytest

from crypto_tracker.alerts import (
    ALTO,
    Alert,
    formatear,
    formatear_puntual,
    formatear_puntuales,
)
from crypto_tracker.puntuales import (
    Puntual,
    PuntualError,
    cumplidas,
    interpretar,
    numero,
    sube,
)

# --- leer lo que escribes ---


def test_interpretar():
    assert interpretar("Bitcoin 70000") == ("bitcoin", 70000.0)


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("70000", 70000.0),
        ("70.000", 70000.0),
        ("1.250.000", 1250000.0),
        ("0,35", 0.35),
        ("70.000,50", 70000.5),
        ("0.35", 0.35),
        ("0.150", 0.15),  # empieza por 0: son decimales, no miles
        ("70000€", 70000.0),
        ("$2500", 2500.0),
    ],
)
def test_numero(texto, esperado):
    assert numero(texto) == esperado


@pytest.mark.parametrize("texto", ["setenta", "inf", "nan", "", "7o000"])
def test_numero_que_no_lo_es(texto):
    assert numero(texto) is None


@pytest.mark.parametrize("argumento", ["", "bitcoin", "bitcoin 70000 ya"])
def test_interpretar_formato_malo(argumento):
    with pytest.raises(PuntualError, match="/alerta bitcoin 70000"):
        interpretar(argumento)


@pytest.mark.parametrize("precio", ["mucho", "0", "-5"])
def test_interpretar_precio_malo(precio):
    with pytest.raises(PuntualError, match="no es un precio"):
        interpretar(f"bitcoin {precio}")


# --- hacia donde espera ---


def test_por_encima_espera_a_que_suba():
    assert sube(70000, 63000) is True


def test_por_debajo_espera_a_que_baje():
    assert sube(55000, 63000) is False


def test_justo_al_precio_de_ahora_no_vale():
    with pytest.raises(PuntualError):
        sube(63000, 63000)


# --- cuando salta ---

SUBE = Puntual(1, "bitcoin", 70000, sube=True)
BAJA = Puntual(2, "bitcoin", 55000, sube=False)


def test_no_salta_antes_de_llegar():
    assert cumplidas([SUBE, BAJA], {"bitcoin": 63000}) == []


def test_salta_al_llegar_justo():
    assert cumplidas([SUBE], {"bitcoin": 70000}) == [SUBE]


def test_salta_aunque_se_pase():
    # entre ciclo y ciclo puede haber dado el salto de golpe
    assert cumplidas([SUBE], {"bitcoin": 72000}) == [SUBE]
    assert cumplidas([BAJA], {"bitcoin": 50000}) == [BAJA]


def test_sin_precio_no_salta():
    assert cumplidas([SUBE], {}) == []


def test_cada_una_con_su_cripto():
    eth = Puntual(3, "ethereum", 4000, sube=True)

    assert cumplidas([SUBE, eth], {"bitcoin": 63000, "ethereum": 4100}) == [eth]


# --- los mensajes ---


def test_mensaje_al_crear():
    texto = formatear_puntual(SUBE, 63000, "eur")

    assert "suba a <b>€70.000,00</b>" in texto
    assert "€63.000,00" in texto


def test_mensaje_al_crear_bajando():
    assert "baje a" in formatear_puntual(BAJA, 63000, "eur")


def test_lista_de_alertas():
    texto = formatear_puntuales([SUBE, BAJA], "eur")

    assert "<code>1</code>  <b>Bitcoin</b> 🔺 €70.000,00" in texto
    assert "<code>2</code>  <b>Bitcoin</b> 🔻 €55.000,00" in texto
    assert "/quitar 1" in texto


def test_lista_vacia():
    assert "No tienes alertas" in formatear_puntuales([], "eur")


def test_el_aviso_dice_que_era_tu_alerta():
    aviso = Alert("bitcoin", 70100, 70000, ALTO, puntual=True)

    texto = formatear(aviso, "eur")

    assert "ha subido de €70.000,00" in texto
    assert "Era tu /alerta" in texto


def test_los_avisos_normales_no_cambian():
    assert "/alerta" not in formatear(Alert("bitcoin", 70100, 70000, ALTO), "eur")
