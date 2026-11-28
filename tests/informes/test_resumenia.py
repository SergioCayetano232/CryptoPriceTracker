"""Tests de /resumenia, sin llamar a la API de verdad."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from crypto_tracker.informes import resumenia
from crypto_tracker.informes.semanal import Semana

AHORA = datetime(2026, 11, 27, 12, tzinfo=timezone.utc)


def _semana():
    serie = [(AHORA - timedelta(days=7), 1000.0), (AHORA, 1100.0)]
    return Semana(serie, [("solana", 25.0), ("bitcoin", -2.5)])


class _Falso:
    """Hace de cliente de Anthropic: apunta lo que le piden y contesta lo que toque."""

    def __init__(self, respuesta=None, error=None):
        self.pedido = None
        self.respuesta = respuesta
        self.error = error
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.pedido = kwargs
        if self.error:
            raise self.error
        return self.respuesta


def _contesta(texto, stop_reason="end_turn"):
    bloques = [SimpleNamespace(type="thinking", thinking="")]
    if texto is not None:
        bloques.append(SimpleNamespace(type="text", text=texto))
    return SimpleNamespace(stop_reason=stop_reason, content=bloques)


def _error_http(clase, codigo):
    peticion = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    return clase("mal", response=httpx2.Response(codigo, request=peticion), body=None)


def test_datos_lleva_la_semana_y_el_peso_de_cada_una():
    texto = resumenia.datos(_semana(), "eur", {"solana": 40.0, "bitcoin": 60.0})

    assert "Valor de la cartera al empezar la semana: 1000.00 EUR" in texto
    assert "Cambio: +100.00 EUR (+10.00 %)" in texto
    assert "- solana: +25.00 %, 40.0 % de la cartera" in texto
    assert "- bitcoin: -2.50 %, 60.0 % de la cartera" in texto


def test_escribir_pide_a_claude_con_lo_que_toca():
    falso = _Falso(_contesta("  Tu cartera ha subido un 10 %.  "))

    frases = resumenia.escribir("los datos", falso)

    assert frases == "Tu cartera ha subido un 10 %."
    assert falso.pedido["model"] == "claude-opus-5-5"
    assert falso.pedido["messages"] == [{"role": "user", "content": "los datos"}]
    assert falso.pedido["fallbacks"] == "default"
    assert falso.pedido["output_config"] == {"effort": "low"}


def test_si_claude_se_niega_lo_dice():
    with pytest.raises(resumenia.ResumenIAError, match="no ha querido"):
        resumenia.escribir("x", _Falso(_contesta(None, "refusal")))


def test_respuesta_en_blanco():
    with pytest.raises(resumenia.ResumenIAError, match="en blanco"):
        resumenia.escribir("x", _Falso(_contesta("   ")))


@pytest.mark.parametrize(
    ("error", "mensaje"),
    [
        (_error_http(anthropic.AuthenticationError, 401), "no vale"),
        (_error_http(anthropic.RateLimitError, 429), "demasiadas peticiones"),
        (_error_http(anthropic.InternalServerError, 500), r"ha fallado \(500\)"),
        (anthropic.AnthropicError("otra cosa"), "No he podido"),
    ],
)
def test_los_errores_salen_explicados(error, mensaje):
    with pytest.raises(resumenia.ResumenIAError, match=mensaje):
        resumenia.escribir("x", _Falso(error=error))


def test_sin_clave_lo_dice_sin_llamar(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)

    with pytest.raises(resumenia.ResumenIAError, match="ANTHROPIC_API_KEY"):
        resumenia.escribir("x")
