"""El icono del panel instalado como app en el móvil."""

import io
from functools import cache

from PIL import Image, ImageDraw

FONDO = "#6d4aff"
# La línea que sube del icono de la pestaña, en una caja de 32.
PUNTOS = [(7, 22), (13, 15), (18, 19), (25, 10)]
# Android recorta el icono en círculo o en lo que quiera: el dibujo va en el
# centro y el color llega hasta el borde. iOS le pone las esquinas él.
MARGEN = 0.2
# Se pinta a lo grande y se encoge: así los bordes salen suaves.
AUMENTO = 4


@cache
def png(lado: int) -> bytes:
    grande = lado * AUMENTO
    imagen = Image.new("RGB", (grande, grande), FONDO)
    dibujo = ImageDraw.Draw(imagen)
    borde, dentro = grande * MARGEN, grande * (1 - 2 * MARGEN)
    # De 7..25 en la caja de 32 a todo el hueco de dentro.
    puntos = [
        (borde + (x - 7) / 18 * dentro, borde + (y - 7) / 18 * dentro)
        for x, y in PUNTOS
    ]
    grosor = round(grande * 0.07)
    dibujo.line(puntos, fill="white", width=grosor, joint="curve")
    # Las puntas redondas, que line() las deja cuadradas.
    for x, y in (puntos[0], puntos[-1]):
        r = grosor / 2
        dibujo.ellipse((x - r, y - r, x + r, y + r), fill="white")

    salida = io.BytesIO()
    imagen.resize((lado, lado), Image.LANCZOS).save(salida, "PNG", optimize=True)
    return salida.getvalue()
