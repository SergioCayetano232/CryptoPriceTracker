"""Invitados: otra gente usando tu bot, cada uno con su archivo y sus cosas."""

import re
import secrets
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from pathlib import Path

from .config import Config

# Cada invitado gasta consultas de tu clave de CoinGecko.
MAX_INVITADOS = 10
CADUCA = timedelta(hours=24)

# Sin 0/O ni 1/I/L, que dictados por teléfono se confunden.
LETRAS = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
LARGO = 8

# Los que tiran de tus claves o de tu servidor, o mandan sobre los demás.
SOLO_DUEÑO = {"invitar", "usuarios", "expulsar", "binance", "consultas"}

SOLO_TUYO = "Eso solo lo puede usar quien lleva el bot."

# Solo números (y el - de los grupos): va en el nombre de un archivo.
_CHAT = re.compile(r"-?\d{1,20}")


class UsuarioError(Exception):
    """El código no vale o no cabe nadie más."""


@dataclass(frozen=True)
class Invitado:
    chat_id: str
    nombre: str | None
    alta: datetime


def es_chat(texto: str) -> bool:
    return bool(_CHAT.fullmatch(texto))


def codigo() -> str:
    return "".join(secrets.choice(LETRAS) for _ in range(LARGO))


def leer_codigo(argumento: str) -> str | None:
    """Lo que viene tras /start. Lo paso a mayúsculas: el móvil pone la primera."""
    texto = argumento.strip().upper()
    if len(texto) == LARGO and all(c in LETRAS for c in texto):
        return texto
    return None


def archivo(config: Config, chat_id: str) -> str:
    """data/usuarios/<chat>.db, junto a la tuya."""
    if not es_chat(chat_id):
        raise ValueError(f"No es un chat: {chat_id!r}")
    return str(Path(config.database_path).parent / "usuarios" / f"{chat_id}.db")


def config_de(config: Config, chat_id: str) -> Config:
    """Tu config, pero con su archivo y su chat. Empieza sin nada: lo que pone tu
    .env en WATCHLIST y PORTFOLIO es tuyo, no suyo."""
    return replace(
        config,
        telegram_chat_id=chat_id,
        database_path=archivo(config, chat_id),
        watchlist=[],
        cartera=(),
        invitado=True,
    )


def nombre(remitente: dict) -> str | None:
    """'Ana (@ana_btc)' con lo que Telegram diga de quien escribe."""
    pila = (remitente.get("first_name") or "").strip()
    usuario = (remitente.get("username") or "").strip()
    if pila and usuario:
        return f"{pila} (@{usuario})"
    return pila or (f"@{usuario}" if usuario else None)


def comprobar_hueco(cuantos: int) -> None:
    if cuantos >= MAX_INVITADOS:
        raise UsuarioError(
            f"El bot ya tiene {MAX_INVITADOS} invitados, que es lo máximo. "
            "Pídele a quien lo lleva que haga hueco."
        )


def caducidad(ahora: datetime) -> datetime:
    return ahora + CADUCA
