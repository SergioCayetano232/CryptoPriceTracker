"""/herencia: lo que tienes y dónde, para tu familia, sin ninguna clave."""

import re
from dataclasses import dataclass
from datetime import date

from ..avisos.recordar import QUITAR
from ..nucleo.simbolos import a_id

EJEMPLO = "/herencia btc Ledger en el cajón del escritorio"
EJEMPLO_NOTA = "/herencia nota Pregunta a mi hermana, sabe dónde está todo"
MAX = 200

# Una frase de recuperación son 12 o 24 palabras en inglés, todas de 3 a 8 letras.
# Una frase normal en español casi siempre lleva "el", "en", "de"... o tildes.
_PALABRA_SEMILLA = re.compile(r"[a-z]{3,8}")
_MIN_PALABRAS = 12
# Las claves privadas sueltas son largas: 51-52 en WIF, 64 en hexadecimal.
# Las direcciones bc1 pueden llegar a 62 y son públicas, así que esas pasan.
_LARGO_CLAVE = 50
_EXTENDIDAS = ("xprv", "yprv", "zprv", "tprv")


class HerenciaError(Exception):
    """Lo que escribiste en /herencia no se entiende o no se puede guardar."""


@dataclass(frozen=True)
class Linea:
    coin_id: str
    cantidad: float
    valor: float | None  # al precio de hoy; None si no hay precio
    donde: str | None


def parece_clave(texto: str) -> bool:
    """Si lo que quieres guardar tiene pinta de frase de recuperación o de clave."""
    palabras = texto.lower().split()
    if len(palabras) >= _MIN_PALABRAS and all(
        _PALABRA_SEMILLA.fullmatch(p) for p in palabras
    ):
        return True
    for p in texto.split():
        if p.lower().startswith(_EXTENDIDAS):
            return True
        if len(p) >= _LARGO_CLAVE and not p.lower().startswith("bc1"):
            return True
    return False


def interpretar(argumento: str) -> tuple:
    """('ver',), ('donde', id, texto o None) o ('nota', texto o None)."""
    partes = argumento.split(maxsplit=1)
    if not partes:
        return ("ver",)
    if len(partes) == 1:
        raise HerenciaError(f"Escríbelo así: {EJEMPLO}, o {EJEMPLO_NOTA}")

    primera, resto = partes[0].lower(), partes[1].strip()
    borrar = resto.lower() in QUITAR
    if not borrar:
        _comprobar(resto)
    if primera == "nota":
        return ("nota", None if borrar else resto)
    return ("donde", a_id(primera), None if borrar else resto)


def _comprobar(texto: str) -> None:
    if parece_clave(texto):
        raise HerenciaError(
            "⛔ Eso parece una frase de recuperación o una clave, y no la guardo. "
            "Aquí va solo DÓNDE está (en qué cajón, qué app, quién lo sabe), nunca "
            "la clave: este chat no es un sitio seguro para eso."
        )
    if len(texto) > MAX:
        raise HerenciaError(f"Es muy largo, como mucho {MAX} letras.")


def lineas(
    cartera: list,  # las Posicion de la cartera
    precios: dict[str, float],
    donde: dict[str, str],
) -> list[Linea]:
    """Lo que tienes, de lo que más vale a lo que menos."""
    lista = [
        Linea(
            p.coin_id,
            p.cantidad,
            p.cantidad * precios[p.coin_id] if p.coin_id in precios else None,
            donde.get(p.coin_id),
        )
        for p in cartera
        if p.cantidad > 0
    ]
    return sorted(lista, key=lambda x: -(x.valor or 0))


def nombre_archivo(hoy: date) -> str:
    return f"herencia-cripto-{hoy:%Y-%m-%d}.txt"
