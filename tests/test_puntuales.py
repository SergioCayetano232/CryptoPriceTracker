"""Tests de las alertas de una sola vez."""

from datetime import datetime, timedelta, timezone

import pytest

from crypto_tracker.alerts import (
    ALTO,
    Alert,
    formatear,
    formatear_puntual,
    formatear_puntuales,
    formatear_quitadas,
)
from crypto_tracker.puntuales import (
    Puntual,
    PuntualError,
    caducadas,
    caducidad,
    cumplidas,
    interpretar,
    interpretar_relativa,
    numero,
    numeros,
    objetivo_relativo,
    separar_caducidad,
    separar_nota,
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
        ("70k", 70000.0),
        ("1,5k", 1500.0),
        ("2.5K€", 2500.0),
    ],
)
def test_numero(texto, esperado):
    assert numero(texto) == esperado


@pytest.mark.parametrize("texto", ["setenta", "inf", "nan", "", "7o000", "k", "70kk"])
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


# --- relativas: /alerta bitcoin +10% ---


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("Bitcoin +10%", ("bitcoin", 10.0)),
        ("bitcoin -5%", ("bitcoin", -5.0)),
        ("bitcoin +2,5%", ("bitcoin", 2.5)),
        ("bitcoin -0.5%", ("bitcoin", -0.5)),
    ],
)
def test_interpretar_relativa(texto, esperado):
    assert interpretar_relativa(texto) == esperado


def test_un_precio_no_es_relativa():
    # asi sigue por el camino de siempre
    assert interpretar_relativa("bitcoin 70000") is None
    assert interpretar_relativa("bitcoin") is None


def test_relativa_sin_signo_pregunta():
    with pytest.raises(PuntualError, match=r"\+10% o -10%"):
        interpretar_relativa("bitcoin 10%")


@pytest.mark.parametrize("texto", ["bitcoin +0%", "bitcoin +%", "bitcoin +mucho%"])
def test_relativa_mal_escrita(texto):
    with pytest.raises(PuntualError):
        interpretar_relativa(texto)


def test_relativa_no_puede_bajar_del_todo():
    with pytest.raises(PuntualError):
        interpretar_relativa("bitcoin -100%")


def test_objetivo_relativo():
    assert objetivo_relativo(60000.0, 10) == pytest.approx(66000.0)
    assert objetivo_relativo(60000.0, -5) == pytest.approx(57000.0)


# --- /quitar ---


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("3", [3]),
        ("#3", [3]),
        ("2 5", [2, 5]),
        ("2, 5,7", [2, 5, 7]),
        ("5 5 2", [5, 2]),
    ],
)
def test_numeros(texto, esperado):
    assert numeros(texto) == esperado


@pytest.mark.parametrize("texto", ["", "  ", "tres", "2 bitcoin", "2.5"])
def test_numeros_malos(texto):
    with pytest.raises(PuntualError):
        numeros(texto)


@pytest.mark.parametrize(
    "quitadas, no_estaban, esperado",
    [
        ([3], [], "🗑 Alerta quitada."),
        ([], [9], "No tengo ninguna alerta con el número 9. Mira /alertas"),
        ([2, 5], [], "🗑 2 alertas quitadas."),
        (
            [],
            [7, 8, 9],
            "No tengo ninguna alerta con los números 7, 8 y 9. Mira /alertas",
        ),
    ],
)
def test_formatear_quitadas(quitadas, no_estaban, esperado):
    assert formatear_quitadas(quitadas, no_estaban) == esperado


@pytest.mark.parametrize(
    "precio, esperado",
    [
        (150.0, "160"),
        (1000.0, "1100"),
        (85601.0, "94000"),
        (0.35, "0,38"),
        (0.00002, "0,000022"),
    ],
)
def test_ejemplo_redondo_por_encima(precio, esperado):
    from crypto_tracker.puntuales import ejemplo, numero

    assert ejemplo(precio) == esperado
    assert numero(ejemplo(precio)) > precio  # y /alerta lo entiende


# --- caducidad ---


@pytest.mark.parametrize(
    "argumento,esperado",
    [
        ("bitcoin 70000 7d", ("bitcoin 70000", 168)),
        ("bitcoin +10% 12h", ("bitcoin +10%", 12)),
        ("bitcoin 70000 2sem", ("bitcoin 70000", 336)),
        ("bitcoin 70000", ("bitcoin 70000", None)),
        ("bitcoin 7d", ("bitcoin 7d", None)),  # sin precio, lo dira interpretar
        ("bitcoin 70000 mucho", ("bitcoin 70000 mucho", None)),
        ("bitcoin", ("bitcoin", None)),
    ],
)
def test_separar_caducidad(argumento, esperado):
    assert separar_caducidad(argumento) == esperado


def test_separar_caducidad_demasiado_larga():
    with pytest.raises(PuntualError, match="Como mucho un año"):
        separar_caducidad("bitcoin 70000 500d")


def test_caducidad():
    ahora = datetime(2026, 10, 8, 12, 0, tzinfo=timezone.utc)

    assert caducidad(ahora, 168) == datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)
    assert caducidad(ahora, None) is None


def test_caducadas():
    ahora = datetime(2026, 10, 8, 12, 0, tzinfo=timezone.utc)
    vieja = Puntual(1, "bitcoin", 70000, True, ahora - timedelta(minutes=1))
    justa = Puntual(2, "bitcoin", 70000, True, ahora)
    viva = Puntual(3, "bitcoin", 70000, True, ahora + timedelta(minutes=1))
    sin = Puntual(4, "bitcoin", 70000, True)

    assert caducadas([vieja, justa, viva, sin], ahora) == [vieja, justa]


# --- la nota ---


@pytest.mark.parametrize(
    "argumento, esperado",
    [
        ("bitcoin 70000", ("bitcoin 70000", None)),
        ("bitcoin 70000 7d", ("bitcoin 70000 7d", None)),
        ("bitcoin 70000 vender la mitad", ("bitcoin 70000", "vender la mitad")),
        ("bitcoin +10% 7d vender la mitad", ("bitcoin +10% 7d", "vender la mitad")),
        ("bitcoin", ("bitcoin", None)),
    ],
)
def test_separar_nota(argumento, esperado):
    assert separar_nota(argumento) == esperado


def test_nota_demasiado_larga():
    with pytest.raises(PuntualError, match="muy larga"):
        separar_nota("bitcoin 70000 " + "a" * 101)
