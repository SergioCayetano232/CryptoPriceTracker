"""/apodo: un mote para ti según cómo llevas la cartera."""

from dataclasses import dataclass

COLECCIONISTA = 6  # criptos distintas
COMPULSIVO = 10  # compras apuntadas
DIAMANTE = 365  # días desde la primera compra sin vender nada


@dataclass(frozen=True)
class Perfil:
    criptos: list[str]  # las que tienes ahora
    compras: int
    ventas: int
    dias: int | None  # desde la primera compra apuntada
    cambio: float | None  # lo que gana o pierde la cartera, en %


def elegir(p: Perfil) -> tuple[str, str, str]:
    """(emoji, mote, el porqué). Gana la primera regla que se cumpla."""
    if not p.criptos:
        return "👀", "El Mirón", "No tienes nada, solo miras"
    if p.cambio is not None and p.cambio <= -50:
        return "🏔️", "Comprador de picos", f"Tu cartera va {p.cambio:+.0f}%"
    if p.cambio is not None and p.cambio >= 100:
        return "🔮", "El Visionario", f"Tu cartera va {p.cambio:+.0f}%"
    if p.ventas > p.compras:
        return (
            "🧻",
            "Manos de papel",
            f"Has vendido {p.ventas} veces y comprado {p.compras}",
        )
    if p.criptos == ["bitcoin"]:
        return "🟠", "Maximalista", "Solo tienes bitcoin, lo demás es ruido"
    if len(p.criptos) >= COLECCIONISTA:
        return "🃏", "El Coleccionista", f"Tienes {len(p.criptos)} criptos distintas"
    if not p.ventas and p.dias is not None and p.dias >= DIAMANTE:
        return "💎", "Manos de diamante", f"{p.dias} días sin vender nada"
    if p.compras >= COMPULSIVO:
        return "🛒", "Comprador compulsivo", f"Llevas {p.compras} compras apuntadas"
    return "🐢", "Hodler tranquilo", "Ni muchas compras ni muchas ventas, a tu ritmo"
