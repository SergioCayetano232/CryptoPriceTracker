"""Tests de /vsbolsa."""

from datetime import date, datetime, timezone

import pytest
import requests

from crypto_tracker import vsbolsa
from crypto_tracker.movimientos import Movimiento
from crypto_tracker.vsbolsa import BolsaError, calcular, interpretar, leer, precio_en

SP = ("S&P 500", "SXR8.DE")
# Viernes 9 y lunes 12 de enero: el fin de semana no hay cierre.
SERIE = [(date(2026, 1, 9), 500.0), (date(2026, 1, 12), 520.0)]


def _mov(id, tipo, cantidad, coste, dia, coin="bitcoin"):
    cuando = datetime(2026, 1, dia, 12, tzinfo=timezone.utc)
    return Movimiento(id, coin, tipo, cantidad, coste, None, cuando)


@pytest.mark.parametrize(
    "dia, sale",
    [
        (9, 500.0),
        (10, 500.0),  # sábado, el del viernes
        (12, 520.0),
        (8, None),  # antes del primero
        (20, None),  # el último queda demasiado lejos
    ],
)
def test_precio_en(dia, sale):
    assert precio_en(SERIE, datetime(2026, 1, dia, 12, tzinfo=timezone.utc)) == sale


def test_le_ganas_a_la_bolsa():
    # 1.000 € el viernes: 2 participaciones a 500, hoy a 600, 1.200 €.
    c = calcular([_mov(1, "compra", 0.02, 1000, 9)], SERIE, 600, {"bitcoin": 75000}, SP)

    assert c.bolsa == pytest.approx(1200)
    assert c.real == pytest.approx(1500)
    assert c.diferencia == pytest.approx(300)
    assert c.ventaja == pytest.approx(25)
    assert c.indice == "S&P 500"


def test_las_ventas_sacan_lo_mismo_de_los_dos_lados():
    lista = [
        _mov(1, "compra", 0.02, 1000, 9),  # 2 participaciones
        _mov(2, "venta", 0.01, 520, 12),  # 1 participación
    ]

    c = calcular(lista, SERIE, 600, {"bitcoin": 50000}, SP)

    assert c.bolsa == pytest.approx(600)
    assert c.real == pytest.approx(500)


def test_las_recompensas_solo_suman_en_lo_real():
    lista = [_mov(1, "compra", 0.02, 1000, 9), _mov(2, "recompensa", 0.01, 400, 12)]

    c = calcular(lista, SERIE, 500, {"bitcoin": 50000}, SP)

    assert c.bolsa == pytest.approx(1000)
    assert c.real == pytest.approx(1500)


def test_sin_cierre_de_ese_dia_no_cuenta():
    lista = [_mov(1, "compra", 0.02, 1000, 9), _mov(2, "compra", 0.01, 500, 25)]

    c = calcular(lista, SERIE, 600, {"bitcoin": 50000}, SP)

    assert c.contados == 1
    assert c.fuera == 1


def test_nada_que_comparar():
    assert calcular([_mov(1, "compra", 1, None, 9)], SERIE, 600, {}, SP) is None
    assert calcular([_mov(1, "recompensa", 1, 10, 9)], SERIE, 600, {}, SP) is None


def test_falta_el_precio_de_hoy():
    assert calcular([_mov(1, "compra", 1, 10, 9)], SERIE, 600, {}, SP) is None


@pytest.mark.parametrize(
    "texto, moneda, sale",
    [
        ("", "eur", ("S&P 500", "SXR8.DE")),
        ("SP500", "eur", ("S&P 500", "SXR8.DE")),
        ("world", "eur", ("MSCI World", "EUNL.DE")),
        ("mundo", "usd", ("MSCI World", "IWDA.L")),
        ("", "usd", ("S&P 500", "CSPX.L")),
    ],
)
def test_interpretar(texto, moneda, sale):
    assert interpretar(texto, moneda) == sale


def test_interpretar_otro_indice():
    with pytest.raises(BolsaError, match="S&P 500 o el MSCI World"):
        interpretar("ibex", "eur")


def test_interpretar_otra_moneda():
    with pytest.raises(BolsaError, match="euros o en dólares"):
        interpretar("", "gbp")


def _yahoo(cierres, ahora=610.0):
    marcas = [
        int(datetime(2026, 1, d, 8, tzinfo=timezone.utc).timestamp())
        for d in (9, 12, 13)
    ]
    return {
        "chart": {
            "result": [
                {
                    "meta": {"regularMarketPrice": ahora},
                    "timestamp": marcas,
                    "indicators": {"quote": [{"close": cierres}]},
                }
            ]
        }
    }


def test_leer_salta_los_dias_sin_cierre():
    serie, ahora = leer(_yahoo([500.0, None, 530.0]))

    assert serie == [(date(2026, 1, 9), 500.0), (date(2026, 1, 13), 530.0)]
    assert ahora == 610.0


def test_leer_sin_precio_de_ahora_usa_el_ultimo_cierre():
    assert leer(_yahoo([500.0, 520.0, 530.0], ahora=None))[1] == 530.0


@pytest.mark.parametrize("datos", [{}, {"chart": {"result": []}}, None, []])
def test_leer_algo_raro(datos):
    assert leer(datos) == ([], None)


def test_pedir_sin_conexion(monkeypatch):
    def get(*a, **k):
        raise requests.ConnectionError("sin red")

    monkeypatch.setattr(vsbolsa.requests, "get", get)

    with pytest.raises(BolsaError, match="Yahoo no contesta"):
        vsbolsa.pedir("SXR8.DE", datetime(2026, 1, 1, tzinfo=timezone.utc))
