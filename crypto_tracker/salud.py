"""Se da cuenta de cuando el bot lleva un rato sin poder hacer su trabajo."""

from datetime import datetime, timedelta, timezone

from .telegram import escape

# Un fallo suelto es ruido, CoinGecko corta un momento y a la siguiente va.
# Media hora seguida sin precios ya merece un mensaje.
MINUTOS_PARA_AVISAR = 30


class Pulso:
    """Lleva la cuenta de cuanto llevamos fallando y dice cuando avisar."""

    def __init__(self, minutos: int = MINUTOS_PARA_AVISAR):
        self.margen = timedelta(minutes=minutos)
        self.fallando_desde: datetime | None = None
        self.avisado = False

    def fallo(self, error: str, ahora: datetime | None = None) -> str | None:
        """Apunta un ciclo fallido. Devuelve el mensaje si toca mandarlo."""
        ahora = ahora or datetime.now(timezone.utc)
        if self.fallando_desde is None:
            self.fallando_desde = ahora

        caido = ahora - self.fallando_desde
        # Una vez por caida, no un mensaje cada cinco minutos.
        if self.avisado or caido < self.margen:
            return None

        self.avisado = True
        return (
            "⚠️ <b>CryptoPriceTracker</b>\n"
            f"Llevo {_duracion(caido)} sin poder consultar los precios, "
            "así que ahora mismo no te avisaría de nada.\n"
            f"Último error: <i>{escape(error)}</i>"
        )

    def exito(self, ahora: datetime | None = None) -> str | None:
        """Apunta un ciclo bueno. Si antes avisamos de la caida, dice que ya va."""
        ahora = ahora or datetime.now(timezone.utc)
        desde, avisado = self.fallando_desde, self.avisado
        self.fallando_desde = None
        self.avisado = False

        if not avisado:
            return None

        return (
            "✅ <b>CryptoPriceTracker</b>\n"
            f"Vuelvo a funcionar tras {_duracion(ahora - desde)} sin precios."
        )


def mensaje_parado(fallos: int, error: str) -> str:
    """El ultimo mensaje antes de que el bucle se rinda."""
    return (
        "🛑 <b>CryptoPriceTracker</b>\n"
        f"Me he parado tras {fallos} errores seguidos.\n"
        f"Último error: <i>{escape(error)}</i>"
    )


def _duracion(tiempo: timedelta) -> str:
    minutos = int(tiempo.total_seconds() // 60)
    if minutos < 60:
        return f"{minutos} min"

    horas, resto = divmod(minutos, 60)
    return f"{horas} h {resto} min" if resto else f"{horas} h"
