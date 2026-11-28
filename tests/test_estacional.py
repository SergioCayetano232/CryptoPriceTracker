"""Tests de /estacional."""

from datetime import date, datetime, timezone

import pytest
import requests

from crypto_tracker import estacional
from crypto_tracker.avisos.alerts import formatear_estacional
from crypto_tracker.estacional import Estacional, EstacionalError, Mes, calcular, leer

AHORA = datetime(2026, 11, 15, tzinfo=timezone.utc)


def _ms(año, mes, dia=1):
    return int(datetime(año, mes, dia, tzinfo=timezone.utc).timestamp() * 1000)


def _vela(año, mes, abre, cierra):
    sig = (año + 1, 1) if mes == 12 else (año, mes + 1)
    return [_ms(año, mes), str(abre), "0", "0", str(cierra), "0", _ms(*sig) - 1]


def test_leer():
    velas = [
        _vela(2025, 8, 50, 100),  # el primero, a medias: fuera
        _vela(2025, 9, 100, 110),
        _vela(2025, 10, 110, 99),
        _vela(2026, 11, 99, 120),  # sin cerrar: fuera
    ]

    meses = leer(velas, AHORA)

    assert [(m.year, m.month) for m, _ in meses] == [(2025, 9), (2025, 10)]
    assert meses[0][1] == pytest.approx(10)
    assert meses[1][1] == pytest.approx(-10)


def test_leer_ignora_lo_raro():
    velas = [
        _vela(2025, 1, 1, 1),
        None,
        [1, 2],
        [_ms(2025, 2), "x", "0", "0", "1", "0", _ms(2025, 3)],
        [_ms(2025, 3), "0", "0", "0", "1", "0", _ms(2025, 4)],
        _vela(2025, 4, 100, 120),
    ]

    assert [m.month for m, _ in leer(velas, AHORA)] == [4]
    assert leer({"code": -1121}, AHORA) == []
    assert leer(None, AHORA) == []


def _mes(año, mes, cambio):
    return (datetime(año, mes, 1, tzinfo=timezone.utc), cambio)


def test_calcular():
    meses = [
        _mes(2021, 10, 40),
        _mes(2022, 10, 5),
        _mes(2023, 10, -2),
        _mes(2022, 6, -30),
        _mes(2023, 6, -10),
    ]

    e = calcular(meses)

    octubre = e.de(10)
    # La mediana: el +40% no la arrastra.
    assert octubre.suele == 5
    assert (octubre.subio, octubre.veces) == (2, 3)
    assert e.de(6).suele == -20
    assert e.mejor.mes == 10 and e.peor.mes == 6
    assert e.desde == 2021
    assert e.años == 3
    assert [m.mes for m in e.meses] == [6, 10]


def test_calcular_nada():
    assert calcular([]) is None


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
        assert params == {"symbol": "BTCUSDT", "interval": "1M", "limit": 1000}
        return _Respuesta([_vela(2025, 1, 1, 2)])

    monkeypatch.setattr(requests, "get", get)

    assert estacional.pedir("BTCUSDT") == [_vela(2025, 1, 1, 2)]


@pytest.mark.parametrize(
    "respuesta, mensaje",
    [
        (_Respuesta({"code": -1121}, 400), "sin datos"),
        (_Respuesta({}, 451), "desde este país"),
        (_Respuesta({}, 500), "Binance no contesta"),
        (_Respuesta(ValueError("no json")), "no es JSON"),
    ],
)
def test_pedir_falla(monkeypatch, respuesta, mensaje):
    monkeypatch.setattr(requests, "get", lambda url, **k: respuesta)

    with pytest.raises(EstacionalError, match=mensaje):
        estacional.pedir("BTCUSDT")


def test_pedir_sin_red(monkeypatch):
    def get(url, **k):
        raise requests.Timeout("lento")

    monkeypatch.setattr(requests, "get", get)

    with pytest.raises(EstacionalError, match="Binance no contesta"):
        estacional.pedir("BTCUSDT")


def _estacional(años=8):
    return Estacional(
        [Mes(9, -4.3, 2, 8), Mes(10, 12.3, 7, 8), Mes(11, 3.0, 5, 8)], 2017, años
    )


def test_formatear():
    texto = formatear_estacional("bitcoin", _estacional(), date(2026, 11, 15))

    assert "📅 <b>Bitcoin</b> mes a mes, desde 2017" in texto
    assert "🔻 Sep: <b>-4,3%</b> · subió 2 de 8" in texto
    assert "🔺 Oct: <b>+12,3%</b> · subió 7 de 8" in texto
    assert "🔺 Nov: <b>+3,0%</b> · subió 5 de 8 ← este mes" in texto
    assert "🏆 El mejor, <b>octubre</b>" in texto
    assert "💀 El peor, <b>septiembre</b>" in texto
    assert "la mediana" in texto
    assert "casi azar" not in texto


def test_formatear_pocos_años():
    texto = formatear_estacional("solana", _estacional(años=2), date(2026, 1, 1))

    assert "Con menos de 4 años es casi azar" in texto
    assert "este mes" not in texto


def test_formatear_un_solo_mes():
    texto = formatear_estacional(
        "hyperliquid", Estacional([Mes(10, -3.2, 0, 1)], 2026, 1)
    )

    assert "🔻 Oct: <b>-3,2%</b> · subió 0 de 1" in texto
    assert "El mejor" not in texto and "El peor" not in texto
