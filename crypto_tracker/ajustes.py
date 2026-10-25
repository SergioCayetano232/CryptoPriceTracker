"""/ajustes: lo que tienes puesto en el .env, sin tener que entrar a mirarlo."""

from datetime import timedelta

from .config import Config
from .salud import _cada, _duracion


def lineas(config: Config) -> list[str]:
    """config tiene que venir ya con lo cambiado por Telegram, o el resumen miente."""
    texto = [
        f"💱 Precios en {config.vs_currency.upper()}",
        f"⏱️ Consulto cada {_cada(config.check_interval)}",
    ]

    if config.history_days:
        texto.append(f"💾 Guardo {config.history_days} días de precios")
    else:
        texto.append("💾 Guardo todos los precios, no borro nada")

    if config.resumen_diario:
        texto.append(f"📰 Resumen cada día a las {config.resumen_diario:%H:%M}")
    else:
        texto.append("📰 Sin resumen diario")

    if config.brusco_porcentaje:
        tramo = _duracion(timedelta(minutes=config.brusco_minutos))
        pct = f"{config.brusco_porcentaje:g}".replace(".", ",")
        texto.append(f"⚡ Aviso si se mueve un {pct}% en {tramo}")
    else:
        texto.append("⚡ Sin aviso de movimientos bruscos")

    if config.extremos_dias:
        texto.append(f"📈 Aviso de máximos y mínimos de {config.extremos_dias} días")
    else:
        texto.append("📈 Sin aviso de máximos y mínimos")

    if config.horas_tranquilas:
        inicio, fin = config.horas_tranquilas
        texto.append(f"🌙 Sin sonar de {inicio:%H:%M} a {fin:%H:%M}")
    else:
        texto.append("🌙 Los avisos suenan siempre")

    return texto


def mensaje(config: Config) -> str:
    return "\n".join(
        [
            "⚙️ <b>Tus ajustes</b>",
            "",
            *lineas(config),
            "",
            "<i>Se cambian en el .env. El resumen, también con /horario</i>",
        ]
    )
