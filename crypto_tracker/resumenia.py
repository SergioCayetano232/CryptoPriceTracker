"""/resumenia: tu semana contada en cuatro frases por Claude, con tus datos."""

import logging
import os

import anthropic

from .semanal import Semana

logger = logging.getLogger("crypto_tracker")

MODELO = "claude-opus-5-5"

INSTRUCCIONES = """\
Escribes el resumen semanal de la cartera de criptomonedas de una persona, que le \
llega por Telegram. Te paso los datos de su semana.

Escribe cuatro frases en español de España, tuteando: cuánto ha cambiado la \
cartera, qué cripto la ha movido más (cuenta su peso, no solo su cambio) y algo \
que llame la atención del reparto o de cómo se ha movido.

Usa solo los datos que te paso. No conoces las noticias de la semana, así que no \
expliques los movimientos con causas de fuera. No des consejos de comprar o \
vender. Texto plano, sin títulos, listas ni markdown. Cifras con coma decimal y \
punto de miles, como en España."""


SIN_CLAVE = (
    "Para esto necesito una clave de Claude: ponla en ANTHROPIC_API_KEY del .env "
    "(se saca en platform.claude.com)."
)


class ResumenIAError(Exception):
    """Algo ha fallado al pedírselo a Claude. El mensaje es para el usuario."""


def datos(semana: Semana, moneda: str, pesos: dict[str, float]) -> str:
    """Lo que le paso a Claude, en texto: nada que no salga de tus precios."""
    m = moneda.upper()
    lineas = [
        f"Valor de la cartera al empezar la semana: {semana.inicio:.2f} {m}",
        f"Valor ahora: {semana.fin:.2f} {m}",
        f"Cambio: {semana.ganancia:+.2f} {m} ({semana.porcentaje or 0:+.2f} %)",
        "",
        "Cada cripto (cambio en la semana, y qué parte de la cartera es ahora):",
    ]
    for coin_id, cambio in semana.cambios:
        peso = pesos.get(coin_id)
        parte = f", {peso:.1f} % de la cartera" if peso is not None else ""
        lineas.append(f"- {coin_id}: {cambio:+.2f} %{parte}")
    return "\n".join(lineas)


def escribir(texto: str, cliente: anthropic.Anthropic | None = None) -> str:
    """Las frases de Claude, o ResumenIAError con algo que enseñar."""
    # Sin clave, la librería no da un error suyo sino un TypeError al llamar: mejor
    # mirarlo antes y decir qué falta.
    if cliente is None and not (
        os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")
    ):
        raise ResumenIAError(SIN_CLAVE)
    try:
        cliente = cliente or anthropic.Anthropic()
        respuesta = cliente.beta.messages.create(
            model=MODELO,
            max_tokens=16000,
            # Resumir cuatro frases no necesita pensar mucho: más rápido y más barato.
            output_config={"effort": "low"},
            # Si lo rechazara por error, que lo intente otro modelo en la misma llamada.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=INSTRUCCIONES,
            messages=[{"role": "user", "content": texto}],
        )
    except anthropic.AuthenticationError as e:
        raise ResumenIAError(
            "La clave de Claude no vale. Revisa ANTHROPIC_API_KEY en el .env."
        ) from e
    except anthropic.RateLimitError as e:
        raise ResumenIAError(
            "Claude tiene demasiadas peticiones ahora. Prueba en un rato."
        ) from e
    except anthropic.APIStatusError as e:
        logger.error("La API de Claude ha fallado: %s %s", e.status_code, e.message)
        raise ResumenIAError(f"La API de Claude ha fallado ({e.status_code}).") from e
    except anthropic.APIConnectionError as e:
        raise ResumenIAError("No he podido conectar con la API de Claude.") from e
    except anthropic.AnthropicError as e:
        logger.warning("Sin poder llamar a Claude: %s", e)
        raise ResumenIAError("No he podido pedírselo a Claude.") from e

    if respuesta.stop_reason == "refusal":
        raise ResumenIAError("Claude no ha querido escribirlo esta vez.")
    frases = "".join(b.text for b in respuesta.content if b.type == "text").strip()
    if not frases:
        raise ResumenIAError("Claude ha contestado en blanco. Prueba otra vez.")
    return frases
