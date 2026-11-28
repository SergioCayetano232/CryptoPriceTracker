"""Tests de /cme."""

import time
from datetime import date, datetime, timedelta, timezone

import pytest

from crypto_tracker.indicadores import cme
from crypto_tracker.indicadores.cme import apertura, cierre, horario_de_verano, leer

UTC = timezone.utc
HORA = timedelta(hours=1)
# Un fin de semana de invierno: el CME para el viernes a las 22:00 UTC y vuelve
# el domingo a las 23:00.
PARA = datetime(2026, 11, 20, 22, tzinfo=UTC)
VUELVE = datetime(2026, 11, 22, 23, tzinfo=UTC)


def _vela(cuando, apertura, maximo, minimo, cierre):
    t = int(cuando.timestamp() * 1000)
    return [t, str(apertura), str(maximo), str(minimo), str(cierre), "1", t, "1"]


def _horas(desde, hasta, precio):
    """Velas de una hora de desde a hasta (sin contarla). precio(cuando) da la vela."""
    velas = []
    cuando = desde
    while cuando < hasta:
        p = precio(cuando)
        velas.append(
            _vela(cuando, *p) if isinstance(p, tuple) else _vela(cuando, p, p, p, p)
        )
        cuando += HORA
    return velas


def _finde(cierra_en=None, hasta=datetime(2026, 11, 25, 6, tzinfo=UTC)):
    """A 100 hasta el viernes, a 110 desde entonces y, si se pide, vuelta a 100."""

    def precio(cuando):
        if cuando < PARA:
            return 100
        if cierra_en is not None and cuando == cierra_en:
            return (110, 111, 99, 105)
        return (110, 111, 109, 110)

    return _horas(datetime(2026, 11, 16, tzinfo=UTC), hasta, precio)


@pytest.mark.parametrize(
    "dia, verano",
    [
        (date(2026, 3, 7), False),
        (date(2026, 3, 8), True),  # el segundo domingo de marzo
        (date(2026, 10, 31), True),
        (date(2026, 11, 1), False),  # el primero de noviembre
        (date(2025, 3, 8), False),
        (date(2025, 3, 9), True),
        (date(2025, 11, 1), True),
        (date(2025, 11, 2), False),
    ],
)
def test_horario_de_verano(dia, verano):
    assert horario_de_verano(dia) is verano


def test_horas_del_cme():
    assert cierre(date(2026, 11, 20)) == PARA
    assert apertura(date(2026, 11, 22)) == VUELVE
    assert cierre(date(2026, 7, 17)) == datetime(2026, 7, 17, 21, tzinfo=UTC)
    assert apertura(date(2026, 7, 19)) == datetime(2026, 7, 19, 22, tzinfo=UTC)


def test_el_hueco_y_cuando_se_cierra():
    vuelta = datetime(2026, 11, 24, 10, tzinfo=UTC)
    c = leer(_finde(vuelta), datetime(2026, 11, 25, 6, tzinfo=UTC))

    h = c.ultimo
    assert len(c.huecos) == 1
    assert h.viernes == PARA
    assert h.domingo == VUELVE
    assert h.antes == 100
    assert h.despues == 110
    assert h.tamaño == pytest.approx(10)
    assert h.cerrado == vuelta
    assert h.horas == 35
    assert c.parado is None
    assert c.precio == 110


def test_sin_volver_sigue_abierto():
    c = leer(_finde(), datetime(2026, 11, 25, 6, tzinfo=UTC))

    assert c.ultimo.cerrado is None
    assert c.ultimo.horas is None
    assert c.cerrados == []


def test_si_abre_igual_se_cierra_en_la_primera_hora():
    velas = _horas(datetime(2026, 11, 16, tzinfo=UTC), VUELVE + 5 * HORA, lambda c: 100)

    h = leer(velas, VUELVE + 5 * HORA).ultimo

    assert h.cerrado == VUELVE
    assert h.horas == 0


def test_en_fin_de_semana_esta_parado():
    sabado = datetime(2026, 11, 21, 12, tzinfo=UTC)
    c = leer(_finde(hasta=sabado), sabado)

    assert c.huecos == []
    assert c.parado == (PARA, 100)
    assert c.precio == 110


def test_los_pendientes_sin_el_ultimo_y_por_cercania():
    # Cuatro fines de semana: sube 10 cada viernes y no vuelve nunca.
    inicio = datetime(2026, 10, 26, tzinfo=UTC)

    def precio(cuando):
        viernes = sum(
            cuando >= cierre(date(2026, 10, 30) + timedelta(weeks=i)) for i in range(4)
        )
        return 100 + 10 * viernes

    c = leer(
        _horas(inicio, datetime(2026, 11, 25, tzinfo=UTC), precio),
        datetime(2026, 11, 25, tzinfo=UTC),
    )

    assert len(c.huecos) == 4
    assert [h.antes for h in c.pendientes] == [120, 110, 100]
    assert c.ultimo.antes == 130


def test_sin_velas_no_hay():
    assert leer([], datetime.now(UTC)) is None
    assert leer({"code": -1}, datetime.now(UTC)) is None
    assert leer([None, ["x"], _vela(PARA, 0, 0, 0, 0)], datetime.now(UTC)) is None


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


def _binance(monkeypatch, velas):
    pedidos = []

    def pedir():
        pedidos.append(1)
        if isinstance(velas, Exception):
            raise velas
        return velas

    monkeypatch.setattr(cme, "pedir", pedir)
    return pedidos


def test_cme_cerrado(config, enviados, monkeypatch):
    _binance(monkeypatch, _finde(datetime(2026, 11, 24, 10, tzinfo=UTC)))

    main.atender(config, _mensaje("/cme"))

    texto = enviados[0]
    assert "🕳️ <b>Hueco del CME de bitcoin</b>" in texto
    assert "a $100 y abrió" in texto
    assert "a $110, un hueco de +10,0% hacia arriba." in texto
    assert "✅ Cerrado el martes 24/11" in texto
    assert "35 h después." in texto


def test_cme_abierto(config, enviados, monkeypatch):
    _binance(monkeypatch, _finde())

    main.atender(config, _mensaje("/hueco"))

    assert (
        "⏳ Sigue abierto: para cerrarlo tendría que volver a $100 (-9,1%"
        in enviados[0]
    )


def test_cme_parado(config, enviados, monkeypatch):
    # Que esté parado depende de la hora de verdad: lo fuerzo.
    _binance(monkeypatch, [])
    monkeypatch.setattr(
        cme, "leer", lambda datos, ahora: cme.Cme([], 110, (PARA, 100.0))
    )

    main.atender(config, _mensaje("/cme"))

    assert "🔒 El CME está parado desde el" in enviados[0]
    assert "Si abriera ahora, el hueco sería de +10,0%." in enviados[0]


def test_cme_solo_bitcoin(config, enviados, monkeypatch):
    pedidos = _binance(monkeypatch, [])

    main.atender(config, _mensaje("/gap eth"))

    assert "/cme" in enviados[0]
    assert pedidos == []


def test_cme_sin_datos(config, enviados, monkeypatch):
    _binance(monkeypatch, [])

    main.atender(config, _mensaje("/cme"))

    assert "no me ha dado bastantes horas" in enviados[0]


def test_cme_binance_caido(config, enviados, monkeypatch):
    _binance(monkeypatch, cme.CmeError("Binance no contesta: timeout"))

    main.atender(config, _mensaje("/cme"))

    assert "No he podido mirarlo ahora mismo: Binance no contesta" in enviados[0]
