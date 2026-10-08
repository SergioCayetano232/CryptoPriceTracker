"""/mercado: lo que vale todo el mercado cripto y cuanto es de Bitcoin."""

import math
from dataclasses import dataclass

# Las dos estables grandes; juntas dicen cuanto dinero esta "aparcado".
ESTABLES = ("usdt", "usdc")


@dataclass(frozen=True)
class Mercado:
    total: float | None
    variacion: float | None  # en 24 h
    bitcoin: float | None  # % del total
    ethereum: float | None
    estables: float | None


def leer(datos, currency: str) -> Mercado:
    data = datos.get("data") if isinstance(datos, dict) else None
    data = data if isinstance(data, dict) else {}
    totales = data.get("total_market_cap")
    partes = data.get("market_cap_percentage")
    totales = totales if isinstance(totales, dict) else {}
    partes = partes if isinstance(partes, dict) else {}

    estables = [_numero(partes.get(e)) for e in ESTABLES]
    return Mercado(
        _numero(totales.get(currency.lower())),
        # Solo viene en dolares. En euros cambia unas decimas, no vale otra consulta.
        _numero(data.get("market_cap_change_percentage_24h_usd")),
        _numero(partes.get("btc")),
        _numero(partes.get("eth")),
        sum(estables) if None not in estables else None,
    )


def grande(valor: float) -> str:
    """2.507.117.360.729 -> '2,51 billones'; 850.000.000.000 -> '850.000 millones'."""
    if valor >= 1e12:
        return f"{valor / 1e12:.2f} billones".replace(".", ",")
    return f"{valor / 1e6:,.0f} millones".replace(",", ".")


def _numero(valor) -> float | None:
    if isinstance(valor, (int, float)) and math.isfinite(valor):
        return float(valor)
    return None
