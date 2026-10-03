"""/convertir: de cripto a dinero y al reves, al precio de ahora."""

from dataclasses import dataclass

from .alerts import SIMBOLOS
from .puntuales import numero

EJEMPLOS = "/convertir 0.05 bitcoin o /convertir 500 eur solana"

# Como lo escribe uno, ademas del codigo y el simbolo.
NOMBRES = {
    "eur": ("euro", "euros"),
    "usd": ("dolar", "dolares", "dólar", "dólares"),
    "gbp": ("libra", "libras"),
}

# "500 eur a solana" o "0.05 bitcoin en euros" se entienden igual.
RELLENO = {"a", "en"}


class ConvertirError(Exception):
    """Lo que escribiste en /convertir no se entiende."""


@dataclass(frozen=True)
class Conversion:
    cantidad: float
    coin_id: str
    desde_dinero: bool  # True si das dinero y quieres saber cuanta cripto es

    def resultado(self, precio: float) -> float:
        return self.cantidad / precio if self.desde_dinero else self.cantidad * precio


def interpretar(argumento: str, currency: str) -> Conversion:
    partes = [p for p in argumento.lower().split() if p not in RELLENO]
    _otra_moneda(partes, currency)
    monedas = _monedas(currency)

    # 500€ o €500 pegado: se separa para que quede igual que "500 €"
    if partes and partes[0] not in monedas:
        for m in monedas:
            if len(m) == 1 and m in partes[0] and partes[0] != m:
                partes[:1] = [partes[0].strip(m), m]
                break

    desde_dinero = len(partes) == 3 and partes[1] in monedas
    if desde_dinero:
        partes.pop(1)
    elif len(partes) == 3 and partes[2] in monedas:
        partes.pop(2)  # "0.05 bitcoin en euros" es lo mismo que sin "en euros"

    if len(partes) != 2:
        raise ConvertirError(f"Escríbelo así: {EJEMPLOS}")

    cantidad = numero(partes[0])
    if cantidad is None or cantidad <= 0:
        raise ConvertirError(f"'{partes[0]}' no es una cantidad. Ej: {EJEMPLOS}")
    return Conversion(cantidad, partes[1], desde_dinero)


def _monedas(currency: str) -> set[str]:
    currency = currency.lower()
    monedas = {currency, *NOMBRES.get(currency, ())}
    if currency in SIMBOLOS:
        monedas.add(SIMBOLOS[currency])
    return monedas


def _otra_moneda(partes: list[str], currency: str) -> None:
    """Si has puesto dolares y los precios van en euros, que se diga claro."""
    for otra, simbolo in SIMBOLOS.items():
        if otra == currency.lower():
            continue
        # Sin esto, "500$ solana" se leeria como 500 solanas.
        if set(partes) & {otra, *NOMBRES[otra]} or any(simbolo in p for p in partes):
            raise ConvertirError(
                f"Los precios los miro en {currency.upper()}, no en {otra.upper()}."
            )
