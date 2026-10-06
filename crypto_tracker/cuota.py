"""Cuantas consultas llevamos a CoinGecko este mes y cuando avisar."""

from datetime import datetime, timezone

# Lo que da la clave Demo gratis al mes.
LIMITE = 10_000

# Al 80% aun hay tiempo de subir CHECK_INTERVAL; al 100% ya toca saberlo.
UMBRALES = (0.8, 1.0)


def mes(ahora: datetime) -> str:
    """'2026-10'. Contamos por mes natural en UTC."""
    return ahora.astimezone(timezone.utc).strftime("%Y-%m")


def umbral_cruzado(antes: int, total: int, limite: int = LIMITE) -> float | None:
    """El umbral que se acaba de pasar, si alguno. El mas alto si saltan dos."""
    for umbral in reversed(UMBRALES):
        if antes < umbral * limite <= total:
            return umbral
    return None


def proyeccion(total: int, ahora: datetime) -> int | None:
    """Con cuantas acabariamos el mes a este ritmo. None si es muy pronto."""
    ahora = ahora.astimezone(timezone.utc)
    inicio = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if inicio.month == 12:
        fin = inicio.replace(year=inicio.year + 1, month=1)
    else:
        fin = inicio.replace(month=inicio.month + 1)

    # El primer dia el ritmo aun no dice nada: un /buscar suelto lo dispara.
    transcurrido = (ahora - inicio) / (fin - inicio)
    if transcurrido < 1 / 30:
        return None
    return round(total / transcurrido)


def mensaje_aviso(
    total: int, umbral: float, ahora: datetime, limite: int = LIMITE
) -> str:
    """El aviso de que se esta acabando la cuota."""
    texto = [f"⚠️ <b>CryptoPriceTracker</b>\n{_llevas(total, limite)}"]

    if umbral >= 1:
        texto.append(
            "A partir de aquí CoinGecko puede cortarme hasta el día 1. "
            "Sube CHECK_INTERVAL en el .env para que no vuelva a pasar."
        )
    else:
        texto.append(_ritmo(total, ahora, limite))
    return "\n".join(t for t in texto if t)


def mensaje_estado(total: int, ahora: datetime, limite: int = LIMITE) -> str:
    """Respuesta de /consultas."""
    return "\n".join(
        t for t in (f"📡 {_llevas(total, limite)}", _ritmo(total, ahora, limite)) if t
    )


def corto(total: int, limite: int = LIMITE) -> str:
    """Una linea para /bot."""
    return (
        f"{_miles(total)} de {_miles(limite)} consultas a CoinGecko "
        f"este mes ({total / limite:.0%})"
    )


def _llevas(total: int, limite: int) -> str:
    return (
        f"Llevas {_miles(total)} de las {_miles(limite)} consultas a CoinGecko "
        f"de este mes ({total / limite:.0%})."
    )


def _ritmo(total: int, ahora: datetime, limite: int) -> str:
    final = proyeccion(total, ahora)
    if final is None:
        return ""
    if final > limite:
        return (
            f"A este ritmo acabarías el mes en unas {_miles(final)}: "
            "sube CHECK_INTERVAL para no quedarte sin precios."
        )
    return f"A este ritmo acabarías en unas {_miles(final)}, vas bien."


def _miles(n: int) -> str:
    return f"{n:,}".replace(",", ".")
