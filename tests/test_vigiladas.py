"""Tests de cambiar lo que se vigila desde Telegram."""

import pytest

from crypto_tracker.alerts import describir, formatear_vigiladas
from crypto_tracker.config import Watch
from crypto_tracker.vigiladas import VigilarError, combinar, interpretar

# --- leer lo que escribes ---


@pytest.mark.parametrize(
    "argumento, watch",
    [
        ("Solana %5", Watch("solana", percent=5)),
        ("solana 5%", Watch("solana", percent=5)),
        ("solana 2,5%", Watch("solana", percent=2.5)),
        ("solana 10", Watch("solana", step=10)),
        ("bitcoin 1.000", Watch("bitcoin", step=1000)),
        ("bitcoin 55000 75.000", Watch("bitcoin", 55000, 75000)),
        ("ethereum - 4000", Watch("ethereum", max_price=4000)),
        ("ethereum 2000 -", Watch("ethereum", min_price=2000)),
    ],
)
def test_interpretar(argumento, watch):
    assert interpretar(argumento)[0] == watch


def test_interpretar_da_la_regla_del_env():
    assert interpretar("solana %5")[1] == "solana:%5.0"
    assert interpretar("ethereum - 4000")[1] == "ethereum::4000.0"


@pytest.mark.parametrize("argumento", ["", "solana", "bitcoin 1 2 3"])
def test_interpretar_formato_malo(argumento):
    with pytest.raises(VigilarError, match="/vigilar solana %5"):
        interpretar(argumento)


def test_interpretar_numero_malo():
    with pytest.raises(VigilarError, match="'mucho' no es un número"):
        interpretar("solana mucho")


@pytest.mark.parametrize(
    "argumento",
    [
        "solana %150",  # porcentaje absurdo
        "bitcoin 75000 55000",  # minimo por encima del maximo
        "bitcoin - -",  # sin ningun lado
        "solana 0",  # paso de cero
    ],
)
def test_interpretar_reglas_que_no_tienen_sentido(argumento):
    with pytest.raises(VigilarError):
        interpretar(argumento)


# --- juntar el .env con lo de Telegram ---

ENV = [Watch("bitcoin", percent=5), Watch("ethereum", step=100)]


def test_sin_cambios_es_el_env():
    assert combinar(ENV, {}) == ENV


def test_anadir_va_al_final():
    assert combinar(ENV, {"solana": "solana:%3"}) == ENV + [Watch("solana", percent=3)]


def test_cambiar_una_del_env_respeta_el_orden():
    assert combinar(ENV, {"bitcoin": "bitcoin:1000"}) == [
        Watch("bitcoin", step=1000),
        Watch("ethereum", step=100),
    ]


def test_dejar_una_del_env():
    assert combinar(ENV, {"bitcoin": None}) == [Watch("ethereum", step=100)]


def test_dejar_una_que_no_estaba_no_hace_nada():
    assert combinar(ENV, {"solana": None}) == ENV


def test_una_regla_rota_no_tumba_nada():
    # si es del .env se queda como estaba, si es nueva se ignora
    assert combinar(ENV, {"bitcoin": "basura", "solana": "basura"}) == ENV


# --- los mensajes ---


@pytest.mark.parametrize(
    "watch, texto",
    [
        (Watch("bitcoin", percent=5), "cada 5 % que se mueva"),
        (Watch("bitcoin", percent=2.5), "cada 2,5 % que se mueva"),
        (Watch("bitcoin", step=1000), "cada €1.000,00"),
        (
            Watch("bitcoin", 55000, 75000),
            "si baja de €55.000,00 o si sube de €75.000,00",
        ),
        (Watch("ethereum", max_price=4000), "si sube de €4.000,00"),
    ],
)
def test_describir(watch, texto):
    assert describir(watch, "eur") == texto


def test_lista_marca_lo_de_telegram():
    texto = formatear_vigiladas(
        [Watch("bitcoin", percent=5), Watch("solana", step=10)], "eur", {"solana"}
    )

    assert "<b>Bitcoin</b>  cada 5 % que se mueva\n" in texto
    assert "<b>Solana</b>  cada €10,00  <i>(desde Telegram)</i>" in texto
