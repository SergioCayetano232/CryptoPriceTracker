"""/copia: lo que vigila y lo que tienes, escrito como va en el .env."""

from datetime import time

from .config import Posicion, Watch


def numero(valor: float) -> str:
    """Con punto y sin ceros de más, que es lo que lee el .env: 0.016, 75000."""
    return f"{valor:.8f}".rstrip("0").rstrip(".")


def regla(w: Watch) -> str:
    if w.percent is not None:
        return f"{w.coin_id}:%{numero(w.percent)}"
    if w.step is not None:
        return f"{w.coin_id}:{numero(w.step)}"
    # Un lado vacío es que ese no se vigila: ethereum::4000
    lados = ("" if x is None else numero(x) for x in (w.min_price, w.max_price))
    return f"{w.coin_id}:" + ":".join(lados)


def posicion(p: Posicion) -> str:
    texto = f"{p.coin_id}:{numero(p.cantidad)}"
    return texto if p.invertido is None else f"{texto}:{numero(p.invertido)}"


def lineas(
    watchlist: list[Watch], cartera: tuple[Posicion, ...], resumen: time | None
) -> list[str]:
    """Las líneas del .env que se pueden cambiar por Telegram."""
    return [
        "WATCHLIST=" + ",".join(regla(w) for w in watchlist),
        "PORTFOLIO=" + ",".join(posicion(p) for p in cartera),
        "RESUMEN_DIARIO=" + (f"{resumen:%H:%M}" if resumen else ""),
    ]
