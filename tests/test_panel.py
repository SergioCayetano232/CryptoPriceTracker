"""Tests de los datos del panel web."""

from datetime import datetime, timedelta, timezone

import pytest

from crypto_tracker import panel
from crypto_tracker.config import Posicion
from crypto_tracker.puntuales import Puntual

AHORA = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)


def _cartera():
    return [
        Posicion("solana", 10, 1000.0),
        Posicion("bitcoin", 0.1, 5000.0),
    ]


def test_cartera_de_la_que_mas_vale_a_la_que_menos():
    filas, faltan = panel.filas_cartera(
        _cartera(), {"bitcoin": 60000.0, "solana": 100.0}, {}, {}
    )

    assert [f.coin_id for f in filas] == ["bitcoin", "solana"]
    assert faltan == []
    assert filas[0].valor == 6000.0
    assert filas[0].peso == pytest.approx(6000 / 7000 * 100)


def test_ganancia_de_cada_una():
    filas, _ = panel.filas_cartera(
        _cartera(), {"bitcoin": 60000.0, "solana": 100.0}, {}, {}
    )
    btc, sol = filas

    assert btc.ganancia == 1000.0
    assert btc.porcentaje == pytest.approx(20.0)
    assert sol.ganancia == 0.0


def test_sin_lo_que_costo_no_hay_ganancia():
    filas, _ = panel.filas_cartera([Posicion("bitcoin", 1)], {"bitcoin": 50.0}, {}, {})

    assert filas[0].ganancia is None
    assert filas[0].porcentaje is None


def test_la_que_no_tiene_precio_se_dice_aparte():
    filas, faltan = panel.filas_cartera(_cartera(), {"bitcoin": 60000.0}, {}, {})

    assert [f.coin_id for f in filas] == ["bitcoin"]
    assert faltan == ["solana"]
    assert filas[0].peso == 100.0


def test_cambio_en_24_horas():
    filas, _ = panel.filas_cartera(
        _cartera(), {"bitcoin": 66000.0, "solana": 100.0}, {"bitcoin": 60000.0}, {}
    )

    assert filas[0].cambio_24h == pytest.approx(10.0)
    assert filas[1].cambio_24h is None


def test_totales_del_panel():
    filas, _ = panel.filas_cartera(
        _cartera(), {"bitcoin": 60000.0, "solana": 100.0}, {}, {}
    )
    p = panel.Panel("eur", filas, [], [], [], AHORA, total_antes=6000.0)

    assert p.total == 7000.0
    assert p.invertido == 6000.0
    assert p.ganancia == 1000.0
    assert p.porcentaje == pytest.approx(100 / 6)
    assert p.cambio_24h == pytest.approx(100 / 6)


def test_panel_sin_cartera():
    p = panel.Panel("eur", [], [], [], [], None)

    assert p.total is None
    assert p.ganancia is None
    assert p.cambio_24h is None


def test_total_de_ayer_necesita_todas():
    assert panel.total_antes(_cartera(), {"bitcoin": 50000.0}) is None
    assert panel.total_antes(
        _cartera(), {"bitcoin": 50000.0, "solana": 90.0}
    ) == pytest.approx(5900.0)


def _alerta(id_, coin_id, objetivo, sube=True):
    return Puntual(id_, coin_id, objetivo, sube)


def test_alertas_primero_las_mas_cercanas():
    lista = panel.alertas(
        [
            _alerta(1, "bitcoin", 80000.0),
            _alerta(2, "bitcoin", 58000.0, sube=False),
            _alerta(3, "rara", 1.0),
        ],
        {"bitcoin": 60000.0},
        None,
    )

    assert [a.id for a in lista] == [2, 1, 3]
    assert lista[0].falta == pytest.approx(-3.333, abs=0.01)
    assert lista[2].falta is None


def test_alerta_de_la_cartera_usa_lo_que_vale_todo():
    [a] = panel.alertas([_alerta(1, "cartera", 8000.0)], {}, 7000.0)

    assert a.precio == 7000.0
    assert a.falta == pytest.approx(100 / 7)


@pytest.mark.parametrize(
    "objetivo, sube, precio, alcanzada",
    [
        (70000.0, True, 60000.0, False),
        (70000.0, True, 70000.0, True),
        (50000.0, False, 49000.0, True),
        (50000.0, False, 60000.0, False),
        (50000.0, False, None, False),
    ],
)
def test_alerta_alcanzada(objetivo, sube, precio, alcanzada):
    assert panel.Alerta(1, "bitcoin", objetivo, sube, precio).alcanzada is alcanzada


def test_muestrear_se_queda_con_el_ultimo():
    valores = list(range(1000))

    muestra = panel.muestrear(valores, 10)

    assert len(muestra) == 10
    assert muestra[0] == 0
    assert muestra[-1] == 999


def test_muestrear_corto_lo_deja_igual():
    assert panel.muestrear([1, 2, 3], 10) == [1, 2, 3]


def test_trazo_de_abajo_arriba():
    # En SVG la y crece hacia abajo: el mínimo va abajo del todo.
    assert panel.trazo([1.0, 3.0, 2.0], 100, 50) == "M0.0,50.0 L50.0,0.0 L100.0,25.0"


def test_trazo_plano_a_media_altura():
    assert panel.trazo([5.0, 5.0], 10, 20) == "M0.0,10.0 L10.0,10.0"


def test_trazo_con_un_punto_no_dibuja():
    assert panel.trazo([5.0], 10, 20) == ""


@pytest.mark.parametrize(
    "atras, texto",
    [
        (timedelta(seconds=20), "hace un momento"),
        (timedelta(minutes=7), "hace 7 min"),
        (timedelta(hours=5), "hace 5 h"),
        (timedelta(days=3), "hace 3 días"),
    ],
)
def test_hace(atras, texto):
    assert panel.hace(AHORA - atras, AHORA) == texto


def test_hace_sin_precios():
    assert panel.hace(None, AHORA) == "todavía sin precios"


def test_parado_tras_tres_ciclos():
    assert not panel.parado(AHORA - timedelta(minutes=14), AHORA, 300)
    assert panel.parado(AHORA - timedelta(minutes=16), AHORA, 300)
    assert panel.parado(None, AHORA, 300)


def test_en_bitcoin_sigue_al_precio_de_bitcoin_desde_el_principio():
    t0 = datetime(2026, 11, 20, 12, tzinfo=timezone.utc)
    serie = [
        (t0, 1000.0),
        (t0 + timedelta(hours=1), 1100.0),
        (t0 + timedelta(hours=2), 900.0),
    ]
    # Bitcoin guardado a otras horas: vale el último de antes de cada punto, así
    # que a las 13:00 aún cuenta el de 50.000 y el de 60.000 entra a las 14:00.
    btc = [(t0 - timedelta(minutes=5), 50000.0), (t0 + timedelta(minutes=70), 60000.0)]

    assert panel.en_bitcoin(serie, btc) == [1000.0, 1000.0, 1200.0]


def test_en_bitcoin_sin_precio_al_principio_no_dibuja_nada():
    t0 = datetime(2026, 11, 20, 12, tzinfo=timezone.utc)
    serie = [(t0, 1000.0), (t0 + timedelta(hours=1), 1100.0)]

    assert panel.en_bitcoin(serie, [(t0 + timedelta(minutes=30), 50000.0)]) == []
