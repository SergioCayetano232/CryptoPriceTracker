"""Tests de /funding."""

import pytest
import requests

from crypto_tracker.avisos.alerts import formatear_funding
from crypto_tracker.indicadores import funding
from crypto_tracker.indicadores.funding import FundingError, como_esta, leer, par

AHORA = {"symbol": "BTCUSDT", "lastFundingRate": "0.00010000"}


def _antes(*tasas):
    return [{"symbol": "BTCUSDT", "fundingRate": t} for t in tasas]


@pytest.mark.parametrize(
    "coin_id, escrito, esperado",
    [
        ("bitcoin", "", "BTCUSDT"),
        ("bitcoin", "bitcoin", "BTCUSDT"),
        ("solana", "SOL", "SOLUSDT"),
        ("pepe", "pepe", "PEPEUSDT"),
    ],
)
def test_par(coin_id, escrito, esperado):
    assert par(coin_id, escrito) == esperado


def test_leer():
    f = leer("BTCUSDT", AHORA, _antes("0.0002", "0.0004"))

    assert f.ahora == pytest.approx(0.01)
    assert f.semana == pytest.approx(0.03)
    assert f.al_año == pytest.approx(0.03 * 3 * 365)
    # Manda la media de la semana, no el último pago.
    assert f.nivel == "Apostando a que sube"


def test_sin_semana_usa_el_ultimo():
    f = leer("BTCUSDT", AHORA, [])
    assert f.semana is None
    assert f.nivel == "Tranquilo"


@pytest.mark.parametrize(
    "tasa, nivel",
    [
        (-0.03, "Muchos apostando a que baja"),
        (-0.005, "Algo más a la baja que al alza"),
        (0.0, "Tranquilo"),
        (0.01, "Tranquilo"),
        (0.03, "Apostando a que sube"),
        (0.08, "Muy apalancado al alza"),
    ],
)
def test_como_esta(tasa, nivel):
    assert como_esta(tasa)[1] == nivel


def test_leer_ignora_lo_raro():
    f = leer("BTCUSDT", AHORA, [None, {"fundingRate": "x"}, {}, *_antes("0.0001")])
    assert f.semana == pytest.approx(0.01)


def test_leer_nada():
    assert leer("BTCUSDT", {}, []) is None
    assert leer("BTCUSDT", {"lastFundingRate": None}, []) is None
    assert leer("BTCUSDT", None, None) is None


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
        assert params["symbol"] == "BTCUSDT"
        if url == funding.ANTES_URL:
            assert params["limit"] == 21
            return _Respuesta(_antes("0.0001"))
        return _Respuesta(AHORA)

    monkeypatch.setattr(requests, "get", get)

    assert funding.pedir("BTCUSDT") == (AHORA, _antes("0.0001"))


def test_pedir_sin_semana_sigue(monkeypatch):
    def get(url, **k):
        if url == funding.ANTES_URL:
            raise requests.ConnectionError("caída")
        return _Respuesta(AHORA)

    monkeypatch.setattr(requests, "get", get)

    assert funding.pedir("BTCUSDT") == (AHORA, [])


@pytest.mark.parametrize(
    "respuesta, mensaje",
    [
        (_Respuesta({"code": -1121}, 400), "sin futuros"),
        (_Respuesta({}, 451), "desde este país"),
        (_Respuesta({}, 500), "Binance no contesta"),
        (_Respuesta(ValueError("no json")), "no es JSON"),
    ],
)
def test_pedir_falla(monkeypatch, respuesta, mensaje):
    monkeypatch.setattr(requests, "get", lambda url, **k: respuesta)

    with pytest.raises(FundingError, match=mensaje):
        funding.pedir("BTCUSDT")


def test_pedir_sin_red(monkeypatch):
    def get(url, **k):
        raise requests.Timeout("lento")

    monkeypatch.setattr(requests, "get", get)

    with pytest.raises(FundingError, match="Binance no contesta"):
        funding.pedir("BTCUSDT")


def test_formatear():
    texto = formatear_funding(leer("BTCUSDT", AHORA, _antes("0.0008", "0.0008")))

    assert "🔥 <b>Funding de BTC: +0,0100%</b> cada 8 h" in texto
    assert "<b>Muy apalancado al alza</b>" in texto
    assert "caídas bruscas" in texto
    assert "Media de la semana: +0,0800%" in texto
    assert "Al año serían un 87,6%" in texto
    assert "Binance" in texto


def test_formatear_negativo_sin_semana():
    texto = formatear_funding(leer("ETHUSDT", {"lastFundingRate": "-0.0003"}, []))

    assert "😱 <b>Funding de ETH: -0,0300%</b>" in texto
    assert "Media de la semana" not in texto
    assert "Al año serían un -32,9%" in texto


# --- el aviso de /funding btc avisa ---


def _f(semana, ahora=0.01):
    from crypto_tracker.indicadores import funding

    return funding.Funding("BTCUSDT", ahora, semana, *funding.como_esta(semana))


def test_separar_la_orden_del_final():
    from crypto_tracker.indicadores import funding

    assert funding.separar("btc avisa") == ("btc", funding.AVISA)
    assert funding.separar("btc Avísame") == ("btc", funding.AVISA)
    assert funding.separar("btc no") == ("btc", funding.QUITAR)
    assert funding.separar("btc") == ("btc", None)
    assert funding.separar("") == ("", None)
    # Sin cripto delante no es una orden: "no" a secas se queda como estaba.
    assert funding.separar("no") == ("no", None)


def test_extremo_solo_en_las_dos_puntas():
    from crypto_tracker.indicadores import funding

    assert funding.extremo(_f(-0.02)) == funding.BAJO
    assert funding.extremo(_f(-0.005)) == ""
    assert funding.extremo(_f(0.01)) == ""
    assert funding.extremo(_f(0.03)) == ""
    assert funding.extremo(_f(0.06)) == funding.ALTO


def test_extremo_mira_la_semana_y_no_un_pago_suelto():
    from crypto_tracker.indicadores import funding

    assert funding.extremo(_f(0.01, ahora=0.09)) == ""


def test_avisa_al_entrar_en_la_punta_y_no_mientras_sigue():
    from crypto_tracker.indicadores import funding
    from crypto_tracker.indicadores.funding import ALTO, BAJO, Vigilado

    assert funding.toca(Vigilado("BTCUSDT", "bitcoin"), _f(0.06)) == (True, ALTO)
    assert funding.toca(Vigilado("BTCUSDT", "bitcoin", ALTO), _f(0.07)) == (False, ALTO)
    # Al calmarse se olvida, para avisar la próxima vez.
    assert funding.toca(Vigilado("BTCUSDT", "bitcoin", ALTO), _f(0.01)) == (False, "")
    # De una punta a la otra también es noticia.
    assert funding.toca(Vigilado("BTCUSDT", "bitcoin", ALTO), _f(-0.02)) == (True, BAJO)


def test_se_mira_una_vez_por_hora():
    from datetime import datetime, timedelta, timezone

    from crypto_tracker.indicadores import funding
    from crypto_tracker.indicadores.funding import Vigilado

    ahora = datetime(2026, 11, 22, 12, 0, tzinfo=timezone.utc)

    assert funding.toca_mirar(Vigilado("BTCUSDT", "bitcoin"), ahora)
    hace_poco = Vigilado("BTCUSDT", "bitcoin", "", ahora - timedelta(minutes=30))
    assert not funding.toca_mirar(hace_poco, ahora)
    hace_rato = Vigilado("BTCUSDT", "bitcoin", "", ahora - timedelta(minutes=60))
    assert funding.toca_mirar(hace_rato, ahora)


def test_mensaje_del_aviso():
    from crypto_tracker.avisos.alerts import formatear_aviso_funding

    texto = formatear_aviso_funding(_f(0.0612))

    assert "🔥 <b>Funding de BTC: muy apalancado al alza</b>" in texto
    assert "Media de la semana: <b>+0,0612%</b> cada 8 h" in texto
    assert "caídas bruscas" in texto
    assert "/funding btc" in texto


def test_formatear_recuerda_que_tienes_el_aviso():
    from crypto_tracker.avisos.alerts import formatear_funding

    assert "🔔 Te aviso" in formatear_funding(_f(0.01), True)
    assert "/funding btc no" in formatear_funding(_f(0.01), True)
    assert "🔔" not in formatear_funding(_f(0.01))
