"""Pilla subidas o caidas fuertes en poco tiempo, crucen o no algun nivel."""

from .alerts import ALTO, BAJO, Alert


def revisar(
    coin_id: str, precios: list[float], porcentaje: float, minutos: int
) -> Alert | None:
    """Mira los precios de la ventana, del mas viejo al de ahora."""
    if len(precios) < 2:
        return None

    ahora = precios[-1]
    techo, suelo = max(precios), min(precios)

    # Contra el maximo y el minimo, no contra el primero: si sube un 10% y
    # luego lo devuelve todo, esa caida tambien cuenta.
    caida = (ahora - techo) / techo * 100 if techo else 0.0
    subida = (ahora - suelo) / suelo * 100 if suelo else 0.0

    if caida <= -porcentaje:
        return Alert(coin_id, ahora, techo, BAJO, percent=caida, minutos=minutos)
    if subida >= porcentaje:
        return Alert(coin_id, ahora, suelo, ALTO, percent=subida, minutos=minutos)
    return None
