"""Tests de /maxpain."""

import time
from datetime import datetime, timezone

import pytest
import requests

from crypto_tracker import maxpain
from crypto_tracker.maxpain import MaxPainError, leer, vence

UTC = timezone.utc
# Un miércoles: el viernes es el 27 y el diario de mañana, el 26.
AHORA = datetime(2026, 11, 25, 12, tzinfo=UTC)


def _op(nombre, abiertas, precio=60_000):
    return {
        "instrument_name": nombre,
        "open_interest": abiertas,
        "estimated_delivery_price": precio,
    }


def _viernes():
    # Calls y puts repartidos: el que menos paga es el de 60.000.
    return [
        _op("BTC-27NOV26-50000-P", 10),
        _op("BTC-27NOV26-60000-P", 5),
        _op("BTC-27NOV26-60000-C", 5),
        _op("BTC-27NOV26-70000-C", 10),
    ]


def test_vence():
    assert vence("27NOV26") == datetime(2026, 11, 27, 8, tzinfo=UTC)
    assert vence("5JAN27") == datetime(2027, 1, 5, 8, tzinfo=UTC)
    with pytest.raises(ValueError):
        vence("27XXX26")


def test_el_max_pain_es_el_que_menos_paga():
    v = leer("BTC", _viernes(), AHORA).viernes

    assert v.max_pain == 60_000
    assert v.pago(60_000) == 0
    # A 70.000: los 5 calls de 60.000 cobran 10.000 cada uno.
    assert v.pago(70_000) == 50_000
    # A 50.000: los 5 puts de 60.000.
    assert v.pago(50_000) == 50_000


def test_el_max_pain_se_va_hacia_donde_hay_mas_calls():
    datos = [
        _op("BTC-27NOV26-50000-C", 100),
        _op("BTC-27NOV26-60000-P", 1),
        _op("BTC-27NOV26-70000-P", 1),
    ]

    assert leer("BTC", datos, AHORA).viernes.max_pain == 50_000


def test_cuentas_del_vencimiento():
    v = leer("BTC", _viernes(), AHORA).viernes

    assert v.calls == 15
    assert v.puts == 15
    assert v.abiertas == 30
    assert v.put_call == 1
    assert v.mas_abiertas(True) == 70_000
    assert v.mas_abiertas(False) == 50_000
    assert v.precio == 60_000


def test_se_salta_los_diarios_y_los_vencidos():
    datos = _viernes() + [
        _op("BTC-26NOV26-55000-C", 500),  # mañana, jueves
        _op("BTC-20NOV26-55000-C", 500),  # ya vencido
    ]

    mp = leer("BTC", datos, AHORA)

    assert mp.viernes.vence == datetime(2026, 11, 27, 8, tzinfo=UTC)
    # El de mañana es el más gordo aunque no sea viernes.
    assert mp.gordo.vence == datetime(2026, 11, 26, 8, tzinfo=UTC)


def test_el_viernes_pasadas_las_8_va_al_siguiente():
    datos = _viernes() + [_op("BTC-4DEC26-60000-C", 1)]

    mp = leer("BTC", datos, datetime(2026, 11, 27, 9, tzinfo=UTC))

    assert mp.viernes.vence == datetime(2026, 12, 4, 8, tzinfo=UTC)


def test_el_gordo():
    datos = _viernes() + [_op("BTC-25DEC26-80000-C", 300)]

    mp = leer("BTC", datos, AHORA)

    assert mp.gordo.vence == datetime(2026, 12, 25, 8, tzinfo=UTC)
    assert mp.gordo.abiertas == 300


def test_ignora_lo_roto():
    datos = _viernes() + [
        None,
        {},
        _op("BTC-27NOV26-60000", 5),
        _op("BTC-27NOV26-60000-X", 5),
        _op("BTC-27XXX26-60000-C", 5),
        _op("BTC-27NOV26-60000-C", "nada"),
        _op("BTC-27NOV26-60000-C", -1),
        _op("BTC-27NOV26-60000-C", 5, precio=0),
        _op("BTC-27NOV26-90000-C", 0),
    ]

    v = leer("BTC", datos, AHORA).viernes

    assert v.abiertas == 30
    assert 90_000 not in {o.strike for o in v.opciones}


def test_sin_viernes_no_hay():
    assert leer("BTC", [], AHORA) is None
    assert leer("BTC", {"x": 1}, AHORA) is None
    assert leer("BTC", [_op("BTC-26NOV26-55000-C", 5)], AHORA) is None


class _Respuesta:
    def __init__(self, datos, status=200):
        self.datos, self.status_code = datos, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))

    def json(self):
        if isinstance(self.datos, Exception):
            raise self.datos
        return self.datos


def test_pedir(monkeypatch):
    pedidos = []

    def get(url, params, timeout):
        pedidos.append(params)
        return _Respuesta({"result": _viernes()})

    monkeypatch.setattr(maxpain.requests, "get", get)

    assert maxpain.pedir("ETH") == _viernes()
    assert pedidos == [{"currency": "ETH", "kind": "option"}]


@pytest.mark.parametrize(
    "respuesta, error",
    [
        (requests.ConnectionError("sin red"), "Deribit no contesta"),
        (_Respuesta({}, 500), "Deribit no contesta"),
        (_Respuesta(ValueError("x")), "no es JSON"),
    ],
)
def test_pedir_falla(monkeypatch, respuesta, error):
    def get(url, params, timeout):
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta

    monkeypatch.setattr(maxpain.requests, "get", get)

    with pytest.raises(MaxPainError, match=error):
        maxpain.pedir("BTC")


# --- el comando ---

import main  # noqa: E402
from crypto_tracker.nucleo import database, telegram  # noqa: E402
from crypto_tracker.nucleo.config import Config, Watch  # noqa: E402


@pytest.fixture
def config(tmp_path):
    ruta = str(tmp_path / "test.db")
    database.init_db(ruta)
    return Config("token", "123", [Watch("solana", percent=5)], "eur", 300, ruta, 0)


@pytest.fixture
def enviados(monkeypatch):
    lista = []
    monkeypatch.setattr(
        telegram, "send_message", lambda t, c, texto, **kw: lista.append(texto) or True
    )
    return lista


def _mensaje(texto):
    return {"chat": {"id": 123}, "text": texto, "date": int(time.time())}


def _deribit(monkeypatch, datos, ahora=AHORA):
    pedidos = []

    def pedir(moneda):
        pedidos.append(moneda)
        if isinstance(datos, Exception):
            raise datos
        return datos

    monkeypatch.setattr(maxpain, "pedir", pedir)
    # Las fechas de los datos son fijas: el "ahora" también.
    leer = maxpain.leer
    monkeypatch.setattr(maxpain, "leer", lambda m, d, a: leer(m, d, ahora))
    return pedidos


def test_maxpain_a_secas_es_bitcoin(config, enviados, monkeypatch):
    datos = [_op(o["instrument_name"], o["open_interest"], 63_000) for o in _viernes()]
    pedidos = _deribit(monkeypatch, datos + [_op("BTC-25DEC26-80000-C", 300, 63_000)])

    main.atender(config, _mensaje("/maxpain"))

    assert pedidos == ["BTC"]
    texto = enviados[0]
    assert "🎯 <b>Max pain de Bitcoin: $60.000</b>" in texto
    assert "Vencen el viernes 27/11 a las " in texto
    assert ": 30 BTC en opciones (2 millones de $)." in texto
    assert "Ahora está a $63.000, un 5,0% por encima." in texto
    assert "Puts entre calls: 1,00, más seguros contra caídas." in texto
    assert "Donde más calls hay: $70.000 · más puts: $50.000" in texto
    assert "El grande de verdad vence el viernes 25/12" in texto
    assert "con el max pain en $80.000." in texto


def test_maxpain_sin_otro_mas_grande(config, enviados, monkeypatch):
    _deribit(monkeypatch, _viernes())

    main.atender(config, _mensaje("/vencimiento"))

    assert "El grande de verdad" not in enviados[0]


def test_maxpain_de_ethereum(config, enviados, monkeypatch):
    datos = [_op("ETH-27NOV26-2000-C", 40, 2_100), _op("ETH-27NOV26-1800-P", 10, 2_100)]
    pedidos = _deribit(monkeypatch, datos)

    main.atender(config, _mensaje("/maxpain eth"))

    assert pedidos == ["ETH"]
    # A 1.800 ni los calls de 2.000 ni los puts de 1.800 cobran nada.
    assert "Max pain de Ethereum: $1.800" in enviados[0]
    assert "50 ETH en opciones ($105.000)" in enviados[0]
    assert "más apuestas a que sube" in enviados[0]


def test_maxpain_de_otra(config, enviados, monkeypatch):
    pedidos = _deribit(monkeypatch, [])

    main.atender(config, _mensaje("/maxpain sol"))

    assert "solo tiene opciones de bitcoin y de ethereum" in enviados[0]
    assert pedidos == []


def test_maxpain_sin_viernes(config, enviados, monkeypatch):
    _deribit(monkeypatch, [])

    main.atender(config, _mensaje("/maxpain"))

    assert "no me ha dado opciones del viernes" in enviados[0]


def test_maxpain_deribit_caido(config, enviados, monkeypatch):
    _deribit(monkeypatch, MaxPainError("Deribit no contesta: timeout"))

    main.atender(config, _mensaje("/maxpain"))

    assert "No he podido mirarlo ahora mismo: Deribit no contesta" in enviados[0]
