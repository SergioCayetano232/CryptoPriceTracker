"""/glosario: lo que significan las palabras raras del mundo cripto."""

import difflib

TERMINOS = {
    "HODL": "Aguantar sin vender pase lo que pase. Viene de un «hold» mal "
    "escrito en un foro en 2013.",
    "FOMO": "El miedo a quedarte fuera: comprar porque sube y lo compra todo el mundo.",
    "FUD": "Miedo, incertidumbre y duda. Noticias o rumores que hacen que la "
    "gente venda.",
    "DCA": "Meter la misma cantidad cada cierto tiempo, sin mirar el precio. "
    "Pruébalo con /dca.",
    "ATH": "El máximo histórico, lo más alto que ha estado nunca. Míralo con /ath.",
    "DYOR": "«Investiga tú mismo». No compres algo solo porque te lo diga alguien.",
    "sat": "La cien millonésima parte de un bitcoin. Lo que vale, en /sat.",
    "halving": "Cada unos cuatro años se paga la mitad por minar un bloque de "
    "Bitcoin. Cuánto falta, en /halving.",
    "ballena": "Alguien con tanta cripto que mueve el precio cuando compra o vende.",
    "altcoin": "Cualquier cripto que no sea Bitcoin.",
    "stablecoin": "Una cripto atada a una moneda normal, como USDT o USDC al dólar.",
    "bull": "Mercado alcista: lleva tiempo subiendo y la gente está animada.",
    "bear": "Mercado bajista: lleva tiempo bajando y nadie quiere comprar.",
    "rekt": "Arruinado después de una mala operación.",
}

# Como lo puede escribir alguien que no sabe el nombre exacto.
SINONIMOS = {
    "hold": "HODL",
    "satoshi": "sat",
    "sats": "sat",
    "whale": "ballena",
    "alt": "altcoin",
    "altcoins": "altcoin",
    "estable": "stablecoin",
    "estables": "stablecoin",
    "stable": "stablecoin",
    "alcista": "bull",
    "bajista": "bear",
}

_POR_MINUSCULA = {t.lower(): t for t in TERMINOS}


def buscar(palabra: str) -> str | None:
    """El término tal cual sale en TERMINOS, o None si no lo conozco."""
    palabra = palabra.strip().lower()
    return SINONIMOS.get(palabra) or _POR_MINUSCULA.get(palabra)


def parecido(palabra: str) -> str | None:
    # Igual que con los comandos: por debajo de 0.75 sugiere cosas sin relación.
    cerca = difflib.get_close_matches(
        palabra.strip().lower(), [*_POR_MINUSCULA, *SINONIMOS], n=1, cutoff=0.75
    )
    return buscar(cerca[0]) if cerca else None
