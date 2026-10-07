"""Se da cuenta de cuando el bot lleva un rato sin poder hacer su trabajo."""

from datetime import datetime, timedelta, timezone

from . import cuota
from .telegram import escape

# Un fallo suelto es ruido, CoinGecko corta un momento y a la siguiente va.
# Media hora seguida sin precios ya merece un mensaje.
MINUTOS_PARA_AVISAR = 30


class Pulso:
    """Lleva la cuenta de cuanto llevamos fallando y dice cuando avisar."""

    def __init__(
        self, minutos: int = MINUTOS_PARA_AVISAR, ahora: datetime | None = None
    ):
        self.margen = timedelta(minutes=minutos)
        self.fallando_desde: datetime | None = None
        self.avisado = False
        # Para /bot: desde cuando esta encendido y cuando trajo precios por ultima vez.
        self.arrancado = ahora or datetime.now(timezone.utc)
        self.ultimo_bien: datetime | None = None

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
        self.ultimo_bien = ahora
        desde, avisado = self.fallando_desde, self.avisado
        self.fallando_desde = None
        self.avisado = False

        if not avisado:
            return None

        return (
            "✅ <b>CryptoPriceTracker</b>\n"
            f"Vuelvo a funcionar tras {_duracion(ahora - desde)} sin precios."
        )


def mensaje_bot(
    pulso: Pulso,
    ahora: datetime,
    vigiladas: int,
    alertas: int,
    callado: datetime | None = None,
    consultas: int | None = None,
) -> str:
    """Respuesta de /bot: si sigue vivo y desde cuando."""
    texto = [
        "🤖 <b>CryptoPriceTracker</b>",
        f"Encendido desde hace {cuanto(ahora - pulso.arrancado)} "
        f"({pulso.arrancado.astimezone():%d/%m a las %H:%M})",
    ]

    if pulso.ultimo_bien is None:
        texto.append("Aún no he terminado ningún ciclo.")
    else:
        texto.append(f"Último ciclo bueno: hace {cuanto(ahora - pulso.ultimo_bien)}")
    # El ultimo bueno puede ser de hace nada y llevar fallando desde entonces.
    if pulso.fallando_desde is not None:
        texto.append(
            f"⚠️ Las consultas fallan desde hace {cuanto(ahora - pulso.fallando_desde)}"
        )

    texto.append(
        f"Vigilo {vigiladas} {'cripto' if vigiladas == 1 else 'criptos'} · "
        f"{alertas} {'alerta puesta' if alertas == 1 else 'alertas puestas'}"
    )
    if consultas is not None:
        texto.append(f"📡 {cuota.corto(consultas)}")
    if callado is not None:
        texto.append(f"🔕 Callado hasta las {callado.astimezone():%H:%M del %d/%m}")
    return "\n".join(texto)


def mensaje_encendido(
    vigiladas: int, intervalo: int, ultimo: datetime | None, ahora: datetime
) -> str:
    """Al arrancar --loop. ultimo es el ultimo precio guardado, si hay alguno."""
    texto = [
        "🟢 <b>CryptoPriceTracker</b>",
        f"Encendido: vigilo {vigiladas} {'cripto' if vigiladas == 1 else 'criptos'} "
        f"cada {_cada(intervalo)}.",
    ]
    # Un par de ciclos sin precio es un reinicio normal; mas, es que estuvo caido.
    if ultimo is not None and ahora - ultimo > timedelta(seconds=intervalo * 2):
        texto.append(
            f"Llevaba apagado desde el {ultimo.astimezone():%d/%m a las %H:%M} "
            f"({cuanto(ahora - ultimo)})."
        )
    return "\n".join(texto)


def mensaje_parado(fallos: int, error: str) -> str:
    """El ultimo mensaje antes de que el bucle se rinda."""
    return (
        "🛑 <b>CryptoPriceTracker</b>\n"
        f"Me he parado tras {fallos} errores seguidos.\n"
        f"Último error: <i>{escape(error)}</i>"
    )


def sin_precio(
    pedidas: list[str], precios: dict[str, float], avisadas: set[str]
) -> list[str]:
    """Las que CoinGecko no conoce y de las que aun no hemos dicho nada."""
    return [c for c in pedidas if c not in precios and c not in avisadas]


def mensaje_sin_precio(coin_ids: list[str], todas: bool = False) -> str:
    """Aviso de ids que no devuelven precio. Casi siempre es un dedazo."""
    nombres = ", ".join(f"<b>{escape(c)}</b>" for c in coin_ids)
    esa = "esas" if len(coin_ids) > 1 else "esa"
    texto = (
        "⚠️ <b>CryptoPriceTracker</b>\n"
        f"CoinGecko no me da precio de {nombres}, así que de {esa} no te "
        "voy a avisar.\n"
        f"Suele ser el id mal escrito. Búscalo con /buscar {escape(coin_ids[0])} "
        "y corrígelo en WATCHLIST."
    )
    # Si no viene ninguna, lo raro es que esten todas mal: suele ser la moneda.
    if todas:
        texto += "\nComo no me llega ninguna, revisa también VS_CURRENCY."
    return texto


def cuanto(tiempo: timedelta) -> str:
    """Como _duracion, pero en dias cuando pasa de uno: '3 d 4 h' y no '76 h'."""
    # Justo despues de arrancar, un "0 min" parece que algo va mal.
    if tiempo < timedelta(minutes=1):
        return "menos de un minuto"
    dias = tiempo.days
    if dias < 1:
        return _duracion(tiempo)
    horas = tiempo.seconds // 3600
    return f"{dias} d {horas} h" if horas else f"{dias} d"


def _cada(segundos: int) -> str:
    """330 -> '5 min 30 s'."""
    minutos, resto = divmod(segundos, 60)
    if not minutos:
        return f"{resto} s"
    return f"{minutos} min {resto} s" if resto else f"{minutos} min"


def _duracion(tiempo: timedelta) -> str:
    minutos = int(tiempo.total_seconds() // 60)
    if minutos < 60:
        return f"{minutos} min"

    horas, resto = divmod(minutos, 60)
    return f"{horas} h {resto} min" if resto else f"{horas} h"
