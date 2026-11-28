"""Tests de /stop."""

import pytest

from crypto_tracker.avisos.stop import (
    Stop,
    StopError,
    calcular,
    coste,
    interpretar,
    nota_movil,
    objetivo_movil,
    porcentaje_de_nota,
    seguir,
    separar_movil,
    subir,
)
from crypto_tracker.cartera import Valor
from crypto_tracker.nucleo.config import Posicion


@pytest.mark.parametrize(
    "texto, sale",
    [
        ("eth -15%", ("ethereum", -15.0)),
        ("bitcoin +50%", ("bitcoin", 50.0)),
        ("sol -7,5%", ("solana", -7.5)),
        ("cartera -20%", ("cartera", -20.0)),
    ],
)
def test_interpretar(texto, sale):
    assert interpretar(texto) == sale


@pytest.mark.parametrize(
    "texto, error",
    [
        ("eth", "Escríbelo así"),
        ("eth 2000", "Escríbelo así"),
        ("eth 15%", "¿Perder o ganar?"),
        ("eth -abc%", "no es un porcentaje"),
        ("eth -0%", "no es un porcentaje"),
        ("eth -100%", "100 %"),
    ],
)
def test_interpretar_mal(texto, error):
    with pytest.raises(StopError, match=error):
        interpretar(texto)


def test_sobre_el_precio_medio():
    # 2 ETH que costaron 5.000: 2.500 de media; ahora a 2.700
    s = calcular("ethereum", -15, Valor("ethereum", 5400, 5000, 2))

    assert s.coste == 2500
    assert s.ahora == 2700
    assert s.objetivo == pytest.approx(2125)
    assert not s.sube
    assert s.llevas == pytest.approx(8)
    assert not s.ya_llego


def test_de_ganancia():
    s = calcular("ethereum", 50, Valor("ethereum", 5400, 5000, 2))

    assert s.objetivo == pytest.approx(3750)
    assert s.sube


def test_de_la_cartera_es_sobre_todo_lo_que_metiste():
    s = calcular("cartera", -20, Valor("total", 9000, 10000))

    assert s.objetivo == pytest.approx(8000)
    assert s.llevas == pytest.approx(-10)


@pytest.mark.parametrize(
    "porcentaje, ahora, llego",
    [(-15, 2200, False), (-15, 2125, True), (-15, 2000, True), (20, 3000, True)],
)
def test_ya_llego(porcentaje, ahora, llego):
    assert Stop("ethereum", porcentaje, 2500, ahora).ya_llego == llego


def test_sin_lo_que_te_costo():
    with pytest.raises(StopError, match="lo que te costó"):
        calcular("ethereum", -15, Valor("ethereum", 5400, None, 2))


def test_cartera_sin_lo_que_te_costo():
    with pytest.raises(StopError, match="cada una de tu cartera"):
        calcular("cartera", -15, Valor("total", 9000, None))


@pytest.mark.parametrize(
    "porcentaje, nota",
    [
        (-15, "Stop: -15% sobre lo que te costó"),
        (7.5, "Stop: +7,5% sobre lo que te costó"),
    ],
)
def test_nota(porcentaje, nota):
    assert Stop("ethereum", porcentaje, 2500, 2700).nota == nota


@pytest.mark.parametrize(
    "texto, sale",
    [
        ("eth -10% movil", ("eth -10%", True)),
        ("eth -10% Móvil", ("eth -10%", True)),
        ("eth -10% trailing", ("eth -10%", True)),
        ("eth -10%", ("eth -10%", False)),
        ("eth -10% otra", ("eth -10% otra", False)),
    ],
)
def test_separar_movil(texto, sale):
    assert separar_movil(texto) == sale


def test_objetivo_movil():
    assert objetivo_movil(80000, -10) == pytest.approx(72000)


@pytest.mark.parametrize(
    "precio, sale",
    [
        (90000, 81000),  # otro máximo: sube
        (80000, None),  # igual que el máximo de antes
        (75000, None),  # bajando no se toca
    ],
)
def test_subir(precio, sale):
    nuevo = subir(72000, -10, precio)
    assert nuevo == (pytest.approx(sale) if sale else None)


def test_nota_movil():
    assert nota_movil(-7.5) == "Stop móvil: -7,5% desde lo más alto"


def test_coste_es_el_precio_medio():
    assert coste("ethereum", [Posicion("ethereum", 2, 6000)]) == 3000


def test_coste_de_la_cartera_es_todo_lo_metido():
    posiciones = [Posicion("bitcoin", 0.1, 5000), Posicion("ethereum", 2, 6000)]
    assert coste("cartera", posiciones) == 11000


@pytest.mark.parametrize(
    "posiciones",
    [
        [],
        [Posicion("bitcoin", 0.1, 5000)],
        [Posicion("ethereum", 2)],
    ],
)
def test_coste_sin_saber_lo_que_costo(posiciones):
    assert coste("ethereum", posiciones) is None


def test_coste_de_la_cartera_si_una_no_dice_lo_que_costo():
    posiciones = [Posicion("bitcoin", 0.1, 5000), Posicion("ethereum", 2)]
    assert coste("cartera", posiciones) is None


def test_seguir_al_comprar_mas_barato():
    # Tenía 1 a 3000 con stop -10% en 2700; compro otra a 2000 y la media baja a 2500.
    nuevo = seguir(2700, -10, "ethereum", [Posicion("ethereum", 2, 5000)])
    assert nuevo == pytest.approx(2250)


def test_seguir_un_stop_de_ganancia():
    nuevo = seguir(4500, 50, "ethereum", [Posicion("ethereum", 2, 8000)])
    assert nuevo == pytest.approx(6000)


def test_seguir_sin_cambios_no_mueve_nada():
    assert seguir(2700, -10, "ethereum", [Posicion("ethereum", 1, 3000)]) is None


def test_seguir_si_lo_has_vendido_todo_se_queda_donde_estaba():
    assert seguir(2700, -10, "ethereum", []) is None


def test_seguir_la_cartera():
    posiciones = [Posicion("bitcoin", 0.1, 5000), Posicion("ethereum", 2, 7000)]
    assert seguir(8800, -20, "cartera", posiciones) == pytest.approx(9600)


@pytest.mark.parametrize(
    "nota, sale",
    [
        ("Stop: -15% sobre lo que te costó", -15.0),
        ("Stop: +7,5% sobre lo que te costó", 7.5),
        (None, None),
        ("vender la mitad", None),
        ("Stop móvil: -10% desde lo más alto", None),
        ("Stop: hola% sobre lo que te costó", None),
    ],
)
def test_porcentaje_de_nota(nota, sale):
    assert porcentaje_de_nota(nota) == sale


@pytest.mark.parametrize("porcentaje", [-15.0, 7.5, 50.0])
def test_porcentaje_de_nota_lee_lo_que_escribe_nota(porcentaje):
    s = Stop("bitcoin", porcentaje, 50000, 66000)
    assert porcentaje_de_nota(s.nota) == porcentaje
