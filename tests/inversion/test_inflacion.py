"""Tests de /inflacion."""

from datetime import date, datetime, timezone

import pytest
import requests

from crypto_tracker.avisos.alerts import formatear_inflacion
from crypto_tracker.inversion import inflacion
from crypto_tracker.inversion.inflacion import (
    Inflacion,
    InflacionError,
    calcular,
    indice,
    leer,
)
from crypto_tracker.inversion.movimientos import Movimiento

# Un 10% de subida en un año, y el último mes publicado es junio.
IPC = {
    date(2025, 1, 1): 100.0,
    date(2025, 6, 1): 104.0,
    date(2026, 1, 1): 110.0,
    date(2026, 6, 1): 110.0,
}
AHORA = datetime(2026, 11, 15, tzinfo=timezone.utc)


def _mov(id, tipo, cantidad, coste, cuando, coin="bitcoin"):
    return Movimiento(id, coin, tipo, cantidad, coste, None, cuando)


def _el(año, mes, dia=10):
    return datetime(año, mes, dia, tzinfo=timezone.utc)


def _jsonstat(meses):
    return {
        "dimension": {
            "time": {"category": {"index": {m: i for i, m in enumerate(meses)}}}
        },
        "value": {str(i): v for i, v in enumerate(meses.values())},
    }


def test_leer():
    datos = _jsonstat({"2026-09": 133.48, "2026-08": 132.65})
    assert leer(datos) == {date(2026, 8, 1): 132.65, date(2026, 9, 1): 133.48}


def test_leer_salta_lo_que_falta():
    datos = _jsonstat({"2026-07": 131.79, "2026-08": 132.65, "raro": 1.0})
    # Eurostat a veces no trae un mes: su posición no sale en value.
    del datos["value"]["1"]
    datos["value"]["2"] = True
    assert leer(datos) == {date(2026, 7, 1): 131.79}


@pytest.mark.parametrize(
    "datos", [None, {}, {"dimension": {}}, {"value": [], "dimension": None}]
)
def test_leer_nada(datos):
    assert leer(datos) == {}


@pytest.mark.parametrize(
    "cuando, esperado",
    [
        (date(2025, 1, 20), 100.0),
        (date(2025, 3, 1), 100.0),  # falta marzo: el de antes
        (date(2026, 11, 15), 110.0),  # aún sin publicar: el último
        (date(2020, 5, 1), 100.0),  # antes del primero: el primero
    ],
)
def test_indice(cuando, esperado):
    assert indice(IPC, cuando) == esperado


def test_le_gana():
    # 1.000 € en enero de 2025, con un 10% de inflación: harían falta 1.100.
    r = calcular(
        [_mov(1, "compra", 0.02, 1000, _el(2025, 1))], {"bitcoin": 60000.0}, AHORA, IPC
    )

    assert r.vale == pytest.approx(1200)
    assert r.puesto == pytest.approx(1000)
    assert r.necesario == pytest.approx(1100)
    assert r.subida == pytest.approx(10)
    assert r.diferencia == pytest.approx(100)
    assert r.de_verdad == pytest.approx(1200 / 1100 * 100 - 100)
    assert r.hasta == date(2026, 6, 1)


def test_cada_compra_con_su_fecha():
    lista = [
        _mov(1, "compra", 0.01, 1000, _el(2025, 1)),  # +10%
        _mov(2, "compra", 0.01, 1040, _el(2025, 6)),  # 104 -> 110
    ]
    r = calcular(lista, {"bitcoin": 100000.0}, AHORA, IPC)

    assert r.necesario == pytest.approx(1100 + 1100)
    assert r.subida == pytest.approx(10)


def test_ventas_restan():
    lista = [
        _mov(1, "compra", 0.02, 1000, _el(2025, 1)),
        _mov(2, "venta", 0.01, 520, _el(2025, 6)),
    ]
    r = calcular(lista, {"bitcoin": 50000.0}, AHORA, IPC)

    assert r.puesto == pytest.approx(480)
    assert r.necesario == pytest.approx(1100 - 550)
    assert r.vale == pytest.approx(500)
    assert r.diferencia < 0


def test_sacaste_mas_de_lo_que_metiste():
    lista = [
        _mov(1, "compra", 0.02, 1000, _el(2025, 1)),
        _mov(2, "venta", 0.01, 3000, _el(2026, 1)),
    ]
    r = calcular(lista, {"bitcoin": 50000.0}, AHORA, IPC)
    assert r.necesario == 0 and r.puesto == 0
    assert r.de_verdad is None


def test_sin_precio_o_sin_ipc():
    lista = [_mov(1, "compra", 0.02, 1000, _el(2025, 1))]
    assert calcular(lista, {}, AHORA, IPC) is None
    assert calcular(lista, {"bitcoin": 1.0}, AHORA, {}) is None


class _Respuesta:
    def __init__(self, datos, status=200):
        self.datos, self.status_code = datos, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")

    def json(self):
        if isinstance(self.datos, Exception):
            raise self.datos
        return self.datos


def test_pedir(monkeypatch):
    def get(url, params, **k):
        assert "prc_hicp_minr" in url
        assert params == {"geo": "ES", "coicop18": "TOTAL", "unit": "I15"}
        return _Respuesta(_jsonstat({"2026-09": 133.48}))

    monkeypatch.setattr(requests, "get", get)

    assert inflacion.pedir() == {date(2026, 9, 1): 133.48}


@pytest.mark.parametrize(
    "respuesta, mensaje",
    [
        (_Respuesta({}, 500), "Eurostat no contesta"),
        (_Respuesta(ValueError("x")), "no es JSON"),
        (_Respuesta({"value": {}}), "no ha dado el IPC"),
    ],
)
def test_pedir_falla(monkeypatch, respuesta, mensaje):
    monkeypatch.setattr(requests, "get", lambda url, **k: respuesta)

    with pytest.raises(InflacionError, match=mensaje):
        inflacion.pedir()


def _hecho(vale, necesario=1100.0, fuera=0):
    return Inflacion(
        vale, 1000.0, necesario, 10.0, _el(2025, 1), date(2026, 9, 1), fuera
    )


def test_formatear_gana():
    texto = formatear_inflacion(_hecho(1200.0), "eur")

    assert "🎈 <b>Tu cartera contra la inflación</b>" in texto
    assert "Desde tu primera compra (01/2025)" in texto
    assert "han subido un <b>10,0%</b>" in texto
    assert (
        "Pusiste €1.000,00: para comprar lo mismo hoy harían falta €1.100,00" in texto
    )
    assert "Lo que te queda vale <b>€1.200,00</b>" in texto
    assert "✅ Le ganas a la inflación: <b>9,1%</b> más de poder de compra" in texto
    assert "(€100,00 por encima)" in texto
    assert "hasta 09/2026" in texto
    assert "tu cartera va en" not in texto


def test_formatear_pierde_en_dolares():
    texto = formatear_inflacion(_hecho(1045.0, fuera=2), "usd")

    assert "🔥 La inflación te gana: has perdido un <b>5,0%</b>" in texto
    assert "($55,00 por debajo)" in texto
    assert "Es la inflación del euro y tu cartera va en USD" in texto
    assert "2 movimientos no cuentan" in texto


def test_formatear_ya_sacaste_todo():
    texto = formatear_inflacion(_hecho(500.0, necesario=0.0), "eur")
    assert "Ya sacaste más de lo que metiste" in texto
    assert "€500,00, es todo ganancia" in texto
