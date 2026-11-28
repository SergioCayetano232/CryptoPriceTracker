"""Tests de /comisionred."""

import pytest
import requests

from crypto_tracker import comisionred
from crypto_tracker.avisos.alerts import formatear_comisionred
from crypto_tracker.comisionred import (
    TAMAÑO,
    ComisionRedError,
    en_dinero,
    leer,
)

AHORA = {
    "fastestFee": 12,
    "halfHourFee": 8,
    "hourFee": 6,
    "economyFee": 3,
    "minimumFee": 1,
}


def _semana(*medianas):
    return [{"avgHeight": 1, "avgFee_50": m, "avgFee_90": m * 2} for m in medianas]


def test_leer():
    c = leer(AHORA, _semana(9, 10, 11))

    assert [t.nombre for t in c.tarifas] == [
        "En unos 10 min",
        "En media hora",
        "En una hora",
        "Sin prisa",
    ]
    assert c.tarifas[1].sats_vb == 8
    assert c.tarifas[1].sats == 8 * TAMAÑO
    assert c.semana == 10
    assert c.nivel == "normal"


@pytest.mark.parametrize(
    "media_hora, nivel",
    [(1, "regalada"), (2, "regalada"), (5, "barata"), (10, "normal"), (14, "cara")],
)
def test_nivel(media_hora, nivel):
    assert leer({**AHORA, "halfHourFee": media_hora}, _semana(10)).nivel == nivel


def test_sin_semana_no_dice_nivel():
    c = leer(AHORA, [])
    assert c.semana is None
    assert c.nivel == ""


def test_sin_semana_pero_regalada():
    assert leer({**AHORA, "halfHourFee": 1}, None).nivel == "regalada"


def test_sin_media_hora_usa_la_primera():
    datos = {"fastestFee": 20, "hourFee": 5}
    assert leer(datos, _semana(10)).nivel == "cara"


def test_leer_ignora_lo_raro():
    c = leer(
        {"fastestFee": "12", "halfHourFee": True, "hourFee": 0, "economyFee": 3},
        [None, {"avgFee_50": "x"}, {"avgFee_50": 4}],
    )

    assert [t.nombre for t in c.tarifas] == ["Sin prisa"]
    assert c.semana == 4


def test_leer_nada():
    assert leer({}, []) is None
    assert leer(None, None) is None
    assert leer([], {}) is None


def test_en_dinero():
    # 1.128 sats a 80.000 por bitcoin: menos de un euro.
    assert en_dinero(1128, 80000) == pytest.approx(0.9024)


class _Respuesta:
    def __init__(self, datos, error=None):
        self.datos, self.error = datos, error

    def raise_for_status(self):
        if self.error:
            raise self.error

    def json(self):
        if isinstance(self.datos, Exception):
            raise self.datos
        return self.datos


def test_pedir(monkeypatch):
    respuestas = {
        comisionred.URL: _Respuesta(AHORA),
        comisionred.SEMANA_URL: _Respuesta(_semana(10)),
    }
    monkeypatch.setattr(requests, "get", lambda url, **k: respuestas[url])

    assert comisionred.pedir() == (AHORA, _semana(10))


def test_pedir_sin_semana_sigue(monkeypatch):
    def get(url, **k):
        if url == comisionred.SEMANA_URL:
            raise requests.ConnectionError("caída")
        return _Respuesta(AHORA)

    monkeypatch.setattr(requests, "get", get)

    assert comisionred.pedir() == (AHORA, [])


def test_pedir_falla(monkeypatch):
    def get(url, **k):
        raise requests.Timeout("lento")

    monkeypatch.setattr(requests, "get", get)

    with pytest.raises(ComisionRedError, match="mempool.space no contesta"):
        comisionred.pedir()


def test_pedir_no_es_json(monkeypatch):
    monkeypatch.setattr(
        requests, "get", lambda url, **k: _Respuesta(ValueError("no json"))
    )

    with pytest.raises(ComisionRedError, match="no es JSON"):
        comisionred.pedir()


def test_formatear():
    texto = formatear_comisionred(leer(AHORA, _semana(10)), 80000.0, "eur")

    assert "⛓️ <b>Lo que cuesta mover bitcoin ahora</b>" in texto
    # 8 sat/vB × 141 vB = 1.128 sats, a 80.000 € son 0,90 €.
    assert "🚶 En media hora: <b>€0,90</b> · 8 sat/vB" in texto
    assert "⚡ En unos 10 min: <b>€1,35</b> · 12 sat/vB" in texto
    assert "🟡 Normal para esta semana (10 sat/vB)" in texto
    assert "141 vB" in texto
    assert "mempool.space" in texto


def test_formatear_cara_y_barata():
    cara = formatear_comisionred(leer({"halfHourFee": 30}, _semana(10)), 80000.0, "eur")
    barata = formatear_comisionred(
        leer({"halfHourFee": 4}, _semana(10)), 80000.0, "eur"
    )

    assert "🔴 Cara" in cara and "Si no corre prisa, espera" in cara
    assert "🟢 Barata" in barata and "monedero" in barata


def test_formatear_centimos():
    texto = formatear_comisionred(leer({"halfHourFee": 1}, []), 5.0, "eur")
    assert "menos de 1 céntimo (141 sats)" in texto
    assert "🎁 Casi regalada" in texto


def test_formatear_sin_precio():
    texto = formatear_comisionred(leer({"halfHourFee": 80}, []), None, "eur")
    assert "<b>11.280 sats</b>" in texto
    assert "Cara" not in texto


def test_formatear_sin_datos():
    assert "Prueba en un rato" in formatear_comisionred(None, 80000.0, "eur")


# --- el aviso de /comisionred 5 ---


@pytest.mark.parametrize(
    "texto, sale",
    [
        ("", None),
        ("5", 5),
        ("5 sat/vB", 5),
        ("12sat", 12),
        ("no", comisionred.QUITAR),
        ("quitar", comisionred.QUITAR),
    ],
)
def test_interpretar(texto, sale):
    assert comisionred.interpretar(texto) == sale


@pytest.mark.parametrize("texto", ["0", "barato", "-3", "5000", "2,5"])
def test_interpretar_mal(texto):
    with pytest.raises(ComisionRedError, match="/comisionred 5"):
        comisionred.interpretar(texto)


def test_toca_cuando_la_de_media_hora_baja_al_limite():
    datos = leer(AHORA, [])  # media hora a 8

    assert comisionred.toca(datos, 8)
    assert comisionred.toca(datos, 10)
    assert not comisionred.toca(datos, 7)
    assert not comisionred.toca(None, 100)


def test_toca_sin_media_hora_mira_la_primera():
    assert comisionred.toca(leer({"economyFee": 3}, []), 3)


def test_pedir_ahora_no_pide_la_semana(monkeypatch):
    pedidas = []
    monkeypatch.setattr(comisionred, "_get", lambda url: pedidas.append(url) or AHORA)

    assert comisionred.pedir_ahora() == AHORA
    assert pedidas == [comisionred.URL]


def test_formatear_el_aviso():
    from crypto_tracker.avisos.alerts import formatear_aviso_comisionred

    texto = formatear_aviso_comisionred(leer(AHORA, []), 10, 80000.0, "eur")

    assert "⛓️ <b>Mover bitcoin ya está barato</b>" in texto
    assert "🚶 En media hora: <b>€0,90</b> · 8 sat/vB" in texto
    assert "Pedías 10 o menos" in texto
    assert "/comisionred 10" in texto


def test_formatear_dice_el_aviso_que_tienes_puesto():
    con = formatear_comisionred(leer(AHORA, []), 80000.0, "eur", 5)
    sin = formatear_comisionred(leer(AHORA, []), 80000.0, "eur")

    assert "🔔 Te aviso cuando la de media hora baje a 5 sat/vB" in con
    assert "🔔" not in sin
