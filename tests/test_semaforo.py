"""Tests de /semaforo."""

from datetime import date

import pytest

from crypto_tracker import semaforo
from crypto_tracker.alerts import formatear_semaforo
from crypto_tracker.bollinger import Bandas
from crypto_tracker.funding import Funding
from crypto_tracker.macd import Macd
from crypto_tracker.miedo import Indice
from crypto_tracker.rsi import Rsi
from crypto_tracker.semaforo import AMBAR, ROJO, VERDE, Voto


def _votos(*valores):
    return [Voto(f"v{i}", v, "porque sí") for i, v in enumerate(valores)]


@pytest.mark.parametrize("valor, voto", [(25, 1), (30, 1), (50, 0), (70, -1), (88, -1)])
def test_rsi(valor, voto):
    v = semaforo.de_rsi(Rsi(valor, 100.0, 30))

    assert v.valor == voto
    assert v.nombre == f"RSI {valor}"


def _macd(macd, señal, hist_ayer):
    return Macd(macd, señal, 100.0, hist_ayer, None, 60)


def test_macd_cogiendo_empuje_arriba():
    assert semaforo.de_macd(_macd(5, 2, 1)).valor == 1


def test_macd_cogiendo_empuje_abajo():
    assert semaforo.de_macd(_macd(-5, -2, -1)).valor == -1


def test_macd_que_se_apaga_no_vota():
    # Sigue arriba, pero menos que ayer
    assert semaforo.de_macd(_macd(5, 4, 3)).valor == 0


@pytest.mark.parametrize("ahora, voto", [(79, 1), (100, 0), (121, -1)])
def test_bandas(ahora, voto):
    b = Bandas(120.0, 100.0, 80.0, ahora, 40.0, None, 30)

    assert semaforo.de_bandas(b).valor == voto


def test_medias():
    assert semaforo.de_medias(110, {7: 100, 30: 90, 90: 80}).valor == 1
    assert semaforo.de_medias(70, {7: 100, 30: 90, 90: 80}).valor == -1
    assert semaforo.de_medias(95, {7: 100, 30: 90, 90: 80}).valor == 0


def test_con_una_sola_media_no_hay_voto():
    assert semaforo.de_medias(110, {7: 100, 30: None, 90: None}) is None


@pytest.mark.parametrize("valor, voto", [(10, 1), (25, 1), (50, 0), (75, -1)])
def test_miedo_vota_al_reves_que_la_gente(valor, voto):
    assert semaforo.de_miedo(Indice(valor, "", date(2026, 11, 22))).valor == voto


@pytest.mark.parametrize(
    "ahora, semana, voto",
    [(-0.02, None, 1), (0.01, None, 0), (0.06, None, -1), (0.06, 0.01, 0)],
)
def test_funding_mira_la_semana_si_la_hay(ahora, semana, voto):
    f = Funding("BTCUSDT", ahora, semana, "", "", "")

    assert semaforo.de_funding(f).valor == voto


@pytest.mark.parametrize(
    "valores, color",
    [
        ((1, 1, 0), VERDE),
        ((1, 1, 1, -1), VERDE),
        ((1, 0, 0), AMBAR),
        ((1, -1, 0, 0), AMBAR),
        ((1, 1, -1, -1, -1), AMBAR),
        ((-1, -1, 0), ROJO),
    ],
)
def test_luz(valores, color):
    assert semaforo.luz(_votos(*valores)) == color


def test_con_dos_votos_no_hay_luz():
    assert semaforo.luz(_votos(1, 1)) is None


def test_mensaje_verde():
    votos = [
        Voto("RSI 28", 1, "sobrevendida, suele rebotar"),
        Voto("MACD", 0, "pierde empuje, sin dirección clara"),
        Voto("Bollinger", 1, "por debajo de su banda, más barata de lo normal"),
        Voto("Medias", -1, "por debajo de todas, tendencia a la baja"),
        Voto("Miedo 18", 1, "miedo extremo en el mercado, suele ser buen momento"),
    ]

    texto = formatear_semaforo("bitcoin", votos, VERDE, ["el funding"])

    assert texto.startswith("🟢 <b>Bitcoin</b>: luz verde")
    assert "3 a favor · 1 en contra · 1 en medio" in texto
    assert "✅ <b>RSI 28</b>: sobrevendida, suele rebotar" in texto
    assert "❌ <b>Medias</b>: por debajo de todas" in texto
    assert "⚪ <b>MACD</b>: pierde empuje" in texto
    assert "Sin datos de el funding" in texto
    assert "no es un consejo" in texto


def test_mensaje_rojo_y_ambar():
    assert formatear_semaforo("solana", _votos(-1, -1, -1), ROJO, []).startswith(
        "🔴 <b>Solana</b>: luz roja"
    )
    ambar = formatear_semaforo("solana", _votos(1, -1, 0), AMBAR, [])
    assert ambar.startswith("🟡 <b>Solana</b>: luz ámbar")
    assert "Sin datos" not in ambar
